"""Salida: el mismo resumen en tres formatos.

Separar el calculo del formato permite agregar un formato nuevo sin tocar la
logica de negocio, y probar cada parte por separado.

Nota sobre caracteres: la salida se imprime en la consola de Windows, que no
siempre usa UTF-8. Por eso el reporte se mantiene en ASCII (nada de flechas ni
guiones largos): un carater fuera de la codificacion de la consola aborta el
programa con UnicodeEncodeError.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from dataclasses import asdict

from .estadisticas import totales
from .modelos import Estadisticas

MENSAJE_SIN_DATOS = "(sin datos para los filtros aplicados)"

#: Columnas del reporte: (encabezado, ancho, formato para el valor).
_COLUMNAS_NUMERICAS = (
    ("MUESTRAS", 8, "d"),
    ("MIN", 10, ".2f"),
    ("MAX", 10, ".2f"),
    ("PROMEDIO", 10, ".2f"),
    ("DESVIO", 9, ".2f"),
    ("ALARMAS", 8, "d"),
    ("%ALARMA", 8, ".1f"),
)


def formatear_tabla(resumen: Sequence[Estadisticas]) -> str:
    """Tabla alineada para leer en la terminal."""
    if not resumen:
        return MENSAJE_SIN_DATOS

    # max() con desempaquetado (*): el primer argumento es el piso (el ancho del
    # encabezado) y el resto son los anchos reales de los datos.
    ancho_tag = max(len("TAG"), *(len(item.tag) for item in resumen))
    ancho_unidad = max(len("UNIDAD"), *(len(item.unidad) for item in resumen))

    encabezado = f"{'TAG':<{ancho_tag}}  {'UNIDAD':<{ancho_unidad}}"
    for titulo, ancho, _ in _COLUMNAS_NUMERICAS:
        encabezado += f"  {titulo:>{ancho}}"

    separador = "-" * len(encabezado)
    lineas = [encabezado, separador]

    for item in resumen:
        celdas = (
            item.muestras,
            item.minimo,
            item.maximo,
            item.promedio,
            item.desvio,
            item.alarmas,
            item.porcentaje_alarmas,
        )
        fila = f"{item.tag:<{ancho_tag}}  {item.unidad:<{ancho_unidad}}"
        # zip() recorre columnas y valores en paralelo; el desempaquetado en el
        # for saca de una el ancho y el formato de cada columna.
        for (_, ancho, formato), valor in zip(_COLUMNAS_NUMERICAS, celdas, strict=True):
            fila += f"  {valor:>{ancho}{formato}}"
        lineas.append(fila)

    cantidad_tags, muestras, alarmas = totales(resumen)  # desempaquetado de tupla
    lineas.append(separador)
    lineas.append(f"TOTAL: {cantidad_tags} tags | {muestras} muestras | {alarmas} alarmas")
    return "\n".join(lineas)


def _a_diccionario(item: Estadisticas) -> dict[str, object]:
    """Pasa un ``Estadisticas`` a dict, redondeado y con los derivados incluidos."""
    datos = asdict(item)
    # asdict() no incluye las properties, hay que agregarlas a mano.
    datos["porcentaje_alarmas"] = item.porcentaje_alarmas
    datos["rango"] = item.rango
    # Redondeo solo en la salida: los calculos se hacen en precision completa.
    return {
        clave: round(valor, 4) if isinstance(valor, float) else valor
        for clave, valor in datos.items()
    }


def formatear_json(resumen: Sequence[Estadisticas]) -> str:
    """JSON con los totales incluidos, para encadenar con otra herramienta."""
    cantidad_tags, muestras, alarmas = totales(resumen)
    documento = {
        "totales": {"tags": cantidad_tags, "muestras": muestras, "alarmas": alarmas},
        "tags": [_a_diccionario(item) for item in resumen],
    }
    return json.dumps(documento, indent=2, ensure_ascii=False)


def formatear_csv(resumen: Sequence[Estadisticas]) -> str:
    """CSV para volver a abrir en Excel o cargar en una base."""
    if not resumen:
        return ""
    columnas = list(_a_diccionario(resumen[0]))
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=columnas, lineterminator="\n")
    escritor.writeheader()
    escritor.writerows(_a_diccionario(item) for item in resumen)
    return buffer.getvalue().rstrip("\n")


#: Tabla de despacho: agregar un formato es agregar una entrada, no otro if.
FORMATEADORES = {
    "tabla": formatear_tabla,
    "json": formatear_json,
    "csv": formatear_csv,
}
