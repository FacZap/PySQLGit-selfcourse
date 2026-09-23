# TL;DR - TODO

[X] Semana 4 — Modelado + JOINs + CTEs
[] Semana 5 — Window functions + planes de ejecución
[] Semana 6 — Diseño + ingesta
[] Semana 7 — Transformación + analítica
[] Semana 8 — Empaque + portfolio

# Guía a futuro — Bloque 2 (SQL Pro) + Bloque 3 (Capstone)

> **Cómo usar esta guía:** no es un tutorial semana a semana como `guia-sem2.md`/`guia-sem3.md`
> (esas traen esqueletos de código para una sola semana, con TODOs para completar). Esta es tu
> **fuente de verdad y ayuda memoria** para las Semanas 4 a 8 de una sola vez: temas, recursos,
> entregable y checklist tal como están en el roadmap, más una "chuleta" de sintaxis SQL y
> patrones de arquitectura para consultar mientras escribís el código a mano. No resuelve tu
> ejercicio puntual — el esquema propio, las queries propias, la arquitectura propia del pipeline
> las seguís pensando vos. Si al llegar a una semana concreta querés más profundidad tipo
> sem2/sem3, escribí un `guia-semN.md` dedicado en el mismo estilo.

## Contexto general

Estado actual del repo:

- **Semana 2** — en curso: falta terminar de migrar `print` a `logging` en
  [cli.py](tagstats/cli.py) y dejar `pytest -q` en verde otra vez.
- **Semana 3** — planeada en `guia-sem3.md` pero **sin implementar**: el paquete `tagframe/`
  (pandas) todavía no existe en el árbol.
