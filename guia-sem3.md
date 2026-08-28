# Plan de Semana 3 — para escribir a mano

> **Cómo usar este plan:** es una guía de estudio, no una solución. Trae *dónde* va cada
> cosa, *por qué*, esqueletos con `# TODO` y las trampas que te vas a encontrar. El código
> lo escribís vos. Nada de copiar/pegar bloques terminados.

## Contexto

Semana 3 del roadmap: **POO + pandas + tests**. Lo que ya tenés cubierto desde antes:

- **POO liviano y properties** — `tagstats/` ya trae dataclasses con `@property`
  (`es_confiable`, `porcentaje_alarmas`, `rango` en [modelos.py](tagstats/modelos.py)) y una
  jerarquía de excepciones con herencia real (`ErrorDeDatos` → `CabeceraInvalidaError`,
  `FilaInvalidaError` en [lectura.py:30](tagstats/lectura.py)).
- **pytest: fixtures + parametrize** — ya se usan en [tests/conftest.py](tests/conftest.py) y
  [tests/test_lectura.py:41](tests/test_lectura.py).
- **README con secciones** — el [README.md](README.md) ya está completo.

Lo que **falta** para cerrar Sem 3, y que esta guía cubre:

- **pandas de verdad**: `DataFrame`, indexing, `groupby`, `merge`. Hoy el proyecto tiene **cero**
  pandas (usa `csv` + generadores).
- **Una clase Loader/Cleaner explícita** que cargue y limpie datos (CSV → DataFrame limpio).
- **Deduplicación** (hoy no existe manejo de duplicados en ningún lado).
- **Tag/release v0.1 en GitHub** (`git tag` está vacío).

**Decisión de diseño (importante):** todo esto va en un **paquete nuevo aparte, `tagframe/`**,
hermano de `tagstats/`, que **reusa los CSV de `data/`**. Motivo: `tagstats` presume de **cero
dependencias de runtime** (lo repiten README, `docs/CONCEPTOS.md` y la guía de Sem 2) y no
queremos ensuciar esa identidad metiéndole pandas. `tagframe` es el que depende de pandas;
`tagstats` queda intacto.

**Objetivo:** entregar un módulo orientado a objetos que **carga y limpia** un CSV de proceso
(→ `DataFrame` limpio) con **suite de tests en pytest**, y **etiquetar una release v0.1**.

Restricciones del proyecto: **Python ≥ 3.11**; **pandas solo en `tagframe`** (`tagstats` sigue
con `dependencies = []`); tests en verde antes de cada PR.

---

## Marco de ramas

El tema de git de **esta** semana es **tags / releases** y **README con secciones** (no merge vs.
rebase, eso fue Sem 2). Así que el flujo es simple:

| Rama | Contenido | Integración |
|---|---|---|
| `feat/tagframe` | Todo el paquete `tagframe/` + tests + doc | PR real en GitHub → merge a `main` |
| (sobre `main` ya mergeado) | **Tag `v0.1.0` + Release** | `git tag` anotado + Release por la web/gh |

- El tag se hace **después** de mergear, sobre `main`, cuando `pytest -q` está en verde.
- `gh` puede no estar instalado (como en Sem 2): tenés el camino por la **web de GitHub** más abajo.

---

## Estructura del paquete (espeja el split "por responsabilidad" de `tagstats`)

Mirá cómo `tagstats/__init__.py` divide por responsabilidad; replicá esa idea:

```
tagframe/
  __init__.py     __version__ + docstring que explica el split
  fuentes.py      FuenteDeDatos (ABC) -> FuenteCSV          [HERENCIA]     CSV  -> DataFrame crudo
  limpieza.py     Limpiador + ResultadoLimpieza             [pandas + properties]  crudo -> limpio
  cargador.py     Cargador: compone Fuente + Limpiador      [COMPOSICION]  -> DataFrame limpio
  analisis.py     resumen(df, limites): groupby + merge     [GROUPBY+MERGE] -> DataFrame de stats
```

Cada archivo toca **un** tema de la semana. Si al final no sabés en qué archivo mirar un
concepto, el split quedó mal.

---

## Parte A — `fuentes.py`  ·  herencia (ABC → CSV)

**Idea:** una base abstracta `FuenteDeDatos` que promete un método `leer() -> DataFrame`, y una
implementación concreta `FuenteCSV`. Esto es herencia **no forzada**: deja la puerta abierta a un
futuro `FuenteSQL` (el repo se llama *PySQLGit*: el SQL viene después) sin tocar el resto.

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
import pandas as pd

class FuenteDeDatos(ABC):
    """Contrato: sé de dónde salen los datos crudos, no cómo se limpian."""
    @abstractmethod
    def leer(self) -> pd.DataFrame:
        ...

