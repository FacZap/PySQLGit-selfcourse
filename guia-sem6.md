# Semana 6 — Diseño + ingesta: arrancar `industrial-data-pipeline`

> **Cómo usar esta guía:** es una guía de estudio, no una solución. Trae *dónde* va cada cosa,
> *por qué*, las decisiones que tenés que tomar vos y las trampas que te vas a encontrar. Los
> bloques de código son **anatomía y esqueletos**, no implementaciones para copiar. El módulo de
> ingesta lo escribís vos.

## Qué vas a lograr

Un repo nuevo, `industrial-data-pipeline`, con un módulo que toma un CSV crudo de sensores, lo
**valida**, y lo deja en PostgreSQL. Corriéndolo dos veces seguidas la base queda igual que
corriéndolo una vez.

Esto cierra los cuatro ítems de Semana 6 en [guia-a-futuro.md](guia-a-futuro.md) y es el piso
sobre el que se apoyan las Semanas 7 y 8: sin datos en la base no hay KPIs que calcular ni repo
que mostrar.

### El corte con lo anterior

Las Semanas 4 y 5 fueron SQL puro adentro de **este** repo. Semana 6 arranca un repo **nuevo y
separado**. Eso no es un detalle administrativo: cambia qué podés reusar y cómo.

| | `PySQLGit-selfcourse` | `industrial-data-pipeline` |
|---|---|---|
| Qué es | Tu cuaderno de curso | Tu pieza de portfolio |
| Lector | Vos | Alguien que te está por contratar |
| Layout | Paquetes sueltos en la raíz | `src/` layout |
| Datos | 4 CSV de ejercicio | Los mismos, pero como *ejemplo reproducible* |
| Commits | "TODO missing", "let Claude finish the code" | Los mira otra persona |

**La consecuencia práctica:** todo lo que quieras usar de `tagframe`/`tagstats` hay que
**copiarlo**, no importarlo. Un repo de portfolio que no clona y corre solo no sirve para nada.

---

## Parte 0 — Antes de escribir código: las tres decisiones

Tomalas ahora y anotalas en el README. Las tres se pagan caras si las dejás para después.

### Decisión 1: ¿repo nuevo de verdad?

[guia-a-futuro.md](guia-a-futuro.md) dice repo aparte, y la razón es el lector: nadie que te esté
evaluando quiere ver tu semana 2 de logging al lado del pipeline. La alternativa —una carpeta más
acá— te ahorra media hora hoy y te cuesta la Semana 8 entera.

Si elegís repo aparte (lo recomendado), el arranque:

```bash
git init industrial-data-pipeline
```

**El `.gitignore` va en el primer commit, antes que cualquier otra cosa.** No es prolijidad: si
un `.env` con la password entra al historial aunque sea una vez, borrarlo después no lo saca —
sigue vivo en ese commit y cualquiera que clone lo recupera. Arrancá copiando el
[.gitignore](.gitignore) de este repo, que ya tiene la sección de credenciales.

### Decisión 2: ¿qué driver?

La chuleta dice `psycopg2-binary`. Existe también **psycopg 3** (el paquete se llama `psycopg`, a
secas), que es el sucesor oficial y cambia el connection string:

```
postgresql+psycopg2://...    # psycopg2
postgresql+psycopg://...     # psycopg 3
```

Los dos andan con SQLAlchemy 2.0. `psycopg2-binary` tiene más ejemplos dando vueltas; `psycopg` es
lo que se usa en proyectos nuevos. **Elegí uno y escribí en el README por qué** — esa línea vale
más en una entrevista que el driver que hayas elegido.

> Trampa de `-binary`: el sufijo significa "viene compilado, no necesitás compilador de C". Es
> perfecto para desarrollo y para el CI de Semana 8. En un deploy serio se usa `psycopg2` a secas.
> Sabelo; no te preocupes por eso ahora.

### Decisión 3: ¿SQLAlchemy ORM, SQLAlchemy Core, o el driver crudo?

Tres niveles, de más abstracto a menos:

| | Cómo se ve un insert | A favor | En contra |
|---|---|---|---|
| **ORM** | `session.add(Reading(...))` | Objetos Python, relaciones, el esquema vive en el código | Capa gorda para algo que solo inserta |
| **Core** | `conn.execute(insert(readings), filas)` | SQL explícito, pero con parámetros y tipos | Tenés que conocer SQL (ya lo conocés) |
| **Driver crudo** | `cur.executemany("INSERT ...", filas)` | Cero magia, `execute_values` es rapidísimo | Vos manejás conexiones, transacciones y tipos |

