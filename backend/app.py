# backend/app.py
import uuid
import threading
import sys
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))

from sesiones import sesiones, actualizar_sesion, log
from rpa.ejecutar import ejecutar_rpa

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


class ConfiguracionSincronizacion(BaseModel):
    ciclo: int
    anio: int
    campus: bool
    paideia: bool


class ConfirmacionBody(BaseModel):
    nombre_calendario: str


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