class FuenteCSV(FuenteDeDatos):
    COLUMNAS = ("timestamp", "tag", "valor", "unidad", "calidad")

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)

    def leer(self) -> pd.DataFrame:
        # TODO: pd.read_csv(self.ruta, dtype=str)  <- leer TODO como texto a propósito:
        #       la limpieza/coerción de tipos es responsabilidad de Limpiador, no de acá.
        #       Con dtype=str evitás que pandas "adivine" y te oculte los N/A e inf.
        # TODO: validar que estén las COLUMNAS (si falta alguna, levantá un error claro,
        #       al estilo CabeceraInvalidaError de tagstats/lectura.py).
        ...
```

**Trampas de `read_csv`:**
- La fila corrida de [data/sensores_sucios.csv](data/sensores_sucios.csv) —
  `2026-08-24T06:00:00,PT-204,4,82,bar,Good` (un decimal `4,82` sin comillas)— trae **6 campos
  para 5 columnas**. `read_csv` puede tirar `ParserError`. Decidí a conciencia: `on_bad_lines=
  "warn"` (saltea y avisa) vs. `on_bad_lines="error"` (corta). En Sem 1 esto se detectaba
  explícitamente ([lectura.py:70](tagstats/lectura.py)); anotá la diferencia de filosofía.
- `dtype=str` es a propósito: si dejás que pandas infiera, `""` puede volverse `NaN` y `"4"`
  un `int`, y perdés el control de la limpieza. Leé crudo, limpiá después.

---

## Parte B — `limpieza.py`  ·  nulos, tipos, duplicados (indexing + properties)

**Idea:** un `Limpiador` que recibe el DataFrame crudo y devuelve uno limpio, **regla por regla**.
Cada regla mapea a una fila real del CSV sucio. Además exponé un `ResultadoLimpieza` con
`@property` (ahí entra el tema *properties*).

```python
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
        # TODO: 0.0 si filas_entrada == 0 (no dividas por cero), si no 100 * descartadas / entrada
        ...

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
        ...
```

**Trampas de la limpieza:**
- `errors="coerce"` es el patrón central: basura → `NaN`/`NaT`, y limpiás con `dropna`.
- `inf` sobrevive a `dropna` si no lo pasás a `NaN` antes. Es el caso `PT-204,inf,bar,Uncertain`.
- `tag` vacío es `""`, **no** `NaN`: `dropna` no lo toca; filtralo aparte.
- `drop_duplicates` sin `subset` compara la fila **entera**; vos querés la clave `(timestamp, tag)`.
- Después de filtrar filas, el índice queda con huecos: `reset_index(drop=True)` para que los tests
  no dependan de índices salteados.
- **Nota de aprendizaje:** el CSV `data/sensores_sucios.csv` no trae un duplicado exacto. Para
  probar la regla 5, en el test inyectás una fila repetida en un DataFrame chico (ver Parte F).

---

## Parte C — `cargador.py`  ·  composición

**Idea:** el `Cargador` **tiene** una fuente y un limpiador (los recibe), y encadena. No hereda de
ninguno: los *compone*. Esta es la diferencia con la Parte A (que era herencia).

```python
from __future__ import annotations
import pandas as pd
from .fuentes import FuenteDeDatos
from .limpieza import Limpiador, ResultadoLimpieza

class Cargador:
    def __init__(self, fuente: FuenteDeDatos, limpiador: Limpiador | None = None) -> None:
        self.fuente = fuente                       # composición: lo recibe, no lo hereda
        self.limpiador = limpiador or Limpiador()

    def cargar(self) -> ResultadoLimpieza:
        # TODO: crudo = self.fuente.leer(); return self.limpiador.limpiar(crudo)
        ...
```

- **Por qué composición y no herencia acá:** un `Cargador` no *es* una fuente ni *es* un limpiador;
  *usa* uno de cada. Herencia sería modelar "es-un"; composición modela "tiene-un". Anotá esta
  distinción, es el corazón del tema de la semana.
- Como `fuente` es del tipo base `FuenteDeDatos`, el mismo `Cargador` sirve para `FuenteCSV` hoy y
  para `FuenteSQL` mañana sin cambiar una línea. Eso es lo que compra la ABC de la Parte A.

---

## Parte D — `analisis.py`  ·  groupby + merge

**Idea:** reproducir el resumen de Sem 1 (min, max, promedio, desvío, alarmas por tag) pero con
pandas. Ventaja pedagógica enorme: **ya conocés las respuestas correctas** (están en el README),
así que podés validar tu `groupby`/`merge` contra ellas.

```python
from __future__ import annotations
import pandas as pd

