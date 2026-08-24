# Conceptos aplicados en `tagstats`

Semana 1 del roadmap. Qué se usó, por qué y dónde mirarlo en el código.

---

## 1. El problema y la forma de la solución

El entregable es un CLI que lee un CSV de lecturas de tags y devuelve mínimo,
máximo, promedio y conteo de alarmas. Podría resolverse en 40 líneas dentro de
un solo archivo. No se hizo así, y esa es la primera decisión: el proyecto está
partido en cinco módulos, cada uno con **una** responsabilidad.

| Módulo | Responde a |
|---|---|
| `modelos.py` | ¿Qué *es* un dato? |
| `lectura.py` | ¿Cómo *entra*? |
| `estadisticas.py` | ¿Qué se *calcula*? |
| `reporte.py` | ¿Cómo *sale*? |
| `cli.py` | ¿Cómo lo *pide* el usuario? |

El motivo es práctico, no estético: cada pieza se prueba sola. `estadisticas.py`
no sabe qué es un CSV, así que sus pruebas no tocan el disco y corren en
milisegundos. Cuando mañana los datos vengan de una consulta SQL en vez de un
archivo (semana 3 del roadmap), se cambia `lectura.py` y el resto no se entera.

El flujo completo es una cadena: **leer → filtrar → agrupar → calcular →
formatear**.

---

## 2. Entorno: ruff, black y VS Code

**black** es un formateador con una sola opinión y casi ningún parámetro. Su
valor no es el estilo que elige sino que elimina la discusión: nadie revisa un PR
comentando dónde va un salto de línea, porque no hay decisión que tomar. Se
configuró en `pyproject.toml` con `line-length = 100`.

**ruff** es el linter: encuentra imports sin usar, variables muertas, nombres
indefinidos, ordena imports y sugiere sintaxis moderna. Es la misma familia de
reglas de flake8 + isort + pyupgrade, escrito en Rust, y corre en milisegundos
sobre todo el proyecto. Las reglas seleccionadas están en `pyproject.toml`
(`select = ["E", "F", "W", "I", "UP", "B", "C4", "SIM", "RUF"]`).

Lo importante es que **los dos comparten `line-length = 100`**. Si no coinciden,
black corta a 88 y ruff se queja de las líneas de 89: dos herramientas peleándose
por el mismo archivo.

`.vscode/settings.json` los conecta al editor: black formatea al guardar, ruff
arregla y ordena imports al guardar, y pytest queda habilitado en la pestaña
Testing. `.vscode/` **no** está en el `.gitignore` a propósito: es configuración
del proyecto, no del programador, y conviene que viaje con el repo para que todos
formateen igual.

> En este entorno no se creó `.venv` (se pidió omitirlo) y ruff/black no están
> instalados, así que `scripts/verificar.ps1` los saltea con un aviso. En un
> proyecto real, el venv es el primer paso: aísla las versiones de las
> dependencias del proyecto de las del sistema, y `requirements-dev.txt` las
> vuelve reproducibles en otra máquina.

---

## 3. Git: commits atómicos y Conventional Commits

Un commit **atómico** contiene un cambio completo y coherente: la funcionalidad
y sus pruebas juntas. La prueba de fuego es que se pueda revertir solo sin
romper nada. Por eso los tests de `estadisticas.py` viajan en el mismo commit
que `estadisticas.py`, no en un `test: agregar pruebas` al final.

**Conventional Commits** es la convención `tipo(alcance): descripción`
(`feat`, `fix`, `docs`, `test`, `chore`, `refactor`). Sirve para leer el
historial de un vistazo, pero sobre todo permite que una herramienta genere el
CHANGELOG y decida la próxima versión: `feat` sube la minor, `fix` la patch,
`BREAKING CHANGE` la major.

El trabajo se hizo en una rama (`feat/estadisticas-cli`) y se integró a `main`
con `git merge --no-ff`. El `--no-ff` fuerza un commit de merge aunque no haga
falta: en el grafo queda visible qué commits formaron parte de la misma unidad
de trabajo, cosa que un fast-forward borra.

