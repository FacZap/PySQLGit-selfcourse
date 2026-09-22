-- =====================================================================
-- 04_verificar.sql  -  Semana 4  -  ESQUELETO PARA COMPLETAR
--
-- Responsabilidad: demostrar que la carga salio bien. No con la sensacion de
-- que "no tiro error", sino comparando contra numeros que ya conocemos.
--
-- Como correrlo, parado en la raiz del repo:
--     psql -U postgres -h localhost -d industrial -f sql/04_verificar.sql
--
-- Este archivo es el equivalente de tests/ para la parte SQL. Semana 4 no
-- tiene pytest contra la base (eso llega en Semana 6, con psycopg2): por
-- ahora el "test" sos vos mirando si el numero coincide.
-- =====================================================================


-- =====================================================================
-- POR QUE TENEMOS ORACULO
--
-- La gracia de este proyecto es que las respuestas correctas YA EXISTEN. El
-- mismo dataset ya fue procesado dos veces en Python: por tagstats (Semana 1,
-- stdlib) y por tagframe (Semana 3, pandas), y los resultados estan escritos
-- en README.md:55-64.
--
-- Asi que no estas verificando "me parece que dio bien". Estas verificando
-- contra una tabla de numeros que tiene que dar IGUAL. Si SQL y Python
-- difieren, uno de los dos esta mal, y averiguar cual es el ejercicio.
--
-- La tabla, para tenerla a mano (README.md:57-64):
--
--   TAG     UNIDAD  MUESTRAS    MIN      MAX   PROMEDIO  DESVIO  ALARMAS
--   FT-310  m3/h       144     67.30    95.30    82.07    8.59      0
--   LT-115  %          144     27.10    81.40    60.26   16.97      0
--   MT-501  A          144     25.40    51.30    31.57    4.26      3
--   PT-204  bar        144      2.19     5.28     4.66    0.65      9
--   TT-101  degC       144     73.70   102.10    80.24    7.27     16
--   VT-501  mm/s       144      1.59     7.95     3.74    1.42      6
--
--   TOTAL: 6 tags | 864 muestras | 34 alarmas
-- =====================================================================


-- ---------------------------------------------------------------------
-- Chequeo 1  -  cantidades basicas
--
-- TODO: escribi las consultas que cuenten filas en tags, limites y readings.
--       Esperado: 6, 6 y 864.
--
--       Pista de presentacion: podes hacer las tres de un saque con UNION ALL
--       y una columna de etiqueta, para leer una sola tabla de salida en vez
--       de tres. Algo con la forma:
--           SELECT 'tags' AS tabla, COUNT(*) FROM tags
--           UNION ALL
--           SELECT 'limites', COUNT(*) FROM limites
--           ...
--       No es obligatorio, pero acostumbrarte a UNION ALL ahora te sirve.
-- ---------------------------------------------------------------------

-- SELECT 'tags' AS tabla, COUNT(*) FROM tags
-- SELECT 'limites' AS tabla, COUNT(*) FROM limites
-- SELECT 'lecturas' AS tabla, COUNT(*) FROM readings

SELECT 'tags' AS tabla, COUNT(*) AS cantidad FROM tags
UNION ALL
SELECT 'limites', COUNT(*) FROM limites
UNION ALL
SELECT 'lecturas', COUNT(*) FROM readings;

-- ---------------------------------------------------------------------
-- Chequeo 2  -  integridad referencial
--
-- TODO: escribi una consulta que busque lecturas cuyo tag_id NO exista en
--       tags. Esperado: CERO filas.
--       Pista: LEFT JOIN de readings contra tags, filtrando por
--              t.tag_id IS NULL. Ese patron (LEFT JOIN + IS NULL) es la
--              forma clasica de preguntar "que hay en A que no este en B", y
--              lo vas a reusar toda la vida.
--
-- Nota honesta: si pusiste bien la FOREIGN KEY en 01_esquema.sql, este
-- chequeo es IMPOSIBLE que falle, porque el motor no te dejaria insertar esa
-- fila ni queriendo. Lo escribis igual por dos motivos: para comprobar con
-- tus ojos que la FK esta haciendo su trabajo, y para aprender el patron
-- antes de necesitarlo en una base que no disenaste vos.
--
-- El chequeo que SI puede fallar es el de al lado:
--
-- TODO: busca tags que no tengan ninguna lectura (LEFT JOIN al reves).
--       Con este dataset esperado es cero, porque los 6 tags midieron. Pero
--       ninguna restriccion garantiza eso: un sensor puede existir en el
--       catalogo y no haber reportado nada. Es un hueco real que la base no
--       te avisa.
-- ---------------------------------------------------------------------

