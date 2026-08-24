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
tests/              70 pruebas de pytest
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

## Decisiones que vale la pena conocer

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
