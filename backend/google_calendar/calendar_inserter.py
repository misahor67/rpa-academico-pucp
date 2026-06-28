# google_calendar/calendar_inserter.py
import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

import locale

# Configurar la localización para español
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

def _parsear_fecha_paideia(texto: str) -> datetime.datetime | None:
    """
    Parsea fechas en formato PAIDEIA:
    'jueves, 23 de abril de 2026, 00:00'
    """
    if not texto:
        return None
    try:
        # Eliminar el día de la semana: "jueves, 23 de abril de 2026, 00:00"
        partes = texto.split(", ", 1)
        resto = partes[1] if len(partes) > 1 else partes[0]
        # resto = "23 de abril de 2026, 00:00"
        fecha_hora = resto.rsplit(", ", 1)
        fecha_str = fecha_hora[0]   # "23 de abril de 2026"
        hora_str = fecha_hora[1]    # "00:00"

        partes_fecha = fecha_str.split(" de ")
        dia = int(partes_fecha[0])
        mes = MESES_ES[partes_fecha[1].lower()]
        anio = int(partes_fecha[2])

        hora, minuto = map(int, hora_str.split(":"))
        return datetime.datetime(anio, mes, dia, hora, minuto)
    except Exception:
        return None

def _normalizar_datetime(valor) -> str:
    """Convierte date o datetime a string ISO 8601 para la API de Google Calendar."""
    if isinstance(valor, datetime.datetime):
        # Si no tiene timezone, asumir hora local
        if valor.tzinfo is None:
            return valor.isoformat()
        return valor.isoformat()
    if isinstance(valor, datetime.date):
        return datetime.datetime.combine(valor, datetime.time.min).isoformat()
    return str(valor)


def _construir_evento_google(evento: dict, recordatorio_minutos: int | None = None) -> dict | None:
    """
    Convierte un evento del sistema al formato requerido por Google Calendar API.
    Retorna None si el evento no tiene fechas válidas.

    recordatorio_minutos: si se especifica (y está en el rango permitido
    por la API, 0 a 40320 minutos = 4 semanas), se agrega un recordatorio
    tipo popup ese número de minutos antes del inicio del evento. Este es
    el mecanismo de "recordatorio de proximidad" (R3.1): se delega a
    Google Calendar, que ya corre de forma permanente, en lugar de que
    el sistema deba vigilar el reloj por su cuenta.
    """
    inicio = evento.get("inicio")
    fin = evento.get("fin")

    # Si no tiene inicio/fin (eventos PAIDEIA), parsear desde fecha_apertura/fecha_cierre
    if not inicio or not fin:
        inicio = _parsear_fecha_paideia(evento.get("fecha_apertura", ""))
        fin = _parsear_fecha_paideia(evento.get("fecha_cierre", ""))

    if not inicio or not fin:
        return None

    fuente = evento.get("fuente", "desconocido").upper()
    curso = evento.get("curso") or evento.get("titulo") or "Sin título"
    tipo = evento.get("tipo") or ""
    descripcion = evento.get("descripcion") or ""
    ubicacion = evento.get("ubicacion") or ""

    titulo = f"[{fuente}] {tipo} - {curso}" if tipo else f"[{fuente}] {curso}"

    evento_google = {
        "summary": titulo,
        "location": ubicacion,
        "description": f"Fuente: {fuente}\n{descripcion}".strip(),
        "start": {
            "dateTime": _normalizar_datetime(inicio),
            "timeZone": "America/Lima",
        },
        "end": {
            "dateTime": _normalizar_datetime(fin),
            "timeZone": "America/Lima",
        },
    }

    if recordatorio_minutos is not None and 0 <= recordatorio_minutos <= 40320:
        evento_google["reminders"] = {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": recordatorio_minutos},
            ],
        }

    return evento_google


def insertar_eventos(
    creds: Credentials, eventos: list[dict], calendar_id: str = "primary",
    recordatorio_minutos: int | None = None,
) -> dict:
    """
    Inserta la lista de eventos en Google Calendar.
    Retorna un resumen con la cantidad de eventos insertados y fallidos.
    """
    service = build("calendar", "v3", credentials=creds)

    insertados = 0
    fallidos = 0

    print(f"\nInsertando {len(eventos)} eventos en Google Calendar...")

    for evento in eventos:
        evento_google = _construir_evento_google(evento, recordatorio_minutos)

        if evento_google is None:
            print(f"  Omitido (sin fechas): {evento.get('curso') or evento.get('titulo', 'Sin título')}")
            fallidos += 1
            continue

        try:
            service.events().insert(
                calendarId=calendar_id,
                body=evento_google,
            ).execute()
            print(f"  Insertado: {evento_google['summary']}")
            insertados += 1
        except Exception as e:
            print(f"  Error al insertar '{evento_google['summary']}': {e}")
            fallidos += 1

    print(f"\nResumen: {insertados} insertados | {fallidos} fallidos")
    return {"insertados": insertados, "fallidos": fallidos}

def limpiar_calendario(creds: Credentials, calendar_id: str = "primary") -> None:
    """Elimina todos los eventos del calendario indicado."""
    service = build("calendar", "v3", credentials=creds)
    print("\nLimpiando calendario...")

    page_token = None
    eliminados = 0

    while True:
        eventos = service.events().list(
            calendarId=calendar_id,
            pageToken=page_token,
            maxResults=250,
        ).execute()

        for evento in eventos.get("items", []):
            try:
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=evento["id"],
                ).execute()
                eliminados += 1
            except Exception as e:
                print(f"  Error al eliminar evento: {e}")

        page_token = eventos.get("nextPageToken")
        if not page_token:
            break

    print(f"Calendario limpiado: {eliminados} eventos eliminados.")