**Para un pipeline de ingesta, Core suele ser la respuesta correcta** y casi nadie lo dice: el ORM
existe para aplicaciones que *navegan* un grafo de objetos, y vos estás haciendo un `INSERT` de
864 filas. Pero el checklist pide SQLAlchemy y el ORM es lo que te van a preguntar, así que una
salida honesta es: **modelo declarativo (ORM) para definir el esquema, Core para el insert masivo**.
Son la misma librería y se mezclan sin problema.

---

## Parte 1 — La arquitectura: tres palabras y dos fronteras

El entregable dice **ingesta → validación → storage**. Las flechas importan más que las cajas.

```
   archivo/API/simulador          reglas                    PostgreSQL
        │                           │                            │
        ▼                           ▼                            ▼
   ┌─────────┐   filas crudas   ┌──────────┐  filas válidas  ┌─────────┐
   │ INGESTA │ ───────────────► │VALIDACIÓN│ ──────────────► │ STORAGE │
   └─────────┘   (texto, dict)  └──────────┘   (tipadas)     └─────────┘
                                     │
                                     └──► filas rechazadas (¿a dónde?)
```

### Qué define cada frontera

**Frontera 1 (ingesta → validación):** de acá para allá **no se sabe de dónde vino el dato**. Si
tu validador recibe un `Path` o abre un archivo, la frontera está mal puesta, y el día que el dato
venga de una API tenés que reescribir la validación.

Esto ya lo resolviste una vez: [tagframe/fuentes.py](tagframe/fuentes.py) define la ABC
`FuenteDeDatos` con un solo método `leer()`, y `Cargador` depende del contrato y no del CSV
([tagframe/cargador.py](tagframe/cargador.py)). **Ese diseño se copia tal cual.** El docstring de
`fuentes.py` literalmente dice que mañana entra `FuenteSQL` sin tocar el resto — mañana es hoy.

**Frontera 2 (validación → storage):** de acá para allá **no se sabe si el dato era válido**, ya
está garantizado. El módulo de storage no valida nada: inserta. Si tenés un `if valor is None` en
la capa de storage, la validación quedó incompleta.

### El mapa de archivos

```
industrial-data-pipeline/
  src/
    industrial_data_pipeline/
      __init__.py
      config.py       # de dónde sale la URL de la base (env vars). Nada más.
      fuentes.py      # INGESTA: ABC + FuenteCSV. Devuelve filas crudas.
      validacion.py   # VALIDACIÓN: filas crudas -> filas tipadas + rechazos
      modelos.py      # el esquema (tablas declarativas de SQLAlchemy)
      db.py           # STORAGE: engine, sesión, create_all, insert idempotente
      pipeline.py     # el que encadena los tres. La única función "pública".
      __main__.py     # CLI: python -m industrial_data_pipeline data/x.csv
  tests/
  data/               # los CSV de ejemplo, copiados de PySQLGit
  .env.example        # commiteado, SIN valores reales
  requirements.txt
  README.md
```

**Un módulo por responsabilidad, y el nombre del módulo es la responsabilidad.** Si `db.py`
termina con una función que parsea fechas, se te corrió una frontera.

---

## Parte 2 — El `src/` layout: por qué acá sí

`tagstats` vive suelto en la raíz de este repo. `industrial_data_pipeline` va adentro de `src/`.
No es capricho ni moda.

### ELI5 del problema que resuelve

Sin `src/`, cuando corrés `pytest` parado en la raíz del repo, Python encuentra tu paquete
**porque está en el directorio actual**, no porque esté instalado. Entonces:

- Tus tests pasan contra los archivos del repo.
- El paquete instalado (el que le llega al usuario) puede estar roto —por ejemplo, te olvidaste de
  incluir un archivo en el empaquetado— y **los tests no se enteran nunca**.

Con `src/`, el directorio actual **no** contiene el paquete. La única forma de que
`import industrial_data_pipeline` funcione es que esté instalado. O sea: tus tests prueban lo
mismo que va a recibir el usuario.

### La consecuencia operativa

Con `src/` layout **tenés que instalar el paquete** antes de correr los tests:

