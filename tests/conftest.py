"""Fixtures compartidas por todas las pruebas.

pytest descubre este archivo solo: no hay que importarlo desde ningun lado.

Las fixtures que escriben archivos usan ``tmp_path``, un directorio temporal
que pytest crea y borra por cada prueba. Asi las pruebas no dependen de los
CSV de ``data/`` (que pueden cambiar) ni se pisan entre si.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from tagstats.modelos import Lectura, Limite

CSV_LECTURAS = """timestamp,tag,valor,unidad,calidad
2026-08-24T06:00:00,TT-101,70.0,degC,Good
2026-08-24T06:05:00,TT-101,80.0,degC,Good
2026-08-24T06:10:00,TT-101,99.0,degC,Bad
2026-08-24T06:00:00,PT-204,4.5,bar,Good
2026-08-24T06:05:00,PT-204,2.5,bar,Good
"""

CSV_LIMITES = """tag,minimo,maximo
TT-101,60,95
PT-204,3.0,6.5
"""


@pytest.fixture
def csv_lecturas(tmp_path: Path) -> Path:
    """CSV valido con 2 tags y 5 lecturas, numeros elegidos para calcular a mano."""
    ruta = tmp_path / "lecturas.csv"
    ruta.write_text(CSV_LECTURAS, encoding="utf-8")
    return ruta


@pytest.fixture
def csv_limites(tmp_path: Path) -> Path:
    """CSV de limites que deja 1 alarma en cada tag del fixture anterior."""
    ruta = tmp_path / "limites.csv"
    ruta.write_text(CSV_LIMITES, encoding="utf-8")
    return ruta


@pytest.fixture
def limite_tt101() -> Limite:
    return Limite(tag="TT-101", minimo=60.0, maximo=95.0)


@pytest.fixture
def lecturas_tt101() -> list[Lectura]:
    """Tres lecturas de TT-101: 70, 80 y 99 degC (la ultima, fuera de rango)."""
    return [
        Lectura(datetime(2026, 8, 24, 6, 0), "TT-101", 70.0, "degC", "Good"),
        Lectura(datetime(2026, 8, 24, 6, 5), "TT-101", 80.0, "degC", "Good"),
        Lectura(datetime(2026, 8, 24, 6, 10), "TT-101", 99.0, "degC", "Bad"),
    ]
