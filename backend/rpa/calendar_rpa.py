# backend/rpa/calendar_rpa.py

from google_calendar.auth import get_credentials
from google_calendar.conflict_resolver import resolver_conflictos
from google_calendar.calendar_inserter import _construir_evento_google
from googleapiclient.discovery import build
from sesiones import actualizar_sesion, log


def ejecutar_calendar(sesion_id: str, nombre_cal: str, eventos_campus: list, eventos_paideia: list) -> list:
    """
    Crea el calendario en Google Calendar (eliminando uno anterior si existe),
    inserta todos los eventos con progreso en tiempo real y retorna los eventos insertados.
    """
    actualizar_sesion(sesion_id,
        estado="sincronizando",
        mensaje="Creando calendario en Google Calendar...",
        progreso=85)

    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    # Eliminar calendario anterior con el mismo nombre
    calendarios = service.calendarList().list().execute()
    for cal in calendarios.get("items", []):
        if cal.get("summary") == nombre_cal:
            service.calendars().delete(calendarId=cal["id"]).execute()
            log(sesion_id, f"Calendario anterior eliminado: {nombre_cal}")
            break

    # Crear nuevo calendario
    calendario_nuevo = service.calendars().insert(body={
        "summary": nombre_cal,
        "timeZone": "America/Lima"
    }).execute()
    nuevo_calendar_id = calendario_nuevo["id"]
    log(sesion_id, f"Calendario creado: {nombre_cal}")

    actualizar_sesion(sesion_id,
        estado="sincronizando",
        mensaje="Insertando eventos en Google Calendar...",
        nombre_calendario=nombre_cal,
        progreso=88)

    # Resolver conflictos y insertar eventos
    eventos_finales = resolver_conflictos(eventos_campus, eventos_paideia)
    total_insertar = len(eventos_finales)
    actualizar_sesion(sesion_id, total_insertar=total_insertar, insertados=0)

    insertados = 0
    for evento in eventos_finales:
        evento_google = _construir_evento_google(evento)
        if evento_google is None:
            continue
        try:
            service.events().insert(
                calendarId=nuevo_calendar_id,
                body=evento_google,
            ).execute()
            insertados += 1
            ultimo = evento_google.get("summary", "")
            actualizar_sesion(sesion_id,
                insertados=insertados,
                ultimo_evento=ultimo,
                progreso=88 + int((insertados / total_insertar) * 11))
        except Exception as e:
            log(sesion_id, f"Error insertando evento: {e}")

    return eventos_finales, nuevo_calendar_id
