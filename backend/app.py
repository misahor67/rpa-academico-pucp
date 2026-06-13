# backend/app.py
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import threading
import sys
import os

# Agregar el directorio backend al path para importar los módulos del RPA
sys.path.insert(0, os.path.dirname(__file__))

app = FastAPI(
    title="RPA Académico PUCP",
    description="API para centralización de actividades académicas PUCP",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Almacén de sesiones en memoria
sesiones = {}

# ── Modelos ───────────────────────────────────────────────────────────────────
class ConfiguracionSincronizacion(BaseModel):
    ciclo: int
    anio: int
    campus: bool
    paideia: bool

# ── Helpers ───────────────────────────────────────────────────────────────────
def actualizar_sesion(sesion_id: str, **kwargs):
    if sesion_id in sesiones:
        sesiones[sesion_id].update(kwargs)

def log(sesion_id: str, mensaje: str):
    if sesion_id in sesiones:
        logs = sesiones[sesion_id].get("logs", [])
        logs.append(mensaje)
        sesiones[sesion_id]["logs"] = logs[-20:]  # máximo 20 logs
    print(mensaje)

# ── Proceso RPA en background ─────────────────────────────────────────────────
def ejecutar_rpa(sesion_id: str, config: dict):
    try:
        from create_driver import create_driver
        from campus.campus_extractor import CampusCalendarioIcs
        from paideia.paideia_extractor import PaideiaExtractor
        from google_calendar.auth import get_credentials
        from google_calendar.conflict_resolver import resolver_conflictos
        from google_calendar.calendar_inserter import insertar_eventos, limpiar_calendario
        from config import ICS_DIR, PAIDEIA_CRONOGRAMAS_DIR, CALENDAR_ID

        ciclo = config["ciclo"]
        anio = config["anio"]
        extraer_campus = config["campus"]
        extraer_paideia = config["paideia"]

        eventos_campus = []
        eventos_paideia = []
        _driver = None

        # ── Campus Virtual ────────────────────────────────────────────────────
        if extraer_campus:
            actualizar_sesion(sesion_id,
                estado="esperando_login_campus",
                mensaje="Esperando login en Campus Virtual...",
                progreso=5)
            log(sesion_id, "Abriendo Campus Virtual...")

            ICS_DIR.mkdir(parents=True, exist_ok=True)
            _driver = create_driver(download_dir=ICS_DIR)

            campus = CampusCalendarioIcs(_driver, ICS_DIR)
            campus.login()

            actualizar_sesion(sesion_id,
                estado="extrayendo_campus",
                mensaje="Login detectado. Extrayendo datos...",
                progreso=15)
            log(sesion_id, "Login Campus Virtual exitoso. Descargando ICS...")

            campus.go_to_calendar()
            campus.descargar_ics_ciclo(ciclo, anio)
            eventos_campus = campus.extraer_eventos_desde_ics(ciclo, anio)

            actualizar_sesion(sesion_id,
                progreso=45,
                mensaje=f"{len(eventos_campus)} eventos extraídos de Campus Virtual")
            log(sesion_id, f"Campus Virtual: {len(eventos_campus)} eventos")

        # ── PAIDEIA ───────────────────────────────────────────────────────────
        if extraer_paideia:
            actualizar_sesion(sesion_id,
                estado="esperando_login_paideia",
                mensaje="Esperando login en PAIDEIA...",
                progreso=50)

            PAIDEIA_CRONOGRAMAS_DIR.mkdir(parents=True, exist_ok=True)

            if _driver is None:
                _driver = create_driver()
                paideia = PaideiaExtractor(_driver, PAIDEIA_CRONOGRAMAS_DIR)
                paideia.login()
            else:
                paideia = PaideiaExtractor(_driver, PAIDEIA_CRONOGRAMAS_DIR)
                _driver.get("https://paideiacursos.pucp.edu.pe/my/courses.php")

            actualizar_sesion(sesion_id,
                estado="extrayendo_paideia",
                mensaje="Extrayendo datos de PAIDEIA...",
                progreso=60)
            log(sesion_id, "Extrayendo PAIDEIA...")

            try:
                paideia.buscar_por_ciclo(ciclo, anio)
            except Exception as e:
                log(sesion_id, f"Advertencia búsqueda PAIDEIA: {e}")

            eventos_paideia = paideia.extraer_eventos(ciclo, anio)

            actualizar_sesion(sesion_id,
                progreso=80,
                mensaje=f"{len(eventos_paideia)} entregas extraídas de PAIDEIA")
            log(sesion_id, f"PAIDEIA: {len(eventos_paideia)} eventos")

        # ── Google Calendar ───────────────────────────────────────────────
        actualizar_sesion(sesion_id,
            estado="esperando_confirmacion",
            mensaje="Extracción completada. Esperando confirmación del usuario...",
            progreso=82,
            total_campus=len(eventos_campus),
            total_paideia=len(eventos_paideia))

        # Esperar hasta que el usuario confirme desde P8
        import time as time_module
        log(sesion_id, "Esperando confirmación del usuario...")
        timeout = 300  # 5 minutos para confirmar
        elapsed = 0
        confirmado = False
        while elapsed < timeout:
            time_module.sleep(1)
            elapsed += 1
            sesion = sesiones.get(sesion_id, {})
            if sesion.get("confirmado") is True:
                confirmado = True
                break

        if not confirmado:
            actualizar_sesion(sesion_id,
                estado="error",
                mensaje="Tiempo de espera agotado. El usuario no confirmó la sincronización.")
            return

        nombre_cal = sesiones[sesion_id].get(
            "nombre_calendario", f"RPA Académico — {sesion_id[:8]}")

        actualizar_sesion(sesion_id,
            estado="sincronizando",
            mensaje="Creando calendario en Google Calendar...",
            progreso=85)

        # Crear calendario y obtener su ID
        creds = get_credentials()
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)

        calendario_nuevo = service.calendars().insert(body={
            "summary": nombre_cal,
            "timeZone": "America/Lima"
        }).execute()

        nuevo_calendar_id = calendario_nuevo["id"]
        log(sesion_id, f"Calendario creado: {nombre_cal} ({nuevo_calendar_id})")

        actualizar_sesion(sesion_id,
            estado="sincronizando",
            mensaje="Insertando eventos en Google Calendar...",
            progreso=90)

        eventos_finales = resolver_conflictos(eventos_campus, eventos_paideia)
        insertar_eventos(creds, eventos_finales, calendar_id=nuevo_calendar_id)

        actualizar_sesion(sesion_id,
            estado="completado",
            mensaje="Sincronización completada exitosamente",
            progreso=100,
            eventos=eventos_finales,
            total_campus=len(eventos_campus),
            total_paideia=len(eventos_paideia),
            nombre_calendario=nombre_cal,
            calendar_id=nuevo_calendar_id)

        actualizar_sesion(sesion_id,
            estado="completado",
            mensaje="Sincronización completada exitosamente",
            progreso=100,
            eventos=eventos_finales,
            total_campus=len(eventos_campus),
            total_paideia=len(eventos_paideia))
        log(sesion_id, f"Completado: {len(eventos_finales)} eventos insertados")

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
            except:
                pass

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"mensaje": "RPA Académico PUCP - API funcionando"}

