# campus/campus_extractor.py
import re
import time
import datetime
from pathlib import Path
from icalendar import Calendar
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import (
    CICLOS, NOMBRES_MESES, MESES_A_NUMERO,
    DOWNLOAD_WAIT_SEC,
)


class CampusCalendarioIcs:
    """
    Extractor del calendario del Campus Virtual PUCP.

    Flujo principal:
        1. login()           → autentica al usuario
        2. go_to_calendar()  → navega al módulo de agenda (iframe)
        3. descargar_ics_ciclo()  → por cada mes del ciclo:
               - navega al mes
               - click "Ver mes" + "Exportar eventos"
               - espera el .ics descargado
        4. extraer_eventos_desde_ics()  → parsea los .ics y devuelve
               una lista de dicts con los eventos del ciclo
    """

    def __init__(self, driver, download_dir: Path):
        self.driver = driver
        self.download_dir = download_dir
        self.wait = WebDriverWait(driver, 10)

    # ------------------------------------------------------------------
    # AUTENTICACIÓN
    # ------------------------------------------------------------------

    def login(self):
        """Abre el campus y espera a que el usuario haga login manual."""
        self.driver.get("https://campusvirtual.pucp.edu.pe")
        print("Ingresa tus credenciales en el navegador…")
        WebDriverWait(self.driver, 300).until(
            EC.element_to_be_clickable((By.ID, "menu-toggle"))
        )
        print("Login detectado.")

    # ------------------------------------------------------------------
    # NAVEGACIÓN AL CALENDARIO
    # ------------------------------------------------------------------

    def go_to_calendar(self):
        """Abre el módulo Agenda y cambia el contexto al iframe del calendario."""
        self.wait.until(EC.element_to_be_clickable((By.ID, "menu-toggle"))).click()
        self.wait.until(EC.element_to_be_clickable((By.ID, "agenda"))).click()

        iframe = self.wait.until(EC.presence_of_element_located((By.ID, "frame_mid")))
        self.driver.switch_to.frame(iframe)

        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#calPrinc .days"))
        )
        print("Calendario cargado (iframe).")

    # ------------------------------------------------------------------
    # LECTURA DEL MES/AÑO VISIBLE
    # ------------------------------------------------------------------

    def get_mes_anio_actual(self) -> tuple[int | None, int | None]:
        """Lee el mes y año que muestra actualmente el calendario."""
        try:
            header = self.driver.find_element(
                By.CSS_SELECTOR, "#calPrinc_scroll_message"
            )
            texto = header.text.strip().lower()
            for nombre, numero in MESES_A_NUMERO.items():
                if nombre in texto:
                    for parte in texto.split():
                        if parte.isdigit() and len(parte) == 4:
                            return numero, int(parte)
                    return numero, None
        except Exception:
            pass
        return None, None

    # ------------------------------------------------------------------
    # NAVEGACIÓN ENTRE MESES
    # ------------------------------------------------------------------

    def _click_nav(self, selector: str):
        """Hace click en el botón anterior/siguiente y espera que cambie el header."""
        texto_actual = self.driver.find_element(
            By.CSS_SELECTOR, "#calPrinc_scroll_message"
        ).text
        btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        self.driver.execute_script("arguments[0].click();", btn)
        WebDriverWait(self.driver, 5).until(
            lambda d: d.find_element(
                By.CSS_SELECTOR, "#calPrinc_scroll_message"
            ).text != texto_actual
        )

    def navegar_a_mes(self, mes_objetivo: int, anio_objetivo: int):
        """Navega hacia adelante o atrás hasta alcanzar el mes/año objetivo."""
        mes_actual, anio_actual = self.get_mes_anio_actual()
        if mes_actual is None or anio_actual is None:
            print("  No se pudo leer el mes actual del calendario.")
            return

        diff = (anio_objetivo * 12 + mes_objetivo) - (anio_actual * 12 + mes_actual)
        if diff == 0:
            return

        print(f"  Navegando {abs(diff)} mes(es) {'adelante' if diff > 0 else 'atrás'}…")
        for _ in range(abs(diff)):
            selector = "#calPrinc_scroll_next" if diff > 0 else "#calPrinc_scroll_prev"
            self._click_nav(selector)

        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#calPrinc_data .days"))
        )

    # ------------------------------------------------------------------
    # EXPORTACIÓN ICS
    # ------------------------------------------------------------------

    def _handle_alert(self):
        """Cierra cualquier alert/popup que haya quedado abierto."""
        try:
            alert = self.driver.switch_to.alert
            print("  Alert:", alert.text)
            alert.accept()
        except Exception:
            pass

    def _wait_ics_tras_export(self, antes: set[str]) -> Path:
        """
        Espera hasta DOWNLOAD_WAIT_SEC segundos a que aparezca
        un nuevo archivo .ics en el directorio de descarga.
        """
        deadline = time.time() + DOWNLOAD_WAIT_SEC
        while time.time() < deadline:
            nuevos = [
                p for p in self.download_dir.iterdir()
                if p.is_file()
                and p.suffix.lower() == ".ics"
                and not p.name.lower().endswith((".tmp", ".crdownload"))
                and p.name not in antes
            ]
            if nuevos:
                archivo = max(nuevos, key=lambda x: x.stat().st_mtime)
                time.sleep(1)   # asegurar escritura completa
                return archivo
            time.sleep(0.25)
        raise TimeoutError(f"No apareció un nuevo .ics en {self.download_dir}")

    def click_exportar_eventos(self):
        """Hace click en el botón 'Exportar eventos'."""
        self._handle_alert()
        try:
            btn = self.wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    '#opciones button[onclick*="ExportarAgenda"]',
                ))
            )
            self.driver.execute_script("arguments[0].click();", btn)
        except Exception:
            # fallback: llamar la función JS directamente
            self.driver.execute_script(
                "if (typeof ExportarAgenda === 'function') ExportarAgenda();"
            )
        self._handle_alert()

    def click_ver_mes(self):
        """Refresca la vista mensual del calendario."""
        btn = self.wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'div.button[onclick*="verMesClick"]',
            ))
        )
        self.driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)

    def descargar_ics_ciclo(self, ciclo: int, anio: int) -> list[Path]:
        """
        Descarga un .ics por cada mes del ciclo indicado.
        Omite meses que ya tienen archivo en disco.
        Devuelve la lista de rutas guardadas.
        """
        meses = CICLOS[ciclo]["meses"]
        nombre_ciclo = CICLOS[ciclo]["nombre"]
        self.download_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nDescargando {len(meses)} .ics — {nombre_ciclo} {anio}")
        guardados: list[Path] = []

        for mes in meses:
            nombre_archivo = f"campus_{anio}_{mes:02d}_{NOMBRES_MESES[mes]}.ics"
            destino = self.download_dir / nombre_archivo

            print(f"\n--- {NOMBRES_MESES[mes]} {anio} ---")

            # Saltar si ya existe y no está vacío
            if destino.exists() and destino.stat().st_size > 0:
                print(f"  Ya existe: {destino.name}")
                guardados.append(destino)
                continue

            self._handle_alert()
            self.navegar_a_mes(mes, anio)
            time.sleep(0.8)

            # Verificar que la navegación fue correcta
            mes_leido, anio_leido = self.get_mes_anio_actual()
            if (mes_leido, anio_leido) != (mes, anio):
                print(f"  Aviso: calendario muestra {mes_leido}/{anio_leido}, reintentando…")
                self.navegar_a_mes(mes, anio)
                time.sleep(0.8)

            # Snapshot de archivos previos para detectar el nuevo .ics
            antes = {p.name for p in self.download_dir.iterdir() if p.is_file()}

            self.click_ver_mes()
            self.click_exportar_eventos()

            descargado = self._wait_ics_tras_export(antes)

            if destino.exists():
                destino.unlink()
            descargado.replace(destino)

            print(f"  Guardado: {destino.name}")
            guardados.append(destino)

        return guardados

    # ------------------------------------------------------------------
    # PARSEO DE ARCHIVOS .ICS (métodos estáticos: no dependen del driver)
    # ------------------------------------------------------------------

    @staticmethod
    def parsear_summary(summary: str) -> dict:
        """
        Extrae los campos estructurados del SUMMARY de un evento PUCP.
        Formato esperado:
          TIPO DE CURSO (CICLO, CODIGO, HORARIO N, SESION MODALIDAD)
        """
        patron = re.compile(
            r"""
            (?P<tipo>.+?)\s+DE\s+
            (?P<curso>.+?)
            \s*\(
            (?P<ciclo>\d{4}-\d)
            \s*,\s*
            (?P<codigo>[A-Z0-9_-]+)
            \s*,\s*
            HORARIO\s+(?P<horario>\d+)
            \s*,\s*
            SESION\s+(?P<modalidad>.+?)
            \s*\)
            """,
            re.VERBOSE | re.IGNORECASE,
        )
        match = patron.search(summary)
        if not match:
            return {
                "tipo": None, "curso": summary, "ciclo": None,
                "codigo": None, "horario": None, "modalidad": None,
            }
        return {
            "tipo":      match.group("tipo").strip(),
            "curso":     match.group("curso").strip(),
            "ciclo":     match.group("ciclo").strip(),
            "codigo":    match.group("codigo").strip(),
            "horario":   match.group("horario").strip(),
            "modalidad": match.group("modalidad").strip().upper(),
        }

    @staticmethod
    def parsear_ics(ruta: Path) -> list[dict]:
        """Lee un archivo .ics y devuelve sus VEVENTs como lista de dicts."""
        with ruta.open("rb") as f:
            cal = Calendar.from_ical(f.read())

        eventos = []
        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            summary = str(component.get("summary", ""))
            info = CampusCalendarioIcs.parsear_summary(summary)

            dtstart = component.get("dtstart")
            dtend   = component.get("dtend")
            inicio  = dtstart.dt if dtstart else None
            fin     = dtend.dt   if dtend   else None

            eventos.append({
                "archivo":     ruta.name,
                "tipo":        info["tipo"],
                "curso":       info["curso"],
                "codigo":      info["codigo"],
                "ciclo":       info["ciclo"],
                "horario":     info["horario"],
                "modalidad":   info["modalidad"],
                "inicio":      inicio,
                "fin":         fin,
                "fecha":       inicio.date().isoformat() if inicio else None,
                "hora_inicio": inicio.strftime("%H:%M") if inicio else None,
                "hora_fin":    fin.strftime("%H:%M")    if fin    else None,
                "ubicacion":   str(component.get("location",    "")),
                "descripcion": str(component.get("description", "")),
                "uid":         str(component.get("uid",         "")),
            })
        return eventos

    def extraer_eventos_desde_ics(self, ciclo: int, anio: int) -> list[dict]:
        """
        Lee todos los .ics del directorio de descarga y filtra
        los eventos que pertenecen al ciclo/año indicado.
        """
        rutas = sorted(self.download_dir.glob("*.ics"))
        if not rutas:
            raise FileNotFoundError(f"No hay archivos .ics en {self.download_dir}")

        print(f"\nArchivos .ics a procesar ({len(rutas)}):")
        for p in rutas:
            print(f"  - {p.name}")

        meses_ciclo = CICLOS[ciclo]["meses"]
        todos: list[dict] = []

        for ruta in rutas:
            for ev in self.parsear_ics(ruta):
                if ev["inicio"] is None:
                    continue
                fecha = ev["inicio"].date() if isinstance(ev["inicio"], datetime.datetime) \
                        else ev["inicio"]
                if fecha.year == anio and fecha.month in meses_ciclo:
                    todos.append(ev)

        return todos

