"""Calculo: de un flujo de lecturas a un resumen por tag."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from statistics import fmean, pstdev

from .modelos import Estadisticas, Lectura, Limite


def agrupar_por_tag(lecturas: Iterable[Lectura]) -> dict[str, list[Lectura]]:
    """Agrupa las lecturas por tag conservando el orden de aparicion.

    ``defaultdict(list)`` evita el clasico ``if tag not in grupos: grupos[tag] = []``
    en cada iteracion.
    """
    grupos: defaultdict[str, list[Lectura]] = defaultdict(list)
    for lectura in lecturas:
        grupos[lectura.tag].append(lectura)
    # Se devuelve un dict normal: un defaultdict que escapa del modulo crea
    # claves fantasma con solo consultarlo (grupos["TT-999"] -> [] y queda).
    return dict(grupos)


def estadisticas_de_tag(
    tag: str, lecturas: Sequence[Lectura], limite: Limite | None = None
) -> Estadisticas:
    """Calcula el resumen de un tag.

    Raises:
        ValueError: si no hay lecturas. Un min/max/promedio de cero muestras no
            existe, y devolver 0.0 seria mentir sobre el proceso.
    """
    if not lecturas:
        raise ValueError(f"{tag}: no hay lecturas para calcular estadisticas")

    # List comprehension: los valores se recorren varias veces (min, max, fmean),
    # asi que conviene materializarlos una sola vez.
    valores = [lectura.valor for lectura in lecturas]

    # Set comprehension: normalmente da un unico elemento; si da mas de uno, el
    # CSV mezcla unidades para el mismo tag y hay que verlo en el reporte.
    unidades = {lectura.unidad for lectura in lecturas}
    unidad = unidades.pop() if len(unidades) == 1 else "/".join(sorted(unidades))

    # Expresion generadora dentro de sum(): cuenta sin construir la lista.
    alarmas = sum(1 for valor in valores if limite is not None and limite.en_alarma(valor))

    return Estadisticas(
        tag=tag,
        unidad=unidad,
        muestras=len(valores),
        minimo=min(valores),
        maximo=max(valores),
        promedio=fmean(valores),
        # pstdev = desvio poblacional: describimos las muestras del periodo,
        # no inferimos sobre una poblacion mayor. Con una sola muestra es 0.0.
        desvio=pstdev(valores) if len(valores) > 1 else 0.0,
        alarmas=alarmas,
    )


def resumir(
    lecturas: Iterable[Lectura], limites: Mapping[str, Limite] | None = None
) -> list[Estadisticas]:
    """Resume todas las lecturas, un ``Estadisticas`` por tag, ordenado por tag."""
    limites = limites or {}
    grupos = agrupar_por_tag(lecturas)
    return [
        estadisticas_de_tag(tag, grupo, limites.get(tag.upper()))
        for tag, grupo in sorted(grupos.items())
    ]


def totales(resumen: Iterable[Estadisticas]) -> tuple[int, int, int]:
    """Devuelve ``(cantidad_tags, muestras, alarmas)`` del resumen completo.

    El llamador desempaqueta: ``tags, muestras, alarmas = totales(resumen)``.
    """
    resumen = list(resumen)
    return (
        len(resumen),
        sum(item.muestras for item in resumen),
        sum(item.alarmas for item in resumen),
    )
