# PySQLGit — tagstats · tagframe

Dos paquetes hermanos que resuelven el mismo problema —resumir un CSV de
lecturas de tags/sensores por **mínimo, máximo, promedio, desvío y alarmas**—
con herramientas distintas, a propósito:

| Paquete | Semana | Herramienta | Dependencias de runtime |
|---|---|---|---|
| [`tagstats`](#tagstats) | 1 | biblioteca estándar (`csv`, `statistics`, generadores) | **ninguna** |
| [`tagframe`](#tagframe) | 3 | pandas (`DataFrame`, `groupby`, `merge`) | `pandas>=2.2` (extra `frame`) |

Los dos leen los mismos CSV de `data/` y **tienen que dar los mismos números**;
esa coincidencia es lo que verifican los tests de `tagframe`.

---

# tagstats

CLI en Python que lee un CSV de lecturas de tags/sensores y devuelve, por tag:
**mínimo, máximo, promedio, desvío y conteo de alarmas**.

Entregable de la **Semana 1** del roadmap: entorno pro + Git base + Python
idiomático. Sin dependencias de runtime: todo sale de la biblioteca estándar
(`csv`, `argparse`, `statistics`, `pathlib`, `dataclasses`).

---

## Requisitos

- Python 3.11 o superior (probado en 3.14).
- Para desarrollo: `pip install -r requirements-dev.txt` (ruff, black, pytest).

> **Nota sobre el entorno virtual:** lo normal es aislar el proyecto con
> `python -m venv .venv`. En esta resolución se pidió explícitamente omitirlo, así
> que el proyecto se corre con el Python del sistema. El `.gitignore` ya
> contempla `.venv/` para cuando se agregue.

## Uso rápido

```powershell
# Resumen completo del turno, con límites por tag
python -m tagstats data/sensores_planta.csv -l data/limites.csv

# Un solo tag, salida JSON para encadenar con otra herramienta
python -m tagstats data/sensores_planta.csv -l data/limites.csv -t TT-101 -f json

# Ventana de tiempo y solo muestras de calidad buena
python -m tagstats data/sensores_planta.csv -l data/limites.csv `
    --desde 2026-08-24T11:00 --hasta 2026-08-24T12:30 --solo-confiables
```

Salida:

```
TAG     UNIDAD  MUESTRAS         MIN         MAX    PROMEDIO     DESVIO   ALARMAS   %ALARMA
-------------------------------------------------------------------------------------------
FT-310  m3/h         144       67.30       95.30       82.07       8.59         0       0.0
LT-115  %            144       27.10       81.40       60.26      16.97         0       0.0
MT-501  A            144       25.40       51.30       31.57       4.26         3       2.1
PT-204  bar          144        2.19        5.28        4.66       0.65         9       6.2
TT-101  degC         144       73.70      102.10       80.24       7.27        16      11.1
VT-501  mm/s         144        1.59        7.95        3.74       1.42         6       4.2
-------------------------------------------------------------------------------------------
TOTAL: 6 tags | 864 muestras | 34 alarmas
```

Para ver todas las opciones: `python -m tagstats --help`.
Para un recorrido guiado: `powershell -ExecutionPolicy Bypass -File scripts\demo.ps1`.

## Opciones

| Opción | Qué hace |
|---|---|
| `csv` | CSV de lecturas (obligatorio) |
| `-l, --limites` | CSV de límites por tag. Sin él, las alarmas cuentan 0 |
| `-t, --tag` | Filtra por tag; se puede repetir (`-t TT-101 -t PT-204`) |
| `--desde` / `--hasta` | Recorta la ventana de tiempo (ISO-8601) |
| `--solo-confiables` | Usa solo las muestras con calidad `Good`/`OK` |
| `-f, --formato` | `tabla` (por defecto), `json` o `csv` |
| `--tolerante` | Saltea filas inválidas en vez de cortar, y avisa por stderr |
| `-o, --salida` | Escribe el reporte en un archivo UTF-8 |

Códigos de salida: `0` todo bien · `1` error de datos o de archivo · `2` uso incorrecto.

## Formato de los datos

`data/sensores_planta.csv` (lecturas):

```csv
timestamp,tag,valor,unidad,calidad
2026-08-24T06:00:00,TT-101,78.13,degC,Good
```

`data/limites.csv` (rango operativo; fuera de él es alarma):

```csv
tag,minimo,maximo,unidad,descripcion
TT-101,60,95,degC,Temperatura de salida del reactor
```

Datasets incluidos:

| Archivo | Para qué sirve |
|---|---|
| `data/sensores_planta.csv` | 864 filas, 6 tags, 12 h de turno cada 5 min. Incluye dos excursiones de proceso y picos aislados |
| `data/limites.csv` | Límites operativos de los 6 tags |
| `data/sensores_sucios.csv` | Caso hostil: valor `N/A`, celda vacía, timestamp con otro formato, tag vacío, `inf` y una fila corrida por un decimal con coma |
| `data/sensores_vacio.csv` | Solo cabecera: el CLI avisa y sale con 0 |

`data/sensores_planta.csv` se regenera con `python scripts/generar_datos.py`
(semilla fija: el archivo sale idéntico siempre, así el `git diff` queda limpio).

## Estructura

```
tagstats/
  modelos.py        Lectura, Limite, Estadisticas (dataclasses)
  lectura.py        parseo del CSV y filtros (generadores)
  estadisticas.py   min, max, promedio, desvío, alarmas
  reporte.py        formato tabla / json / csv
  cli.py            argumentos, códigos de salida, stdout vs stderr
tagframe/
  fuentes.py        FuenteDeDatos (ABC) -> FuenteCSV       [herencia]
  limpieza.py       Limpiador + ResultadoLimpieza          [properties]
  cargador.py       Cargador: compone fuente + limpiador   [composición]
  analisis.py       resumen(): groupby + merge             [pandas]
tests/              pruebas de pytest (tagstats + tagframe)
scripts/            generación de datos, verificación local, demo
docs/CONCEPTOS.md   por qué está hecho así
docs/PASOS.md       en qué orden se armó, paso a paso
```

El flujo es una cadena de generadores: **leer → filtrar → agrupar → calcular →
formatear**. El CSV se recorre una sola vez y nunca entra entero en memoria.

## Desarrollo

```powershell
python -m pytest                                              # pruebas
powershell -ExecutionPolicy Bypass -File scripts\verificar.ps1 # lint + formato + pruebas
```

`scripts\verificar.ps1` avisa y saltea las herramientas que no estén instaladas,
así que sirve igual antes de instalar ruff y black.

## Decisiones de tagstats que vale la pena conocer

- **Los bordes del límite no son alarma**: `60.0` y `95.0` con límite `[60, 95]`
  están *en rango*. Es la convención de la mayoría de los DCS.
- **Desvío poblacional** (`pstdev`), no muestral: se describe el turno medido,
  no se infiere sobre una población mayor.
- **Fallar rápido por defecto**: una fila mala corta la corrida con el número de
  fila y el motivo. `--tolerante` es una decisión explícita de quien corre el
  comando, no el comportamiento por omisión: un promedio calculado sobre datos
  silenciosamente descartados es peor que un error.
- **La salida es ASCII puro**: la consola de Windows no siempre usa UTF-8 y un
  carácter fuera de su codificación aborta el programa con `UnicodeEncodeError`.

El detalle de los conceptos de Python usados está en
[docs/CONCEPTOS.md](docs/CONCEPTOS.md), y el orden en que se armó el proyecto, en
[docs/PASOS.md](docs/PASOS.md).

---

# tagframe

Entregable de la **Semana 3**: POO (herencia y composición) + pandas + tests.
Mismo dominio que `tagstats`, otra caja de herramientas.

**Por qué un paquete aparte y no pandas dentro de `tagstats`:** `tagstats`
presume de cero dependencias de runtime y eso es parte de lo que enseña (la
cadena de generadores, el CSV que se recorre una sola vez). Meterle pandas
borraría esa identidad. `tagframe` es el que depende de pandas; `tagstats` queda
intacto y su `[project].dependencies` sigue en `[]`.

## Instalación

```powershell
pip install -e .[frame]          # instala pandas y deja tagframe usable
```

Para desarrollo, `pip install -r requirements-dev.txt` ya incluye pandas.

## Uso

```python
from tagframe.analisis import leer_limites, resumen
from tagframe.cargador import Cargador
from tagframe.fuentes import FuenteCSV

# CSV crudo -> DataFrame limpio, con el balance de lo que se descartó
resultado = Cargador(FuenteCSV("data/sensores_planta.csv")).cargar()
print(resultado.filas_entrada, resultado.filas_salida, resultado.porcentaje_descartado)

# DataFrame limpio -> resumen por tag (mismos números que tagstats)
print(resumen(resultado.df, leer_limites("data/limites.csv")))
```

```
   tag unidad  muestras  minimo  maximo  promedio  desvio  alarmas  porcentaje_alarmas
FT-310   m3/h       144   67.30   95.30     82.07    8.59        0                0.00
LT-115      %       144   27.10   81.40     60.26   16.97        0                0.00
MT-501      A       144   25.40   51.30     31.57    4.26        3                2.08
PT-204    bar       144    2.19    5.28      4.66    0.65        9                6.25
TT-101   degC       144   73.70  102.10     80.24    7.27       16               11.11
VT-501   mm/s       144    1.59    7.95      3.74    1.42        6                4.17
```

Sobre `data/sensores_sucios.csv` entran 11 filas y salen 6 (45.5% descartado).

## Las cinco reglas de limpieza

Cada una corresponde a una fila real de `data/sensores_sucios.csv`:

| # | Regla | Fila que la motiva |
|---|---|---|
| 1 | `valor` a numérico con `errors="coerce"` (tolera decimal con coma) | `TT-101,N/A` y `TT-101,` (vacío) |
| 2 | `±inf` → `NaN` **antes** de `dropna` | `PT-204,inf,bar,Uncertain` |
| 3 | `timestamp` a fecha ISO con `errors="coerce"` | `24/08/2026 06:20` |
| 4 | descartar `tag` vacío (`""`, no `NaN`) y `NaT`/`NaN` | `2026-08-24T06:25:00,,80.60` |
| 5 | `drop_duplicates(subset=["timestamp","tag"], keep="last")` | ninguna: se prueba inyectando el duplicado |

La fila corrida (`4,82` sin comillas, 6 campos para 5 columnas) no la agarra
ninguna regla: la descarta el parser de pandas antes de llegar al `Limpiador`.
`FuenteCSV` la cuenta en `filas_corridas`, y con `FuenteCSV(..., estricto=True)`
corta con `FilaCorridaError` en vez de saltearla.

## Qué tema vive en cada archivo

| Archivo | Tema de la semana |
|---|---|
| `fuentes.py` | **Herencia**: ABC `FuenteDeDatos` → `FuenteCSV`. Deja lugar a un `FuenteSQL` sin tocar nada más |
| `limpieza.py` | **Properties**: `ResultadoLimpieza.filas_descartadas` y `.porcentaje_descartado` se calculan, no se guardan |
| `cargador.py` | **Composición**: el `Cargador` *tiene* una fuente y un limpiador; no *es* ninguno |
| `analisis.py` | **groupby + merge**: stats por tag y conteo de alarmas contra `limites.csv` |

## Decisiones propias de tagframe

- **Leer todo como texto** (`dtype=str`, `keep_default_na=False`): si pandas
  infiere tipos, `"N/A"` ya llega como `NaN` y la limpieza deja de ser explícita.
  La fuente lee; el limpiador decide qué es nulo.
- **`ddof=0`** en el desvío: poblacional, como el `pstdev` de Semana 1. El
  default de pandas es `ddof=1` y no coincide con la tabla de arriba.
- **Un solo dato → desvío `0.0`**, no `NaN`: no hay dispersión que describir, y
  un `NaN` contagiaría sumas y reportes.
- **Tag sin límite → 0 alarmas**: el `merge` es `how="left"`, así que `minimo` y
  `maximo` quedan en `NaN` y la comparación da `False`. "Sin límite, no hay
  alarma", igual que Semana 1.
- **Tolerar la fila corrida por defecto** (al revés que `tagstats`, que corta):
  el parser es de pandas y la fila mala nunca llega al código propio, así que no
  se puede informar *qué* fila ni *qué* sobraba. Lo único honesto es contarla; el
  corte queda como opción explícita (`estricto=True`).
