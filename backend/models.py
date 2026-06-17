# backend/models.py
from sqlalchemy import (
    Column, Integer, SmallInteger, String, Date, DateTime,
    Enum, Text, DECIMAL, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base
import enum


# ── Enums ─────────────────────────────────────────────────────────────────────

class EstadoSemestre(str, enum.Enum):
    semestre_regular = "Semestre regular"
    ciclo_verano = "Ciclo de verano"

class TipoActividad(str, enum.Enum):
    clase = "Clase"
    laboratorio = "Laboratorio"
    practica = "Práctica"
    examen = "Examen"
    entrega = "Entrega"

class RecurrenciaActividad(str, enum.Enum):
    semanal = "Semanal"
    quincenal = "Quincenal"
    una_vez = "Solo una vez"

class EstadoActividad(str, enum.Enum):
    pendiente = "Pendiente"
    completado = "Completado"

class FuenteActividad(str, enum.Enum):
    campus = "Campus Virtual"
    paideia = "PAIDEIA"


# ── T01: semestre ─────────────────────────────────────────────────────────────

class Semestre(Base):
    __tablename__ = "semestre"

    id_semestre  = Column(Integer, primary_key=True, autoincrement=True)
    nombre       = Column(String(20), nullable=False)
    anio         = Column(SmallInteger, nullable=False)
    ciclo        = Column(SmallInteger, nullable=False, comment="0=Verano, 1=Primero, 2=Segundo")
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin    = Column(Date, nullable=False)
    estado = Column(Enum("Semestre regular", "Ciclo de verano"), nullable=False, default="Semestre regular")

    cursos = relationship("Curso", back_populates="semestre")


# ── T02: curso ────────────────────────────────────────────────────────────────

class Curso(Base):
    __tablename__ = "curso"

    id_curso     = Column(Integer, primary_key=True, autoincrement=True)
    codigo       = Column(String(10), nullable=False)
    nombre       = Column(String(150), nullable=False)
    modalidad    = Column(String(30), nullable=True)
    creditos     = Column(DECIMAL(4, 2), nullable=True)
    facultad     = Column(String(100), nullable=True)
    seccion      = Column(String(10), nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin    = Column(Date, nullable=True)
    horario      = Column(String(10), nullable=True)
    id_semestre  = Column(Integer, ForeignKey("semestre.id_semestre"), nullable=False)

    semestre      = relationship("Semestre", back_populates="cursos")
    actividades   = relationship("ActividadAcademica", back_populates="curso")
    estudiantes   = relationship("CursoEstudiante", back_populates="curso")
    profesores    = relationship("CursoProfesor", back_populates="curso")


# ── T03: estudiante ───────────────────────────────────────────────────────────

class Estudiante(Base):
    __tablename__ = "estudiante"

    id_estudiante = Column(Integer, primary_key=True, autoincrement=True)
    codigo_pucp   = Column(String(8), nullable=False, unique=True)
    nombre        = Column(String(150), nullable=False)
    correo        = Column(String(150), nullable=False, unique=True)
    especialidad  = Column(String(100), nullable=True)

    actividades = relationship("ActividadAcademica", back_populates="estudiante")
    cursos      = relationship("CursoEstudiante", back_populates="estudiante")


# ── T04: profesor ─────────────────────────────────────────────────────────────

class Profesor(Base):
    __tablename__ = "profesor"

    id_profesor = Column(Integer, primary_key=True, autoincrement=True)
    codigo_pucp = Column(String(8), nullable=False, unique=True)
    nombre      = Column(String(150), nullable=False)
    email       = Column(String(150), nullable=True)

    cursos = relationship("CursoProfesor", back_populates="profesor")


# ── T05: actividad_academica ──────────────────────────────────────────────────

class ActividadAcademica(Base):
    __tablename__ = "actividad_academica"

    id_actividad  = Column(Integer, primary_key=True, autoincrement=True)
    nombre        = Column(String(255), nullable=False)
    tipo          = Column(Enum("Clase", "Laboratorio", "Práctica", "Examen", "Entrega"), nullable=False)
    fecha_inicio  = Column(DateTime, nullable=False)
    fecha_fin     = Column(DateTime, nullable=False)
    recurrencia   = Column(Enum("Semanal", "Quincenal", "Solo una vez"), nullable=False, default="Solo una vez")
    estado        = Column(Enum("Pendiente", "Completado"), nullable=False, default="Pendiente")
    lugar         = Column(String(100), nullable=True)
    fuente        = Column(Enum("Campus Virtual", "PAIDEIA"), nullable=False)
    url_origen    = Column(Text, nullable=True)
    id_curso      = Column(Integer, ForeignKey("curso.id_curso"), nullable=False)
    id_estudiante = Column(Integer, ForeignKey("estudiante.id_estudiante"), nullable=False)

    curso       = relationship("Curso", back_populates="actividades")
    estudiante  = relationship("Estudiante", back_populates="actividades")
    notificaciones = relationship("Notificacion", back_populates="actividad")


# ── T06: notificacion ─────────────────────────────────────────────────────────

class Notificacion(Base):
    __tablename__ = "notificacion"

    id_notificacion        = Column(Integer, primary_key=True, autoincrement=True)
    nombre                 = Column(String(200), nullable=False)
    correo_destino         = Column(String(150), nullable=False)
    mensaje                = Column(Text, nullable=True)
    tiempo_anticipacion    = Column(Integer, nullable=False, comment="Minutos antes del evento")
    id_actividad_academica = Column(Integer, ForeignKey("actividad_academica.id_actividad"), nullable=False)

    actividad = relationship("ActividadAcademica", back_populates="notificaciones")


# ── T07: curso_estudiante ─────────────────────────────────────────────────────

class CursoEstudiante(Base):
    __tablename__ = "curso_estudiante"

    id_curso      = Column(Integer, ForeignKey("curso.id_curso"), primary_key=True)
    id_estudiante = Column(Integer, ForeignKey("estudiante.id_estudiante"), primary_key=True)

    curso      = relationship("Curso", back_populates="estudiantes")
    estudiante = relationship("Estudiante", back_populates="cursos")


# ── T08: curso_profesor ───────────────────────────────────────────────────────

class CursoProfesor(Base):
    __tablename__ = "curso_profesor"

    id_curso    = Column(Integer, ForeignKey("curso.id_curso"), primary_key=True)
    id_profesor = Column(Integer, ForeignKey("profesor.id_profesor"), primary_key=True)

    curso    = relationship("Curso", back_populates="profesores")
    profesor = relationship("Profesor", back_populates="cursos")