-- prueba básica
SELECT r.tag_id, t.nombre
FROM readings as r
LEFT JOIN tags as t
on t.tag_id = r.tag_id
LIMIT 5;

-- lecturas cuyo tag_id NO exista en tags (imposible, debería dar 0)
SELECT r.tag_id, t.nombre
FROM readings as r
LEFT JOIN tags as t
on t.tag_id = r.tag_id
WHERE t.tag_id IS NULL;

-- tags que no tengan ninguna lectura (podría pasar: comms error, data errors,
-- instrumentos desconectados, etc)
--
-- CORREGIDO (revision): estaba WHERE r.valor IS NULL, ya lo cambiaste por
--   WHERE r.tag_id IS NULL. Dejo el por que, que es lo que vale:
--
--   valor NO era una eleccion neutra. Daba el resultado correcto, pero de
--   casualidad. valor es
--   NUMERIC NOT NULL en 01_esquema.sql, asi que la unica manera de que salga
--   NULL es que el LEFT JOIN no haya encontrado pareja. O sea: la consulta
--   funciona apoyandose en una propiedad de la que no deberia depender.
--
--   Por que importa. El idioma LEFT JOIN + IS NULL contesta "que hay en A que
--   no este en B" SOLO si testeas una columna que no puede ser NULL en B. Las
--   dos candidatas seguras son la clave del JOIN (r.tag_id) o la PK
--   (r.reading_id); cualquier otra columna te ata a su nullability de hoy.
--   El dia que valor pase a ser NULLABLE -- un sensor que reporta la marca de
--   tiempo pero no el valor, que es un caso real -- esta consulta pasa a
--   contestar otra pregunta: "tags sin lecturas O con lecturas sin valor".
--   Y no te vas a enterar, porque no va a fallar: va a mentir. Es exactamente
--   el bug que la guia describe con el stddev, el que no rompe nada.
SELECT t.nombre, r.tag_id
FROM tags as t
LEFT JOIN readings as r
on t.tag_id = r.tag_id
WHERE r.tag_id IS NULL;

-- NOTA (revision), menor, vale para las dos consultas de arriba: la columna
--   que traes del lado que NO matcheo siempre va a salir NULL, por definicion
--   del LEFT JOIN + IS NULL (t.nombre en una, r.tag_id en la otra). No esta
--   mal, pero es una columna de NULLs. Si el objetivo es "decime QUE tag no
--   tiene lecturas", lo util es traer t.tag_id y t.nombre, los dos del lado
--   que si existe.

-- ---------------------------------------------------------------------
-- Chequeo 3  -  cobertura temporal
--
-- TODO: por cada tag, mostra la primera y la ultima lectura y cuantas hay.
--       Esperado: los 6 tags arrancan en 2026-08-24 06:00:00 y tienen 144
--       muestras cada uno.
--       Pista: MIN() y MAX() tambien funcionan sobre TIMESTAMP, no solo
--       sobre numeros.
--
-- Por que este chequeo existe: los COUNT del chequeo 1 pueden dar perfecto
-- estando todo mal. 864 filas donde un tag tiene 200 y otro 88 suma igual
-- 864. Contar el total no prueba nada sobre la distribucion.
-- ---------------------------------------------------------------------


-- MAL
-- SELECT * FROM readings
-- where MIN("timestamp");
--
-- NOTA (revision): bien visto que esta mal, y vale saber POR QUE. WHERE se
--   evalua fila por fila, ANTES de que exista cualquier agregacion: cuando
--   Postgres esta mirando una fila todavia no calculo ningun MIN, asi que no
--   hay nada contra que comparar. La clausula que filtra DESPUES de agregar
--   es HAVING. Conviene memorizar el par junto: WHERE antes, HAVING despues.


