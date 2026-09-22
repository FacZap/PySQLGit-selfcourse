# Semana 4 — Cargar los CSV de ejemplo a PostgreSQL

> **Cómo usar esta guía:** es una guía de estudio, no una solución. Trae *dónde* va cada cosa,
> *por qué*, esqueletos con `TODO` en [sql/](sql/) y las trampas que te vas a encontrar. El SQL
> lo escribís vos. Nada de copiar/pegar bloques terminados.

## Qué vas a lograr

Los 6 tags de [data/limites.csv](data/limites.csv) y las 864 lecturas de
[data/sensores_planta.csv](data/sensores_planta.csv) viviendo en una base PostgreSQL llamada
`industrial`, en un esquema normalizado, sin escribir una línea de Python.

Cierra el `[] Cargar datos de ejemplo` de [guia-a-futuro.md:123](guia-a-futuro.md) y te deja los
datos sobre los que practicar los JOINs y las CTEs que pide el entregable de la semana.

**Semana 4 es SQL puro.** No toca [tagstats/](tagstats/) ni [tagframe/](tagframe/), no suma
dependencias, `pytest -q` no se entera de nada. Eso no es un accidente: es el punto. Ahora mismo
tenés el mismo dataset procesado dos veces en Python, así que cuando lo proceses una tercera vez
en SQL, **ya sabés qué número tiene que dar**. Es la mejor situación posible para aprender un
lenguaje nuevo.

### Los archivos

| Archivo | Qué hace |
|---|---|
| [sql/01_esquema.sql](sql/01_esquema.sql) | La forma de la base: `tags`, `limites`, `readings`, vista `alarmas`. Cero filas |
| [sql/02_staging.sql](sql/02_staging.sql) | Los CSV entran crudos, como texto, sin interpretar |
| [sql/03_carga.sql](sql/03_carga.sql) | De crudo a normalizado: casts, JOINs, `ON CONFLICT` |
| [sql/04_verificar.sql](sql/04_verificar.sql) | Demostrar que salió bien, contra los números del README |
| [scripts/cargar_db.ps1](scripts/cargar_db.ps1) | Wrapper opcional: corre los cuatro en orden |

---

## Parte 0 — Conectarse

El paso que todos subestiman y donde se va la primera hora.

### Lo que ya tenés

PostgreSQL 18 **ya está instalado y corriendo** en tu máquina, como servicio de Windows.
Comprobalo:

```powershell
Get-Service postgresql*
```

Tiene que decir `Running`. Si dice `Stopped`, arrancalo desde Servicios de Windows.

**ELI5 de qué es un servidor de base de datos:** es un programa que ya está prendido en tu
máquina, esperando que alguien le hable. No es un archivo que abrís, como un `.csv`. Es más
parecido a un mozo: está ahí, vos le pedís cosas y él te las trae. `psql` es el teléfono para
hablarle.

### El problema: `psql` no está en el PATH

El instalador oficial de PostgreSQL en Windows **no agrega sus herramientas al PATH**. Si escribís
`psql` te va a decir que no existe. En esta máquina está acá:

```
E:\Program Files\PostgreSQL18\18\bin\psql.exe
```

**Ojo, esa no es la ruta por defecto.** El instalador propone
`C:\Program Files\PostgreSQL\18\bin`, pero acá quedó en `E:`, y la carpeta se llama
`PostgreSQL18`, no `PostgreSQL`. Si alguna vez lo reinstalás en otro lado, no la adivines: la
ruta real te la dice el propio servicio de Windows.

```bash
(Get-CimInstance Win32_Service -Filter "Name='postgresql-x64-18'").PathName
```

