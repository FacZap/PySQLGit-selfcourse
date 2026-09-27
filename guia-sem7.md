# Semana 7 — Transformación + analítica: de filas a KPIs

> **Cómo usar esta guía:** es una guía de estudio, no una solución. Los bloques de código son
> **anatomía y esqueletos**; las fórmulas de los KPIs las definís vos. Lo que sí trae completo son
> los **oráculos**: los números contra los que tenés que verificar. Esa es la parte más valiosa y
> la que nadie te va a regalar en un proyecto real.

## Qué vas a lograr

Una capa que lee de la base que cargaste en Semana 6, resamplea las series a una frecuencia útil,
calcula 2–3 KPIs de proceso, y tiene tests que los cubren. **Mismo input → mismo output, siempre.**

Cierra los cuatro ítems de Semana 7 en [guia-a-futuro.md](guia-a-futuro.md).

### La palabra clave del entregable es "reproducible"

No es un adjetivo de relleno. Significa: si corrés el pipeline hoy, mañana, y en otra máquina,
sobre los mismos datos, sale **exactamente** lo mismo. Byte por byte si hace falta.

Suena obvio hasta que lo intentás. Los enemigos, de más a menos frecuente:

| Enemigo | Cómo se ve |
|---|---|
| **`SELECT` sin `ORDER BY`** | El orden de las filas de Postgres **no está garantizado**. Cambia con el plan de ejecución, con un `VACUUM`, con la cantidad de filas. Tu `df.head()` cambia y no tocaste nada |
| `datetime.now()` adentro de un cálculo | "últimas 24 horas" da distinto cada vez que corre |
| Iterar un `set` | Python ordena los sets de forma no determinística entre procesos |
| Aritmética de punto flotante | `0.1 + 0.2 != 0.3`. Sumar en distinto orden da distinto último decimal |
| Redondear en el medio | Redondear y después promediar ≠ promediar y después redondear |

**La regla operativa:** toda query de la que salga un DataFrame lleva `ORDER BY`. Sí, aunque
después ordenes en pandas. El costo es cero y te ahorra un día de "¿por qué el test pasa a veces?".

---

## Parte 0 — La decisión que define la semana: ¿SQL o pandas?

Podés calcular lo mismo de las dos formas. Ya lo hiciste: `tagstats` con stdlib, `tagframe` con
pandas, y las Semanas 4–5 con SQL. Los tres dan la misma tabla.

Así que la pregunta no es "¿se puede?" sino "¿dónde conviene?".

| Criterio | Gana SQL | Gana pandas |
|---|---|---|
| **Volumen** | Muchas filas: agregás en la base y traés 72 filas | Pocas filas: traés todo y jugás |
| **Tipo de cálculo** | Agregaciones, JOINs, ventanas | Formas raras, interpolación, gráficos |
| **Dónde vive el dato** | Ya está en la base | Viene de un CSV o de una API |
| **Testeabilidad** | Necesitás una base para testear | Un DataFrame a mano y listo |
| **Quién lo lee** | Un DBA, un analista | Un dev de Python |

**La respuesta razonable para este pipeline:** el trabajo pesado en SQL (agregar 864 filas a 72),
la forma final y los KPIs derivados en pandas. Y la razón concreta es la de la primera columna:
traer 864 filas a Python para promediarlas funciona; traer 8 millones no.

> **Lo que ya tenés escrito y podés reusar tal cual:** las ventanas de
> [sql/05_promedio_movil.sql](sql/05_promedio_movil.sql) y los rankings de
> [sql/06_ranking_alarmas.sql](sql/06_ranking_alarmas.sql). Ese SQL no fue un ejercicio suelto —
> era el insumo de esta semana. Copiá las queries al repo nuevo, como archivos `.sql` o como
> constantes, y llamalas desde Python.

---

## Parte 1 — Leer SQL desde Python sin pegarse un tiro

### La forma correcta