- **Semanas 4 a 8** (esta guía) — **no hay una sola línea de SQL ni de base de datos en el repo
  todavía**: cero SQLAlchemy, cero driver, cero `.sql`, cero CI. Arranca todo de cero (aunque
  [CONCEPTOS.md](docs/CONCEPTOS.md) ya dejaba la posta escrita: *"cuando mañana los datos vengan
  de una consulta SQL en vez de un archivo..."* — ese momento es este).

Los Bloques 2 y 3 cambian de terreno respecto de las semanas anteriores. **Bloque 2** es SQL puro
y no toca `tagstats`/`tagframe` para nada. **Bloque 3** es un **proyecto nuevo y separado**,
`industrial-data-pipeline`, pensado como pieza de portfolio para Upwork — no un paquete más
adentro de este repo.

**Restricciones que se mantienen:** Python ≥ 3.11, un entregable por semana, código y docstrings
en español como en `tagstats`/`tagframe`.

---

## Decisión de arquitectura: motor SQL

**Motor elegido: PostgreSQL.**

El roadmap original linkeaba documentación de T-SQL/SQL Server ("Microsoft — T-SQL CTE",
"Microsoft — OVER clause") y mencionaba `pyodbc` como driver en Semana 6 — esa combinación
apuntaba a SQL Server. Se decidió **PostgreSQL** en su lugar: instalación más liviana, muy buen
soporte de CTEs, window functions y `EXPLAIN ANALYZE`, y es además la sintaxis que ya usa el
recurso "Mode — SQL Tutorial" de Semana 4. Como consecuencia, en esta guía:

- `pyodbc` → **`psycopg2`** (driver de PostgreSQL para SQLAlchemy).
- Los links de Microsoft T-SQL quedan reemplazados por la documentación oficial de PostgreSQL
  equivalente (uno por semana, más abajo).

### Instalación

- **Nativa (Windows):** instalador desde
  [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) (incluye
  pgAdmin). Durante la instalación anotá el usuario `postgres` y la contraseña elegida — los vas
  a necesitar para el connection string.
- **Docker (alternativa, si ya lo tenés instalado):**
  ```bash
  docker run --name pg-industrial -e POSTGRES_PASSWORD=tu_password -p 5432:5432 -d postgres:16
  ```
- **Cliente GUI recomendado:** pgAdmin (viene con el instalador nativo) o
  [DBeaver](https://dbeaver.io/) (multi-motor, gratis) para mirar tablas y planes de ejecución sin
  vivir en la CLI.

### Dependencias nuevas

Mismo patrón que usó `guia-sem3.md` para pandas: extra opcional, no dependencia base, así
`tagstats` sigue con `dependencies = []` si esto termina viviendo en este repo:

```toml
[project.optional-dependencies]
frame = ["pandas>=2.2"]                                # ya existente (Sem 3)
sql   = ["sqlalchemy>=2.0", "psycopg2-binary>=2.9"]    # nuevo, para industrial-data-pipeline
```

**Si `industrial-data-pipeline` termina siendo un repo aparte (lo más probable — ver Semana 6), va
en su propio `requirements.txt`:**

```
sqlalchemy==2.0.*
psycopg2-binary==2.9.*
```

### Connection string

```python
# postgresql+psycopg2://usuario:password@host:puerto/nombre_db
URL = "postgresql+psycopg2://postgres:tu_password@localhost:5432/industrial"
```

> **Trampa de seguridad:** nunca hardcodees usuario/password en el código. Usá variables de
> entorno (`os.environ["DB_PASSWORD"]`) o un archivo `.env` + `python-dotenv`. Si usás `.env`,
> sumalo al `.gitignore` — hoy el `.gitignore` del repo **no tiene ninguna entrada de DB/secrets**,
> así que agregá `.env` (y `*.db`/`*.sqlite3` si en algún momento probás algo con SQLite).

---

## Semana 4 — Modelado + JOINs + CTEs

Foco: pensar en relaciones y escribir queries legibles.

**Temas:** diseño de tablas y claves · índices (intro) · JOINs (inner/left/...) · agregaciones ·
CTEs (`WITH`) · subqueries.

**Recursos:**
- [Mode — SQL Tutorial](https://mode.com/sql-tutorial/) — interactivo.
- [Use The Index, Luke!](https://use-the-index-luke.com/) — índices y performance.
- [PostgreSQL — Queries with WITH](https://www.postgresql.org/docs/current/queries-with.html) —
  reemplaza al recurso de T-SQL del roadmap original (CTEs en Postgres).

**★ Entregable:** esquema relacional para datos de planta (tags, lecturas, alarmas) + 8–10
consultas que usen JOINs y CTEs.

**Checklist:**
```
[] Diseñar esquema con tablas tags / readings / alarms
[X] Cargar datos de ejemplo
[] Escribir 5 queries con JOINs
[] Escribir 3 queries con CTEs encadenadas
```

### Chuleta — DDL y JOINs

```sql
-- Tabla + clave foránea (patrón general, adaptá nombres/columnas a tu propio esquema)
CREATE TABLE tags (
    tag_id     SERIAL PRIMARY KEY,
    nombre     TEXT NOT NULL UNIQUE,
    unidad     TEXT NOT NULL
);

CREATE TABLE readings (
    reading_id  SERIAL PRIMARY KEY,
    tag_id      INTEGER NOT NULL REFERENCES tags(tag_id),
    "timestamp" TIMESTAMP NOT NULL,
    valor       NUMERIC NOT NULL,
    calidad     TEXT NOT NULL
);

CREATE INDEX idx_readings_tag_ts ON readings (tag_id, "timestamp");
```

```sql
-- Los 4 JOINs básicos, mismo par de tablas
SELECT r.*, t.nombre
FROM readings r
INNER JOIN tags t ON t.tag_id = r.tag_id;      -- solo filas con match en ambos lados

SELECT t.*, r.*
FROM tags t
LEFT JOIN readings r ON r.tag_id = t.tag_id;   -- todos los tags, aunque no tengan lecturas

SELECT t.*, r.*
FROM tags t
RIGHT JOIN readings r ON r.tag_id = t.tag_id;  -- todas las lecturas, aunque el tag no exista

SELECT t.*, r.*
FROM tags t
FULL JOIN readings r ON r.tag_id = t.tag_id;   -- unión de los dos casos de arriba
```

### Chuleta — agregaciones y subqueries

```sql
-- GROUP BY + HAVING (HAVING filtra DESPUÉS de agrupar; WHERE filtra ANTES)
SELECT tag_id, COUNT(*) AS n_lecturas, AVG(valor) AS promedio
FROM readings
GROUP BY tag_id
HAVING COUNT(*) > 100;

-- Subquery: tags cuyo promedio supera el promedio general de la planta
SELECT tag_id, AVG(valor) AS promedio
FROM readings
GROUP BY tag_id
HAVING AVG(valor) > (SELECT AVG(valor) FROM readings);
```

Esa misma subquery se puede reescribir como CTE (ver abajo) — son dos formas de lo mismo; la CTE
gana en legibilidad cuando el cálculo intermedio se reusa más de una vez.

### Chuleta — CTEs

```sql
-- CTE simple
WITH lecturas_altas AS (
    SELECT * FROM readings WHERE valor > 100
)
SELECT tag_id, COUNT(*) FROM lecturas_altas GROUP BY tag_id;

-- CTEs encadenadas (una usa a la otra)
WITH por_tag AS (
    SELECT tag_id, AVG(valor) AS promedio
    FROM readings
    GROUP BY tag_id
),
sobre_promedio AS (
    SELECT r.*
    FROM readings r
    JOIN por_tag p ON p.tag_id = r.tag_id
    WHERE r.valor > p.promedio
)
SELECT * FROM sobre_promedio;
```

**Trampas:**
- `LEFT JOIN` + filtro sobre la tabla de la derecha puesto en el `WHERE` lo convierte en un
  `INNER JOIN` sin querer — si necesitás conservar las filas sin match, ese filtro va en el `ON`.
- `COUNT(columna)` ignora `NULL`; `COUNT(*)` no. Fijate cuál de los dos necesitás según si la
  columna puede venir vacía.
- Una CTE no es una tabla temporal materializada por defecto: Postgres puede "inlinearla" en el
  plan. No la uses solo para "cachear" un cálculo caro esperando que se ejecute una única vez.

---

## Semana 5 — Window functions + planes de ejecución

Foco: el núcleo analítico de SQL y cómo leer performance.

**Temas:** `ROW_NUMBER`/`RANK` · `LAG`/`LEAD` · promedios móviles con `OVER` · execution plans ·
índices y costo.

**Recursos:**
- [PostgreSQL — Window Functions](https://www.postgresql.org/docs/current/tutorial-window.html)
  — reemplaza al recurso de OVER clause de T-SQL del roadmap original.
- [Use The Index, Luke — Execution Plans](https://use-the-index-luke.com/sql/explain)
- [Mode — Window Functions](https://mode.com/sql-tutorial/sql-window-functions/)
- [PostgreSQL — Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)

**★ Entregable:** queries analíticas con ventanas (promedio móvil de una variable de proceso,
detección de saltos con LAG) + análisis documentado de un execution plan.

**Checklist:**
```
[x] Calcular promedio móvil de una señal con OVER
[skipped] Detectar variaciones bruscas con LAG/LEAD
[] Ranking de alarmas por equipo con RANK
[skipped] Leer un execution plan y anotar qué optimizar
```

### Chuleta — window functions

```sql
-- ROW_NUMBER / RANK: numerar u ordenar dentro de cada grupo (PARTITION BY)
SELECT
    tag_id,
    "timestamp",
    valor,
    ROW_NUMBER() OVER (PARTITION BY tag_id ORDER BY "timestamp") AS nro_lectura,
    RANK()       OVER (PARTITION BY tag_id ORDER BY valor DESC)  AS ranking_por_valor
FROM readings;

-- LAG/LEAD: comparar una fila con la anterior/siguiente (útil para detectar saltos)
SELECT
    tag_id, "timestamp", valor,
    valor - LAG(valor) OVER (PARTITION BY tag_id ORDER BY "timestamp") AS delta
FROM readings;

-- Promedio móvil: frame explícito con ROWS BETWEEN
SELECT
    tag_id, "timestamp", valor,
    AVG(valor) OVER (
        PARTITION BY tag_id
        ORDER BY "timestamp"
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW   -- ventana de 5 lecturas
    ) AS promedio_movil
FROM readings;
```

### Chuleta — leer un execution plan

```sql
EXPLAIN ANALYZE
SELECT t.nombre, AVG(r.valor)
FROM readings r
JOIN tags t ON t.tag_id = r.tag_id
GROUP BY t.nombre;
```

Qué mirar primero en la salida de `EXPLAIN ANALYZE`:
1. **De adentro hacia afuera:** el plan se lee de la línea más indentada hacia la de más afuera —
   eso es lo que se ejecuta primero.
2. **`Seq Scan` vs `Index Scan`:** un `Seq Scan` en una tabla grande suele ser la señal de que
   falta un índice sobre la columna del `WHERE`/`JOIN`.
3. **`cost=` (estimado) vs `actual time=` (real):** si difieren mucho, las estadísticas de la
   tabla están desactualizadas (`ANALYZE nombre_tabla;` las refresca).
4. **`rows=` estimado vs. filas reales devueltas:** una diferencia grande es otra señal de
   estadísticas desactualizadas o de un filtro mal indexado.

**Trampas:**
- Sin `ORDER BY` dentro del `OVER (...)`, `LAG`/`LEAD`/el promedio móvil no tienen un orden
  garantizado — el resultado puede variar entre ejecuciones.
- `RANK()` deja huecos después de un empate (1, 2, 2, 4); `DENSE_RANK()` no (1, 2, 2, 3). Elegí a
  propósito cuál necesitás.
- Un índice ayuda en lectura pero cuesta en cada `INSERT`/`UPDATE` — no indexes "por las dudas"
  todas las columnas.

---

## Semana 6 — Diseño + ingesta

Foco: arquitectura del pipeline y carga de datos a una DB.

**Temas:** arquitectura ingesta→validación→storage · estructura de proyecto (`src/`, `tests/`) ·
SQLAlchemy / **psycopg2** · `requirements.txt`.

**Git esta semana:** ⎇ estructura de repo profesional.

**Recursos:**
- [SQLAlchemy — Quickstart](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
- [Real Python — Project Structure](https://realpython.com/python-application-layouts/)
- [Pro Git](https://git-scm.com/book/en/v2) — repaso.

**★ Entregable:** módulo de ingesta que toma datos crudos de sensores (CSV / fuente simulada) y
los carga validados en una base de datos.

**Checklist:**
```
[] Definir la arquitectura del pipeline en el README
[] Estructurar el repo (src/, tests/, requirements)
[] Implementar ingesta con validación de datos
[] Persistir en DB con SQLAlchemy o psycopg2
```

### Chuleta — estructura de proyecto

Este capstone es un **repo nuevo** (`industrial-data-pipeline`), separado de
`PySQLGit-selfcourse` — por eso acá sí aplica un `src/` layout (a diferencia de `tagstats`, que
vive suelto en la raíz de este repo):

```
industrial-data-pipeline/
  src/
    industrial_data_pipeline/
      __init__.py
      ingesta.py        # lee la fuente cruda (CSV/simulada), valida, devuelve filas limpias
      modelos.py         # tablas SQLAlchemy (o dataclasses si preferís SQL crudo con psycopg2)
      db.py               # engine, sesión, conexión
  tests/
  data/
  requirements.txt
  README.md
```

### Chuleta — SQLAlchemy: engine + tabla + insert

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

class Base(DeclarativeBase):
    pass

engine = create_engine("postgresql+psycopg2://postgres:tu_password@localhost:5432/industrial")

# TODO: definir tus tablas como clases (equivalente ORM del CREATE TABLE de Sem 4)
class Tag(Base):
    __tablename__ = "tags"
    tag_id: Mapped[int] = mapped_column(primary_key=True)
    # TODO: resto de columnas con Mapped[tipo] = mapped_column(...)

Base.metadata.create_all(engine)   # crea las tablas si no existen

# Insertar con validación previa (esto es "ingesta", no un insert ciego)
with Session(engine) as session:
    # TODO: validar cada fila cruda antes del session.add(...)
    session.commit()
```

**Trampas:**
- No insertes filas crudas sin validar tipos/rangos primero — esa validación es justamente el
  "→ validación →" del flujo del entregable, no un detalle opcional.
- `create_all` no hace *migraciones* (no actualiza una tabla que ya existe con un esquema
  distinto) — para eso se usaría Alembic más adelante; para este capstone alcanza con
  `create_all` sobre una DB nueva.
- Si el CSV puede traer filas repetidas, decidí la estrategia (¿upsert? ¿ignorar? ¿fallar?) antes
  de escribir el insert, no la dejes para "después".

---

## Semana 7 — Transformación + analítica

Foco: convertir datos crudos en KPIs reproducibles.

**Temas:** limpieza y resampleo temporal · KPIs (móviles, anomalías simples) · SQL desde Python ·
tests del pipeline.

**Recursos:**
- [pandas — Time Series](https://pandas.pydata.org/docs/user_guide/timeseries.html)
- [pytest — repaso de fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)

**★ Entregable:** capa de transformación + analítica con resultados reproducibles (mismo input →
mismo output) y tests que la cubran.

**Checklist:**
```
[] Resamplear series temporales (p. ej. promedios por hora)
[] Calcular 2-3 KPIs del proceso
[] Ejecutar queries analíticas desde Python
[] Tests que validen el pipeline end-to-end
```

### Chuleta — pandas resample

```python
import pandas as pd

# df con índice datetime (si "timestamp" es una columna, primero df = df.set_index("timestamp"))
df = df.set_index("timestamp")

# Promedio por hora, por tag
horario = df.groupby("tag")["valor"].resample("1h").mean()

# Varias agregaciones a la vez
resumen = df.groupby("tag")["valor"].resample("1h").agg(["mean", "min", "max", "std"])
```

### Chuleta — leer SQL desde Python (misma capa de Sem 6)

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg2://postgres:tu_password@localhost:5432/industrial")

# pd.read_sql acepta SQL crudo (reusá las queries que ya escribiste en Sem 4/5)
df = pd.read_sql(
    "SELECT * FROM readings WHERE tag_id = %(tag_id)s",
    engine,
    params={"tag_id": 1},
)
```

### Chuleta — test de pipeline reproducible

```python
# mismo espíritu que tests/conftest.py de tagstats: fixture con datos de entrada fijos,
# assert sobre el resultado exacto (no solo "no explota")
import pytest

@pytest.fixture
def datos_de_ejemplo():
    # TODO: DataFrame chico y fijo, con un resultado esperado que puedas calcular a mano
    ...

def test_kpi_es_reproducible(datos_de_ejemplo):
    resultado_1 = calcular_kpi(datos_de_ejemplo)
    resultado_2 = calcular_kpi(datos_de_ejemplo)
    assert resultado_1 == resultado_2   # mismo input -> mismo output, nada de azar oculto
```

**Trampas:**
- `resample` necesita un índice `DatetimeIndex` ordenado — si el CSV no viene ordenado por
  fecha, ordená antes (`df = df.sort_index()`).
- Igual que en `tagframe` (Sem 3): decidí `ddof=0` (poblacional) vs. `ddof=1` (muestral, default
  de pandas) para el desvío estándar, y sé consistente en todo el pipeline.
- Nunca concatenes valores directamente en un string SQL (`f"... WHERE tag_id = {tag_id}"`) — es
  el vector clásico de SQL injection. Usá siempre parámetros (`params={...}` como arriba, o
  `text("... WHERE tag_id = :tag_id")` con SQLAlchemy).

---

## Semana 8 — Empaque + portfolio

Foco: dejar el proyecto presentable y vendible.

**Temas:** README profesional + diagrama · GitHub Actions (CI: corre tests) · badges · framing
para cliente / Upwork.

**Git esta semana:** ⎇ CI con GitHub Actions · ⎇ release final.

**Recursos:**
- [GitHub Actions — Python](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python)
- [makeareadme.com](https://www.makeareadme.com/) — plantilla de README.

**★ Entregable:** repo `industrial-data-pipeline` público y pulido: README con diagrama, CI
corriendo tests, descripción orientada a cliente. Listo para mostrar.

**Checklist:**
```
[] README con propósito, arquitectura y cómo correrlo
[] Diagrama de arquitectura del pipeline
[] CI con GitHub Actions que corra los tests
[] Escribir la descripción del proyecto pensada para un cliente Upwork
[] Release v1.0 + repo en modo portfolio
```

### Chuleta — outline de README

```
# industrial-data-pipeline

Una línea: qué hace y para quién (dato de sensores -> DB -> KPIs).

## Arquitectura
(diagrama + 2-3 líneas: ingesta -> validación -> storage -> transformación -> analítica)

## Instalación
## Uso rápido
## Estructura del proyecto
## Tests
## Decisiones de diseño
(igual que docs/CONCEPTOS.md de tagstats: por qué Postgres, por qué este esquema, trade-offs)
```

### Chuleta — CI mínimo (GitHub Actions) + badge

```yaml
# .github/workflows/tests.yml
name: tests
on: [push, pull_request]
jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest -q
```

```markdown
![tests](https://github.com/FacZap/industrial-data-pipeline/actions/workflows/tests.yml/badge.svg)
```

**Trampas:**
- Si los tests del capstone necesitan una DB real, el job de CI también necesita una — GitHub
  Actions permite levantar Postgres como `services:` del job (buscar "postgres service
  container" en la doc de Actions) en vez de mockear todo.
- Un README con capturas de pantalla o un diagrama (aunque sea hecho a mano en una herramienta
  simple) vende mucho más que uno de solo texto para un cliente de Upwork.
- "Portfolio" implica datos de ejemplo commiteados (`data/`) para que cualquiera pueda clonar y
  correrlo sin pedirte credenciales — separá bien qué es dato de ejemplo y qué exige DB propia.

---

## Verificación de punta a punta

```bash
psql -U postgres -h localhost -c "SELECT version();"
```
```bash
pytest -q
```
```bash
python -c "from sqlalchemy import create_engine; create_engine('postgresql+psycopg2://postgres:tu_password@localhost:5432/industrial').connect(); print('conexion ok')"
```
Esperado: `psql`/el `connect()` confirman que Postgres está arriba y accesible antes de tocar
código; `pytest -q` en verde en cada entrega semanal, tanto en `industrial-data-pipeline` como
(sin romperlo) en `PySQLGit-selfcourse`.

## Mapa contra el checklist de la pantalla

| Semana | Ítem del checklist | Se cubre en |
|---|---|---|
| 4 | Diseñar esquema con tablas tags / readings / alarms | Chuleta — DDL y JOINs |
| 4 | Cargar datos de ejemplo | Decisión de arquitectura (instalación) |
| 4 | Escribir 5 queries con JOINs | Chuleta — DDL y JOINs |
| 4 | Escribir 3 queries con CTEs encadenadas | Chuleta — CTEs |
| 5 | Calcular promedio móvil de una señal con OVER | Chuleta — window functions |
| 5 | Detectar variaciones bruscas con LAG/LEAD | Chuleta — window functions |
| 5 | Ranking de alarmas por equipo con RANK | Chuleta — window functions |
| 5 | Leer un execution plan y anotar qué optimizar | Chuleta — leer un execution plan |
| 6 | Definir la arquitectura del pipeline en el README | Chuleta — estructura de proyecto |
| 6 | Estructurar el repo (src/, tests/, requirements) | Chuleta — estructura de proyecto |
| 6 | Implementar ingesta con validación de datos | Chuleta — SQLAlchemy: engine + tabla + insert |
| 6 | Persistir en DB con SQLAlchemy o psycopg2 | Chuleta — SQLAlchemy: engine + tabla + insert |
| 7 | Resamplear series temporales | Chuleta — pandas resample |
| 7 | Calcular 2-3 KPIs del proceso | Chuleta — pandas resample |
| 7 | Ejecutar queries analíticas desde Python | Chuleta — leer SQL desde Python |
| 7 | Tests que validen el pipeline end-to-end | Chuleta — test de pipeline reproducible |
| 8 | README con propósito, arquitectura y cómo correrlo | Chuleta — outline de README |
| 8 | Diagrama de arquitectura del pipeline | Chuleta — outline de README |
| 8 | CI con GitHub Actions que corra los tests | Chuleta — CI mínimo + badge |
| 8 | Descripción del proyecto para cliente Upwork | Semana 8 (Entregable) |
| 8 | Release v1.0 + repo en modo portfolio | Semana 8 (Entregable) |

## Orden sugerido

1. Cerrar primero lo que está abierto en **este** repo: terminar Semana 2 (`guia-sem2.md`,
   logging) y, si aplica, Semana 3 (`guia-sem3.md`, `tagframe`) — el Bloque 2 no depende
   técnicamente de ellas, pero el roadmap las da por hechas antes de llegar a Semana 4.
2. **Semana 4 → 5** (Bloque 2, SQL puro): instalar Postgres primero (Decisión de arquitectura),
   después esquema (Sem 4) y recién después window functions/planes de ejecución (Sem 5) — Sem 5
   asume datos ya cargados y queries con JOINs para practicar ventanas sobre ellas.
3. **Semana 6 → 7 → 8** (Bloque 3, capstone): arrancar el repo nuevo `industrial-data-pipeline`
   recién en Semana 6 (no antes) — ingesta primero, transformación/analítica después (necesita
   datos ya cargados), empaque al final (necesita que el resto ya funcione y esté testeado).