El `.gitignore` deja afuera lo que se **regenera** (`__pycache__/`, `.venv/`,
`.pytest_cache/`, `.ruff_cache/`) y lo que es **local** (salidas del CLI). La
regla: si borrarlo no duele porque se vuelve a crear, no va al repo.

---

## 4. Python idiomático

### Dataclasses en vez de diccionarios

`modelos.py` define `Lectura`, `Limite` y `Estadisticas` como dataclasses en vez
de pasar `dict` sueltos. Un `dict` acepta cualquier clave: `lectura["valorr"]`
falla recién en producción, y `lectura.get("valor")` devuelve `None` en silencio.
Con una dataclass, el editor autocompleta y el error aparece al escribir.

```python
@dataclass(frozen=True, slots=True)
class Lectura:
    timestamp: datetime
    tag: str
    valor: float
```

`frozen=True` la hace inmutable: una lectura histórica no se corrige "en el
aire", y si algo intenta hacerlo, explota donde está el bug. `slots=True` saca
el `__dict__` por instancia: menos memoria y atributos más rápidos, que importa
cuando el CSV trae cientos de miles de filas.

### Generadores (`yield`): el corazón del diseño

`leer_lecturas()` no devuelve una lista: es un generador que produce una
`Lectura` por vez. Un export de historiador de un mes puede tener millones de
filas; `list(...)` significaría cargarlas todas en RAM para después descartar el
90 % con un filtro.

```python
for numero_fila, fila in enumerate(lector, start=2):
    yield parsear_fila(fila, numero_fila)
```

`filtrar()` es otro generador que **consume** al primero, y `resumir()` es el
que finalmente los consume a ambos. El archivo se recorre **una sola vez** y la
memoria usada no depende del tamaño del archivo. Ese `start=2` es un detalle
chico con mucho retorno: la fila 1 es la cabecera, así que el número que reporta
un error coincide con el que muestra el editor al abrir el CSV.

### Comprehensions

Se usan donde expresan "transformar/filtrar esta colección", no como reemplazo
universal del `for`:

```python
valores = [lectura.valor for lectura in lecturas]              # list
unidades = {lectura.unidad for lectura in lecturas}            # set: detecta unidades mezcladas
alarmas = sum(1 for v in valores if limite.en_alarma(v))       # expresión generadora: no arma la lista
```

La tercera es la más interesante: `sum(1 for ...)` cuenta sin construir ninguna
lista intermedia. Y en `reporte.py` hay una **dict comprehension** que redondea
solo en la salida, dejando los cálculos en precisión completa.

Regla que se siguió: si la comprehension necesita un `if/else` anidado o pasa de
una línea legible, vuelve a ser un `for`. `agrupar_por_tag()` es un `for`
explícito por eso mismo.

### Unpacking

Aparece en tres formas distintas:

```python
inicio, fin, delta = perfil.excursion                    # tupla → variables
ancho_tag = max(len("TAG"), *(len(i.tag) for i in resumen))  # * expande argumentos
parsear_fila({**FILA_OK, "valor": "N/A"}, 2)             # ** copia un dict cambiando una clave
```

El `max(piso, *anchos)` calcula el ancho de la columna tomando el encabezado
como mínimo. El `{**FILA_OK, campo: valor}` en las pruebas construye el caso
malo cambiando **un** campo del caso bueno: el test dice exactamente qué es lo
distinto.

### f-strings con formato dinámico

Las f-strings no son solo interpolación; el mini-lenguaje de formato es lo que
hace que la tabla se alinee sola:

```python
f"{item.tag:<{ancho_tag}}"        # alinear a izquierda, ancho calculado en runtime
f"{valor:>{ancho}{formato}}"      # ancho Y formato (.2f / d) tomados de una constante
f"valor invalido: {texto!r}"      # !r muestra las comillas: se ve si vino ' 78 ' con espacios
```

El `!r` en los mensajes de error es un hábito que ahorra sesiones enteras de
depuración: distingue `78` de `"78 "` de `""`.

### Biblioteca estándar antes que dependencias

