"""De crudo a limpio, **regla por regla**.  Tema: pandas + *properties*.

El ``Limpiador`` recibe el DataFrame de texto que devolvio una ``FuenteDeDatos``
y aplica cinco reglas, cada una atada a una fila real de
``data/sensores_sucios.csv``. Devuelve un ``ResultadoLimpieza``: el DataFrame
limpio **y** el balance de lo que entro y lo que salio, porque un promedio
calculado sobre filas descartadas en silencio es peor que un error.

El patron central es ``errors="coerce"``: la basura se convierte en ``NaN``/``NaT``
en vez de explotar, y despues se filtra de una sola vez con ``dropna``. Es la
version vectorizada del ``try/except`` fila por fila de ``tagstats.parsear_fila``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: Columnas de texto que se normalizan (strip) antes de cualquier filtro.
COLUMNAS_TEXTO = ("tag", "unidad", "calidad")

#: Clave que define "la misma medicion": un tag no se mide dos veces en el mismo
#: instante. Si aparece repetida, alguien duplico el export.
CLAVE_DUPLICADOS = ("timestamp", "tag")


@dataclass(frozen=True, slots=True)
class ResultadoLimpieza:
    """Que entro, que salio y por que. Inmutable, como los modelos de Sem 1.

    Los conteos se guardan como datos y los derivados se exponen como
    ``@property``: no se pueden desincronizar del DataFrame porque no se
    almacenan, se calculan.
    """

    df: pd.DataFrame  # el DataFrame ya limpio
    filas_entrada: int
    filas_salida: int

    @property
    def filas_descartadas(self) -> int:
        return self.filas_entrada - self.filas_salida

    @property
    def porcentaje_descartado(self) -> float:
        """Porcentaje de filas descartadas (0.0 si no entro ninguna).

        El guard de division por cero es el mismo criterio que
        ``Estadisticas.porcentaje_alarmas`` en tagstats: un CSV vacio no es un
        error de calculo, es simplemente 0%.
        """
        if self.filas_entrada == 0:
            return 0.0
        return 100.0 * self.filas_descartadas / self.filas_entrada


class Limpiador:
    """Aplica las reglas de limpieza. Sin estado: se puede reusar y compartir."""

    def limpiar(self, crudo: pd.DataFrame) -> ResultadoLimpieza:
        n_entrada = len(crudo)
        # copy() porque el resto de las reglas asignan columnas: sin esto se
        # mutaria el DataFrame de quien llama (y pandas avisaria con un warning).
        df = crudo.copy()

        # 1) TIPOS: valor a numerico.
        #    astype("string") -> tolera que la columna ya venga numerica (los
        #    tests arman DataFrames a mano) sin romper el acceso .str.
        #    .str.replace(",", ".") -> decimal con coma, igual que Sem 1.
        #    errors="coerce" -> 'N/A' y '' se vuelven NaN en vez de explotar.
        #    astype("float64") -> baja del Float64 nullable al float de numpy,
        #    que es lo que esperan np.inf, dropna y groupby mas abajo.
        df["valor"] = pd.to_numeric(
            df["valor"].astype("string").str.replace(",", ".", regex=False),
            errors="coerce",
        ).astype("float64")

        # 2) inf NO lo agarra dropna (es un float perfectamente valido): hay que
        #    mapearlo a NaN antes. Es la fila 'PT-204,inf,bar,Uncertain'. Un inf
        #    que sobrevive envenena max, promedio y desvio de todo el tag.
        df["valor"] = df["valor"].replace([np.inf, -np.inf], np.nan)

        # 3) TIMESTAMP a fecha. El '24/08/2026 06:20' no es ISO -> NaT con coerce.
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601", errors="coerce")

        # 4) NULOS/vacios. Ojo: un tag vacio llega como "" (string), no como NaN,
        #    asi que dropna no lo toca; hay que filtrarlo aparte.
        for columna in COLUMNAS_TEXTO:
            # fillna("") primero: si la fuente ya convirtio "" a NaN, .str.strip()
            #    devuelve NaN y NaN es *truthy*, o sea que el filtro lo dejaria pasar.
            df[columna] = df[columna].fillna("").astype("string").str.strip()
        df = df[df["tag"] != ""]  # descarta tag vacio
        df = df.dropna(subset=["timestamp", "valor"])  # descarta NaT y NaN

        # 5) DUPLICADOS: la misma (timestamp, tag) medida dos veces es sospechosa.
        #    Sin subset, drop_duplicates compara la fila entera y no detectaria
        #    un duplicado que difiere en la calidad. keep="last" se queda con la
        #    ultima, que en un export de historiador suele ser la corregida.
        df = df.drop_duplicates(subset=list(CLAVE_DUPLICADOS), keep="last")

        # Despues de filtrar, el indice queda con huecos (0, 2, 5...). Se resetea
        # para que nadie -tests incluidos- dependa de indices salteados.
        return ResultadoLimpieza(
            df=df.reset_index(drop=True),
            filas_entrada=n_entrada,
            filas_salida=len(df),
        )
