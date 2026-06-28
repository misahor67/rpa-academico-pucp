# campus/campus_cursos_extractor.py
#
# Extractor de cursos matriculados, horario y docente(s) desde la sección
# "Cursos y actividades" del Campus Virtual PUCP.
#
# Sigue el mismo patrón de campus_extractor.py (clase con self.driver,
# self.wait, métodos separados por responsabilidad).
#
# Regla de negocio para el caso "Ver docentes" (cursos sin un único
# docente listado, como Proyecto de Fin de Carrera): se abre la ventana
# emergente y se filtran los profesores cuya categoría es "PRINCIPAL" y
# cuyo horario coincide con el horario del curso. Puede devolver 0, 1 o
# varios resultados; en este último caso, todos se consideran docentes
# válidos del curso (relación N:M, igual que la tabla curso_profesor).

import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class CampusCursosExtractor:
    """
    Extractor de cursos matriculados del Campus Virtual PUCP.

    Flujo principal:
        1. ir_a_cursos_y_actividades()  → navega al iframe de cursos
        2. extraer_cursos()             → devuelve la lista de cursos del
                                           ciclo actual, resolviendo el
                                           caso especial "Ver docentes"
                                           para cada curso que lo requiera
    """

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    # ------------------------------------------------------------------
    # NAVEGACIÓN
    # ------------------------------------------------------------------

    def ir_a_cursos_y_actividades(self):
        """Abre el módulo 'Cursos y actividades' y cambia el contexto
        al iframe donde vive la tabla real."""
        self.driver.switch_to.default_content()

        # El menú lateral puede estar cerrado en este punto del flujo
        # (p. ej. después de navegar el calendario de Campus Virtual),
        # así que lo abrimos primero, igual que hace go_to_calendar()
        # en campus_extractor.py.
        try:
            self.wait.until(
                EC.element_to_be_clickable((By.ID, "menu-toggle"))
            ).click()
        except Exception:
            # Si el menú ya estaba abierto, el toggle puede no ser
            # clickeable en este momento; no es un error bloqueante.
            pass

        self.wait.until(
            EC.element_to_be_clickable((By.ID, "cursoactividades"))
        ).click()

        iframe = self.wait.until(
            EC.presence_of_element_located((By.ID, "frame_mid"))
        )
        self.driver.switch_to.frame(iframe)

        self.wait.until(
            EC.presence_of_element_located((By.ID, "tablaCursosRegulares"))
        )
        print("Sección 'Cursos y actividades' cargada (iframe).")

    # ------------------------------------------------------------------
    # EXTRACCIÓN DE LA TABLA PRINCIPAL DE CURSOS
    # ------------------------------------------------------------------

    def extraer_cursos(self) -> list[dict]:
        """
        Extrae todos los cursos matriculados del ciclo actual, junto con
        su código, nombre, créditos, horario y docente(s).

        Devuelve una lista de diccionarios:
            {
                "codigo": str,
                "nombre": str,
                "creditos": str,
                "horario": str,
                "docentes": list[dict],  # [{"nombre": str, "codigo_pucp": str, "email": str|None}, ...]
            }
        """
        html_tabla = self.driver.find_element(
            By.ID, "tablaCursosRegulares"
        ).get_attribute("outerHTML")

        cursos_crudos = self._parsear_tabla_cursos(html_tabla)

        cursos = []
        for c in cursos_crudos:
            docentes = []
            if c["docente_nombre"] and c["docente_codigo"]:
                docentes = [{
                    "nombre": c["docente_nombre"],
                    "codigo_pucp": c["docente_codigo"],
                    "email": None,  # no disponible en la tabla principal
                }]
            elif c["ver_docentes_args"]:
                # Caso especial: hay que abrir la ventana "Ver docentes"
                # y filtrar por categoría PRINCIPAL + horario del curso.
                docentes = self._resolver_ver_docentes(
                    codigo_curso=c["codigo"],
                    horario_curso=c["horario"],
                )

            cursos.append({
                "codigo": c["codigo"],
                "nombre": c["nombre"],
                "creditos": c["creditos"],
                "horario": c["horario"],
                "docentes": docentes,
            })

        return cursos

    @staticmethod
    def _parsear_tabla_cursos(tabla_html: str) -> list[dict]:
        """Parsing por expresiones regulares de la tabla de cursos."""
        filas = re.findall(r"<tr>(.*?)</tr>", tabla_html, re.DOTALL)

        cursos = []
        for fila in filas:
            codigo_match = re.search(
                r'<td class="pucpCelda celdaPanel" width="5%" valign="top"><p align="Left">([^<]+)</p>',
                fila,
            )
            if not codigo_match:
                continue  # fila vacía (PRA/EXA/LAB) o encabezado

            codigo = codigo_match.group(1).strip()

            nombre_match = re.search(
                r"PanelCursoPersonaCiclo\([^)]*\)[^>]*>([^<]+)</a>", fila
            )
            nombre = nombre_match.group(1).strip() if nombre_match else None

            creditos_match = re.search(r'<p align="center">\s*([\d.]+)\s*</p>', fila)
            creditos = creditos_match.group(1).strip() if creditos_match else None

            tipo_horario_match = re.search(
                r'<p align="center">(CLA|PRA|EXA|LAB)</p>.*?'
                r'<p align="center">(\d+)</p>',
                fila,
                re.DOTALL,
            )
            horario = tipo_horario_match.group(2) if tipo_horario_match else None

            # Docente "normal": PanelPersona("código"); ... >NOMBRE</a>
            # Capturamos código y nombre en una sola expresión.
            docente_normal = re.search(
                r'PanelPersona\(&quot;([^&]*)&quot;\)[^>]*>([^<]+)</a>', fila
            )
            if not docente_normal:
                # Variante sin &quot; (HTML ya decodificado, como lo ve Selenium en vivo)
                docente_normal = re.search(
                    r'PanelPersona\("([^"]*)"\)[^>]*>([^<]+)</a>', fila
                )

            docente_especial = re.search(r"muestraDocentes\(([^)]*)\)", fila)

            docente_nombre = None
            docente_codigo = None
            ver_docentes_args = None
            if docente_normal:
                codigo_prof = docente_normal.group(1).strip()
                nombre_prof = docente_normal.group(2).strip()
                if codigo_prof and nombre_prof:  # descarta el caso vacío PanelPersona(" ")
                    docente_codigo = codigo_prof
                    docente_nombre = nombre_prof
            if not docente_nombre and docente_especial:
                ver_docentes_args = docente_especial.group(1)

            cursos.append({
                "codigo": codigo,
                "nombre": nombre,
                "creditos": creditos,
                "horario": horario,
                "docente_nombre": docente_nombre,
                "docente_codigo": docente_codigo,
                "ver_docentes_args": ver_docentes_args,
            })

        return cursos

    # ------------------------------------------------------------------
    # CASO ESPECIAL: "VER DOCENTES" (ventana nueva)
    # ------------------------------------------------------------------

    def _resolver_ver_docentes(self, codigo_curso: str, horario_curso: str) -> list[dict]:
        """
        Abre la ventana 'Ver docentes' del curso indicado, filtra los
        profesores con categoría PRINCIPAL cuyo horario coincide con
        horario_curso, y devuelve sus datos (nombre, código, email).
        Cierra la ventana antes de retornar, dejando el driver de vuelta
        en el iframe de cursos.
        """
        ventana_principal = self.driver.current_window_handle
        ventanas_antes = self.driver.window_handles

        try:
            link = self.driver.find_element(
                By.XPATH,
                f"//a[contains(@href, 'muestraDocentes') and contains(@href, '{codigo_curso}')]",
            )
        except Exception:
            print(f"  No se encontró el link 'Ver docentes' para {codigo_curso}.")
            return []

        self.driver.execute_script("arguments[0].click();", link)

        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: len(d.window_handles) > len(ventanas_antes)
            )
        except Exception:
            print(f"  La ventana 'Ver docentes' de {codigo_curso} no llegó a abrirse.")
            return []

        ventana_nueva = [
            v for v in self.driver.window_handles if v not in ventanas_antes
        ][0]
        self.driver.switch_to.window(ventana_nueva)
        time.sleep(0.5)  # margen corto para que la ventana termine de renderizar

        html_ventana = self.driver.page_source
        docentes = self._filtrar_docentes_principal(html_ventana, horario_curso)

        self.driver.close()
        self.driver.switch_to.window(ventana_principal)
        # Volvemos a entrar al iframe de cursos, ya que cerrar la ventana
        # nos deja en el contexto de la ventana principal (fuera del iframe)
        iframe = self.driver.find_element(By.ID, "frame_mid")
        self.driver.switch_to.frame(iframe)

        return docentes

    @staticmethod
    def _filtrar_docentes_principal(html_ventana: str, horario_objetivo: str) -> list[dict]:
        """Filtra, de la ventana 'Ver docentes', los profesores con
        categoría PRINCIPAL cuyo horario coincide con horario_objetivo.
        Devuelve [{"nombre": str, "codigo_pucp": str, "email": str|None}, ...]
        """
        filas = re.findall(r'<tr>\s*<td class="pucpCampo".*?</tr>', html_ventana, re.DOTALL)

        resultado = []
        for fila in filas:
            codigo_match = re.search(
                r'AbrirPanel&amp;codigo=([^"]+)"', fila
            )
            nombre_match = re.search(
                r'pucpLinkCelda[a-zA-Z]*" href="[^"]*" onmouseover="[^"]*">\s*([^<]+)</a>',
                fila,
            )
            categoria_match = re.search(
                r'pucpCelda[a-zA-Z]*" width="12%" height="18">([^<]+)</td>', fila
            )
            horario_match = re.search(
                r'pucpCelda[a-zA-Z]*" width="17%" height="18">([^<]+)<br', fila
            )
            email_match = re.search(r"dirPara=([^&\"]+)&", fila)

            if not (nombre_match and categoria_match and horario_match):
                continue

            nombre = nombre_match.group(1).strip()
            categoria = categoria_match.group(1).strip()
            horario_texto = horario_match.group(1).strip()

            if categoria == "PRINCIPAL" and horario_objetivo in horario_texto:
                resultado.append({
                    "nombre": nombre,
                    "codigo_pucp": codigo_match.group(1).strip() if codigo_match else None,
                    "email": email_match.group(1).strip() if email_match else None,
                })

        return resultado