# Plan de Semana 2 — para escribir a mano

> **Cómo usar este plan:** es una guía de estudio, no una solución. Trae *dónde* va cada
> cosa, *por qué*, esqueletos con `# TODO` y las trampas que te vas a encontrar. El código
> lo escribís vos. Nada de copiar/pegar bloques terminados.

## Contexto

El código de Semana 1 (`tagstats/`) ya trae **dataclasses**, **type hints** y **excepciones
custom** (`ErrorDeDatos` → `CabeceraInvalidaError`, `FilaInvalidaError` en
[lectura.py:30](tagstats/lectura.py)). Lo que falta para cerrar el checklist de Sem 2:

- **Logging en vez de prints** — hoy [cli.py](tagstats/cli.py) usa `print(..., file=sys.stderr)` en 10 lugares.
- **Decoradores propios** — hoy solo hay built-in (`@dataclass`, `@property`).
- **`*args`/`**kwargs`** — hoy no aparecen de forma variádica.
- **Flujo de rama + Pull Request real** — Sem 1 se mergeó local; el remoto tiene solo `main`.

Y un ejercicio de aprendizaje que pediste: **reimplementar los modelos SIN dataclasses**, en
dos formas (clase a mano y `NamedTuple`), para *ver con los ojos* qué te genera `@dataclass`.

