# Pasos: cómo se armó esto, en orden

El orden real en que se hicieron las cosas, explicado simple. Cada paso dice
**qué** se hizo y **por qué en ese momento** y no antes o después.

Si querés rehacerlo vos mismo, se puede seguir de arriba a abajo.

---

## Fase 0 — Mirar antes de tocar (5 minutos)

### 1. Preguntarle a la máquina qué tiene instalado

```powershell
python --version; git --version; python -m pytest --version; ruff --version; black --version
```

*Por qué primero:* resultó que **ruff y black no estaban instalados**. Enterarse
ahora vale 5 minutos; enterarse a mitad del proyecto, cuando ya escribiste 500
líneas con un estilo que después el formateador te va a cambiar entero, vale una
tarde.

### 2. Crear las carpetas vacías

`data/ docs/ scripts/ tagstats/ tests/ .vscode/`

*Por qué:* decidir dónde va cada cosa **antes** de tener cosas. Si empezás con
todo en un solo archivo, mudarlo después es una hora de imports rotos.

---

## Fase 1 — Las reglas antes del código

Nada de esto es "el programa". Es el molde donde el programa va a entrar.

### 3. `.gitignore`

*Por qué primero de todo:* la regla es simple — **si se puede regenerar, no va al
repo**. Si lo escribís después del primer `git add .`, ya subiste `__pycache__/`
y sacarlo del historial es un dolor de cabeza.

### 4. `pyproject.toml`

Config de ruff (linter), black (formateador) y pytest, todo en un solo archivo.

*Por qué:* acá se decide `line-length = 100` **una vez** y lo usan las dos
herramientas. Si black corta a 88 y ruff se queja de las de 89, las dos se pelean
por el mismo archivo para siempre.

Un detalle que evita un dolor clásico: `pythonpath = ["."]`. Es lo que hace que
`import tagstats` funcione en las pruebas **sin instalar nada**.

### 5. `requirements-dev.txt` y `.vscode/`

La lista de herramientas de desarrollo, y la config para que VS Code formatee al
guardar y encuentre las pruebas solo.

*Por qué `.vscode/` NO se ignora:* es config del **proyecto**, no tuya. Si viaja
con el repo, el que se sume mañana formatea igual que vos desde el minuto cero.

---

## Fase 2 — El código, de adentro hacia afuera

Regla de oro: **empezar por lo que no depende de nada**. Así, cuando escribís
cada archivo, todo lo que necesita ya existe.

```
modelos → lectura → estadisticas → reporte → cli
 (nada)   (modelos)   (modelos)    (stats)  (todos)
```

### 6. `tagstats/__init__.py`

Casi vacío: solo el nombre y la versión.

*Por qué:* convierte la carpeta en un paquete importable. Es el "ya existe algo"
que permite escribir la primera prueba.

### 7. `modelos.py` — **las cajas**

`Lectura` (una muestra), `Limite` (el rango permitido), `Estadisticas` (el
resultado).

*Por qué antes que nada:* es el vocabulario. Todo el resto del programa habla de
estas tres cosas. Si esto cambia después, cambia todo; si está bien pensado, el
resto sale casi solo.

*ELI5:* primero decidís qué forma tienen las piezas, después armás la máquina.

### 8. `lectura.py` — **el que abre el archivo**

Convierte filas de texto del CSV en `Lectura` de verdad, y avisa con detalle
cuando una fila está rota.

*Por qué acá:* necesita saber qué es una `Lectura` (paso 7), y nada más.

### 9. `estadisticas.py` — **la calculadora**

Agrupa por tag y saca min, max, promedio, desvío y alarmas.

*Por qué está separado del paso 8:* así **no sabe qué es un CSV**. Se puede
probar con listas hechas a mano, sin tocar el disco, y el día que los datos vengan
de una base SQL este archivo no se entera.

### 10. `reporte.py` — **el que lo escribe lindo**

El mismo resultado en tabla, JSON o CSV.

*Por qué separado también:* agregar un formato nuevo mañana no toca ni una línea
de la calculadora.