```python
import pandas as pd
from sqlalchemy import text

CONSULTA = text("""
    SELECT ...
    FROM readings r
    JOIN tags t ON t.tag_id = r.tag_id
    WHERE t.nombre = :tag          -- <- parámetro con nombre, NO f-string
    ORDER BY r."timestamp"         -- <- SIEMPRE
""")

with engine.connect() as conn:
    df = pd.read_sql(CONSULTA, conn, params={"tag": nombre})
```

### Las cuatro trampas

**1. Nunca un f-string.** `f"... WHERE nombre = '{tag}'"` es SQL injection de manual. No importa
que el valor venga de tu propio código hoy: mañana viene de un argumento del CLI. Con parámetros,
el driver escapa por vos y además la base puede cachear el plan.

**2. `NUMERIC` llega como `Decimal` y pandas lo guarda como `object`.** Es la trampa que te avisó
[sql/01_esquema.sql](sql/01_esquema.sql) al final. El síntoma: `df["valor"].mean()` funciona pero
`df["valor"].rolling(5).mean()` explota, o `df.dtypes` dice `object` donde esperabas `float64`.

```python
df.dtypes    # <- mirá esto SIEMPRE después del primer read_sql. Son 2 segundos.
```

Tres salidas, elegí una: castear en la query (`r.valor::float8 AS valor`), castear en pandas
(`.astype("float64")`), o haber usado `DOUBLE PRECISION` en el esquema. La primera es la que menos
sorprende a quien lee el código.

**3. `parse_dates`.** `pd.read_sql` suele devolver bien los `TIMESTAMP`, pero si la columna llega
como texto, todo lo de la Parte 2 falla con un mensaje confuso sobre índices. Chequealo en el
mismo `df.dtypes`: tiene que decir `datetime64[ns]`.

**4. `engine` vs `connection`.** Pasarle el `engine` a `read_sql` funciona, pero abre y cierra una
conexión por llamada. Si vas a hacer cinco consultas seguidas, abrí una conexión con
`with engine.connect() as conn:` y reusala.

---

## Parte 2 — Resampleo: el concepto y sus tres trampas

### ELI5

Tus datos vienen cada 5 minutos. Nadie mira 144 puntos por tag: se miran promedios por hora.
Resamplear es **cambiar la frecuencia de una serie temporal**, agregando (de 5 min a 1 h) o
interpolando (de 1 h a 5 min).

No es un `groupby` común. Un `groupby` agrupa por valores que existen; un `resample` **genera los
canastos aunque no haya datos adentro**. Esa diferencia es todo el punto: si el historiador se
cayó entre las 10 y las 11, un `groupby` no te muestra esa hora y un `resample` te la muestra
vacía. Vos querés verla vacía.

### El oráculo de esta semana

Tus datos son perfectos para verificar: 6 tags × 144 muestras cada 5 minutos, de **06:00 a 17:55**.

```
12 horas × 6 tags = 72 filas después de resamplear a 1 hora
cada canasto: exactamente 12 muestras (12 × 5 min = 1 h)
```

**Si no te da 72 filas de 12 muestras, algo está mal.** Los sospechosos, en orden:

| Te dio | Probablemente |
|---|---|
| 78 filas | Tenés un canasto de más: el bucket de las 18:00 con 0 muestras (mirá `closed`/`label`) |
| 144 filas | No agrupaste por tag; estás resampleando los 6 tags mezclados |
| 6 filas | Agrupaste solo por tag y el resample no hizo nada (índice mal puesto) |
| 72 filas pero con 11 y 13 | El `label`/`closed` te corrió el borde del canasto |

### Trampa 1: el índice

`resample` necesita un `DatetimeIndex`. Si tu fecha es una columna, tenés dos caminos:

```python
df = df.set_index("timestamp")              # opción A: la fecha pasa a ser el índice
# ... y después .sort_index(), porque resample asume orden

df.groupby(["tag", pd.Grouper(key="timestamp", freq="1h")])   # opción B: sin tocar el índice
```

La opción B (`pd.Grouper`) es la que menos gente conoce y la que mejor se lee cuando agrupás por
tag **y** por tiempo a la vez, que es justo tu caso. Probá las dos y quedate con la que entiendas
al releerla en un mes.