-- BUG (revision): esta consulta no contesta lo que pide el chequeo 3.
--
--   Lo pedido:  por cada tag, la primera y la ultima lectura, y cuantas hay.
--   Lo que da:  la primera lectura de TODA la tabla, sin separar por tag.
--
--   Faltan las tres cosas que hacen al chequeo: no hay GROUP BY, no hay
--   COUNT y no hay MAX. Y eso es justo lo que explica el comentario de mas
--   arriba: el total de 864 puede dar perfecto con un tag en 200 y otro en
--   88. Para detectar eso hay que mirar la DISTRIBUCION, y la distribucion
--   solo aparece agrupando.
--
--   La forma que falta es un GROUP BY por tag con tres agregaciones en la
--   misma fila: COUNT(*), MIN("timestamp") y MAX("timestamp"), con el JOIN a
--   tags para ver el nombre en vez del tag_id. Es la misma estructura que el
--   chequeo 4 que esta resuelto mas abajo: mirala si te trabas, pero esta
--   escribila vos.
--
--   Detalle aparte: SELECT * te trae reading_id y calidad, que no aportan
--   nada aca. Ademas, cuando agrupes no vas a poder pedir * .

SELECT *
FROM readings
WHERE "timestamp" = (
    SELECT MIN("timestamp")
    FROM readings
);

-- alternativa
/* SELECT *
FROM readings
ORDER BY "timestamp" ASC
LIMIT 1; */
--
-- BUG (revision): esa "alternativa" NO es equivalente a la de arriba, y la
--   diferencia esta viva en ESTOS datos, no en un caso de laboratorio.
--
--   La subconsulta devuelve TODAS las filas empatadas en el minimo.
--   El ORDER BY + LIMIT 1 devuelve UNA, y cual, no te lo promete nadie: sin
--   un criterio de desempate en el ORDER BY, Postgres elige la que le quede
--   comoda y puede cambiar de corrida en corrida.
--
--   Aca los 6 tags arrancan todos en 2026-08-24 06:00:00, o sea que hay 6
--   filas empatadas en el minimo: la de arriba devuelve 6 filas, la
--   "alternativa" devuelve 1. Contestan preguntas distintas.
--
--   "El minimo" y "una fila que tiene el minimo" solo coinciden cuando no
--   hay empates. Casi siempre hay empates.

-- ---------------------------------------------------------------------
-- Chequeo 4  -  EL importante: reproducir la tabla del README en SQL
--
-- TODO: escribi UNA consulta que devuelva, por tag:
--           nombre, unidad, muestras, minimo, maximo, promedio, desvio
--       ordenada por nombre, y compara fila por fila contra la tabla de
--       arriba.
--
--       Pista 1: es un JOIN de readings con tags + GROUP BY.
--       Pista 2: las agregaciones que necesitas son COUNT, MIN, MAX, AVG y
--                una funcion de desvio (segui leyendo, hay trampa).
--       Pista 3: para comparar contra el README te conviene redondear a dos
--                decimales con ROUND(..., 2). Ojo: en Postgres ROUND con dos
--                argumentos quiere NUMERIC; sobre un AVG que devolvio DOUBLE
--                PRECISION tenes que castear.
--
-- ***** LA TRAMPA DEL DESVIO - lee esto antes de escribir la consulta *****
--
--   Postgres te da DOS funciones de desvio estandar y NO son la misma:
--
--       stddev_samp()  -> desvio MUESTRAL   (divide por n-1)
--       stddev_pop()   -> desvio POBLACIONAL (divide por n)
--
--   Y stddev(), a secas, es alias de stddev_samp(). O sea: el default de
--   Postgres es el MUESTRAL.
--
--   Pero este proyecto usa el POBLACIONAL en todos lados: tagstats usa
--   pstdev (Semana 1) y tagframe usa .std(ddof=0) con un comentario que dice
--   exactamente esto (tagframe/analisis.py, el bloque del groupby).
--
--   Entonces: si escribis stddev() te va a dar PARECIDO pero distinto que el
--   README, y con 144 muestras la diferencia es tan chica que se puede pasar
--   por alto. Ese es justo el tipo de bug que hay que aprender a cazar: el
--   que no rompe nada, solo miente un poquito.
--
--   TODO: usa la que corresponde, y deja un comentario al lado diciendo por
--         que. Si tenes 30 segundos, corre las dos y mira la diferencia con
--         tus propios ojos: entender por que n-1 no es lo mismo que n vale
--         mas que memorizar cual usar.
--
-- ***** SEGUNDA DIFERENCIA, mas sutil, sobre la unidad *****
--
--   En Python la unidad sale de las LECTURAS, y si un tag mezclara unidades
--   el resumen lo muestra como "bar/psi" para que se vea el problema
--   (tagframe/analisis.py). En tu esquema la unidad vive en tags, una sola
--   vez, asi que esa mezcla es imposible por construccion.
--
--   Las dos decisiones son defendibles y dan lo mismo con estos datos. Pero
--   son decisiones DISTINTAS, y conviene que sepas que las tomaste: el
--   esquema previene el problema, el codigo Python lo detecta. Prevenir es
--   mejor cuando podes; detectar es lo que te queda cuando el dato ya vino.
-- ---------------------------------------------------------------------