def resumen(df: pd.DataFrame, limites: pd.DataFrame) -> pd.DataFrame:
    # 1) GROUPBY: stats por tag.  TODO:
    #    g = df.groupby("tag")["valor"].agg(muestras="count", minimo="min",
    #                                        maximo="max", promedio="mean",
    #                                        desvio=lambda s: s.std(ddof=0))
    #    OJO ddof=0  -> desvío POBLACIONAL (pstdev), como Sem 1. El default de
    #    pandas es ddof=1 (muestral) y NO va a coincidir con los números del README.

    # 2) MERGE con límites para contar alarmas.  TODO:
    #    con_lim = df.merge(limites[["tag", "minimo", "maximo"]], on="tag", how="left")
    #    fuera = (con_lim["valor"] < con_lim["minimo"]) | (con_lim["valor"] > con_lim["maximo"])
    #    OJO: el borde exacto NO es alarma (60.0 y 95.0 están EN rango), igual que
    #    Limite.en_alarma en tagstats/modelos.py:54. Por eso < y >, no <= y >=.
    #    alarmas = fuera.groupby(con_lim["tag"]).sum()

    # 3) Unir stats + alarmas, ordenar por tag, resetear índice.  TODO.
    ...
```

**Cómo leer los límites** (los usa el merge). `data/limites.csv` tiene columnas
`tag,minimo,maximo,unidad,descripcion`:

```python
def leer_limites(ruta) -> pd.DataFrame:
    # TODO: pd.read_csv(ruta) y quedate al menos con tag, minimo, maximo (numéricos).
    ...
```

**Trampas de análisis:**
- `.std(ddof=0)` vs. default `ddof=1` — la más importante. Sin esto, el desvío no matchea Sem 1.
- Con **una sola muestra** por tag, `std` da `NaN`; Sem 1 devolvía `0.0`. Decidí (`fillna(0.0)`) y
  anotá por qué.
- Un tag sin fila en `limites` (merge `how="left"`) deja `minimo/maximo` en `NaN` → la comparación
  da `False` → 0 alarmas. Es el comportamiento correcto ("sin límite, no hay alarma"), igual que
  Sem 1; confirmalo con un test.
- Si un mismo tag mezcla unidades, `groupby` no se entera; si querés paridad total, agregá la unidad
  al `groupby` o un chequeo aparte (lo hacía `estadisticas_de_tag`).

---

## Parte E — Config del paquete (para pegar, no para pensar)

Estos son los únicos cambios fuera de `tagframe/`. Mantienen a `tagstats` con cero deps.

**`pyproject.toml`:** sumá el paquete y pandas como **extra opcional** (no como dep base):

```toml
[tool.setuptools]
packages = ["tagstats", "tagframe"]      # <- agregar "tagframe"

[project.optional-dependencies]
frame = ["pandas>=2.2"]                  # <- nuevo. tagstats [project].dependencies SIGUE = []
```

Instalás lo de pandas con: `pip install -e .[frame]`.

**`requirements-dev.txt`:** sumá `pandas` (y opcional `pandas-stubs` para el tipado):

```
pandas==2.2.2
pandas-stubs==2.2.2.240807   # opcional, para que ruff/el editor no se quejen del tipado
```

---

## Parte F — Tests (fixtures + parametrize)

Van en `tests/` (misma carpeta; `pythonpath=["."]` ya deja `import tagframe`). Espejá el patrón
parametrizado de [tests/test_lectura.py:41](tests/test_lectura.py).

**`tests/test_tagframe_limpieza.py`** — un caso por tipo de dato sucio:

```python
import numpy as np, pandas as pd, pytest
from tagframe.limpieza import Limpiador

FILA_OK = {"timestamp": "2026-08-24T06:00:00", "tag": "TT-101",
           "valor": "78.5", "unidad": "degC", "calidad": "Good"}

@pytest.fixture
def limpiador() -> Limpiador:
    return Limpiador()

def _df(**overrides) -> pd.DataFrame:
    fila = {**FILA_OK, **overrides}
    return pd.DataFrame([fila], dtype=str)

@pytest.mark.parametrize("campo, valor", [
    ("valor", "N/A"),                 # tipo: no numérico
    ("valor", ""),                    # nulo
    ("valor", "inf"),                 # no finito
    ("timestamp", "24/08/2026 06:20"),# formato de fecha inválido -> NaT
    ("tag", "   "),                   # tag vacío
])
def test_descarta_fila_sucia(limpiador, campo, valor):
    res = limpiador.limpiar(_df(**{campo: valor}))
    assert res.filas_salida == 0
    assert res.filas_descartadas == 1

def test_deduplica_por_timestamp_y_tag(limpiador):
    df = pd.concat([_df(), _df()], ignore_index=True)   # dos filas idénticas
    res = limpiador.limpiar(df)
    assert res.filas_salida == 1

def test_conserva_la_fila_valida(limpiador):
    res = limpiador.limpiar(_df())
    assert res.filas_salida == 1
    assert res.porcentaje_descartado == 0.0