> Ojo con `"1h"` en minúscula. En pandas 2.2 el alias `"1H"` quedó deprecado y tira `FutureWarning`.
> Los alias que vas a usar: `"5min"`, `"1h"`, `"1D"`.

### Trampa 2: dónde cae el borde

`resample` tiene dos parámetros que nadie lee hasta que los números no cierran:

- **`closed`**: ¿el borde del canasto pertenece al canasto de antes o al de después?
- **`label`**: ¿el canasto se llama por su borde izquierdo o derecho?

Para frecuencias como `"1h"` los defaults son `closed="left"`, `label="left"`: el canasto `07:00`
contiene `[07:00, 08:00)` — incluye las 07:00, **no** incluye las 08:00.

Esto no es trivia. Si tu canasto de las 07:00 te da 13 muestras en vez de 12, es esto.

### Trampa 3: el hueco vacío no es cero

Un canasto sin datos te da `NaN`, no `0`. Y está bien que sea así: "no medimos" no es lo mismo que
"medimos cero". La decisión es tuya y hay que tomarla explícitamente:

| Qué hacer | Cuándo |
|---|---|
| Dejar `NaN` | Casi siempre. Es honesto y se propaga solo |
| `fillna(0)` | **Casi nunca** en un dato de proceso. Un promedio de temperatura de 0 °C es mentira |
| `dropna()` | Si el consumidor de abajo no tolera huecos, y lo documentás |
| `ffill()` | Si el dato es "último valor conocido" (un setpoint, un estado) y no una medición |

**Experimento de 5 minutos:** borrá una hora entera de un tag con un `DELETE` dentro de un
`BEGIN; ... ROLLBACK;` (el mismo truco del experimento al final de
[sql/05_promedio_movil.sql](sql/05_promedio_movil.sql)) y mirá qué le pasa a tus 72 filas. Si
siguen siendo 72 con un `NaN`, resampleaste bien. Si son 71, estás usando un `groupby` disfrazado.

---

## Parte 3 — Los KPIs: elegir bien es la mitad del trabajo

El checklist pide 2–3. Elegí **pocos y defendibles** antes que muchos y decorativos: en la
entrevista te van a preguntar por qué esos, no cuántos.

### La regla de oro

**Escribí la fórmula en una línea de español antes de escribir una línea de código.** Si no podés,
todavía no sabés qué estás calculando. Y en esa línea tienen que estar las tres respuestas:

1. ¿Sobre qué período? (una hora, un turno, el dataset entero)
2. ¿Qué pasa con los datos faltantes? (se ignoran, invalidan el KPI, cuentan como malos)
3. ¿Qué unidad tiene el resultado? (%, minutos, °C, adimensional)

### Candidatos, con el oráculo al lado

**KPI 1 — Tiempo en alarma (%)**

*"Porcentaje de muestras del período en las que el valor estuvo fuera del rango operativo."*

Es el mejor primer KPI porque **ya lo tenés calculado tres veces**. La columna `%ALARMA` de
[README.md](README.md):

```
TAG     MUESTRAS  ALARMAS  %ALARMA
FT-310     144        0       0.0
LT-115     144        0       0.0
MT-501     144        3       2.1
PT-204     144        9       6.2
TT-101     144       16      11.1
VT-501     144        6       4.2
                     ──
TOTAL      864       34      3.94 %
```

Si tu KPI sobre el dataset entero no da esos seis números, no sigas: está mal.

> **Pista sobre el nombre:** "tiempo en alarma" y "porcentaje de muestras en alarma" son lo mismo
> **solo si el muestreo es uniforme**. El tuyo lo es (cada 5 min, siempre). Si un día no lo fuera,
> el porcentaje de muestras deja de ser tiempo. Anotá ese supuesto en el docstring — ese tipo de
> nota es lo que separa a alguien que copió una fórmula de alguien que la entendió.

**KPI 2 — Disponibilidad del dato (%)**

*"Porcentaje de muestras con calidad `Good` sobre el total esperado del período."*

