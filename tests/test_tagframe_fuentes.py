"""Pruebas de la entrada: contrato de la ABC, cabecera y filas corridas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tagframe.cargador import Cargador
from tagframe.fuentes import (
    CabeceraInvalidaError,
    FilaCorridaError,
    FuenteCSV,
    FuenteDeDatos,
)
from tagframe.limpieza import Limpiador

CSV_OK = """timestamp,tag,valor,unidad,calidad
2026-08-24T06:00:00,TT-101,70.0,degC,Good
2026-08-24T06:05:00,TT-101,99.0,degC,Bad
"""

CSV_FILA_CORRIDA = """timestamp,tag,valor,unidad,calidad
2026-08-24T06:00:00,TT-101,70.0,degC,Good
2026-08-24T06:05:00,PT-204,4,82,bar,Good
"""


@pytest.fixture
def csv_ok(tmp_path: Path) -> Path:
    ruta = tmp_path / "lecturas.csv"
    ruta.write_text(CSV_OK, encoding="utf-8")
    return ruta


@pytest.fixture
def csv_fila_corrida(tmp_path: Path) -> Path:
    """El caso '4,82' sin comillas: 6 campos para 5 columnas."""
    ruta = tmp_path / "corrido.csv"
    ruta.write_text(CSV_FILA_CORRIDA, encoding="utf-8")
    return ruta


def test_la_abc_no_se_puede_instanciar():
    """FuenteDeDatos es un contrato, no una clase util."""
    with pytest.raises(TypeError):
        FuenteDeDatos()  # type: ignore[abstract]


def test_fuente_csv_es_una_fuente_de_datos(csv_ok: Path):
    assert isinstance(FuenteCSV(csv_ok), FuenteDeDatos)


def test_leer_devuelve_todo_como_texto(csv_ok: Path):
    """La coercion de tipos es del Limpiador; la fuente no adivina."""
    df = FuenteCSV(csv_ok).leer()

    assert len(df) == 2
    assert df["valor"].tolist() == ["70.0", "99.0"]


def test_leer_acepta_ruta_como_texto(csv_ok: Path):
    assert len(FuenteCSV(str(csv_ok)).leer()) == 2


@pytest.mark.parametrize(
    ("cabecera", "faltante"),
    [
        ("timestamp,tag,valor,unidad", "calidad"),
        ("timestamp,tag,unidad,calidad", "valor"),
        ("a,b,c,d,e", "timestamp"),
    ],
)
def test_cabecera_invalida_dice_que_falta(tmp_path: Path, cabecera: str, faltante: str):
    ruta = tmp_path / "malo.csv"
    ruta.write_text(f"{cabecera}\n", encoding="utf-8")

    with pytest.raises(CabeceraInvalidaError) as excepcion:
        FuenteCSV(ruta).leer()

    assert faltante in str(excepcion.value)
    assert ruta.name in str(excepcion.value)


def test_columna_extra_no_invalida_la_cabecera(tmp_path: Path):
    """La validacion es de subconjunto: sobrar columnas no es un error."""
    ruta = tmp_path / "extra.csv"
    ruta.write_text(
        "timestamp,tag,valor,unidad,calidad,operador\n"
        "2026-08-24T06:00:00,TT-101,70.0,degC,Good,ana\n",
        encoding="utf-8",
    )

    assert "operador" in FuenteCSV(ruta).leer().columns


def test_fila_corrida_se_saltea_y_se_cuenta(csv_fila_corrida: Path):
    fuente = FuenteCSV(csv_fila_corrida)
    df = fuente.leer()

    assert len(df) == 1  # la fila de 6 campos no llego al DataFrame
    assert fuente.filas_corridas == 1


def test_fila_corrida_estricta_corta(csv_fila_corrida: Path):
    """La politica la decide quien construye la fuente, no esta cableada."""
    with pytest.raises(FilaCorridaError):
        FuenteCSV(csv_fila_corrida, estricto=True).leer()


def test_csv_solo_cabecera_devuelve_vacio(tmp_path: Path):
    ruta = tmp_path / "vacio.csv"
    ruta.write_text("timestamp,tag,valor,unidad,calidad\n", encoding="utf-8")

    assert FuenteCSV(ruta).leer().empty


def test_archivo_inexistente_no_es_error_de_fuente(tmp_path: Path):
    """ErrorDeFuente es de contenido; el disco tiene sus propias excepciones."""
    with pytest.raises(FileNotFoundError):
        FuenteCSV(tmp_path / "no_existe.csv").leer()


class FuenteFalsa(FuenteDeDatos):
    """Cualquier cosa que cumpla el contrato sirve: no hace falta un archivo."""

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def leer(self) -> pd.DataFrame:
        return self._df


def test_el_cargador_acepta_cualquier_fuente():
    """Lo que compra la ABC: el Cargador no sabe que hay un CSV del otro lado."""
    df = pd.DataFrame(
        [
            {
                "timestamp": "2026-08-24T06:00:00",
                "tag": "TT-101",
                "valor": "70.0",
                "unidad": "degC",
                "calidad": "Good",
            }
        ],
        dtype=str,
    )

    assert Cargador(FuenteFalsa(df)).cargar().filas_salida == 1


def test_el_cargador_usa_el_limpiador_que_recibe(csv_ok: Path):
    """Composicion: se le puede inyectar otro limpiador sin tocar el Cargador."""
    limpiador = Limpiador()
    cargador = Cargador(FuenteCSV(csv_ok), limpiador)

    assert cargador.limpiador is limpiador


def test_el_cargador_crea_un_limpiador_por_defecto(csv_ok: Path):
    assert isinstance(Cargador(FuenteCSV(csv_ok)).limpiador, Limpiador)
