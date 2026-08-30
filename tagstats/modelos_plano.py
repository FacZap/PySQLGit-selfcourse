"""
**Contrato a respetar (lo que los tests exigen):**
- `Lectura(datetime, "TT-101", 78.0, "degC", calidad)` — construcción posicional.
- `Limite(tag=..., minimo=..., maximo=...)` — por keyword; `minimo>maximo` ⇒ `ValueError("limite invalido")`.
- Propiedades: `.es_confiable`, `.en_alarma(v)`, `.porcentaje_alarmas`, `.rango`.
- **Inmutable:** `lectura.valor = 999` ⇒ `AttributeError`.

Por cada clase escribí a mano lo que ``@dataclass(frozen=True, slots=True)`` te generaba:
1. Lectura
2. Limite
3. Estadisticas

Alternativas para hacerlo (que pude encontrar):
*Classes & Objects:
    Classes provide a means of bundling data and functionality together. Creating a new class creates a new type of object, allowing new instances of that type to be made. Each class instance can have attributes attached to it for maintaining its state. Class instances can also have methods (defined by its class) for modifying its state

    ``frozen=True``  -> inmutable: una lectura historica no se corrige "en el aire".
    ``slots=True``   -> sin ``__dict__`` por instancia: menos memoria y mas rapido,
                        que importa cuando el CSV trae cientos de miles de filas.


__dict__: most objects store their attributes here (see where are attributes stored?)
__slots__: classes using this are more memory efficient than classes using __dict__
__match_args__: classes can define a tuple noting the significance of positional attributes when the class is used in structural pattern matching (match-case)
"""

from __future__ import annotations
# from dataclasses import dataclass
from datetime import datetime

#: Valores de la columna ``calidad`` que consideramos dato confiable.
#: Un ``frozenset`` porque es constante, no se modifica y la busqueda es O(1).
CALIDADES_CONFIABLES = frozenset({"good", "ok", "buena"})


class Lectura:
    """Una muestra de un tag en un instante determinado."""

    __slots__ = ("timestamp", "tag", "valor", "unidad", "calidad")   # = slots=True
    __match_args__ = ("timestamp", "tag", "valor", "unidad", "calidad")  # dataclass lo genera solo

    def __init__(self, timestamp, tag, valor, unidad, calidad):
        # freeze: en __init__ hay que BYPASSEAR el bloqueo con object.__setattr__
        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "tag", tag)
        object.__setattr__(self, "valor", valor)
        object.__setattr__(self, "unidad", unidad)
        object.__setattr__(self, "calidad", calidad)
        """
        Por que no se podria haber hecho esto?
                self.timestamp = timestamp
                self.tag = tag
                ...

        RESPUESTA: porque `self.timestamp = timestamp` es azucar sintactico para
        `type(self).__setattr__(self, "timestamp", timestamp)`. Y dos lineas mas
        abajo redefinimos justamente `__setattr__` para que SIEMPRE levante
        AttributeError, sin excepcion para el propio __init__. Entonces la primera
        asignacion normal ya explotaria, incluso antes de terminar de construir el
        objeto. `object.__setattr__(self, nombre, valor)` esquiva el metodo que
        vos sobrescribiste y llama directo a la implementacion base de `object`,
        que si sabe escribir en el slot.
        """

        """
        Ah, es porque tengo que redefinir __setattr__ para levantar AttributeError?

        RESPUESTA: si, exacto. `frozen=True` en un dataclass no existe "de verdad":
        por abajo el decorador te genera un `__setattr__` (y un `__delattr__`) que
        rechazan cualquier intento de escritura despues de construido el objeto, y
        para poder poner los valores iniciales usa `object.__setattr__` dentro del
        `__init__` que genera. Aca estamos haciendo a mano exactamente eso mismo.
        """

    def __setattr__(self, nombre, valor):        # = frozen=True
        raise AttributeError(f"{type(self).__name__} es inmutable")

    def __delattr__(self, nombre):                # frozen tambien bloquea el del
        raise AttributeError(f"{type(self).__name__} es inmutable")

    def __repr__(self):                            # = repr generado
        return (
            f"{type(self).__name__}(timestamp={self.timestamp!r}, tag={self.tag!r}, "
            f"valor={self.valor!r}, unidad={self.unidad!r}, calidad={self.calidad!r})"
        )

    def _campos(self):
        # Tupla de comparacion: la misma que dataclass usa para __eq__/__hash__.
        return (self.timestamp, self.tag, self.valor, self.unidad, self.calidad)

    def __eq__(self, otro):                        # compara la tupla de campos
        if type(otro) is not type(self):
            return NotImplemented
        return self._campos() == otro._campos()

    def __hash__(self):                            # OJO: definir __eq__ pone __hash__=None;
        return hash(self._campos())                #      frozen dataclass te lo agrega solo

    @property
    def es_confiable(self):
        """True si el historiador marco la muestra como buena."""
        return self.calidad.strip().lower() in CALIDADES_CONFIABLES


