# backend/rpa/ejecutar.py

import time as time_module
from create_driver import create_driver
from sesiones import actualizar_sesion, log, sesiones
from rpa.campus_rpa import ejecutar_campus
from rpa.paideia_rpa import ejecutar_paideia
from rpa.calendar_rpa import ejecutar_calendar


def ejecutar_rpa(sesion_id: str, config: dict):
    ciclo = config["ciclo"]
    anio = config["anio"]
    extraer_campus = config["campus"]
    extraer_paideia = config["paideia"]

    eventos_campus = []
    eventos_paideia = []
    pdfs_estado = []
    _driver = None

    try:
        # ── Campus Virtual ────────────────────────────────────────────────────
        if extraer_campus:
            from config import ICS_DIR
            ICS_DIR.mkdir(parents=True, exist_ok=True)
            _driver = create_driver(download_dir=ICS_DIR)
            eventos_campus = ejecutar_campus(sesion_id, _driver, ciclo, anio)

        # ── PAIDEIA ───────────────────────────────────────────────────────────
        if extraer_paideia:
            if _driver is None:
                # Solo PAIDEIA: crear driver nuevo sin sesión previa
                _driver = create_driver()

            eventos_paideia, pdfs_estado = ejecutar_paideia(
                sesion_id, _driver, ciclo, anio,
                tiene_sesion_previa=extraer_campus  # True si ya pasó por Campus
            )

        # ── Esperar confirmación del usuario (P8) ─────────────────────────────
        actualizar_sesion(sesion_id,
            estado="esperando_confirmacion",
            mensaje="Extracción completada. Esperando confirmación del usuario...",
            progreso=82,
            total_campus=len(eventos_campus),
            total_paideia=len(eventos_paideia),
            pdfs=pdfs_estado)

        log(sesion_id, "Esperando confirmación del usuario...")
        timeout = 300
        elapsed = 0
        confirmado = False
        while elapsed < timeout:
            time_module.sleep(1)
            elapsed += 1
            if sesiones.get(sesion_id, {}).get("confirmado") is True:
                confirmado = True
                break

        if not confirmado:
            actualizar_sesion(sesion_id,
                estado="error",
                mensaje="Tiempo de espera agotado. El usuario no confirmó.")
            return

        nombre_cal = sesiones[sesion_id].get(
            "nombre_calendario", f"RPA Académico — {sesion_id[:8]}")

        # ── Google Calendar ───────────────────────────────────────────────────
        eventos_finales, nuevo_calendar_id = ejecutar_calendar(
            sesion_id, nombre_cal, eventos_campus, eventos_paideia)

        # ── Completado ────────────────────────────────────────────────────────
        actualizar_sesion(sesion_id,
            estado="completado",
            mensaje="Sincronización completada exitosamente",
            progreso=100,
            eventos=eventos_finales,
            total_campus=len(eventos_campus),
            total_paideia=len(eventos_paideia),
            nombre_calendario=nombre_cal,
            calendar_id=nuevo_calendar_id)
        log(sesion_id, f"Completado: {len(eventos_finales)} eventos insertados")

        # ── Guardar en base de datos ──────────────────────────────────────────
        try:
            from database import SessionLocal
            from app import guardar_sincronizacion_en_bd
            db = SessionLocal()
            guardar_sincronizacion_en_bd(sesion_id, db)
            db.close()
            log(sesion_id, "Historial guardado en base de datos")
        except Exception as e:
            log(sesion_id, f"Advertencia: no se pudo guardar en BD: {e}")

    except Exception as e:
        actualizar_sesion(sesion_id,
            estado="error",
            mensaje=f"Error: {str(e)}",
            progreso=0)
        log(sesion_id, f"ERROR: {str(e)}")
    finally:
        if _driver:
            try:
                _driver.quit()
            except Exception:
                pass
