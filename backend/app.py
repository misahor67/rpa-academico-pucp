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

sys.path.insert(0, os.path.dirname(__file__))

from sesiones import sesiones, actualizar_sesion, log
from rpa.ejecutar import ejecutar_rpa
from database import get_db, engine
from models import (
    Base, Semestre, ActividadAcademica, Estudiante, Curso, Profesor,
    CursoProfesor, FuenteActividad, TipoActividad, EstadoSemestre,
)
from config import ESTUDIANTE_CODIGO_PUCP, ESTUDIANTE_NOMBRE, ESTUDIANTE_CORREO

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
    recordatorio_minutos: int | None = None  # minutos antes del evento para el recordatorio (popup) en Google Calendar; None = sin recordatorio personalizado


class ConfirmacionBody(BaseModel):
    nombre_calendario: str


# ── Helpers BD ────────────────────────────────────────────────────────────────

def _normalizar_nombre_curso(nombre: str) -> str:
    """Normaliza un nombre de curso para poder compararlo entre Campus
    Virtual y PAIDEIA (mayúsculas, sin espacios extra ni tildes)."""
    import unicodedata
    if not nombre:
        return ""
    nombre = nombre.strip().upper()
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = " ".join(nombre.split())  # colapsa espacios múltiples
    return nombre


def _obtener_o_crear_estudiante(db: Session) -> Estudiante:
    """Sistema mono-usuario: siempre el mismo estudiante, configurado
    en config.py. Ver Capítulo 9, sección 9.2.2, sobre la evolución
    futura hacia un sistema multiusuario."""
    estudiante = db.query(Estudiante).filter_by(
        codigo_pucp=ESTUDIANTE_CODIGO_PUCP
    ).first()
    if not estudiante:
        estudiante = Estudiante(
            codigo_pucp=ESTUDIANTE_CODIGO_PUCP,
            nombre=ESTUDIANTE_NOMBRE,
            correo=ESTUDIANTE_CORREO,
        )
        db.add(estudiante)
        db.flush()
    return estudiante


def _obtener_o_crear_profesor(db: Session, datos_docente: dict) -> Profesor | None:
    """Busca o crea un Profesor a partir de los datos extraídos
    (nombre, codigo_pucp, email). Devuelve None si no hay código
    (no se puede identificar de forma única)."""
    codigo = datos_docente.get("codigo_pucp")
    if not codigo:
        return None

    profesor = db.query(Profesor).filter_by(codigo_pucp=codigo).first()
    if not profesor:
        profesor = Profesor(
            codigo_pucp=codigo,
            nombre=datos_docente.get("nombre") or "Sin nombre",
            email=datos_docente.get("email"),
        )
        db.add(profesor)
        db.flush()
    return profesor


def _crear_indice_cursos(db: Session, cursos_extraidos: list[dict], semestre: Semestre) -> dict:
    """
    Crea (o reutiliza) en BD cada curso de cursos_extraidos, asociando
    sus docentes vía CursoProfesor. Devuelve un índice para resolver
    rápidamente el id_curso de cada actividad académica:
        {
            "por_codigo": {codigo_curso: id_curso},
            "por_nombre": {nombre_normalizado: id_curso},
        }
    """
    indice = {"por_codigo": {}, "por_nombre": {}}

    for c in cursos_extraidos:
        codigo = c.get("codigo")
        nombre = c.get("nombre") or "Curso sin nombre"
        if not codigo:
            continue

        curso = db.query(Curso).filter_by(
            codigo=codigo, id_semestre=semestre.id_semestre
        ).first()
        if not curso:
            creditos = None
            try:
                creditos = float(c.get("creditos")) if c.get("creditos") else None
            except (TypeError, ValueError):
                creditos = None

            curso = Curso(
                codigo=codigo,
                nombre=nombre[:150],
                creditos=creditos,
                horario=c.get("horario"),
                id_semestre=semestre.id_semestre,
            )
            db.add(curso)
            db.flush()

        # Asociar docente(s), evitando duplicados en curso_profesor
        for docente in c.get("docentes", []):
            profesor = _obtener_o_crear_profesor(db, docente)
            if not profesor:
                continue
            existe = db.query(CursoProfesor).filter_by(
                id_curso=curso.id_curso, id_profesor=profesor.id_profesor
            ).first()
            if not existe:
                db.add(CursoProfesor(id_curso=curso.id_curso, id_profesor=profesor.id_profesor))

        indice["por_codigo"][codigo] = curso.id_curso
        indice["por_nombre"][_normalizar_nombre_curso(nombre)] = curso.id_curso

    db.flush()
    return indice


