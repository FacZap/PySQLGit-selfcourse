"""Pruebas de la entrada de datos: parseo, errores y filtros."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from tagstats.lectura import (
    CabeceraInvalidaError,
    FilaInvalidaError,
    filtrar,
    leer_lecturas,
    leer_limites,
    parsear_fila,
)

FILA_OK = {
    "timestamp": "2026-08-24T06:00:00",
    "tag": "TT-101",
    "valor": "78.5",
    "unidad": "degC",
    "calidad": "Good",
}


def test_parsear_fila_valida():
    lectura = parsear_fila(FILA_OK, numero_fila=2)

    assert lectura.tag == "TT-101"
    assert lectura.valor == pytest.approx(78.5)
    assert lectura.timestamp == datetime(2026, 8, 24, 6, 0)
    assert lectura.es_confiable


def test_parsear_fila_acepta_decimales_con_coma():
    assert parsear_fila({**FILA_OK, "valor": "78,5"}, 2).valor == pytest.approx(78.5)


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("valor", "N/A", "valor invalido"),
        ("valor", "", "columnas vacias"),
        ("valor", "inf", "valor no finito"),
        ("valor", "nan", "valor no finito"),
        ("timestamp", "24/08/2026 06:00", "timestamp invalido"),
        ("tag", "   ", "columnas vacias"),
    ],
)
def test_parsear_fila_invalida_explica_el_motivo(campo: str, valor: str, motivo: str):
    with pytest.raises(FilaInvalidaError) as excepcion:
        parsear_fila({**FILA_OK, campo: valor}, numero_fila=47)

    assert excepcion.value.numero_fila == 47
    assert motivo in str(excepcion.value)
    # El numero de fila viaja en el mensaje: sin eso hay que buscar a ojo.
    assert "fila 47" in str(excepcion.value)


def test_leer_lecturas_lee_todas_las_filas(csv_lecturas: Path):
    lecturas = list(leer_lecturas(csv_lecturas))

    assert len(lecturas) == 5
    assert [lectura.tag for lectura in lecturas[:3]] == ["TT-101"] * 3


def test_leer_lecturas_es_perezoso(csv_lecturas: Path):
    """El generador no lee nada hasta que se le pide el primer elemento."""
    generador = leer_lecturas(csv_lecturas)

    primera = next(generador)

    assert primera.valor == pytest.approx(70.0)


def test_leer_lecturas_soporta_bom_de_excel(tmp_path: Path):
    ruta = tmp_path / "con_bom.csv"
    contenido = "timestamp,tag,valor,unidad,calidad\n2026-08-24T06:00:00,TT-101,70,degC,Good\n"
    ruta.write_text(contenido, encoding="utf-8-sig")  # asi guarda Excel

    assert len(list(leer_lecturas(ruta))) == 1


def test_leer_lecturas_corta_ante_una_fila_mala_por_defecto(tmp_path: Path):
    ruta = tmp_path / "sucio.csv"
    ruta.write_text(
        "timestamp,tag,valor,unidad,calidad\n"
        "2026-08-24T06:00:00,TT-101,70,degC,Good\n"
        "2026-08-24T06:05:00,TT-101,ROTO,degC,Good\n",
        encoding="utf-8",
    )

    with pytest.raises(FilaInvalidaError):
        list(leer_lecturas(ruta))


def test_leer_lecturas_tolerante_saltea_y_reporta(tmp_path: Path):
    ruta = tmp_path / "sucio.csv"
    ruta.write_text(
        "timestamp,tag,valor,unidad,calidad\n"
        "2026-08-24T06:00:00,TT-101,70,degC,Good\n"
        "2026-08-24T06:05:00,TT-101,ROTO,degC,Good\n"
        "2026-08-24T06:10:00,TT-101,72,degC,Good\n",
        encoding="utf-8",
    )
    descartes: list[FilaInvalidaError] = []

    lecturas = list(leer_lecturas(ruta, al_descartar=descartes.append))

    assert len(lecturas) == 2
    assert len(descartes) == 1
    assert descartes[0].numero_fila == 3


def test_leer_lecturas_detecta_columnas_de_mas(tmp_path: Path):
    """Un decimal con coma sin comillas corre las columnas: eso no puede pasar callado."""
    ruta = tmp_path / "corrido.csv"
    ruta.write_text(
        "timestamp,tag,valor,unidad,calidad\n2026-08-24T06:00:00,PT-204,4,82,bar,Good\n",
        encoding="utf-8",
    )

    with pytest.raises(FilaInvalidaError, match="columna"):
        list(leer_lecturas(ruta))


def test_cabecera_sin_las_columnas_esperadas(tmp_path: Path):
    ruta = tmp_path / "otra_cosa.csv"
    ruta.write_text("fecha;sensor;medicion\n", encoding="utf-8")

    with pytest.raises(CabeceraInvalidaError, match="faltan columnas"):
        list(leer_lecturas(ruta))


def test_archivo_inexistente(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        list(leer_lecturas(tmp_path / "no_existe.csv"))


def test_archivo_solo_con_cabecera(tmp_path: Path):
    ruta = tmp_path / "vacio.csv"
    ruta.write_text("timestamp,tag,valor,unidad,calidad\n", encoding="utf-8")

    assert list(leer_lecturas(ruta)) == []


def test_leer_limites(csv_limites: Path):
    limites = leer_limites(csv_limites)

    assert set(limites) == {"TT-101", "PT-204"}
    assert limites["TT-101"].maximo == pytest.approx(95.0)


def test_leer_limites_invertido_falla(tmp_path: Path):
    ruta = tmp_path / "limites.csv"
    ruta.write_text("tag,minimo,maximo\nTT-101,95,60\n", encoding="utf-8")

    with pytest.raises(FilaInvalidaError, match="limite invalido"):
        leer_limites(ruta)


def test_filtrar_por_tag_ignora_mayusculas(csv_lecturas: Path):
    lecturas = list(filtrar(leer_lecturas(csv_lecturas), tags=["tt-101"]))

    assert len(lecturas) == 3


def test_filtrar_por_rango_de_tiempo(csv_lecturas: Path):
    lecturas = list(
        filtrar(leer_lecturas(csv_lecturas), desde=datetime(2026, 8, 24, 6, 5))
    )

    # quedan TT-101 de 06:05 y 06:10, y PT-204 de 06:05
    assert len(lecturas) == 3
    assert all(lectura.timestamp >= datetime(2026, 8, 24, 6, 5) for lectura in lecturas)


def test_filtrar_solo_confiables_descarta_la_calidad_mala(csv_lecturas: Path):
    lecturas = list(filtrar(leer_lecturas(csv_lecturas), solo_confiables=True))

    assert len(lecturas) == 4
    assert all(lectura.es_confiable for lectura in lecturas)


def test_filtros_se_combinan(csv_lecturas: Path):
    lecturas = list(
        filtrar(leer_lecturas(csv_lecturas), tags=["TT-101"], solo_confiables=True)
    )

    assert [lectura.valor for lectura in lecturas] == [70.0, 80.0]
