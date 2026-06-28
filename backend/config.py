# config.py
import datetime
from pathlib import Path

CICLOS = {
    0: {"nombre": "Verano",    "meses": [1, 2, 3]},
    1: {"nombre": "Regular 1", "meses": [3, 4, 5, 6, 7]},
    2: {"nombre": "Regular 2", "meses": [8, 9, 10, 11, 12]},
}

NOMBRES_MESES = {
    1: "Enero",  2: "Febrero",  3: "Marzo",
    4: "Abril",  5: "Mayo",     6: "Junio",
    7: "Julio",  8: "Agosto",   9: "Septiembre",
    10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

MESES_A_NUMERO = {v.lower(): k for k, v in NOMBRES_MESES.items()}

ICS_DIR = Path(__file__).resolve().parent / "ics"
PAIDEIA_CRONOGRAMAS_DIR = Path(__file__).resolve().parent / "cronogramas_paideia"
PAIDEIA_EVENTOS_JSON_DIR = Path(__file__).resolve().parent / "eventos_paideia_json"
DOWNLOAD_WAIT_SEC = 120
CALENDAR_ID = "c_c9b60a71fe38b69e40f9357da3d9afd91a76cfa408bcf03db2d00d9c832460f7@group.calendar.google.com"

# ── Estudiante (sistema mono-usuario en esta versión) ─────────────────────────
# El sistema actual está diseñado para un único estudiante por instalación.
# Si en el futuro el sistema evoluciona a multiusuario (ver Capítulo 9,
# "Trabajos futuros", sección 9.2.2), este valor debería reemplazarse por
# el código del estudiante autenticado en cada sesión.
ESTUDIANTE_CODIGO_PUCP = "20197102"
ESTUDIANTE_NOMBRE = "VEGA GRIJALVA, LEONARDO JOSE"
ESTUDIANTE_CORREO = "a20197102@pucp.edu.pe"