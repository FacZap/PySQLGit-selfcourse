"""tagstats: estadisticas de tags de planta a partir de un CSV de historiador.

El paquete esta dividido por responsabilidad:

* ``modelos``       -> que es un dato (Lectura, Limite, Estadisticas)
* ``lectura``       -> como entra el dato (parseo del CSV, filtros)
* ``estadisticas``  -> que se calcula (min, max, promedio, alarmas)
* ``reporte``       -> como sale el dato (tabla, json, csv)
* ``cli``           -> como lo pide el usuario (argumentos, codigos de salida)
* ``decoradores``   -> nuevo
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
