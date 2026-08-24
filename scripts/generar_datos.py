"""Genera el dataset de ejemplo ``data/sensores_planta.csv``.

Se usa una semilla fija: dos corridas producen exactamente el mismo archivo, asi
el ``git diff`` queda limpio y las pruebas manuales son reproducibles.

Uso:
    python scripts/generar_datos.py
"""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

SEMILLA = 20260824
INICIO = datetime(2026, 8, 24, 6, 0, 0)
PASO = timedelta(minutes=5)
MUESTRAS = 144  # 12 horas de turno

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "data" / "sensores_planta.csv"


@dataclass(frozen=True, slots=True)
class PerfilTag:
    """Como se comporta un tag simulado a lo largo del turno."""

    tag: str
    unidad: str
    base: float
    amplitud: float
    ruido: float
    periodo: int  # muestras que tarda un ciclo completo
    decimales: int
    # Desvio sostenido: (muestra_inicio, muestra_fin, delta). Simula una
    # excursion real de proceso, que es lo que despues cuenta como alarma.
    excursion: tuple[int, int, float] | None = None
    # Picos aislados: (probabilidad, delta). Simula ruido electrico o arranques.
    pico: tuple[float, float] | None = None


PERFILES = (
    PerfilTag("TT-101", "degC", 78.0, 3.5, 0.6, 48, 2, excursion=(60, 76, 20.0)),
    PerfilTag("PT-204", "bar", 4.8, 0.35, 0.08, 36, 3, excursion=(100, 109, -2.3)),
    PerfilTag("FT-310", "m3/h", 82.0, 12.0, 2.0, 24, 1),
    PerfilTag("LT-115", "%", 55.0, 25.0, 1.2, 96, 1),
    PerfilTag("VT-501", "mm/s", 3.2, 0.9, 0.35, 18, 2, excursion=(124, 144, 3.6)),
    PerfilTag("MT-501", "A", 31.0, 4.5, 1.1, 30, 1, pico=(0.02, 16.0)),
)

CALIDADES_MALAS = ("Uncertain", "Bad")
PROBABILIDAD_CALIDAD_MALA = 0.02


def valor_simulado(perfil: PerfilTag, indice: int, rng: random.Random) -> float:
    """Onda base + ruido + eventos, redondeado a los decimales del instrumento."""
    valor = perfil.base + perfil.amplitud * math.sin(2 * math.pi * indice / perfil.periodo)
    valor += rng.gauss(0.0, perfil.ruido)

    if perfil.excursion is not None:
        inicio, fin, delta = perfil.excursion  # desempaquetado de tupla
        if inicio <= indice < fin:
            valor += delta

    if perfil.pico is not None:
        probabilidad, delta = perfil.pico
        if rng.random() < probabilidad:
            valor += delta

    return round(valor, perfil.decimales)


def calidad_simulada(rng: random.Random) -> str:
    """La mayoria de las muestras son buenas; algunas llegan degradadas."""
    if rng.random() < PROBABILIDAD_CALIDAD_MALA:
        return rng.choice(CALIDADES_MALAS)
    return "Good"


def generar_filas(rng: random.Random) -> list[tuple[str, str, str, str, str]]:
    """Genera las filas ordenadas por timestamp y luego por tag, como un historiador."""
    filas = []
    for indice in range(MUESTRAS):
        timestamp = (INICIO + indice * PASO).isoformat()
        for perfil in PERFILES:
            valor = valor_simulado(perfil, indice, rng)
            filas.append(
                (timestamp, perfil.tag, f"{valor}", perfil.unidad, calidad_simulada(rng))
            )
    return filas


def main() -> int:
    rng = random.Random(SEMILLA)
    filas = generar_filas(rng)

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    # newline="" es obligatorio en el modulo csv: sin eso, Windows escribe \r\r\n.
    # lineterminator="\n" mantiene el archivo igual en Windows y en Linux.
    with DESTINO.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo, lineterminator="\n")
        escritor.writerow(("timestamp", "tag", "valor", "unidad", "calidad"))
        escritor.writerows(filas)

    print(f"{DESTINO.relative_to(RAIZ)}: {len(filas)} filas, {len(PERFILES)} tags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