### 11. `cli.py` + `__main__.py` — **el mostrador de atención**

Los argumentos (`--tag`, `--formato`, `--tolerante`), los mensajes de error y el
código de salida.

*Por qué último:* es la capa que **usa todas las anteriores**. Se escribe cuando
ya hay algo que ofrecer.

*Truco importante:* `main()` recibe los argumentos como parámetro y **devuelve**
un número en vez de cortar el programa. Eso es lo que después permite probarlo
sin lanzar un proceso aparte. Decisión de 30 segundos, ahorra horas de tests.

---

## Fase 3 — Los datos, para tener con qué jugar

### 12. `scripts/generar_datos.py`

Un script que inventa 864 lecturas de 6 sensores con **semilla fija**.

*Por qué un script y no un CSV escrito a mano:* semilla fija = el archivo sale
**idéntico** todas las veces. Si lo regenerás, `git diff` no muestra nada. Con
datos al azar, cada corrida ensuciaría el repo.

*Por qué datos con "vida":* se le metieron dos excursiones de proceso y picos
aislados a propósito. Un CSV donde todo está perfecto no prueba nada: el conteo
de alarmas daría 0 y nunca sabrías si funciona.

### 13. `data/sensores_sucios.csv` — **escrito a mano, con maldad**

Doce filas con: un `N/A`, una celda vacía, un timestamp en otro formato, un tag
vacío, un `inf` y un decimal escrito `4,82`.

*Por qué a mano:* querés controlar **exactamente** qué tipo de mugre hay. Un
generador aleatorio no te da eso.

### 14. Volver al paso 8 a arreglar algo que recién apareció acá

El `4,82` sin comillas parte la fila en una columna de más: el programa leía la
unidad como `"82"` y **seguía andando como si nada**. Un dato corrupto que no
avisa es peor que un error.

Se agregó `restkey` en `lectura.py` para detectarlo y cortar.

*Por qué contarlo:* esto es lo normal. Escribir los datos hostiles **encuentra
bugs**. No es que el plan salió mal, es para lo que sirve el paso.

---

## Fase 4 — Las pruebas

### 15. `tests/test_smoke.py` — el "hola mundo"

Dos líneas: que 2+2 sea 4 y que el paquete se importe.

*Por qué esta primero:* si esta falla, el problema es el entorno (intérprete
equivocado, paquete no encontrado), no tu código. Es el fusible.

### 16. `tests/conftest.py` — los datos de prueba compartidos

CSV chiquitos que pytest crea y borra solo en una carpeta temporal.

*Por qué temporal y no `data/`:* las pruebas no pueden depender de un archivo que
mañana alguien edita. Y si dos pruebas escriben, no se pisan.

*Detalle que parece tontería:* los números son 70, 80 y 99, **porque el promedio
da 83 exacto** y lo podés verificar de cabeza. Un test cuyo resultado esperado lo
sacaste de correr el código no prueba nada: solo confirma que el código hace lo
que hace.

### 17. Una prueba por módulo, en el mismo orden que el paso 7 al 11

`test_modelos` → `test_lectura` → `test_estadisticas` → `test_reporte` → `test_cli`.

*Qué se prueba en cada una:* que funcione con datos buenos, **y qué pasa con los
malos** (archivo que no existe, CSV vacío, fila rota, límite invertido). La mitad
de los tests son del segundo tipo. Ahí viven los bugs.

> Nota honesta: acá los tests se escribieron **después** del código. Con TDD sería
> al revés — test primero, verlo fallar, después el código. Para la semana 1 está
> bien así; vale saber que el orden "puro" es el otro.

### 18. Correr `python -m pytest` y encontrar una falla

Falló un test del filtro por fecha: esperaba 2 resultados y daban 3.

**Se arregló el test, no el código** — el que había contado mal era yo. Antes de
tocar nada, siempre la misma pregunta: *¿quién está equivocado, el programa o mi
expectativa?*

---

## Fase 5 — Usarlo como lo usaría una persona

### 19. Correr el CLI de verdad, contra los datos de verdad

