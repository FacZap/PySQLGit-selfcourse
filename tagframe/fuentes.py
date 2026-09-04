from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
import pandas as pd

"""
    Two-dimensional, size-mutable, potentially heterogeneous tabular data.

    Data structure also contains labeled axes (rows and columns). Arithmetic operations align on both row and column labels. Can be thought of as a dict-like container for Series objects. The primary pandas data structure.

    class pandas.DataFrame(data=None, index=None, columns=None, dtype=None, copy=None)
    ejemplo
    df = pd.DataFrame(np.random.randn(6, 4), index=dates, columns=list("ABCD"))
    df2 = pd.DataFrame(
        {
            "A": 1.0,
            "B": pd.Timestamp("20130102"),
            "C": pd.Series(1, index=list(range(4)), dtype="float32"),
            "D": np.array([3] * 4, dtype="int32"),
            "E": pd.Categorical(["test", "train", "test", "train"]),
            "F": "foo",
        }
    )
"""

class ErrorDeFuente(ValueError):
    """Base de los errores de una FuenteDeDatos (no de sistema de archivos)."""


class CabeceraInvalidaError(ErrorDeFuente):
    """El CSV no tiene las columnas esperadas."""


class FuenteDeDatos(ABC):
    """Contrato: sé de dónde salen los datos crudos, no cómo se limpian."""
    @abstractmethod
    def leer(self) -> pd.DataFrame: # sin argumentos, devuelve un pd.Dataframe
        ...

# EJEMPLO:
# fuente = FuenteCSV(Path("data/sensores_planta.csv"))
# df = fuente.leer()

class FuenteCSV(FuenteDeDatos):
    COLUMNAS = ("timestamp", "tag", "valor", "unidad", "calidad")

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)

    def leer(self) -> pd.DataFrame:
        lector = pd.read_csv(self.ruta, dtype=str) #lector es un pd.DataFrame, no un generador ni un iterador. No hace falta hacerle un yield.
        # validar cabecera
            # if lector.columns == self.COLUMNAS:
            # lector.columns es un pd.Index; compararlo con == contra una tupla hace una comparación elemento a elemento (te devuelve un array de True/False, uno por columna) y además exige que estén en el mismo orden y sin ninguna de más. Un CSV real puede traer las columnas en otro orden, o alguna extra, y sería válido igual.
            # Lo que necesitás no es "¿son exactamente iguales?" sino "¿están todas las requeridas presentes?" — es un chequeo de subconjunto, no de igualdad.
            #     presentes = {columna.strip().lower() for columna in (columnas or ())}
            #     faltantes = [columna for columna in requeridas if columna not in presentes]
        presentes = {columna.strip().lower() for columna in lector.columns} # Con pd.read_csv ya te da nombres de columna "limpios" normalmente — no es grave dejarlo, pero preguntate si lo estás copiando por costumbre o porque de verdad lo necesitás acá.
        faltantes = [columna for columna in self.COLUMNAS if columna not in presentes]
        if faltantes:
            raise CabeceraInvalidaError(
                f"{self.ruta.name}: faltan columnas obligatorias: {', '.join(faltantes)}"
            )
        return lector
    
        # en el momento en que metés un yield adentro, Python convierte automáticamente tu función en un generador, y eso choca con lo que prometiste devolver.

        #       la limpieza/coerción de tipos es responsabilidad de Limpiador, no de acá.
        #       Con dtype=str evitás que pandas "adivine" y te oculte los N/A e inf.

        
    
    """
    Mirá cómo lo resuelve leer_lecturas en tagstats/lectura.py con csv.DictReader — acá el equivalente pandas es pd.read_csv(self.ruta, dtype=str).
    """