def _resolver_id_curso(ev: dict, indice: dict, curso_generico_id: int) -> int:
    """
    Resuelve el id_curso real de un evento, probando primero por código
    de curso. Tanto los eventos de Campus Virtual (vía SUMMARY del .ics)
    como los de PAIDEIA (vía el título de la página del curso, formato
    "AÑO-CICLO NOMBRE (CODIGO-HORARIO)") ya traen el código real de
    curso en ev["codigo"]. El cruce por nombre normalizado se mantiene
    solo como respaldo, para el caso en que el código no esté disponible.
    Si no hay coincidencia alguna, devuelve el curso genérico de respaldo.
    """
    codigo_ev = ev.get("codigo")
    if codigo_ev and codigo_ev in indice["por_codigo"]:
        return indice["por_codigo"][codigo_ev]

    nombre_ev = ev.get("curso") or ev.get("titulo") or ev.get("nombre") or ""
    nombre_norm = _normalizar_nombre_curso(nombre_ev)
    if nombre_norm and nombre_norm in indice["por_nombre"]:
        return indice["por_nombre"][nombre_norm]

    return curso_generico_id


def _obtener_o_crear_curso_generico(db: Session, semestre: Semestre) -> Curso:
    """
    Curso de respaldo para actividades que no se pudieron asociar a
    ningún curso real extraído (p. ej. si la extracción de cursos falló
    o el nombre no coincide con ningún curso conocido). Mantiene la
    integridad referencial sin recurrir a relajar las foreign keys.
    """
    curso = db.query(Curso).filter_by(
        codigo="SIN_CURSO", id_semestre=semestre.id_semestre
    ).first()
    if not curso:
        curso = Curso(
            codigo="SIN_CURSO",
            nombre="Actividad sin curso identificado",
            id_semestre=semestre.id_semestre,
        )
        db.add(curso)
        db.flush()
    return curso