`csv`, `argparse`, `statistics`, `pathlib`, `dataclasses`, `collections`. Cero
dependencias de runtime significa cero problemas de instalación en la máquina de
planta. Pandas hubiera resuelto el cálculo en tres líneas, pero para 864 filas
es traer 50 MB de dependencia para no aprender qué pasa abajo, que es
justamente el objetivo de la semana 1.

Detalles de la estándar que valen la pena:

- `csv.DictReader(archivo, restkey=...)` avisa cuando una fila trae columnas de
  más — el caso real de un decimal escrito `4,82` sin comillas, que corre todas
  las columnas y contamina los datos **en silencio**.
- `encoding="utf-8-sig"` descarta el BOM que Excel agrega al guardar como CSV;
  sin eso la primera columna se llama `﻿timestamp` y no matchea nunca.
- `newline=""` al abrir archivos CSV: sin eso, en Windows se escriben `\r\r\n`.
- `math.isfinite()`: `float("inf")` y `float("nan")` no lanzan excepción pero
  envenenan cualquier `min`/`max`/`promedio` posterior.
- `defaultdict(list)` para agrupar, convertido a `dict` antes de devolverlo: un
  `defaultdict` que escapa del módulo crea claves fantasma con solo consultarlo.

---

## 5. Pruebas con pytest

70 pruebas, todas en `tests/`. Las técnicas usadas:

- **`assert` pelado.** pytest reescribe el assert y muestra los valores de cada
  lado. No hace falta `assertEqual`.
- **Fixtures** (`conftest.py`): datos y archivos de prueba reutilizables. Las que
  escriben archivos usan `tmp_path`, un directorio temporal que pytest crea y
  borra por prueba, así los tests no dependen de `data/` ni se pisan entre sí.
- **`@pytest.mark.parametrize`**: un solo test cubre los bordes del límite
  (`59.9, 60.0, 78.0, 95.0, 95.1`). Cada caso se reporta por separado, así el
  fallo dice qué valor rompió.
- **`pytest.raises`** con `match=`: no alcanza con que falle, tiene que fallar
  *por el motivo correcto* y con un mensaje útil.
- **`capsys`**: captura stdout y stderr para probar el CLI de punta a punta sin
  lanzar un subproceso. Por eso `main()` recibe `argv` y **devuelve** un int en
  vez de llamar a `sys.exit()`: así es testeable.
- **`pytest.approx`**: los flotantes no se comparan con `==`.

Los números de las fixtures están elegidos para poder verificarlos a mano:
70, 80 y 99 dan promedio 83 exacto. Un test cuyo valor esperado salió de correr
el código no prueba nada.

---

## 6. Dos decisiones de diseño que no son de sintaxis

**El callback `al_descartar`.** ¿Qué hace el lector con una fila corrupta:
cortar o saltearla? La respuesta correcta depende de quién pregunta, así que la
política no está cableada: si no se pasa nada, corta con `FilaInvalidaError`; si
se le pasa una función, saltea y le entrega el error. El CLI le pasa
`descartes.append` cuando está `--tolerante` — el método de la lista *es* el
callback, sin lambda de por medio. Por defecto **falla rápido**: un promedio
calculado sobre datos silenciosamente descartados es peor que un error.

**stdout, stderr y códigos de salida.** Los datos van a stdout y los avisos a
stderr, así `tagstats datos.csv -f json > salida.json` produce un JSON limpio y
los avisos igual se ven en pantalla. Y el CLI devuelve 0 / 1 / 2 según qué pasó,
que es lo que mira un script o un pipeline para decidir si sigue.

---

## 7. Qué queda para las próximas semanas

Con más tiempo: percentiles y detección de valores atípicos, límites con
histéresis y tiempo mínimo en alarma (un DCS no alarma por una muestra suelta),
`--paralelo` para varios archivos, y un GitHub Action que corra
`scripts/verificar.ps1` en cada push. También `pip install -e .`, que habilita
el comando `tagstats` directo en vez de `python -m tagstats` — ya está declarado
en `[project.scripts]`.
