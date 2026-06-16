# backend/sesiones.py

sesiones: dict = {}

def actualizar_sesion(sesion_id: str, **kwargs):
    if sesion_id in sesiones:
        sesiones[sesion_id].update(kwargs)

def log(sesion_id: str, mensaje: str):
    if sesion_id in sesiones:
        logs = sesiones[sesion_id].get("logs", [])
        logs.append(mensaje)
        sesiones[sesion_id]["logs"] = logs[-20:]
    print(mensaje)