-- Resuelto en la revision (esta la escribi yo; las otras del archivo son tuyas).

SELECT
    t.nombre                      AS tag,
    t.unidad,
    COUNT(*)                      AS muestras,
    ROUND(MIN(r.valor), 2)        AS minimo,
    ROUND(MAX(r.valor), 2)        AS maximo,
    ROUND(AVG(r.valor), 2)        AS promedio,
    ROUND(stddev_pop(r.valor), 2) AS desvio
        -- stddev_pop y NO stddev(): stddev() es alias de stddev_samp(), que
        -- divide por n-1. Este proyecto usa el POBLACIONAL en los dos motores
        -- Python (pstdev en tagstats, .std(ddof=0) en tagframe), asi que para
        -- que la comparacion contra el README signifique algo, tiene que ser
        -- la misma funcion de los tres lados.
FROM tags AS t
JOIN readings AS r ON r.tag_id = t.tag_id
GROUP BY t.tag_id, t.nombre, t.unidad
ORDER BY t.nombre;

-- Tres decisiones que tomo esa consulta, por si te las preguntas despues:
--
-- 1. JOIN y no LEFT JOIN. Un tag sin lecturas no tiene resumen que mostrar, y
--    el chequeo 2 ya se ocupa de detectarlo. Pero si algun dia lo cambias a
--    LEFT JOIN, ojo con la trampa: COUNT(*) le daria 1 a un tag sin lecturas,
--    porque cuenta la fila de NULLs que fabrica el propio LEFT JOIN. Ahi hay
--    que usar COUNT(r.reading_id), que ignora NULLs y da 0. COUNT(*) y
--    COUNT(columna) no son sinonimos, y esta es LA situacion donde se nota.
--
-- 2. ROUND sin castear. La Pista 3 de arriba avisa que ROUND(x, 2) pide
--    NUMERIC y que sobre un AVG que devolvio DOUBLE PRECISION hay que
--    castear. Aca no hizo falta, y es consecuencia directa de una decision
--    tuya en 01_esquema.sql: declaraste valor como NUMERIC, asi que MIN, MAX,
--    AVG y stddev_pop ya devuelven NUMERIC. Si hubieras puesto REAL, cada
--    ROUND llevaria un ::numeric colgando. Esa es la clase de costo que una
--    eleccion de tipo te cobra tres archivos mas adelante.
--
-- 3. GROUP BY con las tres columnas. Postgres aceptaria GROUP BY t.tag_id a
--    secas, porque tag_id es la PK de tags y nombre y unidad dependen
--    funcionalmente de ella. Las puse explicitas igual: se lee mejor y no
--    depende de una regla que otros motores no implementan.


-- Para ver la trampa del desvio con tus propios ojos, corre esto y compara
-- las dos columnas (son 30 segundos y no se olvida mas):
--
--     SELECT t.nombre,
--            ROUND(stddev_pop(r.valor),  4) AS poblacional_n,
--            ROUND(stddev_samp(r.valor), 4) AS muestral_n_menos_1
--     FROM tags AS t
--     JOIN readings AS r ON r.tag_id = t.tag_id
--     GROUP BY t.tag_id, t.nombre
--     ORDER BY t.nombre;
--
-- Lo interesante no es que difieran: es CUANTO. Redondeado a 2 decimales como
-- el README, FT-310 da 8.59 contra 8.62 y TT-101 da 7.27 contra 7.30 -- se
-- ve. Pero PT-204 da 0.65 con las DOS funciones. Si te hubiera tocado mirar
-- solo esa fila para "confirmar" que estaba bien, te ibas a dormir tranquilo
-- con la funcion equivocada.


