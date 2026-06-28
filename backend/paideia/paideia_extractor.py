# paideia/paideia_extractor.py
import time
import re
import urllib.parse
import urllib.request
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class PaideiaExtractor:
    """
    Extractor de actividades académicas desde PAIDEIA PUCP.

    Estrategias previstas (según arquitectura del proyecto):
        - Web scraping con Selenium (actividades en línea)
        - Extracción PDF con pdfplumber (cronogramas adjuntos)
    """

    def __init__(self, driver, cronogramas_dir: Path | None = None):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        if cronogramas_dir is None:
            cronogramas_dir = Path.cwd() / "cronogramas_paideia"
        self.cronogramas_dir = cronogramas_dir
        self.cronogramas_dir.mkdir(parents=True, exist_ok=True)
        self.cronogramas_descargados: list[dict] = []
        self.cronogramas_urls_por_curso: dict[str, set[str]] = {}
        self.entregables_extraidos: list[dict] = []

    # ------------------------------------------------------------------
    # AUTENTICACIÓN
    # ------------------------------------------------------------------

    def login(self):
        """Abre Paideia y espera a que el usuario haga login manual."""
        self.driver.get("https://paideiacursos.pucp.edu.pe/my/courses.php")
        print("Ingresa tus credenciales en el navegador de Paideia…")
        deadline = time.time() + 300
        found = False
        while time.time() < deadline:
            try:
                if self.driver.find_elements(By.CLASS_NAME, "coursebox"):
                    print("Login detectado en Paideia (coursebox presente).")
                    found = True
                    break
                if self.driver.find_elements(By.CSS_SELECTOR, "input[id^='searchinput-'], div[role='search'], div.simplesearchform"):
                    print("Login detectado en Paideia (buscador presente).")
                    found = True
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not found:
            print("Advertencia: no se detectó el área de cursos ni el buscador tras el login (timeout). Continuando de todas formas.")

    def search_courses(self, query: str):
        """Introduce `query` en el buscador de cursos y ejecuta la búsqueda."""
        input_el = self._obtener_input_buscador()
        try:
            input_el.click()
        except Exception:
            pass

        last_error = None
        for intento in range(1, 4):
            try:
                self._escribir_buscador(input_el, query)
                self.esperar_resultados_busqueda(query, timeout=20)
                print(f"  Búsqueda ejecutada en Paideia: {query} (intento {intento})")
                return
            except Exception as e:
                last_error = e
                time.sleep(1)

        raise TimeoutError(f"No se cargaron resultados filtrados para {query}") from last_error

    def _obtener_input_buscador(self):
        """Obtiene el input visible del buscador de cursos."""
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='search'], div.simplesearchform"))
        )

        candidates = self.driver.find_elements(
            By.CSS_SELECTOR,
            "input[id^='searchinput-'], input[name='search'], input[placeholder*='Buscar'], input[type='text']",
        )

        for el in candidates:
            try:
                if el.is_displayed() and el.is_enabled():
                    return el
            except Exception:
                continue

        if candidates:
            return candidates[0]

        raise RuntimeError("No se encontró input del buscador en Paideia.")

    def _escribir_buscador(self, input_el, query: str):
        """Escribe la consulta en el buscador y dispara eventos para activar el filtro."""
        try:
            input_el.clear()
        except Exception:
            pass

        typed_ok = False
        try:
            for ch in query:
                input_el.send_keys(ch)
                time.sleep(0.05)
            typed_ok = True
        except Exception:
            typed_ok = False

        actual = (input_el.get_attribute("value") or "").strip()
        if (not typed_ok) or actual != query:
            script_set = "arguments[0].value = arguments[1];"
            self.driver.execute_script(script_set, input_el, query)

        script_events = (
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
            "arguments[0].dispatchEvent(new KeyboardEvent('keyup', {bubbles: true, key: '2'}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));"
        )
        self.driver.execute_script(script_events, input_el)

    def esperar_resultados_busqueda(self, query: str, timeout: int = 30):
        """Espera hasta que la vista de cursos muestre resultados cuyo título contenga `query`."""
        deadline = time.time() + timeout
        q = query.strip().lower()
        while time.time() < deadline:
            cursos = self.obtener_lista_cursos(query=query)
            if cursos:
                print(f"  Resultados filtrados listos: {len(cursos)}")
                return cursos
            try:
                inp = self._obtener_input_buscador()
                val = (inp.get_attribute("value") or "").strip().lower()
                if val != q:
                    self._escribir_buscador(inp, query)
            except Exception:
                pass
            time.sleep(0.5)

        raise TimeoutError(f"No se cargaron resultados filtrados para {query}")

    def buscar_por_ciclo(self, ciclo: int, anio: int) -> bool:
        """Construye la cadena `AAAA-C` e inserta en el buscador."""
        query = f"{anio}-{ciclo}"
        print(f"Iniciando búsqueda por ciclo en Paideia: {query}")
        self.search_courses(query)
        return True

    # ------------------------------------------------------------------
    # EXTRACCIÓN
    # ------------------------------------------------------------------

    def extraer_eventos(self, ciclo: int, anio: int, callback=None) -> list[dict]:
        """
        Punto de entrada principal.
        Devuelve lista de dicts con el mismo esquema que CampusCalendarioIcs.

        callback: función opcional que se llama después de procesar cada curso.
            Firma: callback(curso_info: dict)
            Donde curso_info contiene:
                - titulo: str
                - course_id: str
                - secciones: int
                - entregas: int
                - pdfs: int
                - idx: int        (índice 0-based del curso actual)
                - total: int      (total de cursos)
        """
        self.entregables_extraidos = []

        cursos = []
        try:
            cursos = self.obtener_lista_cursos(query=f"{anio}-{ciclo}")
        except Exception as e:
            print(f"Advertencia: no se pudo leer la lista de cursos: {e}")

        print(f"Cursos encontrados tras búsqueda: {len(cursos)}")
        for c in cursos[:10]:
            print(f"  - {c.get('titulo')} -> {c.get('url')}")

        try:
            self.recorrer_cursos(cursos, ciclo, anio, callback=callback)
        except Exception as e:
            print(f"Advertencia: no se pudo recorrer la lista de cursos: {e}")

        print(f"Cronogramas descargados: {len(self.cronogramas_descargados)}")
        for item in self.cronogramas_descargados:
            print(f"  - {item.get('archivo')} ({item.get('curso')})")

        print(f"Entregables extraídos: {len(self.entregables_extraidos)}")
        for item in self.entregables_extraidos:
            print(
                "  - "
                f"{item.get('curso', '')} | "
                f"{item.get('seccion', '')} | "
                f"{item.get('titulo', '')} | "
                f"Apertura: {item.get('fecha_apertura') or 'N/D'} | "
                f"Cierre: {item.get('fecha_cierre') or 'N/D'}"
            )

        return self.entregables_extraidos

    def recorrer_cursos(self, cursos: list[dict], ciclo: int, anio: int, callback=None) -> list[dict]:
        """Recorre cada curso en la misma pestaña y regresa a la lista al terminar.

        callback: función opcional llamada después de procesar cada curso.
        """
        recorridos: list[dict] = []
        if not cursos:
            return recorridos
        query = f"{anio}-{ciclo}"
        total = len(cursos)

        
        #for idx, curso in enumerate(cursos):
        for idx, curso in enumerate(cursos[1:2]):    
            url = curso.get("url") or ""
            if not url:
                continue

            print(f"Recorriendo curso: {curso.get('titulo')}")

            # Contadores antes de procesar este curso
            entregas_antes = len(self.entregables_extraidos)
            pdfs_antes = len(self.cronogramas_descargados)

            secciones_recorridas = 0

            try:
                self.driver.get(url)

                try:
                    WebDriverWait(self.driver, 15).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except Exception:
                    pass

                time.sleep(1)
                titulo_pagina = self.driver.title.strip()
                if not titulo_pagina:
                    try:
                        h1 = self.driver.find_element(By.CSS_SELECTOR, "h1")
                        titulo_pagina = h1.text.strip()
                    except Exception:
                        titulo_pagina = ""

                # El título de la página/pestaña trae el formato real
                # "AÑO-CICLO NOMBRE DEL CURSO (CODIGO-HORARIO)", igual al
                # código y horario que ya se extraen desde Campus Virtual
                # (ver campus/campus_cursos_extractor.py). Esto permite
                # cruzar las actividades de PAIDEIA con el curso real por
                # código, en lugar de depender únicamente del nombre.
                codigo_curso_real, horario_curso_real = self._extraer_codigo_horario(titulo_pagina)

                recorridos.append({
                    "course_id": curso.get("course_id", ""),
                    "titulo": curso.get("titulo", ""),
                    "url": url,
                    "titulo_pagina": titulo_pagina,
                    "codigo_curso_real": codigo_curso_real,
                    "horario_curso_real": horario_curso_real,
                })

                try:
                    resultado_secciones = self.recorrer_secciones_curso(
                        curso, codigo_curso_real, horario_curso_real
                    )
                    secciones_recorridas = len(resultado_secciones)
                except Exception as e:
                    print(f"  Advertencia: no se pudieron recorrer las secciones de este curso: {e}")

            finally:
                try:
                    self.driver.back()
                    time.sleep(1)
                    if not self._lista_cursos_visible():
                        print("  La lista no reapareció; restaurando búsqueda...")
                        self.search_courses(query)
                except Exception:
                    pass

                # Llamar callback con datos reales de este curso
                if callback:
                    entregas_curso = len(self.entregables_extraidos) - entregas_antes
                    pdfs_curso = len(self.cronogramas_descargados) - pdfs_antes
                    try:
                        callback({
                            "titulo": curso.get("titulo", ""),
                            "course_id": curso.get("course_id", ""),
                            "secciones": secciones_recorridas,
                            "entregas": entregas_curso,
                            "pdfs": pdfs_curso,
                            "idx": idx,
                            "total": total,
                        })
                    except Exception as e:
                        print(f"  Advertencia: error en callback de curso: {e}")

        print(f"Cursos recorridos: {len(recorridos)}")
        return recorridos

    @staticmethod
    def _extraer_codigo_horario(titulo_pagina: str) -> tuple[str | None, str | None]:
        """
        Extrae el código de curso y el código de horario desde el título
        de la página de PAIDEIA, con formato:
            "AÑO-CICLO NOMBRE DEL CURSO (CODIGO-HORARIO)"
        Ejemplo real: "2026-1 ESTRATEGIA Y GESTIÓN DE SISTEMAS DE
        INFORMACIÓN (1INF48-1082)" → ("1INF48", "1082")
        Devuelve (None, None) si el título no tiene el formato esperado.
        """
        if not titulo_pagina:
            return None, None
        match = re.search(r"\(([A-Z0-9]+)-(\d+)\)\s*$", titulo_pagina.strip())
        if not match:
            return None, None
        return match.group(1), match.group(2)

    def recorrer_secciones_curso(
        self, curso: dict, codigo_curso_real: str | None = None, horario_curso_real: str | None = None
    ) -> list[dict]:
        """Recorre cada sección visible de un curso usando la barra lateral izquierda."""
        titulo_curso = curso.get("titulo", "")
        curso_id = curso.get("course_id", "")

        if curso_id not in self.cronogramas_urls_por_curso:
            self.cronogramas_urls_por_curso[curso_id] = set()

        secciones = self.obtener_secciones_curso()
        print(f"  Secciones encontradas en '{titulo_curso}': {len(secciones)}")

        recorridos: list[dict] = []
        for seccion in secciones:
            titulo = seccion.get("titulo", "")
            url = seccion.get("url", "")
            if not url:
                continue

            print(f"  Recorriendo sección: {titulo}")
            try:
                self.driver.get(url)
                try:
                    WebDriverWait(self.driver, 15).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except Exception:
                    pass

                time.sleep(1)
                recorridos.append({
                    "titulo_curso": titulo_curso,
                    "titulo_seccion": titulo,
                    "url": url,
                })

                links_cronograma = self.obtener_links_cronograma_en_pagina()
                if links_cronograma:
                    enlaces_nuevos = [
                        link for link in links_cronograma
                        if link.get("href", "").strip() not in self.cronogramas_urls_por_curso[curso_id]
                    ]
                    if enlaces_nuevos:
                        print(f"    Cronogramas detectados: {len(enlaces_nuevos)} (de {len(links_cronograma)} total, {len(links_cronograma) - len(enlaces_nuevos)} duplicados)")
                        for link in enlaces_nuevos:
                            href = link.get("href", "").strip()
                            if href:
                                self.cronogramas_urls_por_curso[curso_id].add(href)
                        self.descargar_cronogramas_curso(curso, enlaces_nuevos)
                    else:
                        print(f"    Cronogramas detectados pero todos son duplicados (omitidos).")
                else:
                    print("    No se detectaron enlaces de cronograma en esta sección.")

                try:
                    eventos = self.obtener_eventos_seccion()
                    if eventos:
                        print(f"    Eventos encontrados: {len(eventos)}")
                        for evento in eventos:
                            print(f"      - {evento.get('titulo')} ({evento.get('tipo')})")
                            detalles = self.extraer_detalles_evento(evento)
                            if detalles:
                                detalles["curso"] = titulo_curso
                                detalles["course_id"] = curso_id
                                detalles["seccion"] = titulo
                                detalles["codigo"] = codigo_curso_real
                                detalles["horario"] = horario_curso_real
                                self.entregables_extraidos.append(detalles)
                                print(
                                    "        "
                                    f"Apertura: {detalles.get('fecha_apertura') or 'N/D'} | "
                                    f"Cierre: {detalles.get('fecha_cierre') or 'N/D'}"
                                )
                                self.driver.get(url)
                                time.sleep(0.5)
                    else:
                        print("    No se detectaron eventos en esta sección.")
                except Exception as e:
                    print(f"    Advertencia: error al extraer eventos: {e}")
            finally:
                try:
                    self.driver.back()
                    time.sleep(1)
                except Exception:
                    pass

        print(f"  Secciones recorridas: {len(recorridos)}")
        return recorridos

    def obtener_secciones_curso(self) -> list[dict]:
        """Obtiene las secciones visibles del curso desde la barra lateral izquierda."""
        script = """
        const sections = Array.from(document.querySelectorAll('#course-index .courseindex-section[data-for="section"]'));
        return sections.map(section => {
            const link = section.querySelector('a.courseindex-link[data-for="section_title"]');
            const title = link ? (link.innerText || link.textContent || '').trim() : '';
            const url = link ? (link.href || '') : '';
            const sectionId = section.getAttribute('data-id') || '';
            const sectionNumber = section.getAttribute('data-number') || '';
            return { titulo: title, url: url, section_id: sectionId, section_number: sectionNumber };
        }).filter(item => item.titulo || item.url);
        """
        secciones = self.driver.execute_script(script)
        return secciones or []

    def obtener_links_cronograma_en_pagina(self) -> list[dict]:
        """Devuelve enlaces PDF cuyo texto/título/href contenga 'cronograma'."""
        script = """
        const anchors = Array.from(document.querySelectorAll('a[href]'));
        const rows = anchors.map(a => ({
            href: a.href || '',
            title: (a.getAttribute('title') || '').trim(),
            text: (a.innerText || a.textContent || '').trim()
        }));

        const normalizeStr = (s) => {
            return s.toLowerCase().replace(/\\s+/g, ' ').trim();
        };

        const isCronograma = (r) => {
            const h = r.href.toLowerCase();
            const t = normalizeStr(r.title);
            const x = normalizeStr(r.text);

            const isResource = (
                h.includes('.pdf') ||
                h.includes('pluginfile.php') ||
                h.includes('mod/resource/view.php')
            );

            const hasCronograma = (
                h.includes('cronograma') ||
                t.includes('cronograma') ||
                x.includes('cronograma')
            );

            return isResource && hasCronograma;
        };

        const filtered = rows.filter(isCronograma);
        const seen = new Set();
        return filtered.filter(r => {
            if (!r.href || seen.has(r.href)) return false;
            seen.add(r.href);
            return true;
        });
        """
        links = self.driver.execute_script(script)
        return links or []

    def descargar_cronogramas_curso(self, curso: dict, links: list[dict]) -> list[Path]:
        """Descarga cronogramas PDF para un curso y los guarda en carpeta dedicada."""
        curso_id = (curso.get("course_id") or "sin_id").strip()
        titulo = (curso.get("titulo") or "curso").strip()
        carpeta_curso = self.cronogramas_dir / f"{curso_id}_{self._slug(titulo)}"
        carpeta_curso.mkdir(parents=True, exist_ok=True)

        guardados: list[Path] = []
        for i, link in enumerate(links, start=1):
            href = (link.get("href") or "").strip()
            if not href:
                continue

            nombre = self._nombre_archivo_desde_url(href)
            if not nombre.lower().endswith(".pdf"):
                nombre = f"cronograma_{i}.pdf"

            destino = carpeta_curso / nombre
            if destino.exists() and destino.stat().st_size > 0:
                guardados.append(destino)
                self.cronogramas_descargados.append({
                    "curso": titulo,
                    "course_id": curso_id,
                    "archivo": destino.name,
                    "ruta": str(destino),
                    "url": href,
                })
                print(f"    Reutilizado cronograma existente: {destino.name}")
                continue

            try:
                self.driver.get(href)
                time.sleep(2)
                pdf_links = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "a[href*='pluginfile.php']"
                )
                if pdf_links:
                    href_real = pdf_links[0].get_attribute("href")
                    self._descargar_url_con_sesion(href_real, destino)
                else:
                    self._descargar_url_con_sesion(href, destino)
                guardados.append(destino)
                self.cronogramas_descargados.append({
                    "curso": titulo,
                    "course_id": curso_id,
                    "archivo": destino.name,
                    "ruta": str(destino),
                    "url": href,
                })
                print(f"    Guardado cronograma: {destino.name}")
            except Exception as e:
                import traceback
                print(f"    Advertencia: fallo al descargar cronograma {href}: {e}")
                print(f"    Detalle: {traceback.format_exc()}")

        return guardados

    def _descargar_url_con_sesion(self, url: str, destino: Path):
        """Descarga una URL reutilizando cookies de Selenium (sesión autenticada)."""
        cookies = self.driver.get_cookies()
        cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name") and c.get("value") is not None)

        user_agent = "Mozilla/5.0"
        try:
            user_agent = self.driver.execute_script("return navigator.userAgent") or user_agent
        except Exception:
            pass

        headers = {
            "User-Agent": user_agent,
            "Referer": self.driver.current_url,
        }
        if cookie_header:
            headers["Cookie"] = cookie_header

        req = urllib.request.Request(url=url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()

        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(data)

    @staticmethod
    def _nombre_archivo_desde_url(url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        name = Path(urllib.parse.unquote(parsed.path)).name.strip()
        return name or "cronograma.pdf"

    @staticmethod
    def _slug(texto: str) -> str:
        t = re.sub(r"\s+", "_", texto.strip())
        t = re.sub(r"[^A-Za-z0-9_\-]", "", t)
        return t[:80] or "curso"

    def _lista_cursos_visible(self) -> bool:
        """Indica si la vista de cursos está visible en la página actual."""
        try:
            if self.driver.find_elements(By.CSS_SELECTOR, "div.card.course-card[data-region='course-content']"):
                return True
            if self.driver.find_elements(By.CSS_SELECTOR, "input[id^='searchinput-'], div[role='search']"):
                return True
        except Exception:
            return False
        return False

    def obtener_eventos_seccion(self) -> list[dict]:
        """Extrae SOLO entregas (assign) de la sección actual."""
        script = """
        const activities = Array.from(document.querySelectorAll('ul.section li.activity[data-for="cmitem"]'));
        return activities.map(activity => {
            const id = activity.getAttribute('data-id') || '';
            const link = activity.querySelector('a.aalink, a.courseindex-link[href]');
            const title = (link ? (link.innerText || link.textContent) : '').trim() ||
                          activity.getAttribute('data-activityname') || '';
            const href = link ? link.href : '';

            const classes = activity.className || '';
            let tipo = 'unknown';
            if (classes.includes('modtype_assign')) tipo = 'assign';
            else if (classes.includes('modtype_quiz')) tipo = 'quiz';
            else if (classes.includes('modtype_forum')) tipo = 'forum';
            else if (classes.includes('modtype_choice')) tipo = 'choice';
            else if (classes.includes('modtype_resource')) tipo = 'resource';
            else if (classes.includes('modtype_url')) tipo = 'url';
            else if (classes.includes('modtype_label')) tipo = 'label';

            return {
                id: id,
                titulo: title,
                url: href,
                tipo: tipo,
                classes: classes
            };
        }).filter(item => {
            return item.tipo === 'assign' && item.titulo && item.url;
        });
        """
        eventos = self.driver.execute_script(script)
        return eventos or []

    def extraer_detalles_evento(self, evento: dict) -> dict:
        """Entra al evento y extrae detalles: fechas, estado, calificación, etc."""
        url = evento.get("url", "")
        if not url:
            return {}

        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1)
        except Exception as e:
            print(f"    Advertencia: no se pudo cargar el evento {evento.get('titulo')}: {e}")
            return {}

        script = """
        const result = {
            titulo: '',
            descripcion: '',
            fecha_apertura: '',
            fecha_cierre: '',
            estado_entrega: '',
            calificacion: '',
            calificacion_sobre: '',
        };

        const h1 = document.querySelector('h1');
        if (h1) {
            result.titulo = (h1.innerText || h1.textContent).trim();
        }

        const intro = document.querySelector('#intro');
        if (intro) {
            result.descripcion = (intro.innerText || intro.textContent).trim().substring(0, 500);
        }

        const datesDiv = document.querySelector('[data-region="activity-dates"]');
        if (datesDiv) {
            const divs = Array.from(datesDiv.querySelectorAll('div'));
            divs.forEach(div => {
                const text = (div.innerText || div.textContent).trim();
                const lower = text.toLowerCase();
                if (lower.includes('apertura:')) {
                    result.fecha_apertura = text.split(':').slice(1).join(':').trim();
                } else if (lower.includes('cierre:')) {
                    result.fecha_cierre = text.split(':').slice(1).join(':').trim();
                }
            });
        }

        const tables = Array.from(document.querySelectorAll('table.generaltable'));
        tables.forEach(table => {
            const rows = Array.from(table.querySelectorAll('tr'));
            rows.forEach(row => {
                const cells = Array.from(row.querySelectorAll('th, td'));
                if (cells.length >= 2) {
                    const label = (cells[0].innerText || cells[0].textContent).trim().toLowerCase();
                    const value = (cells[1].innerText || cells[1].textContent).trim();
                    if (label.includes('estado de la entrega') && !label.includes('calificaci')) {
                        result.estado_entrega = value;
                    } else if (label.includes('calificación') && label.includes('estado de')) {
                        result.estado_entrega = value;
                    }
                }
            });
        });

        const feedbackTables = Array.from(document.querySelectorAll('div.feedback table.generaltable'));
        feedbackTables.forEach(table => {
            const rows = Array.from(table.querySelectorAll('tr'));
            rows.forEach(row => {
                const cells = Array.from(row.querySelectorAll('th, td'));
                if (cells.length >= 2) {
                    const label = (cells[0].innerText || cells[0].textContent).trim().toLowerCase();
                    const value = (cells[1].innerText || cells[1].textContent).trim();
                    if (label.includes('calificación') && !label.includes('estado')) {
                        result.calificacion = value;
                    } else if (label.includes('calificado sobre')) {
                        result.calificacion_sobre = value;
                    }
                }
            });
        });

        return result;
        """

        detalles = self.driver.execute_script(script)
        if detalles:
            detalles["url"] = url
            detalles["tipo"] = evento.get("tipo", "unknown")
        return detalles or {}

    def obtener_lista_cursos(self, query: str | None = None) -> list[dict]:
        """Recorre los elementos de curso visibles y devuelve lista de dicts {titulo, url}."""
        script = """
        const cards = Array.from(document.querySelectorAll("div.card.course-card[data-region='course-content']"));
        return cards.map(card => {
            const link = card.querySelector("a[href*='course/view.php?id=']");
            const titleEl = card.querySelector('span.multiline .sr-only');
            const multilineEl = card.querySelector('span.multiline');
            const title = (
                (titleEl && titleEl.innerText ? titleEl.innerText : '') ||
                (multilineEl && multilineEl.getAttribute('title') ? multilineEl.getAttribute('title') : '') ||
                (link && link.innerText ? link.innerText : '') ||
                (card.querySelector('a[title]') ? card.querySelector('a[title]').getAttribute('title') : '') ||
                card.innerText || ''
            ).trim();
            return {
                titulo: title,
                url: link ? (link.href || '') : '',
                course_id: card.getAttribute('data-course-id') || ''
            };
        }).filter(item => item.titulo || item.url);
        """
        cursos = self.driver.execute_script(script)
        if query:
            q = query.strip().lower()
            cursos = [
                curso for curso in (cursos or [])
                if q in (curso.get("titulo") or "").lower()
            ]
        return cursos or []