```bash
pip install -e .
```

El `-e` (editable) instala un puntero a tu carpeta, no una copia: editás el código y el cambio se
ve sin reinstalar.

> **Trampa:** el [pyproject.toml](pyproject.toml) de este repo tiene `pythonpath = ["."]` en la
> sección de pytest, que es exactamente el truco que el `src/` layout quiere evitar. Si lo copiás
> tal cual al repo nuevo, anulaste el beneficio. En el repo nuevo: o `pip install -e .`, o
> `pythonpath = ["src"]` — pero si elegís lo segundo, sabé que elegiste comodidad sobre garantía.

### `requirements.txt` vs `pyproject.toml`

El checklist pide `requirements.txt`. Hacen cosas distintas y conviene tener los dos:

| | Qué declara | Para quién |
|---|---|---|
| `pyproject.toml` → `dependencies` | Lo que el paquete **necesita**, con rangos (`>=2.0`) | Quien lo instala como librería |
| `requirements.txt` | Lo que **esta corrida concreta** usa, con versiones clavadas (`==2.0.36`) | Quien reproduce tu entorno: vos en otra máquina, y el CI de Semana 8 |

**Trampa de `pip freeze > requirements.txt`:** te vuelca *todo* lo que tengas instalado, incluidas
las dependencias de dependencias y cosas de otros proyectos. Un `requirements.txt` con 80 líneas
en un proyecto de 4 dependencias grita "no sé qué instalé". Escribilo a mano, con las que
importan. Mirá [requirements-dev.txt](requirements-dev.txt) de este repo: cuatro líneas y un
comentario que explica por qué está cada una.

---

## Parte 3 — Validación: qué es y qué no

Esta es la parte que más gente saltea, y es literalmente la flecha del medio del entregable.

### Lo que `Limpiador` ya hace (y podés copiar)

[tagframe/limpieza.py](tagframe/limpieza.py) resuelve cinco reglas: coerción de tipos con
`errors="coerce"`, `inf` a `NaN`, fechas no-ISO, nulos y vacíos, duplicados. Y devuelve un
`ResultadoLimpieza` con `filas_entrada` / `filas_salida`, porque *"un promedio calculado sobre
filas descartadas en silencio es peor que un error"*.

Copialo. Ese código ya está pensado y testeado.

### Lo que le falta para ser "validación de ingesta"

`Limpiador` valida **forma**. Un pipeline que escribe en una base necesita además validar
**dominio**:

| Nivel | Pregunta | Ejemplo con tus datos |
|---|---|---|
| Estructura | ¿están las columnas? | ya lo hace la verificación de cabecera de `FuenteCSV` |
| Tipo | ¿`valor` es un número? | ya lo hace `Limpiador` (`to_numeric`) |
| **Dominio** | ¿el número tiene sentido? | una presión de `-40 bar` parsea perfecto y es físicamente imposible |
| **Referencial** | ¿el tag existe en el catálogo? | un `TT-999` que no está en `limites.csv` |
| **Temporal** | ¿la fecha es plausible? | un timestamp de 1970 o del año que viene |

Las tres últimas son nuevas y son las que justifican la palabra "validado" del entregable.