**Objetivo:** cerrar el entregable de Sem 2 ("refactor de Sem 1 con dataclasses + type hints +
logging, en una branch nueva y mergeada vía PR") + afianzar decoradores y el flujo de git.

Restricción de todo el proyecto: **Python ≥ 3.11**, **cero dependencias de runtime**, y la
salida a consola en **ASCII** (Windows: un acento fuera de la codificación de la consola aborta
con `UnicodeEncodeError` — ver nota en [reporte.py:6](tagstats/reporte.py)).

---

## Marco: una rama por parte, cada una mergeada por PR real

El entregable ES el flujo de git, así que estructurá el trabajo en ramas cortas y hacé un PR
por cada una en `github.com/FacZap/PySQLGit-selfcourse`:

| Rama | Contenido | Cómo integrarla (para practicar los temas de git) |
|---|---|---|
| `feat/logging` | Parte A | **merge** con `--no-ff` (commit de merge visible, como Sem 1) |
| `feat/decoradores` | Parte B | **rebase** sobre `main` actualizado y luego merge → historial lineal; sentís la diferencia vs. `--no-ff` |
| `exercise/modelos-sin-dataclass` | Parte C | spike de aprendizaje; se puede dejar sin mergear o mergear como ejercicio documentado |

- **Abrir el PR:** `gh` no está instalado. Opciones: instalar GitHub CLI
  (`winget install GitHub.cli`) y `gh pr create`, **o** pushear la rama y usar el botón
  *"Compare & pull request"* de la web.
- **Practicar conflictos (opcional):** hacé que `feat/logging` y `feat/decoradores` toquen
  las **mismas líneas de imports** al tope de `cli.py`. Al integrar la segunda vas a tener un
  conflicto real para resolver a mano — que es justo un ítem de la semana.

---

## Parte A — Logging en vez de prints  ·  rama `feat/logging`

**Archivos:** editás [cli.py](tagstats/cli.py) y [tests/test_cli.py](tests/test_cli.py); (opcional) sumás un
logger por módulo en `lectura.py`/`estadisticas.py`.

### A.1 — Un logger por módulo (código de biblioteca NO configura handlers)

Al tope de cada módulo que loguee:

```python
import logging
logger = logging.getLogger(__name__)   # "tagstats.cli", "tagstats.lectura", ...
```

Regla de oro: **la biblioteca solo llama a `logger.<nivel>(...)`; nunca a `basicConfig`.**
Quien decide handlers/formato/nivel es el punto de entrada (el CLI). Así, si mañana `tagstats`
se importa desde otro programa, no le pisás su configuración de logging.

### A.2 — Configurar logging UNA vez, en el entry point

Escribí una función chica en `cli.py`:

```python
def configurar_logging(nivel: int) -> None:
    # TODO: un StreamHandler a sys.stderr, un Formatter simple
    #       (ej. "%(levelname)s %(message)s"), setLevel(nivel) en el root.
    #       Ojo: no acumular handlers si se llama dos veces (en tests).
    ...
```

Y sumá un flag a `construir_parser()` para elegir verbosidad, p. ej. `-v/--verbose`
(`action="count"`, así `-v`=INFO, `-vv`=DEBUG) o `--log-nivel {INFO,DEBUG,...}`. Llamá a
`configurar_logging(...)` al principio de `main()`, antes del `try`.

**Trampa Windows/ASCII:** mantené los mensajes en ASCII (como el resto del proyecto) o el
handler puede explotar con `UnicodeEncodeError` en la consola. No metas acentos en los logs.

### A.3 — Mapear cada `print` actual a un nivel

| Línea actual (cli.py) | Pasa a |
|---|---|
| `aviso: se descartaron N filas` + detalle `  - {error}` | `logger.warning(...)` (el detalle, `logger.warning`/`debug`) |
| `error: no se encontro el archivo` | `logger.error(...)` |
| `error de datos: ...` + `sugerencia: --tolerante` | `logger.error(...)` |
| `error de lectura: ...` | `logger.error(...)` |
| `aviso: no quedaron lecturas` | `logger.warning(...)` |
| `reporte escrito en {salida}` | `logger.info(...)` |
| **`print(reporte)` a stdout** | **QUEDA como print** — es el *dato*, no un log |

> El dato de salida (la tabla/JSON/CSV) va a **stdout** y sigue siendo `print`. Solo migran a
> logging los **avisos/errores de diagnóstico** que hoy van a stderr. Esa distinción
> (dato vs. observabilidad) es el concepto clave del ítem.

### A.4 — Logs de diagnóstico nuevos (bonus barato)

Agregá algunos `logger.debug/info` que hoy no existen: "leyendo %s", "%d lecturas parseadas",
"limites cargados: %d". Usá **formato perezoso con `%`**, no f-strings:

```python
logger.info("leidas %d filas de %s", n, ruta.name)   # SÍ: no formatea si INFO está apagado
logger.info(f"leidas {n} filas")                       # NO: siempre construye el string
```

### A.5 — Migrar los tests: `capsys.err` → `caplog`

Varios tests de `test_cli.py` verifican texto en `capsys.readouterr().err`. Al pasar a logging
ese texto ya no sale por `capsys` sino por el sistema de logging → se leen con la fixture
**`caplog`**. Patrón:

```python
def test_archivo_inexistente_devuelve_1(tmp_path, caplog):
    with caplog.at_level(logging.ERROR):
        codigo = main([str(tmp_path / "no_existe.csv")])
    assert codigo == 1
    assert "no se encontro el archivo" in caplog.text
```

- Tests a migrar (los que hoy asertan sobre `.err`): `test_archivo_inexistente_devuelve_1`,
  `test_fila_invalida_corta_y_sugiere_tolerante`, `test_modo_tolerante_sigue_y_avisa_por_stderr`,
  `test_csv_vacio_avisa_pero_no_es_error`.
- Los que asertan **stdout** (tabla/JSON: `test_reporte_en_tabla`, `test_reporte_en_json`, etc.)
  **NO se tocan**: siguen con `capsys`.
- Gotcha `caplog`: captura por **propagación** al root; no desactives `propagate`. Por defecto
  toma WARNING+; para ver INFO/DEBUG usá `caplog.at_level(logging.INFO)`.

### A.6 — Criterio de aceptación (Parte A)
- `pytest -q` en verde.
- `python -m tagstats data/sensores_planta.csv -l data/limites.csv` → **reporte por stdout,
  logs por stderr**.
- `python -m tagstats data/sensores_planta.csv -f json > out.json` → `out.json` es JSON limpio
  (ningún log se filtró a stdout).
- `python -m tagstats data/inexistente.csv` → log de error en stderr, exit code 1.

---

## Parte B — Decoradores propios  ·  rama `feat/decoradores`

**Archivo nuevo:** `tagstats/decoradores.py`. **Test nuevo:** `tests/test_decoradores.py`.
Elegiste **`@medir_tiempo`** y **`@log_llamada`**.

### B.1 — `@medir_tiempo`

```python
import functools, time, logging
logger = logging.getLogger(__name__)

def medir_tiempo(func):
    @functools.wraps(func)                 # preserva __name__/__doc__ del original
    def envoltura(*args, **kwargs):
        inicio = time.perf_counter()       # perf_counter: monotónico, para medir duraciones
        resultado = func(*args, **kwargs)
        # TODO: logger.debug("%s tardo %.1f ms", func.__name__, (perf_counter()-inicio)*1000)
        return resultado
    return envoltura
```

- **Por qué `functools.wraps`:** sin él, la función decorada pasa a llamarse `envoltura` y
  pierde su docstring. Comprobalo en el test.
- **Trampa del generador:** NO lo pongas en `leer_lecturas`/`filtrar` (son generadores: medirías
  solo el tiempo de *crear* el generador, no el de iterarlo). Aplicalo a funciones **eager**:
  `resumir()` en [estadisticas.py:64](tagstats/estadisticas.py) es el candidato ideal.

### B.2 — `@log_llamada` (de paso, practicás `*args`/`**kwargs`)

Loguea entrada, argumentos y resultado de la función envuelta. Mismo esqueleto con
`*args, **kwargs`. Trampas:
- **No loguees estructuras enormes** (una lista de millones de `Lectura`): logueá `len(args...)`
  o un `repr` recortado, no el objeto entero.
- Usá `logger.debug` (apagado por defecto) y **formato `%` perezoso**.
- Aplicalo a una función chica: `leer_limites` o `estadisticas_de_tag`.

### B.3 — Dónde se aplican
`resumir` ← `@medir_tiempo`; `leer_limites` (o `estadisticas_de_tag`) ← `@log_llamada`.
Con `-vv` (DEBUG) al correr el CLI, ves el timing y la traza de llamada.

### B.4 — Criterio de aceptación (Parte B)
- `tests/test_decoradores.py`: (1) el resultado de una función dummy no cambia al decorarla;
  (2) `funcion_decorada.__name__` sigue siendo el original (prueba de `wraps`);
  (3) con `caplog.at_level(DEBUG)` aparece la línea de timing/llamada.
- `pytest -q` en verde; CLI con `-vv` muestra los logs nuevos.

---

## Parte C — Modelos SIN dataclasses (ejercicio comparativo)  ·  rama `exercise/modelos-sin-dataclass`

Objetivo: reproducir **el mismo contrato** que exige [tests/test_modelos.py](tests/test_modelos.py) sin
`@dataclass`, en **dos** implementaciones, y anotar qué te generaba el decorador. Van en
**archivos paralelos** para que el `modelos.py` original y sus tests sigan en verde.

**Contrato a respetar (lo que los tests exigen):**
- `Lectura(datetime, "TT-101", 78.0, "degC", calidad)` — construcción posicional.
- `Limite(tag=..., minimo=..., maximo=...)` — por keyword; `minimo>maximo` ⇒ `ValueError("limite invalido")`.
- Propiedades: `.es_confiable`, `.en_alarma(v)`, `.porcentaje_alarmas`, `.rango`.
- **Inmutable:** `lectura.valor = 999` ⇒ `AttributeError`.

### C.1 — `tagstats/modelos_plano.py` (clase a mano)

Por cada clase escribí a mano lo que `@dataclass(frozen=True, slots=True)` te generaba:

```python
class Lectura:
    __slots__ = ("timestamp", "tag", "valor", "unidad", "calidad")   # = slots=True

    def __init__(self, timestamp, tag, valor, unidad, calidad):
        # freeze: en __init__ hay que BYPASSEAR el bloqueo con object.__setattr__
        object.__setattr__(self, "timestamp", timestamp)
        # TODO: idem resto de campos

    def __setattr__(self, nombre, valor):        # = frozen=True
        raise AttributeError(f"{type(self).__name__} es inmutable")

    def __repr__(self):  ...                      # = repr generado
    def __eq__(self, otro):  ...                  # compara la tupla de campos
    def __hash__(self):  ...                      # OJO: definir __eq__ pone __hash__=None;
                                                  #      frozen dataclass te lo agrega solo
    @property
    def es_confiable(self): ...
```

- **Aprendizaje 1:** `frozen=True` = override de `__setattr__` + `object.__setattr__` adentro
  del `__init__`. Esto es *exactamente* lo que hace la dataclass por debajo.
- **Aprendizaje 2:** al definir `__eq__` perdés el `__hash__` por defecto → tenés que
  reimplementarlo si querés que el objeto sea hasheable (la dataclass frozen lo hace por vos).
- **`Limite`:** la validación va **directo en `__init__`** (acá no existe `__post_init__`, porque
  el `__init__` lo escribís vos). Anotá la diferencia: la dataclass separa `__post_init__`
  *porque* te genera el `__init__`.

### C.2 — `tagstats/modelos_tupla.py` (`typing.NamedTuple`)

```python
from typing import NamedTuple

class Lectura(NamedTuple):
    timestamp: datetime
    tag: str
    valor: float
    unidad: str
    calidad: str

    @property
    def es_confiable(self) -> bool: ...          # las properties funcionan en NamedTuple
```

- **Gratis:** `__init__`, `__repr__`, `__eq__`, `__hash__` e **inmutabilidad** (asignar `.valor`
  ya tira `AttributeError` porque es una tupla) → el test de inmutabilidad pasa sin escribir nada.
- **Lo incómodo (validar `Limite`):** NamedTuple no tiene `__post_init__` y no podés tocar
  `__init__`; para validar hay que overridear **`__new__`**:

```python
class Limite(NamedTuple):
    tag: str
    minimo: float
    maximo: float
    def __new__(cls, tag, minimo, maximo):
        if minimo > maximo:
            raise ValueError("limite invalido ...")
        return super().__new__(cls, tag, minimo, maximo)
```

  **Aprendizaje 3:** esto muestra por qué el `__post_init__` de la dataclass es más cómodo.

### C.3 — `tests/test_modelos_alternativos.py` (mismo contrato, varias implementaciones)

Parametrizá el módulo bajo prueba para correr **el mismo set de asserts** contra las dos (o
las tres) implementaciones:

```python
import importlib, pytest

@pytest.mark.parametrize("modname", ["tagstats.modelos_plano", "tagstats.modelos_tupla"])
def test_contrato_de_lectura(modname):
    m = importlib.import_module(modname)
    # TODO: reusá los mismos casos que tests/test_modelos.py:
    #       es_confiable, en_alarma en los bordes (59.9/60/95/95.1),
    #       limite invertido ⇒ ValueError, inmutabilidad ⇒ AttributeError,
    #       porcentaje_alarmas == 25.0 y rango == 29.0
```

### C.4 — Cierre del ejercicio: la tabla del "¿qué me generaba `@dataclass`?"

Anotá (en `docs/`, un `SIN_DATACLASS.md` corto, o al final de un CONCEPTOS de Sem 2) la
comparación honesta:

| Cosa | `@dataclass(frozen, slots)` | Clase a mano | NamedTuple |
|---|---|---|---|
| `__init__` | generado | lo escribís | generado |
| `__repr__` / `__eq__` / `__hash__` | generados | los escribís (ojo `__hash__`) | generados |
| inmutabilidad | `frozen=True` | `__setattr__` + `object.__setattr__` | gratis (es tupla) |
| validación | `__post_init__` | en `__init__` | en `__new__` (incómodo) |

### C.5 — Criterio de aceptación (Parte C)
- `pytest tests/test_modelos_alternativos.py -q` en verde (mismo contrato en ambas impls).
- `pytest -q` completo sigue en verde (no rompiste `modelos.py` original).

---

## Verificación de punta a punta

```bash
pytest -q
```
```bash
powershell -File scripts/verificar.ps1
```
Manual (mirá stdout vs stderr por separado):
```bash
python -m tagstats data/sensores_planta.csv -l data/limites.csv
```
```bash
python -m tagstats data/sensores_planta.csv -f json > out.json
```
```bash
python -m tagstats data/sensores_sucios.csv --tolerante -vv
```
```bash
python -m tagstats data/inexistente.csv
```
Esperado: reporte por stdout siempre limpio; avisos/errores + timing (`@medir_tiempo`) +
traza (`@log_llamada`) por stderr con `-vv`; exit code 1 en el archivo inexistente.

---

## Mapa contra el checklist de la pantalla

| Ítem del checklist | Se cubre en |
|---|---|
| Modelar datos con dataclasses + type hints | Ya estaba (Sem 1) + Parte C lo profundiza por contraste |
| Logging en vez de prints | **Parte A** |
| 1-2 excepciones propias y manejarlas | Ya estaba (`ErrorDeDatos`/`FilaInvalidaError`); las reusás en A |
| Feature branch + mergear con PR | **Marco de ramas** (A merge `--no-ff`, B rebase, PR real en GitHub) |
| Temas sueltos: decoradores | **Parte B** (`@medir_tiempo`, `@log_llamada`) |
| Temas sueltos: `*args`/`**kwargs` | **Parte B** (envolturas variádicas) |
| Git: merge vs rebase / resolver conflictos | **Marco de ramas** (merge en A, rebase en B, conflicto provocado opcional) |

## Orden sugerido
1. `feat/logging` (Parte A) → PR → merge `--no-ff`.
2. `feat/decoradores` (Parte B) → rebase sobre `main` → PR → merge.
3. `exercise/modelos-sin-dataclass` (Parte C) → PR de ejercicio.

Cada rama arranca de `main` y termina en verde (`pytest -q`) antes de abrir el PR.
