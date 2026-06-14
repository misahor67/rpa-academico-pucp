# backend/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google_calendar.calendar_inserter import _construir_evento_google
import uuid
import threading
import sys
import os

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

sesiones = {}

class ConfiguracionSincronizacion(BaseModel):
    ciclo: int
    anio: int
    campus: bool
    paideia: bool

class ConfirmacionBody(BaseModel):
    nombre_calendario: str

def actualizar_sesion(sesion_id: str, **kwargs):
    if sesion_id in sesiones:
        sesiones[sesion_id].update(kwargs)

def log(sesion_id: str, mensaje: str):
    if sesion_id in sesiones:
        logs = sesiones[sesion_id].get("logs", [])
        logs.append(mensaje)
        sesiones[sesion_id]["logs"] = logs[-20:]
    print(mensaje)

def ejecutar_rpa(sesion_id: str, config: dict):
    try:
        from create_driver import create_driver
        from campus.campus_extractor import CampusCalendarioIcs
        from paideia.paideia_extractor import PaideiaExtractor
        from google_calendar.auth import get_credentials
        from google_calendar.conflict_resolver import resolver_conflictos
        from config import ICS_DIR, PAIDEIA_CRONOGRAMAS_DIR

        ciclo = config["ciclo"]
        anio = config["anio"]
        extraer_campus = config["campus"]
        extraer_paideia = config["paideia"]

        eventos_campus = []
        eventos_paideia = []
        pdfs_estado = []
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

            # Guardar PDFs detectados para P7
            if hasattr(paideia, 'cronogramas_descargados'):
                for pdf in paideia.cronogramas_descargados:
                    pdfs_estado.append({
                        "nombre": pdf.get("archivo", "cronograma.pdf"),
                        "curso": pdf.get("curso", ""),
                        "estado": "procesable",
                        "mensaje": "Cronograma descargado correctamente."
                    })

            actualizar_sesion(sesion_id,
                progreso=80,
                pdfs=pdfs_estado,
                mensaje=f"{len(eventos_paideia)} entregas extraídas de PAIDEIA")
            log(sesion_id, f"PAIDEIA: {len(eventos_paideia)} eventos — {len(pdfs_estado)} PDFs")

        # ── Esperar confirmación del usuario (P8) ─────────────────────────────
        actualizar_sesion(sesion_id,
            estado="esperando_confirmacion",
            mensaje="Extracción completada. Esperando confirmación del usuario...",
            progreso=82,
            total_campus=len(eventos_campus),
            total_paideia=len(eventos_paideia),
            pdfs=pdfs_estado)

        import time as time_module
        log(sesion_id, "Esperando confirmación del usuario...")
        timeout = 300
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
                mensaje="Tiempo de espera agotado. El usuario no confirmó.")
            return

        nombre_cal = sesiones[sesion_id].get(
            "nombre_calendario", f"RPA Académico — {sesion_id[:8]}")

        # ── Crear calendario ──────────────────────────────────────────────────
        actualizar_sesion(sesion_id,
            estado="sincronizando",
            mensaje="Creando calendario en Google Calendar...",
            progreso=85)

        # Crear calendario — eliminar si ya existe uno con el mismo nombre
        creds = get_credentials()
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)

        # Buscar y eliminar calendario existente con el mismo nombre
        calendarios = service.calendarList().list().execute()
        for cal in calendarios.get("items", []):
            if cal.get("summary") == nombre_cal:
                service.calendars().delete(calendarId=cal["id"]).execute()
                log(sesion_id, f"Calendario anterior eliminado: {nombre_cal}")
                break

        # Crear nuevo calendario limpio
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

        # ── Insertar eventos con progreso ─────────────────────────────────────
        eventos_finales = resolver_conflictos(eventos_campus, eventos_paideia)
        total_insertar = len(eventos_finales)
        actualizar_sesion(sesion_id, total_insertar=total_insertar, insertados=0)

        from googleapiclient.discovery import build as build_service
        service_cal = build_service("calendar", "v3", credentials=creds)

        insertados = 0
        for evento in eventos_finales:
            evento_google = _construir_evento_google(evento)
            if evento_google is None:
                continue
            try:
                service_cal.events().insert(
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
        "pdfs": [],
    }
    hilo = threading.Thread(
        target=ejecutar_rpa,
        args=(sesion_id, config.dict()),
        daemon=True
    )
    hilo.start()
    return {
        "sesion_id": sesion_id,
        "estado": "iniciado",
        "mensaje": "Proceso iniciado."
    }

@app.get("/sincronizacion/{sesion_id}/estado")
def obtener_estado(sesion_id: str):
    if sesion_id not in sesiones:
        return {"error": "Sesión no encontrada"}
    sesion = sesiones[sesion_id].copy()
    sesion.pop("eventos", None)
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

@app.post("/sincronizacion/{sesion_id}/confirmar")
def confirmar_sincronizacion(sesion_id: str, body: ConfirmacionBody):
    if sesion_id not in sesiones:
        return {"error": "Sesión no encontrada"}
    sesiones[sesion_id]["nombre_calendario"] = body.nombre_calendario
    sesiones[sesion_id]["confirmado"] = True
    log(sesion_id, f"Usuario confirmó con calendario: {body.nombre_calendario}")
    return {"ok": True, "nombre_calendario": body.nombre_calendario}