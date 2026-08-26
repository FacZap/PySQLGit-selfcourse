"""Interfaz de linea de comandos.

Reglas que sigue este CLI:

* los datos utiles van a **stdout**, los avisos y errores a **stderr**
  (asi ``tagstats datos.csv -f json > salida.json`` no ensucia el JSON);
* devuelve **codigos de salida** distintos segun que paso: sirve para
  encadenarlo en un script o en un pipeline;
* ``main()`` recibe ``argv`` como parametro para poder testearlo sin subprocesos.

Codigos de salida:
    0  todo bien
    1  error de datos o de archivo
    2  uso incorrecto (lo devuelve argparse solo)
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from . import __version__
from .estadisticas import resumir
from .lectura import ErrorDeDatos, FilaInvalidaError, filtrar, leer_lecturas, leer_limites
from .reporte import FORMATEADORES

MAXIMO_DESCARTES_MOSTRADOS = 5

def configurar_loggging(nivel: int) -> None:
    print("hola mundo!")

def _fecha(texto: str) -> datetime:
    """Convierte texto ISO-8601 a datetime para argparse."""
    try:
        return datetime.fromisoformat(texto)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"fecha invalida {texto!r}: se espera ISO-8601, por ejemplo 2026-08-24T06:00"
        ) from error


def construir_parser() -> argparse.ArgumentParser:
    """Arma el parser. Separado de ``main`` para poder testearlo aparte."""
    parser = argparse.ArgumentParser(
        prog="tagstats",
        description="Resume un CSV de lecturas de tags: min, max, promedio y alarmas.",
        epilog=(
            "Ejemplos:\n"
            "  python -m tagstats data/sensores_planta.csv -l data/limites.csv\n"
            "  python -m tagstats data/sensores_planta.csv -t TT-101 -t PT-204 -f json\n"
            "  python -m tagstats data/sensores_sucios.csv --tolerante\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "csv", type=Path, help="CSV de lecturas (timestamp,tag,valor,unidad,calidad)"
    )
    parser.add_argument(
        "-l",
        "--limites",
        type=Path,
        help="CSV de limites (tag,minimo,maximo). Sin el, las alarmas cuentan 0.",
    )
    parser.add_argument(
        "-t",
        "--tag",
        action="append",
        metavar="TAG",
        help="filtra por tag; se puede repetir (-t TT-101 -t PT-204)",
    )
    parser.add_argument(
        "--desde", type=_fecha, metavar="ISO", help="descarta lo anterior a esta fecha"
    )
    parser.add_argument(
        "--hasta", type=_fecha, metavar="ISO", help="descarta lo posterior a esta fecha"
    )
    parser.add_argument(
        "--solo-confiables",
        action="store_true",
        help="usa solo las muestras con calidad Good/OK",
    )
    parser.add_argument(
        "-f",
        "--formato",
        choices=sorted(FORMATEADORES),
        default="tabla",
        help="formato de salida (por defecto: tabla)",
    )
    parser.add_argument(
        "--tolerante",
        action="store_true",
        help="saltea las filas invalidas en vez de cortar, y avisa por stderr",
    )
    parser.add_argument("-o", "--salida", type=Path, help="escribe el reporte en un archivo UTF-8")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _avisar_descartes(descartes: Sequence[FilaInvalidaError]) -> None:
    """Informa por stderr las filas que se saltearon, sin inundar la consola."""
    print(f"aviso: se descartaron {len(descartes)} filas invalidas", file=sys.stderr)
    for error in descartes[:MAXIMO_DESCARTES_MOSTRADOS]:
        print(f"  - {error}", file=sys.stderr)
    if len(descartes) > MAXIMO_DESCARTES_MOSTRADOS:
        restantes = len(descartes) - MAXIMO_DESCARTES_MOSTRADOS
        print(f"  - ... y {restantes} mas", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada. Devuelve el codigo de salida en vez de llamar a exit()."""
    parser = construir_parser()
    args = parser.parse_args(argv)

    descartes: list[FilaInvalidaError] = []
    # El metodo .append de la lista ES el callback: sin lambda ni funcion extra.
    al_descartar = descartes.append if args.tolerante else None

    try:
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
        resumen = resumir(lecturas, limites)
    except FileNotFoundError as error:
        print(f"error: no se encontro el archivo {error.filename}", file=sys.stderr)
        return 1
    except ErrorDeDatos as error:
        print(f"error de datos: {error}", file=sys.stderr)
        if not args.tolerante:
            print(
                "sugerencia: volve a correr con --tolerante para saltear filas malas",
                file=sys.stderr,
            )
        return 1
    except OSError as error:
        print(f"error de lectura: {error}", file=sys.stderr)
        return 1

    if descartes:
        _avisar_descartes(descartes)

    if not resumen:
        print("aviso: no quedaron lecturas despues de aplicar los filtros", file=sys.stderr)

    reporte = FORMATEADORES[args.formato](resumen)

    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(reporte + "\n", encoding="utf-8")
        print(f"reporte escrito en {args.salida}", file=sys.stderr)
    else:
        print(reporte)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
