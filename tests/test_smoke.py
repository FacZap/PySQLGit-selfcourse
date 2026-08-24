"""Prueba de humo: confirma que pytest corre y que el paquete se importa.

Es el "hola mundo" de pytest. Parece trivial, pero es lo primero que se rompe
cuando el entorno esta mal armado (paquete no encontrado, interprete equivocado).
Si esta falla, no tiene sentido mirar el resto.
"""

import tagstats


def test_pytest_funciona():
    assert 2 + 2 == 4


def test_el_paquete_se_importa():
    assert tagstats.__version__ == "0.1.0"
