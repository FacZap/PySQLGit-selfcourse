"""
**Idea:** un `Limpiador` que recibe el DataFrame crudo y devuelve uno limpio, **regla por regla**.
Cada regla mapea a una fila real del CSV sucio. Además exponé un `ResultadoLimpieza` con
`@property` (ahí entra el tema *properties*).
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True, slots=True)
class ResultadoLimpieza:
    """Qué entró, qué salió y por qué. Inmutable, como los modelos de Sem 1."""
    df: pd.DataFrame          # el DataFrame ya limpio
    filas_entrada: int
    filas_salida: int

    @property
    def filas_descartadas(self) -> int:
        return self.filas_entrada - self.filas_salida

    @property
    def porcentaje_descartado(self) -> float:
        # ✔: 0.0 si filas_entrada == 0 (no dividas por cero), si no 100 * descartadas / entrada
        if self.filas_entrada == 0:
            return 0.0
        return 100 * self.filas_descartadas / self.filas_entrada

class Limpiador:
    def limpiar(self, crudo: pd.DataFrame) -> ResultadoLimpieza:
        n_entrada = len(crudo)
        df = crudo.copy()

        # 1) TIPOS: valor a numérico. errors="coerce" convierte 'N/A' y '' en NaN
        #    en vez de explotar.  TODO:
        #    df["valor"] = pd.to_numeric(df["valor"].str.replace(",", ".", regex=False),
        #                                errors="coerce")
        #    (el .str.replace tolera el decimal con coma, como hacía Sem 1)

        # 2) inf NO lo agarra dropna: primero mapealo a NaN.  TODO:
        #    df["valor"] = df["valor"].replace([np.inf, -np.inf], np.nan)

        # 3) TIMESTAMP a fecha. El '24/08/2026 06:20' (otro formato) -> NaT con coerce.  TODO:
        #    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601", errors="coerce")

        # 4) NULOS/vacíos: tag vacío llega como "" (string), no como NaN.  TODO:
        #    df["tag"] = df["tag"].str.strip()
        #    df = df[df["tag"].astype(bool)]            # descarta tag == ""
        #    df = df.dropna(subset=["timestamp", "valor"])   # descarta NaT y NaN

        # 5) DUPLICADOS: una misma (timestamp, tag) medida dos veces es sospechosa.  TODO:
        #    df = df.drop_duplicates(subset=["timestamp", "tag"], keep="last")

        # TODO: return ResultadoLimpieza(df=df.reset_index(drop=True),
        #                                filas_entrada=n_entrada, filas_salida=len(df))

        