class Limite:
    """Rango operativo esperado de un tag. Fuera de el, hay alarma."""

    __slots__ = ("tag", "minimo", "maximo")
    __match_args__ = ("tag", "minimo", "maximo")

    def __init__(self, tag, minimo, maximo):
        object.__setattr__(self, "tag", tag)
        object.__setattr__(self, "minimo", minimo)
        object.__setattr__(self, "maximo", maximo)
        # Equivalente a mano de __post_init__: se valida aca, no despues de
        # construido, para no arrastrar un limite imposible hasta el calculo,
        # donde el sintoma seria "0 alarmas" sin explicacion.
        if self.minimo > self.maximo:
            raise ValueError(
                f"limite invalido para {self.tag}: minimo ({self.minimo}) > maximo ({self.maximo})"
            )

    def __setattr__(self, nombre, valor):
        raise AttributeError(f"{type(self).__name__} es inmutable")

    def __delattr__(self, nombre):
        raise AttributeError(f"{type(self).__name__} es inmutable")

    def __repr__(self):
        return f"{type(self).__name__}(tag={self.tag!r}, minimo={self.minimo!r}, maximo={self.maximo!r})"

    def _campos(self):
        return (self.tag, self.minimo, self.maximo)

    def __eq__(self, otro):
        if type(otro) is not type(self):
            return NotImplemented
        return self._campos() == otro._campos()

    def __hash__(self):
        return hash(self._campos())

    def en_alarma(self, valor: float) -> bool:
        """True si el valor cae fuera del rango [minimo, maximo]."""
        return not self.minimo <= valor <= self.maximo


class Estadisticas:
    """Resumen de un tag para el periodo analizado."""

    __slots__ = ("tag", "unidad", "muestras", "minimo", "maximo", "promedio", "desvio", "alarmas")
    __match_args__ = __slots__

    """
    __match_args__ = __slots__ no copia la tupla, la alias: hace que __match_args__ apunte al mismo objeto tupla que ya armaste en __slots__ (("tag", "unidad", "muestras", "minimo", "maximo", "promedio", "desvio", "alarmas")), en vez de volver a escribir los ocho nombres a mano como hice en Lectura y Limite.

    Esto es seguro solo porque las tuplas son inmutables — no hay riesgo de que alguien mute una y la otra cambie con ella (como pasaría si fueran listas). Y funciona semánticamente porque:

    __slots__ define el layout de memoria (y de paso, el orden de los campos).
    __match_args__ es lo que usa match/case para mapear posiciones a nombres: case Estadisticas(t, u, m, ...).
    Como en tu __init__ los parámetros están en ese mismo orden, reusar la tupla es correcto — no es casualidad, es que las tres cosas (__slots__, __match_args__, orden de __init__) tienen que estar sincronizadas a mano vos mismo, cosa que @dataclass te garantiza automáticamente porque genera las tres a partir de la misma lista de campos.
    """

    def __init__(self, tag, unidad, muestras, minimo, maximo, promedio, desvio, alarmas):
        object.__setattr__(self, "tag", tag)
        object.__setattr__(self, "unidad", unidad)
        object.__setattr__(self, "muestras", muestras)
        object.__setattr__(self, "minimo", minimo)
        object.__setattr__(self, "maximo", maximo)
        object.__setattr__(self, "promedio", promedio)
        object.__setattr__(self, "desvio", desvio)
        object.__setattr__(self, "alarmas", alarmas)

    def __setattr__(self, nombre, valor):
        raise AttributeError(f"{type(self).__name__} es inmutable")

    def __delattr__(self, nombre):
        raise AttributeError(f"{type(self).__name__} es inmutable")

    def __repr__(self):
        campos = ", ".join(f"{nombre}={getattr(self, nombre)!r}" for nombre in self.__slots__)
        return f"{type(self).__name__}({campos})"

    def _campos(self):
        return tuple(getattr(self, nombre) for nombre in self.__slots__)

    def __eq__(self, otro):
        if type(otro) is not type(self):
            return NotImplemented
        return self._campos() == otro._campos()

    def __hash__(self):
        return hash(self._campos())

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
