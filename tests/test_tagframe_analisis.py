"""Pruebas del analisis: los numeros tienen que dar igual que en Semana 1.

El oraculo es la tabla del README, calculada por ``tagstats`` con la biblioteca
estandar. Si ``groupby``/``merge`` se desvian, estos tests lo cantan.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tagframe.analisis import leer_limites, resumen
from tagframe.cargador import Cargador
from tagframe.fuentes import FuenteCSV

#: Los CSV de data/ se ubican desde el archivo de test, no desde el cwd: asi
#: pytest anda igual desde la raiz o desde tests/.
RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"

#: Tabla del README (Semana 1): tag -> (muestras, min, max, promedio, desvio, alarmas)
SEMANA_1 = {
    "FT-310": (144, 67.30, 95.30, 82.07, 8.59, 0),
    "LT-115": (144, 27.10, 81.40, 60.26, 16.97, 0),
    "MT-501": (144, 25.40, 51.30, 31.57, 4.26, 3),
    "PT-204": (144, 2.19, 5.28, 4.66, 0.65, 9),
    "TT-101": (144, 73.70, 102.10, 80.24, 7.27, 16),
    "VT-501": (144, 1.59, 7.95, 3.74, 1.42, 6),
}


@pytest.fixture(scope="module")
def limites() -> pd.DataFrame:
    return leer_limites(DATOS / "limites.csv")


@pytest.fixture(scope="module")
def resumen_planta(limites: pd.DataFrame) -> pd.DataFrame:
    """La cadena completa: leer -> limpiar -> resumir, indexada por tag."""
    df = Cargador(FuenteCSV(DATOS / "sensores_planta.csv")).cargar().df
    return resumen(df, limites).set_index("tag")


@pytest.mark.parametrize("tag", sorted(SEMANA_1))
def test_matchea_los_numeros_de_semana_1(resumen_planta: pd.DataFrame, tag: str):
    muestras, minimo, maximo, promedio, desvio, alarmas = SEMANA_1[tag]
    fila = resumen_planta.loc[tag]

    assert fila["muestras"] == muestras
    assert fila["minimo"] == pytest.approx(minimo, abs=0.01)
    assert fila["maximo"] == pytest.approx(maximo, abs=0.01)
    assert fila["promedio"] == pytest.approx(promedio, abs=0.01)
    assert fila["desvio"] == pytest.approx(desvio, abs=0.01)  # solo pasa con ddof=0
    assert fila["alarmas"] == alarmas


def test_total_de_alarmas(resumen_planta: pd.DataFrame):
    assert resumen_planta["alarmas"].sum() == 34  # total de Sem 1


def test_conserva_la_unidad_de_cada_tag(resumen_planta: pd.DataFrame):
    assert resumen_planta.loc["TT-101", "unidad"] == "degC"
    assert resumen_planta.loc["FT-310", "unidad"] == "m3/h"


def test_porcentaje_de_alarmas(resumen_planta: pd.DataFrame):
    assert resumen_planta.loc["TT-101", "porcentaje_alarmas"] == pytest.approx(11.1, abs=0.1)


def _df(filas: list[tuple[str, str, float]]) -> pd.DataFrame:
    """DataFrame ya limpio (tipos reales), como el que sale del Limpiador."""
    return pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp(timestamp),
                "tag": tag,
                "valor": valor,
                "unidad": "degC",
                "calidad": "Good",
            }
            for timestamp, tag, valor in filas
        ]
    )


@pytest.mark.parametrize(
    ("valor", "alarmas"),
    [
        (60.0, 0),  # borde inferior exacto: EN rango
        (95.0, 0),  # borde superior exacto: EN rango
        (59.9, 1),
        (95.1, 1),
        (80.0, 0),
    ],
)
def test_el_borde_exacto_no_es_alarma(limites: pd.DataFrame, valor: float, alarmas: int):
    """Misma convencion que Limite.en_alarma: < y >, no <= y >=."""
    df = _df([("2026-08-24T06:00:00", "TT-101", valor)])

    assert resumen(df, limites).loc[0, "alarmas"] == alarmas


def test_tag_sin_limite_no_tiene_alarmas(limites: pd.DataFrame):
    """merge how='left' deja minimo/maximo en NaN -> la comparacion da False."""
    df = _df([("2026-08-24T06:00:00", "XX-999", 9999.0)])

    assert resumen(df, limites).loc[0, "alarmas"] == 0


def test_sin_limites_no_hay_alarmas():
    """Igual que tagstats sin -l: el resumen sale, las alarmas son 0."""
    df = _df([("2026-08-24T06:00:00", "TT-101", 9999.0)])
    salida = resumen(df, limites=None)

    assert salida.loc[0, "alarmas"] == 0
    assert salida.loc[0, "muestras"] == 1


def test_una_sola_muestra_tiene_desvio_cero(limites: pd.DataFrame):
    """pandas daria NaN; Sem 1 daba 0.0 y se replica esa decision."""
    df = _df([("2026-08-24T06:00:00", "TT-101", 78.5)])

    assert resumen(df, limites).loc[0, "desvio"] == 0.0


def test_dataframe_vacio_devuelve_resumen_vacio_con_columnas(limites: pd.DataFrame):
    vacio = Cargador(FuenteCSV(DATOS / "sensores_vacio.csv")).cargar().df
    salida = resumen(vacio, limites)

    assert salida.empty
    assert "alarmas" in salida.columns


def test_ordena_por_tag(limites: pd.DataFrame):
    df = _df(
        [
            ("2026-08-24T06:00:00", "TT-101", 70.0),
            ("2026-08-24T06:00:00", "FT-310", 70.0),
            ("2026-08-24T06:00:00", "MT-501", 30.0),
        ]
    )
    salida = resumen(df, limites)

    assert salida["tag"].tolist() == ["FT-310", "MT-501", "TT-101"]
    assert salida.index.tolist() == [0, 1, 2]


def test_unidades_mezcladas_quedan_a_la_vista(limites: pd.DataFrame):
    """Si un tag mezcla unidades el groupby no se entera; el resumen si."""
    df = _df([("2026-08-24T06:00:00", "PT-204", 4.5), ("2026-08-24T06:05:00", "PT-204", 4.6)])
    df.loc[1, "unidad"] = "psi"

    assert resumen(df, limites).loc[0, "unidad"] == "degC/psi"


def test_leer_limites_devuelve_numeros():
    limites = leer_limites(DATOS / "limites.csv")

    assert set(limites.columns) == {"tag", "minimo", "maximo"}
    assert limites.set_index("tag").loc["TT-101", "maximo"] == pytest.approx(95.0)


def test_leer_limites_rechaza_cabecera_incompleta(tmp_path: Path):
    ruta = tmp_path / "limites.csv"
    ruta.write_text("tag,maximo\nTT-101,95\n", encoding="utf-8")

    with pytest.raises(ValueError, match="minimo"):
        leer_limites(ruta)


def test_csv_sucio_descarta_filas():
    """Verificacion de punta a punta de la guia: filas_descartadas > 0."""
    resultado = Cargador(FuenteCSV(DATOS / "sensores_sucios.csv")).cargar()

    assert resultado.filas_descartadas > 0
    assert resultado.filas_salida == len(resultado.df)
    assert resultado.df["tag"].tolist() == ["TT-101"] * 3 + ["PT-204"] * 3
