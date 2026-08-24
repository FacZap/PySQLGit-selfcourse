"""Pruebas de los modelos: reglas de negocio chicas, faciles de romper sin darse cuenta."""

from __future__ import annotations

from datetime import datetime

import pytest

from tagstats.modelos import Estadisticas, Lectura, Limite


def _lectura(calidad: str) -> Lectura:
    return Lectura(datetime(2026, 8, 24, 6, 0), "TT-101", 78.0, "degC", calidad)


# parametrize: una sola prueba, varios casos. Cada uno se reporta por separado,
# asi el fallo dice exactamente que valor rompio.
@pytest.mark.parametrize(
    ("calidad", "esperado"),
    [
        ("Good", True),
        ("good", True),
        ("  OK  ", True),
        ("Bad", False),
        ("Uncertain", False),
        ("", False),
    ],
)
def test_es_confiable_segun_calidad(calidad: str, esperado: bool):
    assert _lectura(calidad).es_confiable is esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (59.9, True),  # justo por debajo
        (60.0, False),  # el borde NO es alarma
        (78.0, False),
        (95.0, False),  # el borde NO es alarma
        (95.1, True),  # justo por encima
    ],
)
def test_en_alarma_incluye_los_bordes(valor: float, esperado: bool):
    limite = Limite(tag="TT-101", minimo=60.0, maximo=95.0)
    assert limite.en_alarma(valor) is esperado


def test_limite_invertido_falla_al_construirse():
    with pytest.raises(ValueError, match="limite invalido"):
        Limite(tag="TT-101", minimo=95.0, maximo=60.0)


def test_lectura_es_inmutable():
    lectura = _lectura("Good")
    with pytest.raises(AttributeError):
        lectura.valor = 999.0  # type: ignore[misc]


def test_porcentaje_de_alarmas():
    estadisticas = Estadisticas(
        tag="TT-101",
        unidad="degC",
        muestras=200,
        minimo=70.0,
        maximo=99.0,
        promedio=80.0,
        desvio=5.0,
        alarmas=50,
    )
    assert estadisticas.porcentaje_alarmas == 25.0
    assert estadisticas.rango == 29.0
