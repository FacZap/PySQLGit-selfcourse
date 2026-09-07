"""Pruebas de la limpieza: una regla, un caso de dato sucio.

Cada parametro de ``test_descarta_fila_sucia`` corresponde a una fila real de
``data/sensores_sucios.csv``: si alguna regla se rompe, el test dice cual.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tagframe.limpieza import Limpiador, ResultadoLimpieza

FILA_OK = {
    "timestamp": "2026-08-24T06:00:00",
    "tag": "TT-101",
    "valor": "78.5",
    "unidad": "degC",
    "calidad": "Good",
}


@pytest.fixture
def limpiador() -> Limpiador:
    return Limpiador()


def _df(**overrides: str) -> pd.DataFrame:
    """DataFrame de una sola fila, valida salvo por lo que se pise."""
    return pd.DataFrame([{**FILA_OK, **overrides}], dtype=str)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("valor", "N/A"),  # tipo: no numerico
        ("valor", ""),  # nulo
        ("valor", "inf"),  # no finito (sobrevive a dropna si no se mapea a NaN)
        ("valor", "-inf"),
        ("timestamp", "24/08/2026 06:20"),  # otro formato de fecha -> NaT
        ("timestamp", ""),
        ("tag", "   "),  # tag vacio: es "", no NaN
    ],
)
def test_descarta_fila_sucia(limpiador: Limpiador, campo: str, valor: str):
    resultado = limpiador.limpiar(_df(**{campo: valor}))

    assert resultado.filas_salida == 0
    assert resultado.filas_descartadas == 1
    assert resultado.porcentaje_descartado == pytest.approx(100.0)


def test_conserva_la_fila_valida(limpiador: Limpiador):
    resultado = limpiador.limpiar(_df())

    assert resultado.filas_salida == 1
    assert resultado.porcentaje_descartado == 0.0


def test_convierte_los_tipos(limpiador: Limpiador):
    """El DataFrame limpio ya no es texto: es datetime + float."""
    fila = limpiador.limpiar(_df()).df.iloc[0]

    assert fila["timestamp"] == pd.Timestamp("2026-08-24T06:00:00")
    assert fila["valor"] == pytest.approx(78.5)
    assert isinstance(fila["valor"], float)


def test_acepta_decimales_con_coma(limpiador: Limpiador):
    """Misma tolerancia que tagstats.parsear_fila."""
    resultado = limpiador.limpiar(_df(valor="78,5"))

    assert resultado.filas_salida == 1
    assert resultado.df.loc[0, "valor"] == pytest.approx(78.5)


def test_deduplica_por_timestamp_y_tag(limpiador: Limpiador):
    """El CSV sucio no trae un duplicado exacto: se inyecta uno aca."""
    df = pd.concat([_df(), _df()], ignore_index=True)

    assert limpiador.limpiar(df).filas_salida == 1


def test_deduplica_aunque_difieran_las_otras_columnas(limpiador: Limpiador):
    """Por eso drop_duplicates lleva subset: sin el, estas dos filas no matchean."""
    df = pd.concat([_df(calidad="Good"), _df(calidad="Bad")], ignore_index=True)
    resultado = limpiador.limpiar(df)

    assert resultado.filas_salida == 1
    # keep="last": queda la ultima, que es la version corregida del historiador.
    assert resultado.df.loc[0, "calidad"] == "Bad"


def test_no_deduplica_tags_distintos_en_el_mismo_instante(limpiador: Limpiador):
    df = pd.concat([_df(tag="TT-101"), _df(tag="PT-204")], ignore_index=True)

    assert limpiador.limpiar(df).filas_salida == 2


def test_resetea_el_indice(limpiador: Limpiador):
    """Sin reset_index el indice quedaria [1] y los tests dependerian de huecos."""
    df = pd.concat([_df(valor="N/A"), _df()], ignore_index=True)

    assert limpiador.limpiar(df).df.index.tolist() == [0]


def test_no_muta_el_dataframe_de_entrada(limpiador: Limpiador):
    crudo = _df()
    limpiador.limpiar(crudo)

    assert crudo.loc[0, "valor"] == "78.5"  # sigue siendo texto


def test_tag_nulo_tambien_se_descarta(limpiador: Limpiador):
    """Si una fuente convirtio "" a NaN: NaN es truthy, dropna no lo toca."""
    df = _df()
    df.loc[0, "tag"] = np.nan

    assert limpiador.limpiar(df).filas_salida == 0


def test_dataframe_vacio_no_divide_por_cero(limpiador: Limpiador):
    vacio = pd.DataFrame(columns=list(FILA_OK), dtype=str)
    resultado = limpiador.limpiar(vacio)

    assert resultado.filas_entrada == 0
    assert resultado.porcentaje_descartado == 0.0


def test_resultado_es_inmutable(limpiador: Limpiador):
    """frozen=True: el balance no se retoca despues de calcularlo."""
    resultado = limpiador.limpiar(_df())

    assert isinstance(resultado, ResultadoLimpieza)
    with pytest.raises((AttributeError, TypeError)):
        resultado.filas_salida = 99  # type: ignore[misc]