Te devuelve la línea de arranque del servicio, con el `bin\` adentro.

Agregalo **solo para esta sesión de PowerShell** (no toques el PATH del sistema, no hace falta):

```bash
$env:Path += ";E:\Program Files\PostgreSQL18\18\bin"
```

Eso vive mientras la ventana esté abierta. Cerrás PowerShell y se olvida. Cuando confirmes que
todo el flujo te funciona, ahí sí evaluá agregarlo permanente desde Variables de Entorno.

Verificá:

```bash
psql --version
```

Tiene que responder `psql (PostgreSQL) 18.6`.

### El encoding, antes de que te muerda

```bash
$env:PGCLIENTENCODING = "UTF8"
```

**ELI5:** los archivos de [data/](data/) están guardados en UTF-8. La consola de Windows, por
herencia de los años 90, le dice a `psql` que hable WIN1252. Son dos alfabetos distintos, así que
cualquier carácter no-ASCII llega deformado.

Lo importante: **eso no se arregla después**. Si el texto entró roto a la base, quedó roto en el
disco; ninguna consulta lo va a enderezar. Hay que setearlo *antes* de cargar.

Por el mismo motivo, los `.sql` de [sql/](sql/) están escritos **sin acentos** a propósito. Esta
guía sí los usa: acá no hay consola en el medio.

### La password

`psql` te la va a pedir. La definiste vos cuando instalaste PostgreSQL — es la del usuario
`postgres`, el superusuario.

Tres formas de no tener que tipearla cuatro veces seguidas:

| Cómo | Dónde vive | Cuándo conviene |
|---|---|---|
| Que `psql` te la pregunte | En ningún lado | Siempre que sea un comando suelto |
| `$env:PGPASSWORD = "..."` en tu sesión | Solo en la RAM de esa ventana | Cuando vas a correr los 4 archivos seguidos |
| `%APPDATA%\postgresql\pgpass.conf` | Fuera del repo, en tu perfil | Si vas a laburar varios días con esto |

El formato de `pgpass.conf` es una línea:

```
localhost:5432:*:postgres:tu_password
```

**Lo que nunca va:** la password escrita en un `.sql`, en un `.ps1`, o en cualquier cosa que git
pueda ver. Es la trampa que marca [guia-a-futuro.md:97-100](guia-a-futuro.md), y por eso este
cambio agrega `.env` al [.gitignore](.gitignore) — para cuando llegues a Semana 6 y necesites
guardar credenciales de verdad, el repo ya te está cubriendo.

### El saludo

```bash
psql -U postgres -h localhost -c "SELECT version();"
```

Si te devuelve la versión, hablaste con el servidor. Ya está lo difícil.

### Crear la base

```bash
psql -U postgres -h localhost -c "CREATE DATABASE industrial;"
```

**Fijate que no lleva `-d`.** Ese detalle confunde a todo el mundo la primera vez, y tiene una
explicación simple: para hablar con Postgres tenés que estar conectado a *alguna* base, y no
podés crear una base desde adentro de sí misma (todavía no existe). Sin `-d`, `psql` se conecta a
la base que se llama igual que el usuario (`postgres`), que existe desde la instalación. Desde
ahí sí podés crear otras.

Por eso `CREATE DATABASE` no está en [sql/01_esquema.sql](sql/01_esquema.sql): ese archivo ya
corre *adentro* de `industrial`.

De acá en adelante, todos los comandos llevan `-d industrial`.

### Entrar a la consola interactiva

```bash
psql -U postgres -h localhost -d industrial
```

Cuatro meta-comandos que vas a usar todo el tiempo:

| Comando | Qué muestra |
|---|---|
| `\dt` | Las tablas |
| `\dv` | Las vistas |
| `\d readings` | El detalle de una tabla: columnas, tipos, claves, **índices** |
| `\q` | Salir |

Empiezan con `\` porque **no son SQL**: son comandos de `psql` mismo. Esa distinción parece
trivial y es la que explica la Parte 2.

---

## Parte 1 — El esquema

### ELI5: por qué no una sola tabla

La tentación es volcar el CSV tal cual: una tabla con `timestamp, tag, valor, unidad, calidad` y
listo. Funciona. Pero mirá lo que guardarías:

```
2026-08-24T06:00:00,TT-101,77.15,degC,Good
2026-08-24T06:05:00,TT-101,78.20,degC,Good
2026-08-24T06:10:00,TT-101,79.40,degC,Good
   ... 141 veces más ...