Oráculo, contando sobre [data/sensores_planta.csv](data/sensores_planta.csv):

```
849 Good / 864 totales = 98.26 %
no-Good: 3 Bad + 12 Uncertain = 15
por tag:  TT-101 0 | FT-310 1 | MT-501 2 | PT-204 3 | LT-115 3 | VT-501 6
```

La palabra difícil es **"esperado"**. Con 12 h cada 5 min, esperás 144 muestras por tag. Si
llegaron 140, ¿la disponibilidad es sobre 140 (las que llegaron) o sobre 144 (las que debían
llegar)? **Las dos respuestas son defendibles y dan números distintos.** Elegí, documentá, y sé
consistente — este es exactamente el tipo de decisión que un cliente te va a cuestionar.

**KPI 3 — Estabilidad / variabilidad**

*"Desvío estándar del valor por tag y por hora, como medida de qué tan quieto está el proceso."*

Acá reaparece la trampa de siempre: **`ddof`**. [tagframe/analisis.py](tagframe/analisis.py) usa
`ddof=0` (poblacional), `tagstats` usa `pstdev`, y el default de pandas es `ddof=1`. Postgres suma
su propia versión: `stddev()` es alias de `stddev_samp()`, o sea muestral
([guia-sem4.md](guia-sem4.md), Parte 5).

Con 12 muestras por canasto, `ddof=0` y `ddof=1` difieren ~4 %. Lo suficiente para que no cierre
con el README y lo suficiente poco para que no lo veas.

**Otros candidatos, si querés algo menos obvio**

- **Tasa de cambio máxima** (°C/min): el `LAG` de Semana 5, dividido por el intervalo. Sirve para
  detectar rampas. Ojo: si hay un hueco, el delta cruza el hueco y da un valor enorme y falso.
- **Tiempo entre alarmas (MTBA)**: `LAG` sobre la vista `alarmas`. Dato: una alarma que dura 16
  muestras seguidas son 16 filas, no 1 evento. ¿Tu KPI cuenta muestras o **eventos**? Agrupar
  muestras consecutivas en eventos es un ejercicio excelente y bastante más difícil de lo que
  parece.

---

## Parte 4 — Tests: el entregable dice "tests que la cubran"

### Los tres niveles, y cuál cuesta cuánto

| Nivel | Qué prueba | Necesita DB | Cuántos |
|---|---|---|---|
| **Unitario** | Una función de KPI sobre un DataFrame chico | No | Muchos |
| **Integración** | Que la query devuelva lo que creés | Sí | Pocos |
| **End-to-end** | CSV → base → KPI, todo el camino | Sí | Uno o dos |

**El grueso va en unitarios**, y el truco para que sean unitarios de verdad es el mismo que ya usa
[tests/conftest.py](tests/conftest.py): que la función de KPI reciba un **DataFrame**, no una
conexión. Si tu `calcular_disponibilidad()` abre la base adentro, no podés testearla sin base, y
vas a terminar no testeándola.

### El oráculo calculado a mano

```python
@pytest.fixture
def serie_de_6_muestras():
    # TODO: 6 filas, valores elegidos por vos, con el resultado que PODÉS calcular
    #       de cabeza. Ej: 4 dentro de rango y 2 fuera -> 33.33 % en alarma.
    #       Pista: si para saber el resultado esperado tenés que correr tu propia
    #       función, el test no prueba nada. Prueba que el código hace lo que hace.
    ...
```

Ese es el criterio que separa un test de un espejo. `tagframe` lo tiene bien resuelto: sus tests
usan como oráculo la tabla del README, que salió de una implementación **distinta** (`tagstats`).

### Testear contra una base sin volverse loco

Tres estrategias:

| | Cómo | Contra |
|---|---|---|
| **Transacción + rollback** | Fixture que abre una transacción, corre el test, hace rollback | La base tiene que existir igual |
| **Base de test aparte** | `industrial_test`, se crea y se tira en cada corrida | Más lento; hay que crearla en CI |
| **SQLite en memoria** | Rapidísimo, cero setup | **No tiene `ON CONFLICT` igual, ni las mismas funciones.** Estás testeando otra base |

