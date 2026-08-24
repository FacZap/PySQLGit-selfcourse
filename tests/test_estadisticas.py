"""Pruebas del calculo. Los numeros de las fixtures se eligieron para poder
verificarlos a mano: 70, 80 y 99 dan promedio 83 exacto."""

from __future__ import annotations

from datetime import datetime

import pytest

from tagstats.estadisticas import agrupar_por_tag, estadisticas_de_tag, resumir, totales
from tagstats.modelos import Lectura, Limite


def _lectura(tag: str, valor: float, unidad: str = "degC") -> Lectura:
    return Lectura(datetime(2026, 8, 24, 6, 0), tag, valor, unidad, "Good")


def test_agrupar_por_tag():
    lecturas = [_lectura("TT-101", 1), _lectura("PT-204", 2), _lectura("TT-101", 3)]

    grupos = agrupar_por_tag(lecturas)

    assert set(grupos) == {"TT-101", "PT-204"}
    assert len(grupos["TT-101"]) == 2


def test_agrupar_devuelve_dict_comun_no_defaultdict():
    """Un defaultdict que se escapa crea claves fantasma al consultarlo."""
    grupos = agrupar_por_tag([_lectura("TT-101", 1)])

    with pytest.raises(KeyError):
        grupos["TAG-QUE-NO-EXISTE"]


def test_estadisticas_basicas(lecturas_tt101: list[Lectura], limite_tt101: Limite):
    resultado = estadisticas_de_tag("TT-101", lecturas_tt101, limite_tt101)

    assert resultado.muestras == 3
    assert resultado.minimo == pytest.approx(70.0)
    assert resultado.maximo == pytest.approx(99.0)
    assert resultado.promedio == pytest.approx(83.0)
    assert resultado.unidad == "degC"
    # pstdev([70, 80, 99]) = sqrt(434 / 3) = 12.0277...
    assert resultado.desvio == pytest.approx(12.02775, rel=1e-4)


def test_alarmas_cuenta_las_muestras_fuera_de_rango(
    lecturas_tt101: list[Lectura], limite_tt101: Limite
):
    resultado = estadisticas_de_tag("TT-101", lecturas_tt101, limite_tt101)

    assert resultado.alarmas == 1  # solo 99.0 supera el maximo de 95
    assert resultado.porcentaje_alarmas == pytest.approx(33.333, rel=1e-3)


def test_sin_limite_no_hay_alarmas(lecturas_tt101: list[Lectura]):
    resultado = estadisticas_de_tag("TT-101", lecturas_tt101, limite=None)

    assert resultado.alarmas == 0
    assert resultado.porcentaje_alarmas == 0.0


def test_una_sola_muestra_no_rompe_el_desvio():
    resultado = estadisticas_de_tag("TT-101", [_lectura("TT-101", 42.0)])

    assert resultado.muestras == 1
    assert resultado.minimo == resultado.maximo == pytest.approx(42.0)
    assert resultado.desvio == 0.0


def test_sin_lecturas_es_un_error_explicito():
    with pytest.raises(ValueError, match="no hay lecturas"):
        estadisticas_de_tag("TT-101", [])


def test_unidades_mezcladas_quedan_a_la_vista():
    lecturas = [_lectura("TT-101", 70, "degC"), _lectura("TT-101", 158, "degF")]

    assert estadisticas_de_tag("TT-101", lecturas).unidad == "degC/degF"


def test_resumir_ordena_por_tag_y_aplica_limites():
    lecturas = [
        _lectura("TT-101", 99.0),
        _lectura("PT-204", 2.5, "bar"),
        _lectura("PT-204", 4.5, "bar"),
    ]
    limites = {
        "TT-101": Limite("TT-101", 60, 95),
        "PT-204": Limite("PT-204", 3.0, 6.5),
    }

    resumen = resumir(lecturas, limites)

    assert [item.tag for item in resumen] == ["PT-204", "TT-101"]  # alfabetico
    assert [item.alarmas for item in resumen] == [1, 1]


def test_resumir_sin_lecturas_devuelve_lista_vacia():
    assert resumir([]) == []


def test_totales_se_desempaqueta():
    lecturas = [_lectura("TT-101", 99.0), _lectura("PT-204", 2.5, "bar")]
    limites = {"TT-101": Limite("TT-101", 60, 95)}

    cantidad_tags, muestras, alarmas = totales(resumir(lecturas, limites))

    assert (cantidad_tags, muestras, alarmas) == (2, 2, 1)