@app.get("/health")
def health():
    return {"estado": "ok"}

@app.post("/sincronizacion/iniciar")
def iniciar_sincronizacion(config: ConfiguracionSincronizacion):
    sesion_id = str(uuid.uuid4())
    sesiones[sesion_id] = {
        "estado": "esperando_login_campus",
        "mensaje": "Sesión creada. Iniciando proceso...",
        "progreso": 0,
        "config": config.dict(),
        "eventos": [],
        "logs": [],
        "total_campus": 0,
        "total_paideia": 0,
    }
    # Ejecutar RPA en hilo separado para no bloquear la API
    hilo = threading.Thread(
        target=ejecutar_rpa,
        args=(sesion_id, config.dict()),
        daemon=True
    )
    hilo.start()

    return {
        "sesion_id": sesion_id,
        "estado": "iniciado",
        "mensaje": "Proceso iniciado. Abre Campus Virtual en el navegador."
    }

@app.get("/sincronizacion/{sesion_id}/estado")
def obtener_estado(sesion_id: str):
    if sesion_id not in sesiones:
        return {"error": "Sesión no encontrada"}
    sesion = sesiones[sesion_id].copy()
    sesion.pop("eventos", None)  # no enviar eventos completos aquí
    return sesion

@app.get("/sincronizacion/{sesion_id}/eventos")
def obtener_eventos(sesion_id: str):
    if sesion_id not in sesiones:
        return {"error": "Sesión no encontrada"}
    return {
        "sesion_id": sesion_id,
        "total": len(sesiones[sesion_id].get("eventos", [])),
        "total_campus": sesiones[sesion_id].get("total_campus", 0),
        "total_paideia": sesiones[sesion_id].get("total_paideia", 0),
        "eventos": sesiones[sesion_id].get("eventos", [])
    }

class ConfirmacionBody(BaseModel):
    nombre_calendario: str

@app.post("/sincronizacion/{sesion_id}/confirmar")
def confirmar_sincronizacion(sesion_id: str, body: ConfirmacionBody):
    if sesion_id not in sesiones:
        return {"error": "Sesión no encontrada"}
    sesiones[sesion_id]["nombre_calendario"] = body.nombre_calendario
    sesiones[sesion_id]["confirmado"] = True
    log(sesion_id, f"Usuario confirmó con calendario: {body.nombre_calendario}")
    return {"ok": True, "nombre_calendario": body.nombre_calendario}