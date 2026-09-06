"""tagframe: carga, limpieza y analisis de CSV de planta con pandas.

Paquete hermano de ``tagstats``, no reemplazo. ``tagstats`` presume de **cero
dependencias de runtime** (solo biblioteca estandar) y esa identidad se mantiene:
pandas vive aca y solo aca. Los dos leen los mismos CSV de ``data/`` y deben dar
los mismos numeros; esa coincidencia es justamente lo que verifican los tests.

El paquete esta dividido por responsabilidad, igual que ``tagstats``, pero cada
archivo ademas encarna **un** tema de la semana:

* ``fuentes``   -> de donde salen los datos crudos (ABC -> FuenteCSV)   [HERENCIA]
* ``limpieza``  -> como se limpian (5 reglas + ResultadoLimpieza)       [PROPERTIES]
* ``cargador``  -> quien encadena fuente + limpiador                    [COMPOSICION]
* ``analisis``  -> que se calcula (stats por tag, alarmas)              [GROUPBY + MERGE]

Uso tipico::

    from tagframe.analisis import leer_limites, resumen
    from tagframe.cargador import Cargador
    from tagframe.fuentes import FuenteCSV

    resultado = Cargador(FuenteCSV("data/sensores_planta.csv")).cargar()
    print(resultado.filas_descartadas)
    print(resumen(resultado.df, leer_limites("data/limites.csv")))
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
