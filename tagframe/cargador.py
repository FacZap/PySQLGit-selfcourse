"""Quien encadena las piezas.  Tema: **composicion**.

El ``Cargador`` **tiene** una fuente y un limpiador; no *es* ninguno de los dos.
Esa es la diferencia con ``fuentes.py``:

* herencia   = "es-un"    -> ``FuenteCSV`` **es una** ``FuenteDeDatos``.
* composicion = "tiene-un" -> ``Cargador`` **tiene una** fuente y **tiene un** limpiador.

Si el Cargador heredara de FuenteCSV heredaria tambien su ruta, su parser y su
manejo de filas corridas, y quedaria atado al CSV para siempre. Componiendo, el
tipo declarado es la ABC: el mismo Cargador va a servir para un ``FuenteSQL``
sin cambiar una linea. Eso es exactamente lo que compra la abstraccion de la
Parte A, y solo se cobra si el Cargador depende del contrato y no de la clase
concreta.
"""

from __future__ import annotations

from .fuentes import FuenteDeDatos
from .limpieza import Limpiador, ResultadoLimpieza


class Cargador:
    """Compone una fuente y un limpiador: CSV crudo -> DataFrame limpio."""

    def __init__(self, fuente: FuenteDeDatos, limpiador: Limpiador | None = None) -> None:
        self.fuente = fuente  # composicion: lo recibe, no lo hereda
        # El limpiador por defecto se crea aca y no en la firma: un default
        # mutable compartido entre instancias es una de las trampas clasicas de
        # Python. Ademas deja la puerta abierta a inyectar un limpiador propio.
        self.limpiador = limpiador or Limpiador()

    def cargar(self) -> ResultadoLimpieza:
        """Lee y limpia. Devuelve el resultado completo, no solo el DataFrame.

        Devolver ``ResultadoLimpieza`` y no ``df`` a secas es deliberado: quien
        llama se entera de cuantas filas se cayeron. Si solo necesita la tabla,
        pide ``.df``.
        """
        crudo = self.fuente.leer()
        return self.limpiador.limpiar(crudo)
