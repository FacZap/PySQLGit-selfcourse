"""Modelos del dominio.

Se usan ``dataclasses`` en vez de diccionarios sueltos: el tipo documenta que
campos existen, el editor autocompleta y un error de tipeo (``lectura.valorr``)
falla en el momento en vez de devolver ``None`` silenciosamente.

``frozen=True``  -> inmutable: una lectura historica no se corrige "en el aire".
``slots=True``   -> sin ``__dict__`` por instancia: menos memoria y mas rapido,
                    que importa cuando el CSV trae cientos de miles de filas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

#: Valores de la columna ``calidad`` que consideramos dato confiable.
#: Un ``frozenset`` porque es constante, no se modifica y la busqueda es O(1).
CALIDADES_CONFIABLES = frozenset({"good", "ok", "buena"})


@dataclass(frozen=True, slots=True)
class Lectura:
    """Una muestra de un tag en un instante determinado."""

    timestamp: datetime
    tag: str
    valor: float
    unidad: str
    calidad: str

    @property
    def es_confiable(self) -> bool:
        """True si el historiador marco la muestra como buena."""
        return self.calidad.strip().lower() in CALIDADES_CONFIABLES


@dataclass(frozen=True, slots=True)
class Limite:
    """Rango operativo esperado de un tag. Fuera de el, hay alarma."""

    tag: str
    minimo: float
    maximo: float

    def __post_init__(self) -> None:
        # Validar en el constructor evita arrastrar un limite imposible
        # hasta el calculo, donde el sintoma seria "0 alarmas" sin explicacion.
        if self.minimo > self.maximo:
            raise ValueError(
                f"limite invalido para {self.tag}: minimo ({self.minimo}) > maximo ({self.maximo})"
            )

    def en_alarma(self, valor: float) -> bool:
        """True si el valor cae fuera del rango [minimo, maximo]."""
        return not self.minimo <= valor <= self.maximo


@dataclass(frozen=True, slots=True)
class Estadisticas:
    """Resumen de un tag para el periodo analizado."""

    tag: str
    unidad: str
    muestras: int
    minimo: float
    maximo: float
    promedio: float
    desvio: float
    alarmas: int

    @property
    def porcentaje_alarmas(self) -> float:
        """Porcentaje de muestras fuera de rango (0.0 si no hay muestras)."""
        if not self.muestras:
            return 0.0
        return 100.0 * self.alarmas / self.muestras

    @property
    def rango(self) -> float:
        """Diferencia entre el maximo y el minimo observados."""
        return self.maximo - self.minimo
