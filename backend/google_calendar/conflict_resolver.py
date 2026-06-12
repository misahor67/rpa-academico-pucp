# google_calendar/conflict_resolver.py
import datetime


def _obtener_rango(evento: dict) -> tuple[datetime.datetime, datetime.datetime] | None:
    """Extrae inicio y fin del evento como datetime. Retorna None si no tiene fechas."""
    inicio = evento.get("inicio")
    fin = evento.get("fin")

    if not inicio or not fin:
        return None

    if isinstance(inicio, datetime.date) and not isinstance(inicio, datetime.datetime):
        inicio = datetime.datetime.combine(inicio, datetime.time.min)
    if isinstance(fin, datetime.date) and not isinstance(fin, datetime.datetime):
        fin = datetime.datetime.combine(fin, datetime.time.min)

    return inicio, fin


def _hay_choque(rango_a, rango_b) -> bool:
    """Determina si dos rangos de tiempo se solapan."""
    inicio_a, fin_a = rango_a
    inicio_b, fin_b = rango_b
    return inicio_a < fin_b and inicio_b < fin_a


def resolver_conflictos(
    eventos_campus: list[dict],
    eventos_paideia: list[dict],
) -> list[dict]:
    """
    Combina eventos de Campus y PAIDEIA.
    Si dos eventos se solapan en horario, se agregan ambos y se avisa por consola.
    """
    for ev in eventos_campus:
        ev["fuente"] = "campus"
    for ev in eventos_paideia:
        ev["fuente"] = "paideia"

    todos = eventos_campus + eventos_paideia
    choques: int = 0

    for i, evento_a in enumerate(todos):
        rango_a = _obtener_rango(evento_a)
        if rango_a is None:
            continue

        for evento_b in todos[i + 1:]:
            rango_b = _obtener_rango(evento_b)
            if rango_b is None:
                continue

            if _hay_choque(rango_a, rango_b):
                choques += 1
                print(
                    f"  Aviso de choque: '{evento_a.get('curso', evento_a.get('titulo', ''))}' "
                    f"({evento_a['fuente']}) choca con "
                    f"'{evento_b.get('curso', evento_b.get('titulo', ''))}' "
                    f"({evento_b['fuente']})"
                )

    print(f"\nTotal eventos: {len(todos)} | Choques detectados: {choques}")
    return todos