```powershell
python -m tagstats data/sensores_planta.csv -l data/limites.csv
python -m tagstats data/sensores_sucios.csv --tolerante
```

*Por qué, si los tests ya pasan:* los tests prueban las piezas. Recién acá ves si
la tabla se lee bien, si el mensaje de error sirve para algo y si los números
tienen sentido físico. Salió 11 % de alarmas en TT-101, coherente con la
excursión que se había puesto a propósito. Cierra.

### 20. `scripts/verificar.ps1` y `scripts/demo.ps1`

Un comando que corre lint + formato + pruebas, y otro que muestra los casos de
uso.

*Por qué:* lo que no está en un script se olvida. Y `verificar.ps1` avisa y
saltea las herramientas que no están instaladas en vez de explotar.

---

## Fase 6 — Documentar

### 21. `README.md` y `docs/CONCEPTOS.md`

El README dice **cómo se usa**. CONCEPTOS dice **por qué está hecho así**.

*Por qué al final:* recién ahora sabés qué construiste de verdad. Un README
escrito al principio siempre miente un poco.

---

## Fase 7 — El historial de Git, al final y a propósito

### 22. `git init` recién acá

*Por qué no al principio:* porque el orden en que **escribís** el código no es el
orden en que se **lee**. Un historial armado sobre la marcha queda lleno de
"arreglo lo de antes", "ahora sí". Con el proyecto terminado se puede contar la
historia limpia.

(En un equipo se commitea desde el minuto uno, sí. Pero el objetivo de la
checklist era commits atómicos y prolijos, y así salen prolijos.)

### 23. Agrupar los archivos en 10 commits, cada uno con su prueba adentro

```
chore: configurar entorno con ruff, black y pytest
test:  agregar prueba de humo del paquete
feat(datos): generar datasets de ejemplo de sensores
feat(modelos): modelar lecturas, limites y estadisticas
...
docs:  documentar uso del cli y conceptos aplicados
```

*Qué es "atómico":* un cambio completo, con su test al lado. La prueba de fuego:
**¿se puede revertir solo sin romper nada?** Por eso `test_estadisticas.py` viaja
con `estadisticas.py`, y no todo junto en un `test: agregar pruebas` al final.

*Por qué los prefijos `feat:` / `fix:` / `docs:`:* se lee el historial de un
vistazo, y una herramienta puede generar el changelog y decidir la próxima
versión sola.

### 24. Hacer el trabajo en una rama y unirla con `--no-ff`

```powershell
git checkout -b feat/estadisticas-cli   # ... los commits del medio ...
git checkout main
git merge --no-ff feat/estadisticas-cli
```

*Por qué `--no-ff`:* obliga a dejar un commit de unión aunque no haga falta. En
el gráfico queda a la vista **qué commits fueron parte del mismo trabajo**. Sin
eso, quedan sueltos en una fila y se pierde la agrupación.

### 25. Verificar que **cada** commit quede en verde

Se sacó una copia temporal de cada commit y se corrieron las pruebas ahí.

*Por qué:* que el final funcione no significa que los pasos intermedios
funcionen. Un commit roto en el medio rompe cualquier `git bisect` futuro.
Resultado: los 10 en verde (el primero es solo config, no tiene pruebas todavía).

### 26. Chequeos finales

Ninguna línea de más de 100 caracteres, todo compila, `git status` limpio.

---

## La receta corta

1. Fijarse qué hay instalado.
2. Config primero (`.gitignore`, `pyproject.toml`): las reglas antes del código.
3. Código de adentro hacia afuera: modelos → lectura → cálculo → salida → CLI.
4. Datos de ejemplo, **incluyendo datos rotos a propósito**.
5. Pruebas: primero el "hola mundo", después una por módulo, la mitad para los
   casos feos.
6. Usarlo a mano como lo usaría una persona.
7. Documentar.
8. Armar el historial de Git limpio y verificar commit por commit.

**El hilo que une todo:** cada paso se hace cuando lo que necesita ya existe, y
lo que puede fallar se hace fallar a propósito, temprano.
