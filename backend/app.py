# backend/app.py
import uuid
import threading
import sys
import os
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(__file__))

from sesiones import sesiones, actualizar_sesion, log
from rpa.ejecutar import ejecutar_rpa
from database import get_db, engine
from models import Base, Semestre, ActividadAcademica, Estudiante, Curso, FuenteActividad, TipoActividad, EstadoSemestre

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

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


# ── Helpers BD ────────────────────────────────────────────────────────────────

def guardar_sincronizacion_en_bd(sesion_id: str, db: Session):
    """Guarda el resultado de la sincronización en la base de datos."""
    sesion = sesiones.get(sesion_id)
    if not sesion:
        return

    config = sesion.get("config", {})
    ciclo = config.get("ciclo", 0)
    anio = config.get("anio", datetime.now().year)
    eventos = sesion.get("eventos", [])

    try:
        db.execute(text("SET FOREIGN_KEY_CHECKS=0"))  # ← agregar

        # 1. Buscar o crear semestre
        semestre = db.query(Semestre).filter_by(ciclo=ciclo, anio=anio).first()
        if not semestre:
            nombres = {0: f"Verano {anio}", 1: f"Regular 1 {anio}", 2: f"Regular 2 {anio}"}
            semestre = Semestre(
                nombre=nombres.get(ciclo, f"Ciclo {ciclo} {anio}"),
                anio=anio,
                ciclo=ciclo,
                fecha_inicio=datetime(anio, 1, 1).date(),
                fecha_fin=datetime(anio, 12, 31).date(),
                estado="Ciclo de verano" if ciclo == 0 else "Semestre regular"
            )
            db.add(semestre)
            db.flush()

        # 2. Guardar cada evento como actividad_academica
        for ev in eventos:
            nombre = ev.get("curso") or ev.get("summary") or ev.get("titulo") or ev.get("nombre") or "Sin nombre"
            fecha_inicio = ev.get("inicio") or ev.get("dtstart") or ev.get("fecha_inicio")
            fecha_fin = ev.get("fin") or ev.get("dtend") or ev.get("fecha_fin")
            fuente_str = ev.get("fuente", "campus")
            url_origen = ev.get("uid") or ev.get("url") or ev.get("url_origen")

            # Convertir fechas si vienen como string
            if isinstance(fecha_inicio, str):
                try:
                    fecha_inicio = datetime.fromisoformat(fecha_inicio)
                except Exception:
                    fecha_inicio = datetime.now()
            if isinstance(fecha_fin, str):
                try:
                    fecha_fin = datetime.fromisoformat(fecha_fin)
                except Exception:
                    fecha_fin = fecha_inicio

            if not fecha_inicio:
                continue

            # Determinar fuente
            fuente = "Campus Virtual" if "campus" in fuente_str.lower() else "PAIDEIA"

            # Determinar tipo
            nombre_lower = nombre.lower()
            if "examen" in nombre_lower or "exam" in nombre_lower:
                tipo = "Examen"
            elif "práctica" in nombre_lower or "practica" in nombre_lower:
                tipo = "Práctica"
            elif "laboratorio" in nombre_lower or "lab" in nombre_lower:
                tipo = "Laboratorio"
            elif fuente == "PAIDEIA":
                tipo = "Entrega"
            else:
                tipo = "Clase"

            actividad = ActividadAcademica(
                nombre=nombre[:255],
                tipo=tipo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin or fecha_inicio,
                fuente=fuente,
                url_origen=str(url_origen)[:500] if url_origen else None,
                id_curso=1,       # placeholder — se mejora cuando se conecte curso real
                id_estudiante=1,  # placeholder — se mejora cuando se conecte estudiante real
            )
            db.add(actividad)

        db.commit()
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        print(f"BD: {len(eventos)} actividades guardadas para ciclo {ciclo}/{anio}")

    except Exception as e:
        db.rollback()
        print(f"Error guardando en BD: {e}")


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


@app.post("/sincronizacion/{sesion_id}/guardar")
def guardar_sincronizacion(sesion_id: str, db: Session = Depends(get_db)):
    """Guarda los eventos de la sincronización completada en la base de datos."""
    if sesion_id not in sesiones:
        return {"error": "Sesión no encontrada"}
    if sesiones[sesion_id].get("estado") != "completado":
        return {"error": "La sincronización aún no está completada"}
    guardar_sincronizacion_en_bd(sesion_id, db)
    return {"ok": True, "mensaje": "Sincronización guardada en base de datos"}


@app.get("/historial")
def obtener_historial(db: Session = Depends(get_db)):
    """Retorna el historial de semestres sincronizados."""
    try:
        semestres = db.query(Semestre).order_by(Semestre.anio.desc(), Semestre.ciclo.desc()).all()
        resultado = []
        for s in semestres:
            total = db.query(ActividadAcademica).filter(
                ActividadAcademica.fecha_inicio >= s.fecha_inicio,
                ActividadAcademica.fecha_inicio <= s.fecha_fin
            ).count()
            resultado.append({
                "id_semestre": s.id_semestre,
                "nombre": s.nombre,
                "anio": s.anio,
                "ciclo": s.ciclo,
                "fecha_inicio": str(s.fecha_inicio),
                "fecha_fin": str(s.fecha_fin),
                "total_actividades": total,
            })
        return {"historial": resultado}
    except Exception as e:
        return {"error": str(e), "historial": []}
