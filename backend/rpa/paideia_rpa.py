# backend/rpa/paideia_rpa.py

from paideia.paideia_extractor import PaideiaExtractor
from config import PAIDEIA_CRONOGRAMAS_DIR
from sesiones import actualizar_sesion, log


def ejecutar_paideia(sesion_id: str, driver, ciclo: int, anio: int, tiene_sesion_previa: bool = False) -> tuple[list, list]:
    """
    Extrae entregas de PAIDEIA y retorna (eventos_paideia, pdfs_estado).

    tiene_sesion_previa: True si el driver ya tiene sesión activa de Campus Virtual.
    En ese caso se navega directo a PAIDEIA sin pedir login.
    Si es False (solo PAIDEIA), se espera que el usuario haga login manualmente.
    """
    actualizar_sesion(sesion_id,
        estado="esperando_login_paideia",
        mensaje="Esperando login en PAIDEIA...",
        progreso=50)

    PAIDEIA_CRONOGRAMAS_DIR.mkdir(parents=True, exist_ok=True)
    paideia = PaideiaExtractor(driver, PAIDEIA_CRONOGRAMAS_DIR)

    if tiene_sesion_previa:
        # El driver ya tiene sesión PUCP activa desde Campus Virtual,
        # navegar directo a PAIDEIA sin necesidad de login adicional
        driver.get("https://paideiacursos.pucp.edu.pe/my/courses.php")
    else:
        # Solo PAIDEIA: el driver es nuevo, el usuario debe hacer login manualmente
        paideia.login()

    actualizar_sesion(sesion_id,
        estado="extrayendo_paideia",
        mensaje="Extrayendo datos de PAIDEIA...",
        progreso=60)
    log(sesion_id, "Extrayendo PAIDEIA...")

    try:
        paideia.buscar_por_ciclo(ciclo, anio)
    except Exception as e:
        log(sesion_id, f"Advertencia búsqueda PAIDEIA: {e}")

    # Inicializar estado de cursos en la sesión (se irá actualizando con el callback)
    actualizar_sesion(sesion_id, cursos_paideia=[])

    def on_curso_procesado(curso_info: dict):
        """Callback llamado por el extractor después de procesar cada curso."""
        sesion_cursos = []

        # Reconstruir lista acumulada de cursos procesados
        # Usamos idx para saber cuántos van
        idx = curso_info["idx"]
        total = curso_info["total"]

        # Leer estado actual de cursos en sesión
        from sesiones import sesiones
        cursos_actuales = sesiones.get(sesion_id, {}).get("cursos_paideia", [])

        # Agregar el curso recién procesado
        cursos_actuales.append({
            "titulo": curso_info["titulo"],
            "course_id": curso_info["course_id"],
            "secciones": curso_info["secciones"],
            "entregas": curso_info["entregas"],
            "pdfs": curso_info["pdfs"],
            "estado": "completado",
        })

        # Calcular totales acumulados
        total_entregas = sum(c["entregas"] for c in cursos_actuales)
        total_pdfs = sum(c["pdfs"] for c in cursos_actuales)

        progreso = 60 + int(((idx + 1) / total) * 20)  # de 60% a 80%

        actualizar_sesion(sesion_id,
            cursos_paideia=cursos_actuales,
            total_cursos_paideia=total,
            cursos_completados_paideia=idx + 1,
            total_entregas_paideia=total_entregas,
            total_pdfs_paideia=total_pdfs,
            progreso=progreso)

        log(sesion_id, f"PAIDEIA [{idx + 1}/{total}] {curso_info['titulo']}: {curso_info['entregas']} entregas, {curso_info['pdfs']} PDFs")

    eventos_paideia = paideia.extraer_eventos(ciclo, anio, callback=on_curso_procesado)

    # Construir pdfs_estado para P7
    pdfs_estado = []
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

    return eventos_paideia, pdfs_estado
