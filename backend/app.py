# backend/app.py
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

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

# Almacén temporal de sesiones en memoria
sesiones = {}

# ── Modelos ──────────────────────────────────────────────────────────────────
class ConfiguracionSincronizacion(BaseModel):
    ciclo: int        # 0=Verano, 1=Regular1, 2=Regular2
    anio: int
    campus: bool      # True si extrae Campus Virtual
    paideia: bool     # True si extrae PAIDEIA

class EstadoSesion(BaseModel):
    sesion_id: str
    estado: str       # "esperando_login", "extrayendo", "completado", "error"
    mensaje: str
    progreso: int     # 0-100
    eventos: list = []

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"mensaje": "RPA Académico PUCP - API funcionando"}

@app.get("/health")
def health():
    return {"estado": "ok"}

@app.post("/sincronizacion/iniciar")
def iniciar_sincronizacion(config: ConfiguracionSincronizacion):
    """
    Recibe la configuración del usuario y crea una nueva sesión de sincronización.
    """
    sesion_id = str(uuid.uuid4())
    sesiones[sesion_id] = {
        "estado": "esperando_login",
        "mensaje": "Esperando login en Campus Virtual...",
        "progreso": 0,
        "config": config.dict(),
        "eventos": []
    }
    return {
        "sesion_id": sesion_id,
        "estado": "esperando_login",
        "mensaje": "Sesión creada. Redirigiendo al login..."
    }

@app.get("/sincronizacion/{sesion_id}/estado")
def obtener_estado(sesion_id: str):
    """
    El frontend consulta este endpoint cada pocos segundos para ver el progreso.
    """
    if sesion_id not in sesiones:
        return {"error": "Sesión no encontrada"}
    return sesiones[sesion_id]

@app.get("/sincronizacion/{sesion_id}/eventos")
def obtener_eventos(sesion_id: str):
    """
    Retorna los eventos extraídos de una sesión completada.
    """
    if sesion_id not in sesiones:
        return {"error": "Sesión no encontrada"}
    return {
        "sesion_id": sesion_id,
        "total": len(sesiones[sesion_id]["eventos"]),
        "eventos": sesiones[sesion_id]["eventos"]
    }