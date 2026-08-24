"""Pruebas de los formatos de salida.

No se compara la tabla caracter por caracter: eso rompe la prueba cada vez que
se ajusta un ancho. Se verifica lo que importa: que los datos esten, que el
JSON sea JSON valido y que el CSV tenga una fila por tag.
"""

from __future__ import annotations

import csv
import io
import json

import pytest

from tagstats.modelos import Estadisticas
from tagstats.reporte import (
    FORMATEADORES,
    MENSAJE_SIN_DATOS,
    formatear_csv,
    formatear_json,
    formatear_tabla,
)

RESUMEN = [
    Estadisticas("PT-204", "bar", 2, 2.5, 4.5, 3.5, 1.0, 1),
    Estadisticas("TT-101", "degC", 3, 70.0, 99.0, 83.0, 12.02775, 1),
]


def test_tabla_incluye_encabezados_y_datos():
    tabla = formatear_tabla(RESUMEN)

    assert "TAG" in tabla and "ALARMAS" in tabla
    assert "TT-101" in tabla and "degC" in tabla
    assert "83.00" in tabla  # promedio con 2 decimales


def test_tabla_tiene_una_linea_por_tag_mas_encabezado_y_totales():
    lineas = formatear_tabla(RESUMEN).splitlines()

    # encabezado + separador + 2 tags + separador + total
    assert len(lineas) == 6
    assert lineas[-1].startswith("TOTAL:")
    assert "2 tags" in lineas[-1] and "5 muestras" in lineas[-1] and "2 alarmas" in lineas[-1]


def test_tabla_es_ascii_puro():
    """La consola de Windows no siempre es UTF-8: un caracter raro aborta el print."""
    formatear_tabla(RESUMEN).encode("ascii")  # si no es ascii, lanza excepcion


def test_tabla_sin_datos_avisa():
    assert formatear_tabla([]) == MENSAJE_SIN_DATOS


def test_json_es_valido_y_trae_los_totales():
    documento = json.loads(formatear_json(RESUMEN))

    assert documento["totales"] == {"tags": 2, "muestras": 5, "alarmas": 2}
    assert len(documento["tags"]) == 2

    tt101 = next(item for item in documento["tags"] if item["tag"] == "TT-101")
    assert tt101["promedio"] == pytest.approx(83.0)
    assert tt101["porcentaje_alarmas"] == pytest.approx(33.3333, rel=1e-4)
    assert tt101["rango"] == pytest.approx(29.0)


def test_json_vacio_sigue_siendo_json():
    documento = json.loads(formatear_json([]))

    assert documento["tags"] == []
    assert documento["totales"]["muestras"] == 0


def test_csv_tiene_cabecera_y_una_fila_por_tag():
    filas = list(csv.DictReader(io.StringIO(formatear_csv(RESUMEN))))

    assert len(filas) == 2
    assert filas[0]["tag"] == "PT-204"
    assert float(filas[1]["promedio"]) == pytest.approx(83.0)


def test_todos_los_formatos_estan_registrados():
    assert set(FORMATEADORES) == {"tabla", "json", "csv"}
    for formatear in FORMATEADORES.values():
        assert isinstance(formatear(RESUMEN), str)