> **Pista sobre la referencial:** tenés dos lugares donde chequearla — en Python antes del insert,
> o con la FOREIGN KEY que ya escribiste en [sql/01_esquema.sql](sql/01_esquema.sql). La FK te
> garantiza que no entre basura, pero te avisa como una excepción del driver a mitad del batch.
> Chequear en Python te deja dar un mensaje útil ("el tag TT-999 de la fila 412 no existe en el
> catálogo"). **Hacer las dos no es redundante:** una es el mensaje, la otra es la garantía.

### La decisión: ¿qué hacés con la fila que no pasa?

Tres estrategias, y la peor es no elegir:

| | Qué hace | Cuándo |
|---|---|---|
| **Descartar y contar** | La saltea, suma al contador | Lo que ya hace `Limpiador`. Bien para un CSV de ejercicio |
| **Cortar todo** | Levanta excepción, no entra nada | Cuando una sola fila mala significa que el archivo entero es sospechoso |
| **Cuarentena** | La inserta en una tabla `rechazos` con el motivo | Lo que hace un pipeline de producción |

La cuarentena es la que mejor queda en un portfolio y es una tabla más: la fila cruda como texto,
el motivo, el timestamp de ingesta, el nombre del archivo. **El valor no es técnico: es que
alguien puede ir a mirar qué se cayó y por qué**, en vez de confiar en un log que ya se rotó.

### El esqueleto

```python
# validacion.py  -  ESQUELETO
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class LecturaValida:
    """Una fila que ya pasó todo. De acá para abajo nadie vuelve a chequear."""
    # TODO: los campos, con los tipos FINALES (datetime, float/Decimal, str).
    #       Pista: si acá hay un campo `str | None`, preguntate si esa columna
    #       realmente puede faltar o si estás arrastrando la duda del CSV.

@dataclass(frozen=True, slots=True)
class ResultadoValidacion:
    """Qué entró, qué salió, qué se cayó y POR QUÉ."""
    validas: list[LecturaValida]
    # TODO: rechazos. ¿Qué necesitás guardar de una fila rechazada para poder
    #       explicarla mañana? Como mínimo: la fila cruda, el motivo, el nro de fila.
    # TODO: ¿contadores como campos, o como @property derivadas de las listas?
    #       ResultadoLimpieza en tagframe/limpieza.py tomó una postura clara y la
    #       argumenta en su docstring. Leela y decidí si estás de acuerdo.

def validar(filas_crudas) -> ResultadoValidacion:
    # TODO: una función por regla, y esta función las encadena.
    #       Pista: si esto termina siendo un if de 40 líneas, no vas a poder
    #       testear una regla sola. Una regla = una función = un test.
    ...
```

> **Sobre Pydantic:** es la librería que todo el mundo usa para esto y hace la validación
> declarativa (`valor: float = Field(gt=0)`). Es una dependencia más y una sintaxis nueva para
> aprender en una semana que ya trae SQLAlchemy. Hacerlo a mano con dataclasses primero te enseña
> *qué* está haciendo Pydantic; si después lo cambiás, vas a saber qué ganaste.

---

## Parte 4 — SQLAlchemy: los cuatro conceptos que hay que tener claros

### 1. El `Engine` no es una conexión

Es una **fábrica de conexiones con un pool adentro**. Se crea **una vez por proceso**, al arrancar,
y se comparte. Crear un engine por cada insert es el error clásico: cada uno abre su propio pool y
la base se queda sin conexiones.

```python
# TODO: un solo engine, creado una vez. ¿Dónde vive? ¿En config.py? ¿Se inyecta
#       como parámetro? ¿Variable global perezosa?
#       Pista: "variable global" es la respuesta fácil y la que más duele en los
#       tests, porque no podés apuntarlo a otra base sin reimportar el módulo.
engine = create_engine(URL, echo=False)
```

> `echo=True` te imprime cada SQL que SQLAlchemy genera. Prendelo mientras aprendés — es la forma
> más rápida de entender qué está haciendo el ORM por atrás. Apagalo antes de commitear.

### 2. La `Session` es una unidad de trabajo

Una sesión = un bloque de cosas que pasan juntas o no pasan. Se abre, se hace lo que hay que hacer,
se hace `commit()` (o explota y se revierte), se cierra.

```python
with Session(engine) as session:
    # TODO: acá adentro va UN trabajo completo.
    session.commit()
```

**La pregunta de diseño de esta semana:** ¿una sesión para todo el archivo (864 filas entran o no
entra ninguna) o una por lote de N filas? No hay respuesta universal, pero la hay para *tu* caso, y
depende de qué preferís que pase si la fila 700 falla. Escribí la respuesta en el README.

### 3. `create_all` no es migraciones

```python
Base.metadata.create_all(engine)
```

Crea las tablas que **no existen**. Si la tabla existe con otro esquema, **no hace nada y no
avisa**. O sea: cambiás una columna en `modelos.py`, corrés esto, y tu código y tu base quedan
desfasados en silencio.

Mientras aprendés: `DROP` + volver a crear, igual que hace [sql/01_esquema.sql](sql/01_esquema.sql).
Alembic es la herramienta correcta y es un tema para más adelante — **no la metas esta semana**.

### 4. Los tipos no viajan gratis

Tres trampas concretas, en orden de cuánto tiempo hacen perder:

**`NUMERIC` llega como `Decimal`, no como `float`.** Ya está avisado al final de
[sql/01_esquema.sql](sql/01_esquema.sql). `Decimal("4.83") + 0.5` tira `TypeError`. Y
`pd.read_sql` sobre una columna `NUMERIC` te devuelve dtype `object`, no `float64` — lo vas a
sufrir en Semana 7. Tres salidas: castear en la query (`valor::float8`), castear en pandas
(`.astype("float64")`), o usar `DOUBLE PRECISION` en el esquema. Las tres son válidas; elegí una y
sé consistente en todo el pipeline.

**`TIMESTAMP` vs `TIMESTAMPTZ`.** Tu esquema usa `TIMESTAMP` (sin zona), que es razonable para un
dato de planta donde todos hablan en hora local. Pero un `datetime` de Python puede traer `tzinfo`,
y entonces Postgres la descarta sin avisar. Decidí: o todo naive, o todo aware. Los bugs de zona
horaria no rompen nada — corren el dato tres horas, que es peor.

**El autocommit no existe.** Sin `commit()`, tu insert se va con el rollback implícito al cerrar la
sesión. El síntoma es desconcertante: el script dice que insertó 864 filas y `SELECT COUNT(*)`
devuelve 0.

---

## Parte 5 — Idempotencia, otra vez (pero desde Python)

Es la misma pregunta de la Semana 4 (`ON CONFLICT`, Parte 4 de [guia-sem4.md](guia-sem4.md)) y la
respuesta ya la decidiste allá. Lo nuevo es cómo se escribe desde SQLAlchemy.

El `ON CONFLICT` **no es SQL estándar**: es de Postgres. Por eso no está en el `insert()` genérico
sino en el dialecto:

```python
from sqlalchemy.dialects.postgresql import insert   # <- ojo, no el genérico
# TODO: armar el insert y encadenarle .on_conflict_do_nothing(...) o
#       .on_conflict_do_update(...).
#       Pista 1: necesita saber CONTRA QUÉ restricción chocar. Es la misma
#                UNIQUE (tag_id, "timestamp") del esquema — si no la pusiste, acá
#                te va a decir "no unique or exclusion constraint matching the
#                ON CONFLICT specification", y el problema está en modelos.py.
#       Pista 2: ¿cuál de las dos va para readings y cuál para tags/limites?
#                La respuesta está en guia-sem4.md, Parte 4: hechos vs configuración.
```

**El costo de esa línea:** tu pipeline ya no corre en SQLite ni en SQL Server. Es un trade-off real
y de los que se preguntan en entrevistas. Anotalo en el README, en decisiones de diseño.

### 864 inserts o uno solo

```python
# Lento: una ida y vuelta a la base por fila.
for fila in filas:
    session.add(Reading(**fila))

# Rápido: una sola sentencia con muchos parámetros (executemany).
session.execute(insert(Reading), lista_de_diccionarios)
```

Con 864 filas la diferencia es de segundos y no te va a molestar. Con 8 millones es la diferencia
entre 40 minutos y 40 segundos. **Medilo vos** con `time.perf_counter()` alrededor de las dos
versiones: es el experimento de 5 minutos que hace que el concepto no se olvide.

---

## Parte 6 — Credenciales, en serio esta vez

Semana 4 te dejó la password en `$env:PGPASSWORD`, que vive en la RAM de una ventana de PowerShell.
Un pipeline que corre solo necesita otra cosa.

```
.env              <- tus valores reales. EN EL .gitignore. Nunca se commitea.
.env.example      <- las mismas claves, valores falsos. SÍ se commitea.
```

```python
# config.py
import os
# TODO: leer DATABASE_URL (o las piezas sueltas: host, puerto, usuario, base).
#       Pista 1: os.environ["X"] explota si falta; os.environ.get("X") devuelve
#                None y el error aparece tres funciones después, disfrazado. Para
#                una credencial obligatoria, explotar temprano es lo correcto.
#       Pista 2: python-dotenv carga el .env al entorno. Es UNA dependencia más;
#                decidí si la querés o si preferís setear las variables a mano.
#       Pista 3: nunca loguees la URL completa. Tiene la password adentro, y los
#                logs se pegan en tickets, en chats y en capturas de pantalla.
```

`.env.example` no es burocracia: es lo que le permite a alguien que clona tu repo saber **qué
variables necesita** sin leerte el código. En Semana 8 es la diferencia entre un repo que otro
puede correr y uno que no.

---

## Parte 7 — El Git de esta semana

El roadmap marca ⎇ *estructura de repo profesional*. En concreto, lo que un repo público tiene y
este cuaderno no:

| Qué | Por qué |
|---|---|
| `.gitignore` en el **primer** commit | Un secreto que entró al historial no sale con un `rm` |
| `README.md` desde el día 1, aunque sea de 5 líneas | Es lo primero que se lee y lo último que se escribe. Empezalo ya |
| `LICENSE` | Sin licencia, legalmente nadie puede usar tu código. MIT si no querés pensarlo |
| Mensajes de commit que se entienden solos | Compará `feat(sql): semana 5 - promedio movil con OVER` con `TODO missing`. Los dos están en este repo |
| Ramas con nombre de lo que hacen | `feat/ingesta`, `feat/validacion` |

**Conventional Commits:** `tipo(ámbito): qué cambió`, en imperativo. Los tipos que vas a usar:
`feat`, `fix`, `docs`, `test`, `refactor`, `chore`. No es obligatorio, pero es lo que hace que el
historial se lea como una tabla de contenidos — y en Semana 8, lo que te deja armar un CHANGELOG
casi solo.

```bash
git log --oneline
```

Corré eso en tu repo nuevo al final de la semana y leelo como si fuera de otro. ¿Se entiende qué
pasó? Esa es toda la prueba.

---

## Verificación

El oráculo es el mismo de siempre, y por eso esta semana es fácil de verificar: los números ya los
sabés. Están en [README.md](README.md) y los reprodujiste tres veces (`tagstats`, `tagframe`, SQL).

```sql
SELECT COUNT(*) FROM tags;      -- 6
SELECT COUNT(*) FROM readings;  -- 864
SELECT COUNT(*) FROM alarmas;   -- 34
```

**La prueba de verdad, la que no se puede falsear:**

```bash
python -m industrial_data_pipeline data/sensores_planta.csv
```

Correlo dos veces. `readings` tiene que seguir en 864. Si dice 1728, el `ON CONFLICT` no está o
está chocando contra la restricción equivocada.

**La segunda prueba, la que separa "carga" de "ingesta validada":**

```bash
python -m industrial_data_pipeline data/sensores_sucios.csv
```

Ese archivo tiene seis clases de basura distintas, incluida la fila corrida `4,82` que hizo fallar
el `\copy` entero en Semana 4 ([guia-sem4.md](guia-sem4.md), Parte 3). Tu pipeline **no puede
explotar**: tiene que reportar cuántas filas entraron, cuántas se cayeron y por qué. Ese reporte
*es* el entregable.

## Checklist

```
[] Repo nuevo creado, con .gitignore y LICENSE en el primer commit
[] src/ layout + pip install -e . funcionando
[] requirements.txt escrito a mano (no con pip freeze)
[] La arquitectura ingesta->validación->storage escrita en el README (con diagrama)
[] fuentes.py: ABC + FuenteCSV, sin saber nada de la base
[] validacion.py: las 5 reglas de forma + al menos 2 de dominio
[] Decidido y documentado qué pasa con una fila inválida (descartar / cortar / cuarentena)
[] modelos.py: las 3 tablas + la vista, equivalentes a sql/01_esquema.sql
[] db.py: un solo engine, sesión con commit explícito
[] Insert idempotente: correrlo dos veces deja 864 filas
[] sensores_sucios.csv no rompe el pipeline y reporta los descartes
[] Credenciales por entorno. .env ignorado, .env.example commiteado
[] git log --oneline se lee como una tabla de contenidos
```

---

## Lo que NO es esta semana

- **Nada de KPIs ni resampleo.** Es Semana 7, y necesita estos datos ya cargados.
- **Nada de CI ni badges.** Es Semana 8. Ahora el objetivo es que ande en tu máquina.
- **Nada de Alembic.** `create_all` sobre base nueva alcanza. Las migraciones se justifican cuando
  hay un esquema en producción que no podés tirar abajo.
- **Nada de API REST, dashboard ni Docker.** Son la tentación clásica de esta semana y no están en
  el entregable. Un pipeline que ingiere bien vale más que uno que ingiere mal y tiene un endpoint.
- **Nada de tocar `tagstats`/`tagframe`.** Se copia el diseño, no se importa el paquete.