```

El texto `TT-101,degC` está repetido **144 veces**. Y no es solo desperdicio de espacio. Es que si
mañana alguien decide que el tag pasa a llamarse `TT-101A`, tenés que acertarle a 144 filas. Si
le pegás a 143, ahora tenés dos sensores donde había uno, y ninguna consulta te lo va a avisar.

Normalizar es guardar cada hecho **en un solo lugar**:

```
   tags                     limites                   readings
   ────────────             ─────────────             ──────────────
   tag_id ◄──────┬───────── tag_id (PK, FK)           reading_id
   nombre        │          minimo                    tag_id ────────┐
   unidad        │          maximo                    "timestamp"    │
   descripcion   │                                    valor          │
                 │                                    calidad        │
                 └────────────────────────────────────────────────────┘

   6 filas                  6 filas                   864 filas

                        alarmas  (VISTA, 0 filas propias)
                        readings ⋈ tags ⋈ limites, filtrando fuera de rango
```

`TT-101` se escribe una vez. Las 864 lecturas apuntan con un número.

### ELI5: qué es una clave foránea

`readings.tag_id` **referencia** a `tags.tag_id`. Eso significa que el motor no te deja insertar
una lectura de un tag que no existe. Ni queriendo. Ni con un `INSERT` a mano un domingo a las 3am.

La diferencia con validar en Python es de naturaleza, no de grado: una validación en Python es
código que vos escribís y que algún día vas a olvidarte de llamar desde el script nuevo. La clave
foránea la aplica el motor, en cada `INSERT`, viniera de donde viniera.

### ELI5: qué es una vista

Una consulta guardada con nombre. No ocupa lugar y no guarda filas propias: cada vez que le hacés
`SELECT`, se recalcula sobre las tablas reales.

Por eso `alarmas` es vista y no tabla. Una alarma no es algo que un sensor mide: es una
**conclusión** sobre algo que un sensor midió (el valor se fue de rango). Si mañana ingeniería
sube el máximo de `TT-101` de 95 a 100, una *tabla* de alarmas te quedaría llena de alarmas viejas
que ya no son alarmas, y habría que salir a corregirlas a mano. La vista se corrige sola, porque
no guardó nada: vuelve a mirar `limites`.

### La decisión de las tres tablas

Por qué `limites` va aparte y no como dos columnas más en `tags`: **son cosas que cambian a ritmos
distintos**. `tags` dice *qué es* el sensor (identidad — no cambia nunca). `limites` dice *cómo se
opera hoy* (ingeniería de proceso — cambia cuando cambia la receta). Si las mezclás, tocás el
catálogo de sensores cada vez que alguien afloja un setpoint.

Es una relación 1 a 1 y está bien que lo sea. Separar por *cada cuánto cambia* es un criterio tan
válido como separar por *cuántos hay*.

### Dos trampas que están dentro del archivo

Están explicadas en detalle en [sql/01_esquema.sql](sql/01_esquema.sql), pero conviene que las
sepas antes de abrirlo:

**`timestamp` es también un nombre de tipo en SQL.** Si nombrás así a la columna, hay que
escribirla `"timestamp"` con comillas dobles, ahí y en cada consulta futura, para siempre. Es la
vía que eligió la chuleta ([guia-a-futuro.md:141](guia-a-futuro.md)). La alternativa —llamarla
`medido_en` y no pelear más— es igual de válida. Elegí, pero elegí a conciencia.

**El índice de la chuleta puede sobrar.** [guia-a-futuro.md:146](guia-a-futuro.md) propone
`CREATE INDEX idx_readings_tag_ts ON readings (tag_id, "timestamp")`. Pero si le ponés
`UNIQUE (tag_id, "timestamp")` a la tabla, Postgres **ya creó** ese índice por su cuenta, porque
lo necesita para hacer cumplir la restricción. El `CREATE INDEX` sería un segundo índice idéntico:
no acelera nada y encarece cada `INSERT` ([guia-a-futuro.md:300](guia-a-futuro.md)).

No me creas. Creá la tabla, corré `\d readings` y mirá qué índices ya tiene.

---

## Parte 2 — `\copy` vs `COPY`

El concepto central de esta semana, y la fuente número uno de frustración.

Postgres tiene dos formas de leer un archivo, con nombres casi iguales y comportamientos
completamente distintos:

| | Quién abre el archivo | Con qué usuario | Necesita superusuario |
|---|---|---|---|
| `COPY` (SQL) | **El servidor** | El del servicio de Windows | Sí |
| `\copy` (psql) | **psql**, o sea el cliente | El tuyo | No |

**ELI5:** `COPY` es pedirle al mozo que vaya a buscar un papel a tu casa. Él no tiene la llave.
`\copy` es que lo traigas vos y se lo pases en la mesa.

El servidor de Postgres corre como un usuario de servicio de Windows que no tiene por qué ver tu
`D:\Carpetas\...`. Con `\copy`, el archivo lo abre `psql` —el programa que vos ejecutaste, con tus
permisos— y le manda las filas al servidor por la misma conexión que ya tenían abierta.

**Para todo lo que hagas en tu máquina: siempre `\copy`.**

### Las tres trampas, en orden de cuánto tiempo hacen perder

**1. La ruta es relativa al directorio desde el que corriste `psql`.** No a la ubicación del
`.sql`. Por eso todos los comandos de esta guía dicen "parado en la raíz del repo". Si corrés
desde `sql/`, va a buscar `sql/data/limites.csv` y te va a decir `could not open file`.

**2. Es un meta-comando de `psql`, no SQL: va en UNA SOLA LÍNEA.** No lo podés partir en varias
líneas como harías con un `SELECT` largo. Si lo partís, `psql` lee media instrucción y tira un
error que no tiene nada que ver con el problema real.

**3. No existe fuera de `psql`.** pgAdmin y DBeaver hablan SQL, no meta-comandos. Si pegás un
`\copy` ahí, no va a andar.

### La forma

```
\copy nombre_de_tabla FROM 'ruta/al/archivo.csv' WITH (FORMAT csv, HEADER true)
```

`FORMAT csv` le dice que interprete comillas y comas como CSV. `HEADER true` le dice que la
primera línea es la cabecera y que la saltee.

Documentación: <https://www.postgresql.org/docs/current/sql-copy.html>

Cuando sale bien, `psql` te contesta con la cantidad de filas: `COPY 6`, `COPY 864`.

| Te dijo | Qué pasó |
|---|---|
| `COPY 0` | El archivo estaba vacío o solo tenía cabecera |
| `COPY 7` cuando esperabas 6 | Te olvidaste `HEADER true` y cargaste la cabecera como dato |
| `could not open file` | Estás parado en el directorio equivocado |

---

## Parte 3 — Por qué hace falta staging

`\copy` es un embudo tonto, y está bien que lo sea: agarra la columna 1 del archivo y la mete en
la columna 1 de la tabla, la 2 en la 2. No sabe hacer preguntas.

Y tu CSV dice `TT-101`, mientras que `readings` quiere un número (`tag_id`) que solo se puede
averiguar mirando la tabla `tags`. `\copy` no puede hacer esa búsqueda. No es una limitación:
cargar y traducir son dos trabajos distintos y conviene que fallen por separado.

Entonces el CSV aterriza primero en una **tabla espejo** —mismas columnas que el archivo, todo
`TEXT`— y recién después un `INSERT ... SELECT ... JOIN` lo traduce al esquema real.

### Por qué todo `TEXT` en staging

Para separar dos fallas que se parecen y no lo son:

- Si staging es `TEXT`, un `\copy` que falla es un problema de **formato** (columnas corridas,
  separador equivocado).
- Un cast que falla en `03_carga.sql` es un problema de **contenido** (un `N/A` donde iba un
  número).

Si staging tuviera los tipos finales, las dos fallas se verían igual y estarías adivinando.

**Y esto ya lo hacés en Python.** `FuenteCSV` lee todo con `dtype=str` a propósito, y deja la
coerción de tipos para `Limpiador` ([tagframe/fuentes.py](tagframe/fuentes.py),
[tagframe/limpieza.py](tagframe/limpieza.py)). Mismo criterio, otro motor. Cuando veas que la
decisión se repite en dos tecnologías distintas, es porque no era una decisión sobre pandas: era
una decisión sobre datos.

### La trampa de `TEMP`

`CREATE TEMP TABLE` crea una tabla que se muere al cerrar la sesión. Suena perfecto para staging.

El problema: cada `psql -f archivo.sql` es **una sesión distinta**. Si creás la tabla temporal en
`02_staging.sql`, cuando arranque `03_carga.sql` ya no existe.

Dos salidas: tablas normales `staging_*` que borrás explícitamente al final de `03` (es lo que
plantean los esqueletos), o correr todo en una sola sesión con `\i`. La primera es más fácil de
depurar, porque podés mirar el staging entre archivo y archivo.

### La trampa de `sensores_sucios.csv`

**Ese archivo no se carga acá, a propósito.** Tiene esta fila
([data/sensores_sucios.csv:9](data/sensores_sucios.csv)):

```
2026-08-24T06:00:00,PT-204,4,82,bar,Good
```

Es un decimal escrito con coma y sin comillas (`4,82`), así que trae **seis** campos para una
tabla de **cinco** columnas. `\copy` corta la carga entera con `extra data after last expected
column`.

Y no hay forma de decirle "salteá esa y seguí": `\copy` es todo o nada. No tiene el equivalente
del `on_bad_lines="warn"` que sí tiene pandas y que ya usa `FuenteCSV`.

Eso **es** la división del trabajo: los datos sucios se limpian en Python, antes de tocar la base.
La base recibe lo que ya está limpio. Es el orden ingesta → validación → storage que plantea
[guia-a-futuro.md:309](guia-a-futuro.md) para Semana 6.

Vale la pena verlo fallar. Son 30 segundos y no se olvida más.

### La trampa del éxito vacío

```
\copy staging_lecturas FROM 'data/sensores_vacio.csv' WITH (FORMAT csv, HEADER true)
```

Ese archivo tiene solo la cabecera. Responde `COPY 0`: sin error, sin filas.

**"No falló" y "funcionó" no son lo mismo.** Por eso existe
[sql/04_verificar.sql](sql/04_verificar.sql), que compara contra números esperados en vez de
confiar en la ausencia de errores.

---

## Parte 4 — Idempotencia

Querés poder correr la carga dos veces sin duplicar nada. No por prolijidad: porque la vas a
correr diez veces mientras aprendés, y porque un pipeline real reprocesa un día que llegó tarde y
no puede duplicarlo.

Postgres te da `ON CONFLICT`:

```
INSERT INTO tabla (...) SELECT ...
ON CONFLICT (columnas_de_la_restriccion) DO ALGO
```

Se lee: *"si esto choca contra la restricción que hay sobre estas columnas, hacé tal cosa en vez
de fallar"*.

El "algo" son dos opciones, y elegir mal es un bug silencioso:

| | Qué hace | Cuándo |
|---|---|---|
| `DO NOTHING` | Ya existe, no lo toques. **Gana la fila vieja** | **Hechos.** Una lectura del pasado es lo que es. Si el historiador la reenvía, es la misma |
| `DO UPDATE` | Ya existe, pisalo. **Gana la fila nueva** (esto es un *upsert*) | **Configuración.** Si alguien cambió el máximo de `TT-101` en el CSV, querés el valor nuevo |

Y hay una tercera opción que es no poner nada: entonces el `INSERT` **falla** con `duplicate key
value violates unique constraint`. También es válida —fallar fuerte es mejor que duplicar en
silencio— siempre que sea una decisión y no un olvido.

**Antes de escribir los tres `INSERT`, decidí cuál va en cada uno.** La pregunta que lo resuelve:
¿cuál de las tres tablas guarda *configuración* y cuáles guardan *hechos*?

Es la misma trampa que [guia-a-futuro.md](guia-a-futuro.md) marca para Semana 6: *decidí la
estrategia de duplicados de antemano*.

### El detalle que engancha con el esquema

`ON CONFLICT` necesita saber **contra qué restricción** chocar. Si en
[sql/01_esquema.sql](sql/01_esquema.sql) no pusiste `UNIQUE` en `tags.nombre`, acá te va a tirar:

```
no unique or exclusion constraint matching the ON CONFLICT specification
```

Y el problema no está en el `INSERT`: está tres archivos atrás, en el esquema. **La idempotencia
se diseña en el esquema, no se parchea en la carga.** Cuando veas ese error, andá para atrás.

---

## Parte 5 — Verificación cruzada

Acá está lo mejor de esta semana.

Este dataset ya fue procesado dos veces en Python: por `tagstats` (Semana 1, stdlib) y por
`tagframe` (Semana 3, pandas). Los resultados están escritos en
[README.md:55-64](README.md):

```
TAG     UNIDAD  MUESTRAS      MIN      MAX  PROMEDIO  DESVIO  ALARMAS
FT-310  m3/h       144      67.30    95.30     82.07    8.59        0
LT-115  %          144      27.10    81.40     60.26   16.97        0
MT-501  A          144      25.40    51.30     31.57    4.26        3
PT-204  bar        144       2.19     5.28      4.66    0.65        9
TT-101  degC       144      73.70   102.10     80.24    7.27       16
VT-501  mm/s       144       1.59     7.95      3.74    1.42        6

