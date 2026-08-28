from __future__ import annotations
import functools, time, logging

import argparse
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from . import __version__
from .estadisticas import resumir
from .lectura import ErrorDeDatos, FilaInvalidaError, filtrar, leer_lecturas, leer_limites
from .reporte import FORMATEADORES
from .cli import construir_parser
logger = logging.getLogger(__name__)

def medir_tiempo(func):
    @functools.wraps(func)                 # preserva __name__/__doc__ del original
    def envoltura(*args, **kwargs):
        inicio = time.perf_counter()       # perf_counter: monotónico, para medir duraciones
        resultado = func(*args, **kwargs)
        logger.debug("%s tardo %.1f ms", func.__name__, (time.perf_counter() - inicio) * 1000)
        return resultado
    return envoltura

def main(argv: Sequence[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)

    descartes: list[FilaInvalidaError] = []
    # El metodo .append de la lista ES el callback: sin lambda ni funcion extra.
    al_descartar = descartes.append if args.tolerante else None


    limites = leer_limites(args.limites) if args.limites else {}
    # Cadena de generadores: leer -> filtrar -> agrupar. El CSV se recorre
    # una sola vez y recien aca, dentro de resumir(), se consume.
    lecturas = filtrar(
        leer_lecturas(args.csv, al_descartar=al_descartar),
        tags=args.tag,
        desde=args.desde,
        hasta=args.hasta,
        solo_confiables=args.solo_confiables,
    )
    resumir_decorada = medir_tiempo(resumir)
    resumen = resumir_decorada(lecturas, limites)
    print(resumen)
    

if __name__ == "__main__":
    # Sin esto, logger.debug(...) de medir_tiempo no se ve: el root logger
    # arranca en WARNING y sin handler propio. basicConfig() agrega un
    # handler a stderr y baja el nivel a DEBUG, solo cuando se corre como
    # script (no al importar el modulo desde otro lado).
    logging.basicConfig(level=logging.DEBUG)
    
    sys.exit(main())