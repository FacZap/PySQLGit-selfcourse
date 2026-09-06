"""De donde salen los datos crudos.  Tema: **herencia** (ABC -> implementacion).

``FuenteDeDatos`` es una clase base abstracta: promete un ``leer() -> DataFrame``
y nada mas. ``FuenteCSV`` es la unica implementacion de hoy; manana ``FuenteSQL``
(el repo se llama *PySQLGit*) entra sin tocar una linea del resto del paquete,
porque ``Cargador`` depende del contrato, no del CSV.

La herencia aca no es decorativa: hay algo real que compartir (el contrato) y
algo real que varia (el medio). Compara con ``cargador.py``, donde lo correcto
es composicion y no herencia.

Este modulo **no** convierte tipos a proposito: lee todo como texto y deja la
coercion para ``limpieza.Limpiador``. Si pandas "adivinara" los tipos aca, un
``N/A`` se volveria ``NaN`` antes de que nadie decida que hacer con el, y la
limpieza dejaria de ser explicita.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


class ErrorDeFuente(ValueError):
    """Base de los errores de una FuenteDeDatos (no de sistema de archivos)."""


class CabeceraInvalidaError(ErrorDeFuente):
    """El CSV no tiene las columnas esperadas."""


class FilaCorridaError(ErrorDeFuente):
    """Una fila trae mas campos que columnas (coma sin comillas dentro de un campo).

    Solo se levanta con ``FuenteCSV(..., estricto=True)``.

    Diferencia de filosofia con Semana 1: alli el parseo era nuestro
    (``csv.DictReader`` + ``restkey``), asi que se podia informar *que* fila y
    *que* sobraba, y el default era cortar. Aca el parser es de pandas y la fila
    mala se descarta antes de llegar al DataFrame: lo unico honesto que se puede
    hacer es contarla. Por eso el default se invierte (tolerar y contar) y el
    corte queda como opcion explicita de quien construye la fuente.
    """


class FuenteDeDatos(ABC):
    """Contrato: se de donde salen los datos crudos, no como se limpian."""

    @abstractmethod
    def leer(self) -> pd.DataFrame:  # sin argumentos, devuelve un pd.DataFrame
        ...


# EJEMPLO:
# fuente = FuenteCSV(Path("data/sensores_planta.csv"))
# df = fuente.leer()


class FuenteCSV(FuenteDeDatos):
    """Lee un CSV de lecturas y lo entrega **crudo** (todo texto).

    Args:
        ruta: archivo con las columnas de ``COLUMNAS``.
        estricto: que hacer con una fila que trae mas campos que columnas (la
            fila corrida ``4,82`` de ``data/sensores_sucios.csv``). ``False``
            (por defecto) la saltea y la cuenta en ``filas_corridas``; ``True``
            corta con ``FilaCorridaError``.
    """

    COLUMNAS = ("timestamp", "tag", "valor", "unidad", "calidad")

    def __init__(self, ruta: Path | str, *, estricto: bool = False) -> None:
        self.ruta = Path(ruta)
        self.estricto = estricto
        #: Filas que el parser descarto por tener campos de mas. Se completa en
        #: cada ``leer()``: son filas que nunca llegan al Limpiador, asi que sin
        #: este contador ``ResultadoLimpieza`` no las podria reportar.
        self.filas_corridas = 0

    def leer(self) -> pd.DataFrame:
        try:
            with warnings.catch_warnings(record=True) as avisos:
                warnings.simplefilter("always", pd.errors.ParserWarning)
                # dtype=str          -> no adivines tipos, eso lo decide Limpiador.
                # keep_default_na=F  -> ni siquiera conviertas "N/A"/"" a NaN: el
                #                       texto crudo llega entero y la limpieza es
                #                       la unica que decide que es nulo.
                # utf-8-sig          -> descarta el BOM que agrega Excel (si no,
                #                       la primera columna se llama "\ufefftimestamp").
                crudo = pd.read_csv(
                    self.ruta,
                    dtype=str,
                    keep_default_na=False,
                    encoding="utf-8-sig",
                    on_bad_lines="error" if self.estricto else "warn",
                )
        except pd.errors.ParserError as error:
            raise FilaCorridaError(f"{self.ruta.name}: {error}") from error

        self.filas_corridas = sum(
            1 for aviso in avisos if issubclass(aviso.category, pd.errors.ParserWarning)
        )

        # No alcanza con comparar `crudo.columns == self.COLUMNAS`: eso es una
        # comparacion elemento a elemento que exige mismo orden y ninguna columna
        # de mas. Lo que se necesita es "estan todas las requeridas?", o sea un
        # chequeo de subconjunto, igual que _validar_cabecera de tagstats.
        presentes = {columna.strip().lower() for columna in crudo.columns}
        faltantes = [columna for columna in self.COLUMNAS if columna not in presentes]
        if faltantes:
            raise CabeceraInvalidaError(
                f"{self.ruta.name}: faltan columnas obligatorias: {', '.join(faltantes)}"
            )
        return crudo