TOTAL: 6 tags | 864 muestras | 34 alarmas
```

**No estás verificando "me parece que dio bien". Estás verificando contra una tabla de números que
tiene que dar idéntica.** Si SQL y Python difieren, uno de los dos está mal, y averiguar cuál es
el ejercicio.

### La trampa del desvío

Postgres te da **dos** funciones de desvío estándar, y no son la misma:

| Función | Divide por | Qué es |
|---|---|---|
| `stddev_samp()` | n − 1 | Muestral |
| `stddev_pop()` | n | Poblacional |

Y `stddev()` a secas es **alias de `stddev_samp()`**. O sea: el default de Postgres es el muestral.

Pero este proyecto usa el **poblacional** en todos lados: `tagstats` usa `pstdev` y `tagframe` usa
`.std(ddof=0)`, con un comentario que dice exactamente esto
([tagframe/analisis.py](tagframe/analisis.py)).

Si escribís `stddev()`, te va a dar **parecido** pero distinto que el README. Con 144 muestras la
diferencia es tan chica que se puede pasar por alto una tarde entera.

Ese es justo el tipo de bug que hay que aprender a cazar: **el que no rompe nada, solo miente un
poquito.** Corré las dos y mirá la diferencia con tus propios ojos — entender por qué n−1 no es lo
mismo que n vale mucho más que memorizar cuál usar.

### La trampa del borde

La condición de alarma es `valor < minimo OR valor > maximo`. **Estricto.** Ni `<=` ni `>=`: el
valor que toca exactamente el límite **no** es alarma — 60.0 y 95.0 están *en* rango.

No es un capricho: es lo que ya hace `Limite.en_alarma` en
[tagstats/modelos.py](tagstats/modelos.py) y lo repite [tagframe/analisis.py](tagframe/analisis.py).

Si te da 40 alarmas en vez de 34, es esto.

### La diferencia sutil de la unidad

En Python la unidad sale de **las lecturas**, y si un tag mezclara unidades el resumen lo muestra
como `bar/psi` para que el problema se vea. En tu esquema la unidad vive en `tags`, una sola vez,
así que esa mezcla es **imposible por construcción**.

Las dos decisiones son defendibles y dan lo mismo con estos datos. Pero son decisiones distintas y
conviene que sepas que las tomaste: **el esquema previene el problema, el código Python lo
detecta.** Prevenir es mejor cuando podés; detectar es lo que te queda cuando el dato ya te llegó.

### El cruce final

```bash
python -m tagstats data/sensores_planta.csv -l data/limites.csv
```

Las dos tablas tienen que decir lo mismo. Si difieren, no elijas cuál creer: encontrá de dónde
sale la diferencia. Los sospechosos, en orden de probabilidad:

1. `stddev()` en vez de `stddev_pop()` → desvío distinto
2. `<=` / `>=` en vez de `<` / `>` en la vista → más alarmas de la cuenta
3. Filas duplicadas por falta de `ON CONFLICT` → muestras ≠ 144
4. Redondeo aplicado en distinto momento → el último decimal baila

---

## El flujo completo

```bash
$env:Path += ";E:\Program Files\PostgreSQL18\18\bin"
```

```bash
$env:PGCLIENTENCODING = "UTF8"
```

Una sola vez, para crear la base:

```bash
psql -U postgres -h localhost -c "CREATE DATABASE industrial;"
```

Después, parado en la raíz del repo, los cuatro en orden:

```bash
psql -U postgres -h localhost -d industrial -f sql/01_esquema.sql
```

```bash
psql -U postgres -h localhost -d industrial -f sql/02_staging.sql
```

```bash
psql -U postgres -h localhost -d industrial -f sql/03_carga.sql
```

```bash
psql -U postgres -h localhost -d industrial -f sql/04_verificar.sql
```

O el wrapper, cuando ya lo hayas completado:

```bash
powershell -ExecutionPolicy Bypass -File scripts\cargar_db.ps1
```

### El `ON_ERROR_STOP` que te va a salvar

Por defecto, cuando `psql` lee un archivo con `-f` y una instrucción falla, **sigue con la
siguiente** y al final devuelve éxito. O sea: el esquema queda a medias y vos te enterás tres
archivos después.

```bash
psql -U postgres -h localhost -d industrial -v ON_ERROR_STOP=1 -f sql/01_esquema.sql
```

Con eso corta en el primer error y devuelve un exit code distinto de cero. Usalo siempre.

---

## Checklist

```
[] psql responde --version y SELECT version()
[] La base industrial existe
[] 01: \dt lista tags, limites, readings. \dv lista alarmas
[] 01: mirar \d readings y decidir si el CREATE INDEX sobra o no
[] 02: COPY 6 y COPY 864. Mirar 5 filas para ver que no quedaron corridas
[] 03: tags=6, readings=864
[] 03: correrlo DOS VECES y que readings siga en 864   <- la prueba real
[] 04: la tabla por tag coincide con README.md:55-64
[] 04: las alarmas dan 34, y por tag 0/0/3/9/16/6
[] pytest -q no empeoro (control de que no ensuciaste el lado Python)
```

> **Ojo con ese ultimo punto:** hoy `pytest -q` ya falla, y no por culpa de Semana 4.
> [tests/test_cli.py:17](tests/test_cli.py) importa `configurar_logging` pero
> [tagstats/cli.py:32](tagstats/cli.py) la tiene escrita `configurar_loggging` (con tres `g`) y
> con un `print("hola mundo!")` adentro. Es la migracion a `logging` de Semana 2 que quedo a
> medias ([guia-a-futuro.md:24-25](guia-a-futuro.md)). No lo arregles ahora si no queres: solo
> tene presente que ese rojo es viejo y no lo trajo el SQL.

Cuando los seis renglones coincidan con el README, el `[] Cargar datos de ejemplo` de
[guia-a-futuro.md:123](guia-a-futuro.md) está cerrado de verdad, y tenés datos confiables sobre
los que escribir las 8–10 consultas con JOINs y CTEs que pide el entregable.

---

## Lo que NO es esta semana

- **Nada de Python.** No instales `psycopg2` ni SQLAlchemy todavía. Semana 4 es SQL puro; el
  driver llega en Semana 6, y según [guia-a-futuro.md:332](guia-a-futuro.md) en un repo aparte
  (`industrial-data-pipeline`).
- **Nada de `FuenteSQL`.** El asiento ya está reservado en
  [tagframe/fuentes.py](tagframe/fuentes.py) y en [tagframe/cargador.py](tagframe/cargador.py),
  que están tipados contra la ABC justamente para eso. Pero es de más adelante: primero tiene que
  haber datos que leer.
- **Nada de migraciones.** `DROP` + `CREATE` alcanza mientras estés aprendiendo. Alembic es un
  tema de Semana 6, y `create_all` tampoco es migraciones.