```

**`tests/test_tagframe_analisis.py`** — validá contra los números de Sem 1 (README):

```python
import pandas as pd, pytest
from tagframe.cargador import Cargador
from tagframe.fuentes import FuenteCSV
from tagframe.analisis import resumen, leer_limites

@pytest.fixture
def resumen_planta():
    df = Cargador(FuenteCSV("data/sensores_planta.csv")).cargar().df
    return resumen(df, leer_limites("data/limites.csv")).set_index("tag")

def test_tt101_matchea_semana_1(resumen_planta):
    fila = resumen_planta.loc["TT-101"]
    assert fila["muestras"] == 144
    assert fila["minimo"] == pytest.approx(73.70, abs=0.01)
    assert fila["maximo"] == pytest.approx(102.10, abs=0.01)
    assert fila["promedio"] == pytest.approx(80.24, abs=0.01)
    assert fila["desvio"] == pytest.approx(7.27, abs=0.01)   # <- solo pasa con ddof=0
    assert fila["alarmas"] == 16

def test_total_de_alarmas(resumen_planta):
    assert resumen_planta["alarmas"].sum() == 34   # total de Sem 1
```

Con esto ya superás el "≥4 tests con fixtures y parametrize" y de paso validás toda la cadena.

---

## Parte G — Release v0.1 + README

**README:** agregá una sección para `tagframe` (qué es, cómo se instala con `.[frame]`, un ejemplo
de `Cargador(FuenteCSV(...)).cargar()`), separada de la de `tagstats`. Es el ítem *README con
secciones* de la semana.

**Tag + Release** (sobre `main` mergeado y en verde). El tag lo corrés **vos**:

```bash
git tag -a v0.1.0 -m "tagframe v0.1: carga + limpieza pandas con tests"
```
```bash
git push origin v0.1.0
```

- **Release por la web:** en `github.com/FacZap/PySQLGit-selfcourse` → *Releases* → *Draft a new
  release* → elegí el tag `v0.1.0` → título y notas → *Publish release*.
- **Release con gh** (si lo instalás con `winget install GitHub.cli`):
  `gh release create v0.1.0 --title "v0.1.0" --notes "..."`.
- **Versión:** `tagframe/__init__.py` puede arrancar en `__version__ = "0.1.0"`, igual que
  `tagstats`. Si preferís tags por entregable, usá `v0.1.0-tagframe`; para el curso, `v0.1.0` a
  secas alcanza y es el primer release del repo.

---

## Verificación de punta a punta

```bash
pip install -e .[frame]      # o: pip install -r requirements-dev.txt
```
```bash
pytest -q                    # tagstats (intacto) + tagframe, todo verde
```
```bash
python -c "from tagframe.cargador import Cargador; from tagframe.fuentes import FuenteCSV; r=Cargador(FuenteCSV('data/sensores_sucios.csv')).cargar(); print('descartadas:', r.filas_descartadas)"
```
Esperado:
- `pytest -q` en verde, incluida la suite vieja de `tagstats` (no la rompiste).
- El resumen de `tagframe` sobre `data/sensores_planta.csv` **coincide** con la tabla del README.
- Sobre `data/sensores_sucios.csv`, `filas_descartadas > 0`.
- `tagstats` sigue importándose **sin** pandas; `pyproject.toml` `[project].dependencies` sigue `[]`.
- `git tag` lista `v0.1.0` y el Release aparece en GitHub.

---

## Mapa contra el checklist de la pantalla

| Ítem del checklist / tema | Se cubre en |
|---|---|
| Clase Loader/Cleaner con responsabilidades claras | **Parte A** (Fuente), **B** (Limpiador), **C** (Cargador) |
| Limpiar datos con pandas (nulos, tipos, duplicados) | **Parte B** (las 5 reglas) |
| ≥4 tests con fixtures y parametrize | **Parte F** |
| Etiquetar release v0.1 en GitHub | **Parte G** |
| Temas: clases / herencia / composición | **A** (herencia ABC→CSV) + **C** (composición) |
| Temas: properties | **B** (`ResultadoLimpieza`) |
| Temas: pandas DataFrame, indexing | **A** y **B** |
| Temas: groupby + merge | **Parte D** |
| Temas: pytest fixtures, parametrize | **Parte F** |
| Git: tags / releases | **Parte G** |
| Git: README con secciones | **Parte G** |

## Orden sugerido

1. Rama `feat/tagframe`. Config primero (**Parte E**) así `import pandas` anda.
2. **A → B → C → D** (fuente → limpieza → cargador → análisis), corriendo tests a medida
   (**Parte F**) sobre cada pieza.
3. README (**Parte G**), PR, merge a `main`.
4. Tag `v0.1.0` + Release (**Parte G**) sobre `main` en verde.