La primera es la que usa casi todo el mundo y la que mejor te va a servir en Semana 8, cuando el CI
levante un Postgres como servicio. La tercera es una trampa tentadora: te da tests verdes contra un
motor que no es el tuyo.

```python
@pytest.fixture
def conexion_con_rollback(engine):
    # TODO: abrir conexión, empezar transacción, yield, rollback.
    #       Pista: el yield va ADENTRO del bloque, y el rollback DESPUÉS del yield.
    #       Pista 2: si tu código llama a session.commit() por su cuenta, este
    #       patrón solo no alcanza — buscá "SQLAlchemy joining a session into an
    #       external transaction" en la doc. Es el caso real y está documentado.
    ...
```

### Floats en asserts

```python
assert resultado == 3.94          # frágil: puede dar 3.9399999999999995
assert resultado == pytest.approx(3.94, abs=0.01)   # <- así
```

`pytest.approx` es una de esas cosas que, una vez que la conocés, usás siempre.

### El test de reproducibilidad

El que exige el entregable, y es más sutil de lo que parece:

```python
def test_es_reproducible(datos):
    assert calcular_kpis(datos) == calcular_kpis(datos)
```

Eso detecta `datetime.now()` y orden de `set`, pero **no** detecta `SELECT` sin `ORDER BY`, porque
dos corridas seguidas contra la misma base suelen devolver el mismo orden. Para eso: probá la
misma comparación con el DataFrame de entrada **barajado** (`df.sample(frac=1, random_state=0)`).
Un KPI bien escrito no depende del orden de las filas de entrada. Si el test falla ahí, encontraste
un bug real.

---

## Verificación de punta a punta

1. **El resumen por tag desde la base tiene que dar la tabla del README.** Los seis renglones,
   incluido el desvío con `ddof=0`.
2. **72 filas** al resamplear a 1 hora, 12 muestras cada una.
3. **Los KPIs dan lo mismo corridos dos veces**, y lo mismo con las filas de entrada barajadas.
4. `pytest -q` en verde.

```bash
python -m tagstats data/sensores_planta.csv -l data/limites.csv
```

Sigue siendo el juez de última instancia: si tu pipeline nuevo y esa tabla difieren, uno de los dos
está mal, y averiguar cuál es el ejercicio.

## Checklist

```
[] Todas las queries llevan ORDER BY explícito
[] df.dtypes revisado: nada de object donde va float64, timestamp es datetime64
[] Resampleo a 1h: 72 filas, 12 muestras por canasto
[] Decidido (y documentado) qué pasa con un canasto vacío
[] KPI 1: tiempo en alarma, coincide con la columna %ALARMA del README
[] KPI 2: disponibilidad, 98.26 % global, con el denominador documentado
[] KPI 3: el que elijas, con ddof decidido a conciencia
[] Cada KPI tiene su fórmula escrita en una línea de español en el docstring
[] Tests unitarios con oráculo calculado a mano (no con la salida de tu propia función)
[] Un test de integración contra la base, con rollback
[] Un test end-to-end: CSV -> base -> KPI
[] Test de reproducibilidad, incluyendo con las filas de entrada barajadas
```

---

## Lo que NO es esta semana

- **Nada de gráficos ni dashboards.** El entregable dice KPIs reproducibles y tests. Un matplotlib
  lindo no compensa un KPI sin definir.
- **Nada de machine learning.** "Detección de anomalías simples" en el roadmap significa *fuera de
  rango* y *salto brusco*, que ya sabés calcular. Un IsolationForest acá es ruido.
- **Nada de reescribir la ingesta.** Si Semana 6 quedó con deuda, anotala y seguí; el código de
  esta semana lee de la base, no del CSV.
- **Nada de optimizar.** Con 864 filas todo es instantáneo. El `EXPLAIN ANALYZE` de Semana 5 sirve
  para saber leerlo, no para pelear milisegundos acá.
