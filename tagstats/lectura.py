"""Entrada de datos: parseo del CSV y filtros.

Todo lo que devuelve muchas filas es un **generador** (``yield``): el archivo se
recorre de a una fila y nunca entra entero en memoria. Un export de historiador
de un mes son millones de filas; ``list(...)`` no es una opcion.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from datetime import datetime
from pathlib import Path

from .modelos import Lectura, Limite

#: Columnas que el CSV de lecturas debe traer si o si.
COLUMNAS_LECTURAS = ("timestamp", "tag", "valor", "unidad", "calidad")

#: Columnas que el CSV de limites debe traer si o si.
COLUMNAS_LIMITES = ("tag", "minimo", "maximo")

#: Clave donde csv.DictReader deja las columnas de sobra de una fila.
#: Sin esto, una fila con una coma de mas (``4,82`` sin comillas) se lee
#: corrida de lugar y contamina los datos en silencio.
COLUMNA_EXTRA = "_columnas_de_mas"


class ErrorDeDatos(ValueError):
    """Base de los errores de contenido del CSV (no de sistema de archivos)."""


class CabeceraInvalidaError(ErrorDeDatos):
    """El CSV no tiene las columnas esperadas."""


class FilaInvalidaError(ErrorDeDatos):
    """Una fila puntual no se pudo interpretar.

    Guarda el numero de fila y el contenido para que el mensaje sea accionable:
    "fila 47: valor invalido 'N/A'" en vez de un ValueError pelado.
    """

    def __init__(
        self, numero_fila: int, motivo: str, fila: Mapping[str, str] | None = None
    ) -> None:
        super().__init__(f"fila {numero_fila}: {motivo}")
        self.numero_fila = numero_fila
        self.motivo = motivo
        self.fila = dict(fila) if fila is not None else {}


def _validar_cabecera(
    columnas: Iterable[str] | None, requeridas: tuple[str, ...], ruta: Path
) -> None:
    presentes = {columna.strip().lower() for columna in (columnas or ())}
    faltantes = [columna for columna in requeridas if columna not in presentes]
    if faltantes:
        raise CabeceraInvalidaError(
            f"{ruta.name}: faltan columnas obligatorias: {', '.join(faltantes)}"
        )


def parsear_fila(fila: Mapping[str, str], numero_fila: int) -> Lectura:
    """Convierte una fila cruda del CSV en una ``Lectura`` validada.

    Se separa de ``leer_lecturas`` para poder probar el parseo sin tocar disco.
    """
    de_mas = fila.get(COLUMNA_EXTRA)
    if de_mas:
        raise FilaInvalidaError(
            numero_fila,
            f"tiene {len(de_mas)} columna(s) de mas: {de_mas} "
            "(revisa comas sin comillas dentro de un campo)",
            fila,
        )

    # Comprehension: junta en un paso todas las columnas vacias o ausentes.
    faltantes = [
        columna for columna in COLUMNAS_LECTURAS if not (fila.get(columna) or "").strip()
    ]
    if faltantes:
        raise FilaInvalidaError(numero_fila, f"columnas vacias: {', '.join(faltantes)}", fila)

    texto_timestamp = fila["timestamp"].strip()
    try:
        timestamp = datetime.fromisoformat(texto_timestamp)
    except ValueError as error:
        raise FilaInvalidaError(
            numero_fila, f"timestamp invalido: {texto_timestamp!r}", fila
        ) from error

    texto_valor = fila["valor"].strip().replace(",", ".")  # tolera decimales con coma
    try:
        valor = float(texto_valor)
    except ValueError as error:
        raise FilaInvalidaError(numero_fila, f"valor invalido: {texto_valor!r}", fila) from error

    if not math.isfinite(valor):
        # float("nan") y float("inf") no explotan, pero envenenan min/max/promedio.
        raise FilaInvalidaError(numero_fila, f"valor no finito: {texto_valor!r}", fila)

    return Lectura(
        timestamp=timestamp,
        tag=fila["tag"].strip(),
        valor=valor,
        unidad=fila["unidad"].strip(),
        calidad=fila["calidad"].strip(),
    )


def leer_lecturas(
    ruta: Path,
    *,
    al_descartar: Callable[[FilaInvalidaError], None] | None = None,
) -> Iterator[Lectura]:
    """Genera las ``Lectura`` del CSV, de a una.

    Args:
        ruta: archivo CSV con las columnas de ``COLUMNAS_LECTURAS``.
        al_descartar: si es ``None`` (por defecto) una fila mala **corta** la
            lectura con ``FilaInvalidaError``. Si se pasa una funcion, la fila
            se saltea y el error se le entrega a esa funcion.

    El callback resuelve el dilema "fallar rapido vs. seguir": la politica la
    decide quien llama (el CLI, con ``--tolerante``), no esta cableada aca.
    """
    # utf-8-sig descarta el BOM que agrega Excel al guardar como CSV; sin esto
    # la primera columna se llamaria "﻿timestamp" y no matchearia nunca.
    with ruta.open(newline="", encoding="utf-8-sig") as archivo:
        lector = csv.DictReader(archivo, restkey=COLUMNA_EXTRA)
        _validar_cabecera(lector.fieldnames, COLUMNAS_LECTURAS, ruta)
        # start=2 porque la fila 1 del archivo es la cabecera: el numero que
        # reporta el error coincide con el que muestra el editor.
        for numero_fila, fila in enumerate(lector, start=2):
            try:
                yield parsear_fila(fila, numero_fila)
            except FilaInvalidaError as error:
                if al_descartar is None:
                    raise
                al_descartar(error)


def leer_limites(ruta: Path) -> dict[str, Limite]:
    """Lee el CSV de limites y lo devuelve indexado por tag.

    Aca si se materializa todo en un diccionario: son pocas filas y se consulta
    de forma aleatoria (una vez por tag), asi que la busqueda O(1) paga.
    """
    with ruta.open(newline="", encoding="utf-8-sig") as archivo:
        lector = csv.DictReader(archivo)
        _validar_cabecera(lector.fieldnames, COLUMNAS_LIMITES, ruta)
        limites: dict[str, Limite] = {}
        for numero_fila, fila in enumerate(lector, start=2):
            tag = (fila.get("tag") or "").strip()
            if not tag:
                raise FilaInvalidaError(numero_fila, "tag vacio", fila)
            try:
                minimo = float((fila["minimo"] or "").strip().replace(",", "."))
                maximo = float((fila["maximo"] or "").strip().replace(",", "."))
            except ValueError as error:
                raise FilaInvalidaError(
                    numero_fila, f"limite no numerico para {tag}", fila
                ) from error
            try:
                limites[tag.upper()] = Limite(tag=tag, minimo=minimo, maximo=maximo)
            except ValueError as error:
                raise FilaInvalidaError(numero_fila, str(error), fila) from error
    return limites


def filtrar(
    lecturas: Iterable[Lectura],
    *,
    tags: Collection[str] | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    solo_confiables: bool = False,
) -> Iterator[Lectura]:
    """Filtra un flujo de lecturas sin materializarlo.

    Es un generador que consume otro generador: se encadena con
    ``leer_lecturas`` y el archivo sigue recorriendose una sola vez.
    """
    # Normalizar una vez, afuera del bucle: adentro se ejecuta por cada fila.
    tags_buscados = {tag.strip().upper() for tag in tags} if tags else None

    for lectura in lecturas:
        if tags_buscados is not None and lectura.tag.upper() not in tags_buscados:
            continue
        if desde is not None and lectura.timestamp < desde:
            continue
        if hasta is not None and lectura.timestamp > hasta:
            continue
        if solo_confiables and not lectura.es_confiable:
            continue
        yield lectura
