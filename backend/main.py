# main.py
"""
Orquestador principal del RPA PUCP.
Coordina la extracción de Campus Virtual y PAIDEIA,
resuelve conflictos y sincroniza con Google Calendar.
"""

import datetime
import json
import sys
import subprocess
from pathlib import Path

from create_driver import create_driver
from campus.campus_extractor import CampusCalendarioIcs
from paideia.paideia_extractor import PaideiaExtractor
from google_calendar.auth import get_credentials
from google_calendar.conflict_resolver import resolver_conflictos
from google_calendar.calendar_inserter import insertar_eventos, limpiar_calendario
from config import CICLOS, ICS_DIR, PAIDEIA_CRONOGRAMAS_DIR, PAIDEIA_EVENTOS_JSON_DIR, CALENDAR_ID

def pedir_ciclo_y_anio() -> tuple[int, int]:
    """Solicita al usuario el ciclo académico y el año por consola."""
    print("\n=== Selección de ciclo académico ===")
    for num, info in CICLOS.items():
        print(f"  {num} → {info['nombre']} → {len(info['meses'])} mes(es)")

    while True:
        entrada = input("\nIngresa el número de ciclo (0, 1 o 2): ").strip()
        if entrada in ("0", "1", "2"):
            ciclo = int(entrada)
            break
        print("Opción inválida. Ingresa 0, 1 o 2.")

    anio_actual = datetime.date.today().year
    entrada_anio = input(f"Ingresa el año del ciclo [{anio_actual}]: ").strip()
    anio = int(entrada_anio) if entrada_anio.isdigit() else anio_actual

    print(f"\nCiclo seleccionado: {CICLOS[ciclo]['nombre']} {anio}")
    return ciclo, anio


def pedir_fuentes() -> tuple[bool, bool]:
    """Pregunta al usuario qué fuentes desea extraer."""
    print("\n=== Selección de fuentes ===")
    print("  1 → Solo Campus Virtual")
    print("  2 → Solo PAIDEIA")
    print("  3 → Ambas")

    while True:
        entrada = input("\nIngresa una opción (1, 2 o 3): ").strip()
        if entrada == "1":
            return True, False
        elif entrada == "2":
            return False, True
        elif entrada == "3":
            return True, True
        print("Opción inválida. Ingresa 1, 2 o 3.")


def forzar_cierre_driver(driver):
    """Mata el proceso del navegador directamente."""
    try:
        pid = driver.service.process.pid
        subprocess.call(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"No se pudo matar el proceso: {e}")


def run_campus(ciclo: int, anio: int) -> tuple[list[dict], object]:
    """Ejecuta la extracción completa del Campus Virtual.
    Retorna los eventos y el driver activo sin cerrarlo."""
    ICS_DIR.mkdir(parents=True, exist_ok=True)
    driver = create_driver(download_dir=ICS_DIR)

    try:
        campus = CampusCalendarioIcs(driver, ICS_DIR)
        campus.login()
        campus.go_to_calendar()

        campus.descargar_ics_ciclo(ciclo, anio)
        eventos = campus.extraer_eventos_desde_ics(ciclo, anio)
        return eventos, driver

    except KeyboardInterrupt:
        driver.close()
        driver.quit()
        raise


def run_paideia(ciclo: int, anio: int, driver=None) -> list[dict]:
    """Ejecuta la extracción desde PAIDEIA.
    Si recibe un driver lo reutiliza, si no crea uno nuevo."""
    driver_propio = driver is None
    if driver_propio:
        driver = create_driver()

    PAIDEIA_CRONOGRAMAS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        paideia = PaideiaExtractor(driver, PAIDEIA_CRONOGRAMAS_DIR)

        if driver_propio:
            paideia.login()
        else:
            driver.get("https://paideiacursos.pucp.edu.pe/my/courses.php")
            print("Sesión reutilizada. Navegando a PAIDEIA...")

        try:
            paideia.buscar_por_ciclo(ciclo, anio)
        except Exception as e:
            print(f"Advertencia: no se pudo ejecutar búsqueda en Paideia: {e}")

        eventos = paideia.extraer_eventos(ciclo, anio)
        return eventos

    except KeyboardInterrupt:
        driver.close()
        driver.quit()
        raise

    finally:
        if driver_propio:
            driver.quit()


def guardar_eventos_paideia_json(eventos: list[dict], ciclo: int, anio: int) -> Path:
    """Guarda los eventos de Paideia en un JSON con metadatos de ejecución."""
    PAIDEIA_EVENTOS_JSON_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now().isoformat(timespec="seconds")
    output = {
        "fuente": "paideia",
        "anio": anio,
        "ciclo": ciclo,
        "total_eventos": len(eventos),
        "generado_en": now,
        "eventos": eventos,
    }

    file_name = f"paideia_eventos_{anio}-{ciclo}.json"
    file_path = PAIDEIA_EVENTOS_JSON_DIR / file_name
    file_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path


if __name__ == "__main__":
    _driver = None
    try:
        ciclo, anio = pedir_ciclo_y_anio()
        extraer_campus, extraer_paideia = pedir_fuentes()

        eventos_campus = []
        eventos_paideia = []

        if extraer_campus:
            eventos_campus, _driver = run_campus(ciclo, anio)
            print(f"\nEventos Campus Virtual: {len(eventos_campus)}")

        if extraer_paideia:
            eventos_paideia = run_paideia(ciclo, anio, driver=_driver)
            print(f"Eventos PAIDEIA: {len(eventos_paideia)}")
            guardar_eventos_paideia_json(eventos_paideia, ciclo, anio)

        # Resolver conflictos y sincronizar con Google Calendar
        if eventos_campus or eventos_paideia:
            print("\n=== Resolviendo conflictos ===")
            eventos_finales = resolver_conflictos(eventos_campus, eventos_paideia)

            print("\n=== Sincronizando con Google Calendar ===")
            creds = get_credentials()
            limpiar_calendario(creds, calendar_id=CALENDAR_ID)
            insertar_eventos(creds, eventos_finales, calendar_id=CALENDAR_ID)

        input("\nProceso terminado. Presiona Enter para cerrar…")

    except KeyboardInterrupt:
        print("\nInterrupción por teclado recibida. Cerrando...")
    finally:
        if _driver is not None:
            forzar_cierre_driver(_driver)
        sys.exit(1)