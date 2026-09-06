"""Que se calcula.  Tema: **groupby + merge**.

Reproduce el resumen de Semana 1 (muestras, min, max, promedio, desvio y
alarmas por tag) con pandas en vez de ``statistics``. La ventaja pedagogica es
que las respuestas correctas ya se conocen: estan en la tabla del README, y los
tests las usan como oraculo.

Dos pares de funciones equivalentes, para comparar:

======================================  ====================================
tagstats (stdlib)                       tagframe (pandas)
======================================  ====================================
``agrupar_por_tag`` + bucle             ``df.groupby("tag").agg(...)``
``limites.get(tag)`` dentro del bucle   ``df.merge(limites, on="tag")``
======================================  ====================================
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: Columnas del resumen, en el mismo orden que ``tagstats.modelos.Estadisticas``.
COLUMNAS_RESUMEN = (
    "tag",
    "unidad",
    "muestras",
    "minimo",
    "maximo",
    "promedio",
    "desvio",
    "alarmas",
    "porcentaje_alarmas",
)


def leer_limites(ruta: Path | str) -> pd.DataFrame:
    """Lee ``data/limites.csv`` y devuelve ``tag, minimo, maximo`` ya numericos.

    Aca si se dejan inferir los tipos (al reves que en ``FuenteCSV``): son seis
    filas escritas a mano, no un export de historiador, y no hay basura que
    limpiar. ``to_numeric`` sin ``coerce`` es a proposito: un limite no numerico
    es un error de configuracion y tiene que cortar, no volverse NaN y contar
    cero alarmas en silencio.
    """
    limites = pd.read_csv(ruta, encoding="utf-8-sig")
    faltantes = [columna for columna in ("tag", "minimo", "maximo") if columna not in limites]
    if faltantes:
        raise ValueError(f"limites: faltan columnas obligatorias: {', '.join(faltantes)}")
    limites = limites[["tag", "minimo", "maximo"]].copy()
    limites["tag"] = limites["tag"].astype("string").str.strip()
    for columna in ("minimo", "maximo"):
        limites[columna] = pd.to_numeric(limites[columna])
    return limites


def resumen(df: pd.DataFrame, limites: pd.DataFrame | None = None) -> pd.DataFrame:
    """Un resumen por tag, ordenado por tag, con el indice reseteado.

    Args:
        df: DataFrame **ya limpio** (el ``.df`` de un ``ResultadoLimpieza``).
        limites: tabla ``tag, minimo, maximo``. Sin ella, ``alarmas`` es 0 para
            todos, igual que ``tagstats`` sin ``-l``.
    """
    if df.empty:
        # groupby sobre un DataFrame vacio devuelve columnas distintas segun la
        # version de pandas. Se corta antes y se devuelve la forma correcta:
        # los que consumen el resumen no tienen que conocer ese caso borde.
        return pd.DataFrame(columns=list(COLUMNAS_RESUMEN))

    # 1) GROUPBY: las estadisticas por tag, en una sola pasada.
    #    ddof=0 -> desvio POBLACIONAL (el pstdev de Sem 1). El default de pandas
    #    es ddof=1 (muestral) y NO coincide con los numeros del README.
    stats = df.groupby("tag")["valor"].agg(
        muestras="count",
        minimo="min",
        maximo="max",
        promedio="mean",
        desvio=lambda serie: serie.std(ddof=0),
    )
    # Con una sola muestra el desvio da NaN; Sem 1 devolvia 0.0. Se replica esa
    # decision: el desvio de una unica medicion no es "desconocido", es cero
    # (no hay dispersion que describir), y un NaN contagiaria sumas y reportes.
    stats["desvio"] = stats["desvio"].fillna(0.0)

    # La unidad no entra al groupby de arriba: si un tag mezclara unidades, el
    # groupby no se enteraria y el promedio seria una mezcla sin sentido. Se
    # calcula aparte y, si hay mas de una, queda a la vista ("bar/psi"), igual
    # que hacia estadisticas_de_tag.
    stats["unidad"] = df.groupby("tag")["unidad"].agg(
        lambda serie: "/".join(sorted(set(serie.dropna())))
    )

    # 2) MERGE con los limites para contar alarmas.
    #    how="left": un tag sin limite deja minimo/maximo en NaN, la comparacion
    #    da False y por lo tanto 0 alarmas. Es el comportamiento correcto ("sin
    #    limite, no hay alarma") y el mismo de Sem 1 con limites.get(tag) -> None.
    if limites is None or limites.empty:
        stats["alarmas"] = 0
    else:
        con_limite = df.merge(limites[["tag", "minimo", "maximo"]], on="tag", how="left")
        # < y >, no <= y >=: el borde exacto NO es alarma (60.0 y 95.0 estan EN
        # rango), igual que Limite.en_alarma en tagstats/modelos.py.
        fuera = (con_limite["valor"] < con_limite["minimo"]) | (
            con_limite["valor"] > con_limite["maximo"]
        )
        # sum() sobre booleanos cuenta los True. reindex + fillna cubre el tag
        # que quedo sin ninguna fila fuera de rango.
        stats["alarmas"] = (
            fuera.groupby(con_limite["tag"]).sum().reindex(stats.index).fillna(0).astype(int)
        )

    stats["porcentaje_alarmas"] = 100.0 * stats["alarmas"] / stats["muestras"]

    # 3) Salir con el indice reseteado y las columnas en orden: el resumen es un
    #    DataFrame comun, no uno indexado por tag. Quien quiera .loc["TT-101"]
    #    hace set_index("tag"), pero esa decision es del que consume.
    return stats.reset_index().sort_values("tag", ignore_index=True)[list(COLUMNAS_RESUMEN)]