-- ---------------------------------------------------------------------
-- Chequeo 5  -  las alarmas
--
-- TODO: conta las filas de la vista alarmas. Esperado: 34 en total.
--
-- TODO: conta alarmas por tag y compara contra la ultima columna del README:
--       FT-310=0, LT-115=0, MT-501=3, PT-204=9, TT-101=16, VT-501=6.
--
--       Pista importante: si agrupas la VISTA por tag, los tags con CERO
--       alarmas no van a aparecer en el resultado. No estan en la vista, asi
--       que no hay nada que agrupar. Para que FT-310 y LT-115 aparezcan con
--       un 0 tenes que partir de tags y hacer LEFT JOIN contra alarmas.
--
--       Esa diferencia entre "no aparece" y "aparece con cero" es la misma
--       que resuelve tagframe con reindex().fillna(0) despues del groupby
--       (tagframe/analisis.py). Distinta herramienta, identico problema.
--
-- Si te dan 40 alarmas en vez de 34: revisa la vista de 01_esquema.sql.
-- Casi seguro escribiste <= y >= en vez de < y >, y estas contando como
-- alarma el valor que toca exactamente el limite.
-- ---------------------------------------------------------------------

-- BLOQUEANTE (revision): las tres consultas de abajo van a fallar con
--   relation "alarmas" does not exist, y no es culpa de ellas. El CREATE VIEW
--   de 01_esquema.sql:241 no termina en punto y coma, asi que psql se lo come
--   en el EOF sin ejecutarlo ni avisar. Ponele el ";" y recien despues juzga
--   estos resultados.

-- 1
SELECT 'alarmas' as tabla, COUNT(*) AS cantidad FROM alarmas;

-- a lo bruto (no aparecen los 0)
SELECT nombre AS n, COUNT(*) AS num_filas
FROM alarmas
GROUP BY nombre;

-- final
SELECT t.nombre AS n, COUNT(r.nombre) AS num_filas
FROM tags as t
left join alarmas as r
ON r.nombre = t.nombre
GROUP BY t.nombre
ORDER BY n;

-- BIEN (revision), y no es menor: usaste COUNT(r.nombre) y no COUNT(*). Eso
--   es exactamente lo correcto y es la trampa que te marque en el chequeo 4.
--   Con LEFT JOIN, COUNT(*) le daria 1 a FT-310 y LT-115 porque cuenta la
--   fila de NULLs que fabrica el propio join; COUNT(columna) ignora los NULL
--   y da 0. Si hubieras puesto COUNT(*), los dos tags sin alarmas te
--   aparecian con 1 y el total te cerraba en 36 en vez de 34.
--
-- NOTA (revision), de diseno: estas joineando por texto (nombre) porque la
--   vista alarmas solo expone nombre. Funciona, porque tags.nombre es UNIQUE.
--   Pero si a la vista le agregaras tag_id en el SELECT, este join seria por
--   entero contra la PK. Lo que una vista deja salir decide con que se la
--   puede cruzar despues: es una decision de diseno, no un detalle.



-- =====================================================================
-- El cruce final, fuera de psql
--
-- Corre el mismo dataset por Python y compara contra lo que devolvio SQL:
--
--     python -m tagstats data/sensores_planta.csv -l data/limites.csv
--
-- Las dos tablas tienen que decir lo mismo. Si difieren, no elijas cual
-- creer: encontra de donde sale la diferencia. Los sospechosos habituales,
-- en orden de probabilidad:
--
--     1. stddev() en vez de stddev_pop()          -> desvio distinto
--     2. <= / >= en vez de < / > en la vista      -> mas alarmas de la cuenta
--     3. filas duplicadas por falta de ON CONFLICT-> muestras != 144
--     4. redondeo aplicado en distinto momento    -> el ultimo decimal baila
--
-- Cuando los seis renglones coincidan, el checklist
-- "[] Cargar datos de ejemplo" de guia-a-futuro.md:123 esta cerrado de
-- verdad, y tenes datos confiables sobre los que practicar los JOINs y las
-- CTEs que pide el entregable de la semana.
-- =====================================================================