def guardar_sincronizacion_en_bd(sesion_id: str, db: Session):
    """Guarda el resultado de la sincronización en la base de datos,
    asociando cada actividad a su curso, docente(s) y estudiante reales."""
    sesion = sesiones.get(sesion_id)
    if not sesion:
        return

    config = sesion.get("config", {})
    ciclo = config.get("ciclo", 0)
    anio = config.get("anio", datetime.now().year)
    eventos = sesion.get("eventos", [])
    cursos_extraidos = sesion.get("cursos", [])

    try:
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

        # 2. Estudiante (único, mono-usuario)
        estudiante = _obtener_o_crear_estudiante(db)

        # 3. Cursos reales + docentes, a partir de lo extraído de Campus Virtual
        indice_cursos = _crear_indice_cursos(db, cursos_extraidos, semestre)
        curso_generico = _obtener_o_crear_curso_generico(db, semestre)

        # Diccionario id_curso -> nombre de curso, para enriquecer el
        # reporte de cambios detectados (R3.1) con el curso al que
        # pertenece cada actividad nueva o modificada.
        nombres_curso_por_id: dict[int, str] = {
            row.id_curso: row.nombre
            for row in db.query(Curso.id_curso, Curso.nombre).filter_by(
                id_semestre=semestre.id_semestre
            ).all()
        }

        # 3.5. Capturar snapshot de las actividades de una sincronización
        # anterior del MISMO semestre (antes de borrarlas), para poder
        # comparar después qué actividades son nuevas o cambiaron de
        # fecha respecto a esta sincronización (ver R3.1: detección de
        # cambios). La clave de comparación es el identificador estable
        # de cada actividad (uid del .ics de Campus Virtual, o url de la
        # tarea en PAIDEIA) — NO el nombre del curso, ya que varias
        # actividades distintas de un mismo curso comparten ese nombre.
        # Si una actividad no trae identificador estable, se usa
        # (id_curso, nombre, fecha_inicio original) como respaldo, a
        # costa de no poder detectar cambios de fecha para ese caso.
        ids_curso_semestre = [
            row.id_curso for row in db.query(Curso.id_curso).filter_by(
                id_semestre=semestre.id_semestre
            ).all()
        ]
        actividades_anteriores: dict[str, datetime] = {}
        if ids_curso_semestre:
            previas = db.query(ActividadAcademica).filter(
                ActividadAcademica.id_estudiante == estudiante.id_estudiante,
                ActividadAcademica.id_curso.in_(ids_curso_semestre),
            ).all()
            for p in previas:
                clave_previa = p.url_origen or f"{p.id_curso}|{p.nombre}|{p.fecha_inicio.isoformat()}"
                actividades_anteriores[clave_previa] = p.fecha_inicio

            eliminadas = db.query(ActividadAcademica).filter(
                ActividadAcademica.id_estudiante == estudiante.id_estudiante,
                ActividadAcademica.id_curso.in_(ids_curso_semestre),
            ).delete(synchronize_session=False)
            if eliminadas:
                print(f"BD: {eliminadas} actividades de una sincronización "
                      f"anterior de este semestre fueron reemplazadas.")

        # 4. Guardar cada evento como actividad_academica, detectando en
        # el proceso si es una actividad nueva o si cambió de fecha
        # respecto a la sincronización anterior.
        actividades_nuevas: list[dict] = []
        actividades_modificadas: list[dict] = []

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

            id_curso = _resolver_id_curso(ev, indice_cursos, curso_generico.id_curso)
            nombre_guardado = nombre[:255]
            nombre_curso = nombres_curso_por_id.get(id_curso, "Curso sin identificar")

            # Detección de cambios respecto a la sincronización anterior (R3.1)
            clave = url_origen or f"{id_curso}|{nombre_guardado}|{fecha_inicio.isoformat()}"
            fecha_anterior = actividades_anteriores.get(clave)
            if fecha_anterior is None:
                actividades_nuevas.append({
                    "nombre": nombre_guardado,
                    "curso": nombre_curso,
                    "fuente": fuente,
                    "fecha": fecha_inicio.isoformat(),
                })
            elif fecha_anterior != fecha_inicio:
                actividades_modificadas.append({
                    "nombre": nombre_guardado,
                    "curso": nombre_curso,
                    "fuente": fuente,
                    "fecha_anterior": fecha_anterior.isoformat(),
                    "fecha_nueva": fecha_inicio.isoformat(),
                })

            actividad = ActividadAcademica(
                nombre=nombre_guardado,
                tipo=tipo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin or fecha_inicio,
                fuente=fuente,
                url_origen=str(url_origen)[:500] if url_origen else None,
                id_curso=id_curso,
                id_estudiante=estudiante.id_estudiante,
            )
            db.add(actividad)

        db.commit()
        print(f"BD: {len(eventos)} actividades guardadas para ciclo {ciclo}/{anio}")

        return {
            "actividades_nuevas": actividades_nuevas,
            "actividades_modificadas": actividades_modificadas,
        }

    except Exception as e:
        db.rollback()
        print(f"Error guardando en BD: {e}")
        return {"actividades_nuevas": [], "actividades_modificadas": []}


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
