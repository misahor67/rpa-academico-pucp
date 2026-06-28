# backend/rpa/campus_rpa.py

from campus.campus_extractor import CampusCalendarioIcs
from campus.campus_cursos_extractor import CampusCursosExtractor
from config import ICS_DIR, CICLOS, NOMBRES_MESES
from sesiones import actualizar_sesion, log


def ejecutar_campus(sesion_id: str, driver, ciclo: int, anio: int) -> tuple[list, list]:
    """
    Realiza el login en Campus Virtual, descarga los ICS del ciclo,
    extrae los cursos matriculados (con horario y docente reales), y
    retorna una tupla (eventos, cursos).
    """
    actualizar_sesion(sesion_id,
        estado="esperando_login_campus",
        mensaje="Esperando login en Campus Virtual...",
        progreso=5)
    log(sesion_id, "Abriendo Campus Virtual...")

    ICS_DIR.mkdir(parents=True, exist_ok=True)
    campus = CampusCalendarioIcs(driver, ICS_DIR)
    campus.login()

    actualizar_sesion(sesion_id,
        estado="extrayendo_campus",
        mensaje="Login detectado. Extrayendo datos...",
        progreso=15)
    log(sesion_id, "Login Campus Virtual exitoso. Descargando ICS...")

    campus.go_to_calendar()

    meses_ciclo = CICLOS[ciclo]["meses"]

    meses_estado = [
        {"nombre": f"{NOMBRES_MESES[m]} {anio}", "estado": "pendiente", "eventos": 0}
        for m in meses_ciclo
    ]
    actualizar_sesion(sesion_id, meses_campus=meses_estado)

    def on_mes_descargado(mes, destino):
        idx = meses_ciclo.index(mes)
        count = 0
        try:
            eventos_mes = CampusCalendarioIcs.parsear_ics(destino)
            count = len(eventos_mes)
        except Exception as e:
            print(f"Error contando eventos de {destino.name}: {e}")
        meses_estado[idx]["estado"] = "completado"
        meses_estado[idx]["eventos"] = count
        actualizar_sesion(sesion_id,
            meses_campus=meses_estado.copy(),
            progreso=15 + int(((idx + 1) / len(meses_ciclo)) * 25))
        log(sesion_id, f"{NOMBRES_MESES[mes]} {anio}: {count} eventos")

    campus.descargar_ics_ciclo(ciclo, anio, callback=on_mes_descargado)
    eventos_campus = campus.extraer_eventos_desde_ics(ciclo, anio)

    actualizar_sesion(sesion_id,
        progreso=40,
        mensaje=f"{len(eventos_campus)} eventos extraídos de Campus Virtual")
    log(sesion_id, f"Campus Virtual: {len(eventos_campus)} eventos")

    # ── Cursos, horario y docente(s) reales ────────────────────────────
    log(sesion_id, "Extrayendo cursos matriculados (código, horario, docente)...")
    cursos = []
    try:
        cursos_extractor = CampusCursosExtractor(driver)
        cursos_extractor.ir_a_cursos_y_actividades()
        cursos = cursos_extractor.extraer_cursos()
        log(sesion_id, f"Cursos extraídos: {len(cursos)}")
    except Exception as e:
        detalle = str(e) or "(sin mensaje, probablemente timeout esperando un elemento)"
        log(sesion_id, f"Advertencia: no se pudieron extraer los cursos [{type(e).__name__}]: {detalle}")

    actualizar_sesion(sesion_id,
        progreso=45,
        mensaje=f"{len(cursos)} cursos extraídos de Campus Virtual")

    return eventos_campus, cursos