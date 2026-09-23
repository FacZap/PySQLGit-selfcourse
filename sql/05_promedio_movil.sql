-- =====================================================================
-- 05_promedio_movil.sql  -  Semana 5  -  ESQUELETO PARA COMPLETAR
--
-- Responsabilidad: calcular un promedio movil por tag con una ventana
-- COMPLETA (PARTITION BY + ORDER BY + frame), y entender que pasa cuando
-- falta cada una de esas tres piezas.
--
-- Este archivo SOLO LEE. No crea, no borra, no modifica nada: lo podes
-- correr las veces que quieras.
--
-- Como correrlo, parado en la raiz del repo:
--     psql -U postgres -h localhost -d industrial -f sql/05_promedio_movil.sql
--
-- Prerequisito: 01 a 03 ya corridos (readings con 864 filas). Si 04 da
-- verde, estas listo.
--
-- Sin acentos a proposito, igual que 01-04 (psql en Windows + WIN1252).
--
-- Recursos (en este orden):
--   1. Tutorial:  https://www.postgresql.org/docs/current/tutorial-window.html
--   2. Sintaxis del frame (ROWS/RANGE/GROUPS, PRECEDING, default):
--      https://www.postgresql.org/docs/current/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS
--   3. Lista de funciones de ventana:
--      https://www.postgresql.org/docs/current/functions-window.html
--   4. Mode, con ejemplos paso a paso:
--      https://mode.com/sql-tutorial/sql-window-functions/
-- =====================================================================


-- =====================================================================
-- ANATOMIA DE OVER  -  leelo antes de escribir nada
--
--   AVG(valor) OVER (
--       PARTITION BY tag_id                        -- 1. ENTRE QUIENES
--       ORDER BY "timestamp"                       -- 2. EN QUE ORDEN
--       ROWS BETWEEN 5 PRECEDING AND CURRENT ROW   -- 3. CUANTAS FILAS ALREDEDOR
--   )
--
--   1. PARTITION BY  -> parte las filas en grupos. La ventana NUNCA cruza
--                       de un grupo a otro: el promedio de TT-101 no se
--                       mezcla con lecturas de PT-204.
--   2. ORDER BY      -> define que es "la fila anterior". Sin orden no hay
--                       "5 filas antes".
--   3. frame         -> de todas las filas del grupo, cuales entran en la
--                       cuenta para ESTA fila. Se mueve con cada fila.
--
-- La diferencia con GROUP BY, que es lo primero que hay que tener claro:
--   GROUP BY tag_id        -> 864 filas entran, 6 salen. COLAPSA.
--   AVG(...) OVER (...)    -> 864 filas entran, 864 salen. Cada fila
--                             conserva su valor Y gana una columna nueva.
-- =====================================================================

--SELECT nombre, timestamp, valor, AVG(valor) OVER (PARTITION BY nombre) FROM alarmas WHERE nombre='TT-101';

SELECT
    t.nombre AS nombre,
    r.timestamp,
    r.valor,
    ROUND(
        AVG(r.valor) OVER (PARTITION BY t.tag_id),
        2
    ) AS promedio
FROM readings AS r
INNER JOIN tags AS t
    ON t.tag_id = r.tag_id;

-- ---------------------------------------------------------------------
-- Paso 1  -  calentamiento: OVER con SOLO PARTITION BY
--
-- TODO: SELECT de nombre, "timestamp", valor y una columna
--           AVG(valor) OVER (PARTITION BY ...)   AS promedio_tag
--       Filtra a un solo tag (WHERE nombre = 'TT-101') para poder leerlo.
--
--       Pista 1: readings no tiene el nombre "TT-101", tiene tag_id. Te
--                hace falta un JOIN con tags (lo mismo que en la vista
--                alarmas de 01_esquema.sql).
--       Pista 2: AVG de NUMERIC da un NUMERIC con muchos decimales.
--                ROUND(x, 2) lo deja legible. (Si en 01 hubieras elegido
--                REAL, ROUND(real, 2) no existe y te obliga a castear:
--                otra razon a favor de NUMERIC.)
--
-- Pregunta para contestar aca abajo en un comentario:
--       Sin ORDER BY adentro del OVER, cual es el frame? Por que TODAS las
--       filas muestran el mismo numero?
--
-- Oraculo: las 144 filas de TT-101 muestran 80.24 (el PROMEDIO de
--          README.md:57-64). Si da eso, la ventana "ve" todo el grupo.
-- ---------------------------------------------------------------------

SELECT
    t.nombre AS nombre,
    r.timestamp,
    r.valor,
    ROUND(
        AVG(r.valor) OVER (PARTITION BY t.tag_id ORDER BY "timestamp"),
        2
    ) AS promedio_movil_falso
FROM readings AS r
INNER JOIN tags AS t
    ON t.tag_id = r.tag_id;

-- ---------------------------------------------------------------------
-- Paso 2  -  LA TRAMPA: agregar ORDER BY y NO poner frame
--
-- TODO: la misma consulta del paso 1, pero con
--           AVG(valor) OVER (PARTITION BY ... ORDER BY "timestamp")
--       y sin clausula ROWS/RANGE. Ordena la salida por "timestamp".
--
-- Que esta pasando: cuando hay ORDER BY y omitis el frame, Postgres usa
-- este default (buscalo en el recurso 2, esta escrito ahi textual):
--       RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
-- O sea: desde la PRIMERA fila del grupo hasta la actual. Eso es un
-- promedio ACUMULADO, no movil. Parece movil a simple vista (los numeros
-- cambian fila a fila) y por eso es la trampa clasica: la query corre,
-- no tira error, y te da otra cosa.
--
-- Oraculo (TT-101):
--       fila 1  (06:00) -> 77.15     (una sola lectura, promedio = ella)
--       fila 10 (06:45) -> 79.61     (promedio de las primeras 10)
--       fila 144 (17:55)-> 80.24     <- igual al paso 1. Por que?
--                                       Contestalo en un comentario.
-- ---------------------------------------------------------------------

SELECT
    t.nombre AS nombre,
    r.timestamp,
    r.valor,
    ROUND(
        AVG(r.valor) OVER (
            PARTITION BY t.tag_id
            ORDER BY "timestamp"
            ROWS BETWEEN 4 PRECENDING AND CURRENT ROW
        ) AS promedio_movil,
        2
    ) AS promedio
FROM readings AS r
INNER JOIN tags AS t
    ON t.tag_id = r.tag_id;


-- ---------------------------------------------------------------------
-- Paso 3  -  el promedio movil de verdad: ventana completa
--
-- TODO: ahora si, las tres piezas:
--           AVG(valor) OVER (
--               PARTITION BY ...
--               ORDER BY ...
--               ROWS BETWEEN ? PRECEDING AND CURRENT ROW
--           ) AS promedio_movil
--       Deja a la vista, lado a lado: valor, el acumulado del paso 2 y el
--       movil. Ver las tres columnas juntas es lo que hace "clic".
--
-- DECISION (escribila aca abajo antes de tipear el numero):
--       "N PRECEDING AND CURRENT ROW" son N+1 lecturas, no N. El ejercicio
--       dice 5 PRECEDING (= 6 lecturas); la chuleta de guia-a-futuro.md:270
--       dice 4 PRECEDING (= 5 lecturas). Las lecturas vienen cada 5
--       minutos. Cuantos minutos de proceso cubre tu ventana? Elegi uno y
--       dejalo anotado en unidades de TIEMPO, que es como lo va a pensar
--       el operador, no en filas.
--
-- Oraculo con 5 PRECEDING (6 lecturas), TT-101:
--       06:00 -> 77.15
--       06:05 -> 77.78
--       06:10 -> 78.00
--       06:45 (fila 10) -> 80.32     <- compara con 79.61 del paso 2
--
-- Experimento sobre ORDEN DE EVALUACION (te prepara para 06):
--       Agrega  AND "timestamp" >= '2026-08-24 12:00'  al WHERE y mira la
--       fila de las 12:00. El promedio movil CAMBIA. Por que? Pista: el
--       WHERE se ejecuta ANTES que la ventana, asi que las lecturas de las
--       11:35-11:55 ya no existen cuando la ventana las busca.
--       En cambio filtrar por nombre no cambia nada. Por que uno si y el
--       otro no? (Pensa en PARTITION BY.)
-- ---------------------------------------------------------------------

SELECT
    t.nombre AS nombre,
    r.timestamp,
    r.valor,
    ROUND(
        AVG(r.valor) OVER (
            PARTITION BY t.tag_id
            ORDER BY "timestamp"
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS promedio_movil,
    COUNT(*) OVER (
            PARTITION BY t.tag_id
            ORDER BY "timestamp"
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    )
FROM readings AS r
INNER JOIN tags AS t
    ON t.tag_id = r.tag_id;


-- ---------------------------------------------------------------------
-- Paso 4  -  las primeras filas mienten (ventana incompleta)
--
-- En la fila de las 06:00 el "promedio de 6 lecturas" es el promedio de
-- UNA sola. En un grafico de tendencia eso aparece como un arranque raro.
--
-- TODO: (a) agrega  COUNT(*) OVER (<la misma ventana>) AS n_en_ventana
--           y mira cuanto vale en las primeras 6 filas.
--       (b) con un CASE, mostra NULL en promedio_movil mientras la
--           ventana no este completa. Decidi vos si preferis eso o el
--           numero parcial, y anota por que.
--
-- Pista: escribir la ventana dos veces (para AVG y para COUNT) es feo y
--        es donde aparecen los bugs (cambias una y te olvidas la otra).
--        Postgres tiene la clausula WINDOW para nombrarla una vez:
--            SELECT ..., AVG(valor) OVER w, COUNT(*) OVER w
--            FROM ...
--            WHERE ...
--            WINDOW w AS (PARTITION BY ... ORDER BY ... ROWS ...)
--            ORDER BY ...
--        Ojo con el LUGAR: WINDOW va despues de WHERE/GROUP BY/HAVING y
--        antes de ORDER BY. Buscalo en la doc de SELECT:
--        https://www.postgresql.org/docs/current/sql-select.html
--
-- Oraculo: n_en_ventana = 1, 2, 3, 4, 5, 6, 6, 6, ... (con 5 PRECEDING)
-- ---------------------------------------------------------------------




-- ---------------------------------------------------------------------
-- Paso 5  -  ROWS vs RANGE: la diferencia son los EMPATES
--
-- ROWS  cuenta filas fisicas:  "5 filas antes".
-- RANGE cuenta VALORES del ORDER BY: todas las filas con el mismo
--       "timestamp" que la actual son, para RANGE, la MISMA posicion
--       (se llaman "peers" en la doc). Entran todas juntas o ninguna.
--
-- Problema: dentro de un tag NO hay empates. Por que? (Respuesta en
-- 01_esquema.sql, buscala: es una restriccion que escribiste vos.)
-- Asi que con PARTITION BY tag_id, ROWS y RANGE ... UNBOUNDED ... dan
-- igual y no ves nada.
--
-- Para verlos, saca el PARTITION BY: los 6 tags miden en los mismos
-- instantes, entonces cada "timestamp" aparece 6 veces.
--
-- TODO: una consulta SIN PARTITION BY, ordenada por "timestamp", con dos
--       columnas lado a lado:
--           COUNT(*) OVER (ORDER BY "timestamp"
--                          ROWS  BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
--           COUNT(*) OVER (ORDER BY "timestamp"
--                          RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
--       Limitala a las primeras 18 filas (LIMIT) para leerla.
--
-- Oraculo:
--       ROWS  -> 1, 2, 3, 4, 5, 6, 7, 8, ...
--       RANGE -> 6, 6, 6, 6, 6, 6, 12, 12, 12, 12, 12, 12, 18, ...
--
-- Segunda trampa, mas sutil: en la columna ROWS, cual de las 6 filas de
-- las 06:00 es la "1" y cual la "6"? Correla varias veces: nadie te
-- garantiza el orden entre empates. Arreglalo agregando un desempate al
-- ORDER BY (ej: "timestamp", tag_id) y anota la regla:
--       "si el ORDER BY de una ventana ROWS tiene empates, el resultado
--        no es deterministico".
--
-- Y la conclusion de todo el modulo, escribila con tus palabras aca:
--       el default del paso 2 era RANGE, no ROWS. Que habria pasado si
--       hubiera habido empates dentro del tag?
-- ---------------------------------------------------------------------

-- (a) ROWS vs RANGE, sin PARTITION BY: cada "timestamp" aparece 6 veces
--     (un tag por cada una) y ahi se ve la diferencia.
SELECT
    t.nombre AS nombre,
    r."timestamp",
    COUNT(*) OVER (
        ORDER BY r."timestamp"
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS acum_rows,
    COUNT(*) OVER (
        ORDER BY r."timestamp"
        RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS acum_range
FROM readings AS r
INNER JOIN tags AS t
    ON t.tag_id = r.tag_id
ORDER BY r."timestamp", t.nombre
LIMIT 18;

-- Lectura de la salida:
--   acum_rows  -> 1, 2, 3, 4, 5, 6, 7, 8, ...  cuenta FILAS: la actual es
--                 una mas que la anterior, sin importar que compartan el
--                 mismo instante.
--   acum_range -> 6, 6, 6, 6, 6, 6, 12, ...    cuenta POSICIONES del
--                 ORDER BY: las 6 lecturas de las 06:00 son "peers", una
--                 sola posicion, y entran las 6 juntas o ninguna. Por eso
--                 ya en la primera fila vale 6.
--
-- Ojo con el LIMIT 18: se aplica DESPUES de calcular las ventanas (es el
-- ultimo paso de todos). Por eso acum_range puede decir 18 aunque solo
-- estemos viendo 18 filas de las 864. No confundir "lo que muestro" con
-- "lo que la ventana miro".
--
-- Ojo tambien con el ORDER BY de afuera: ese solo decide como IMPRIMO las
-- filas. El orden que usa la ventana es el de adentro del OVER. Son dos
-- cosas distintas y por eso acum_rows se ve desordenado (5, 2, 6, 1, ...)
-- dentro de cada grupo de 6.


-- (b) El mismo calculo, pero con el empate resuelto DENTRO de la ventana.
SELECT
    t.nombre AS nombre,
    r."timestamp",
    COUNT(*) OVER (
        ORDER BY r."timestamp", t.nombre
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS acum_rows,
    COUNT(*) OVER (
        ORDER BY r."timestamp", t.nombre
        RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS acum_range
FROM readings AS r
INNER JOIN tags AS t
    ON t.tag_id = r.tag_id
ORDER BY r."timestamp", t.nombre
LIMIT 18;

-- Que cambio:
--   acum_rows  -> ahora es estable entre corridas: FT-310 siempre es la 1
--                 de las 06:00 y VT-501 siempre la 6, porque el desempate
--                 esta adentro del OVER.
--   acum_range -> tambien cambia! Al agregar nombre al ORDER BY ya NO hay
--                 dos filas con la misma clave de orden, entonces no hay
--                 peers y RANGE pasa a contar 1, 2, 3, ... igual que ROWS.
--
-- REGLA: si el ORDER BY de una ventana ROWS tiene empates, el resultado no
-- es deterministico. Postgres no esta roto: SQL no promete ningun orden
-- entre filas empatadas, asi que puede devolver cualquiera y cambiarlo
-- entre corridas (o con otro plan de ejecucion). Si el numero de fila te
-- importa, desempata vos.
--
-- CONCLUSION del modulo:
--   El default del paso 2 (ORDER BY sin frame) es RANGE, no ROWS. Si
--   dentro de un tag hubiera timestamps repetidos, ese "acumulado" sumaria
--   los empates de golpe: las lecturas repetidas entrarian todas en la
--   misma posicion y las filas empatadas mostrarian TODAS el mismo
--   promedio, en vez de ir incorporandose de a una.
--   Aca no pasa porque readings tiene UNIQUE (tag_id, "timestamp")
--   (01_esquema.sql, restriccion readings_tag_ts_unique), que es lo que
--   garantiza que dentro de un tag no haya dos lecturas en el mismo
--   instante. El esquema es el que hace que la ventana sea predecible.


-- ---------------------------------------------------------------------
-- Paso 6 (bonus)  -  ventana por TIEMPO en vez de por filas
--
-- "6 lecturas" y "25 minutos" son lo mismo SOLO si no faltan lecturas.
-- En la vida real el historiador pierde muestras y ahi divergen. Desde
-- PG11, RANGE acepta un intervalo:
--       RANGE BETWEEN INTERVAL '25 minutes' PRECEDING AND CURRENT ROW
--
-- TODO: pone lado a lado el movil ROWS del paso 3 y este RANGE por tiempo.
--       Hoy tienen que dar IGUAL (el dataset no tiene huecos: 144
--       lecturas por tag, cada 5 min exactos de 06:00 a 17:55).
--
-- Experimento para hacer A MANO en psql (NO lo dejes en este archivo,
-- que es de solo lectura):
--       BEGIN;
--       DELETE FROM readings WHERE ... una lectura de TT-101 ...;
--       -- corre tu consulta del bonus y mira las filas de despues
--       ROLLBACK;     <- deshace el DELETE. No te lo olvides.
-- Cual de las dos columnas te parece "correcta" para una senal de
-- proceso? Anotalo.
-- ---------------------------------------------------------------------

-- EQUIVALENCIA, ajustada a la decision del paso 3 (4 PRECEDING):
--   ROWS BETWEEN 4 PRECEDING               -> 5 lecturas
--   RANGE BETWEEN INTERVAL '20 minutes'    -> de ts-20min a ts, que con
--                                             lecturas cada 5 min son 5
--                                             lecturas: 06:40 ... 07:00.
--   El "25 minutes" del enunciado correspondia a 5 PRECEDING. Regla:
--   N PRECEDING filas  <->  N * 5 minutos. Mismo off-by-one del paso 3,
--   ahora en unidades de tiempo.
--
-- Por que la ventana va en un CTE y el filtro por hora va AFUERA: si
-- pongo  "timestamp" BETWEEN '06:50' AND '07:30'  en el WHERE de adentro,
-- las lecturas de 06:30-06:45 desaparecen ANTES de que corra la ventana y
-- los primeros promedios salen mal (el experimento del paso 3). Afuera,
-- la ventana ya se calculo con todo y el filtro solo recorta lo que miro.
-- Filtrar por nombre adentro SI es seguro: la particion es por tag.
WITH movil AS (
    SELECT
        t.nombre AS nombre,
        r."timestamp",
        r.valor,
        ROUND(AVG(r.valor) OVER w_filas, 2) AS movil_rows,
        COUNT(*)           OVER w_filas     AS n_rows,
        ROUND(AVG(r.valor) OVER w_tiempo, 2) AS movil_range,
        COUNT(*)           OVER w_tiempo    AS n_range
    FROM readings AS r
    INNER JOIN tags AS t
        ON t.tag_id = r.tag_id
    WHERE t.nombre = 'TT-101'
    WINDOW
        w_filas  AS (
            PARTITION BY r.tag_id
            ORDER BY r."timestamp"
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ),
        w_tiempo AS (
            PARTITION BY r.tag_id
            ORDER BY r."timestamp"
            RANGE BETWEEN INTERVAL '20 minutes' PRECEDING AND CURRENT ROW
        )
)
SELECT
    nombre,
    "timestamp",
    valor,
    movil_rows,
    n_rows,
    movil_range,
    n_range,
    movil_rows - movil_range AS diferencia
FROM movil
WHERE "timestamp" BETWEEN '2026-08-24 06:50' AND '2026-08-24 07:30'
ORDER BY "timestamp";

-- Oraculo HOY (sin huecos): las dos columnas iguales, n_rows = n_range = 5
-- y diferencia = 0.00 en todas las filas.
--       06:50  80.34  -> 80.61
--       07:00  82.28  -> 81.04
--       07:15  81.95  -> 81.66
--       07:30  80.82  -> 81.09
--
-- Restriccion de Postgres que vas a chocar si queres desempatar como en el
-- paso 5: RANGE con un offset (INTERVAL '20 minutes' PRECEDING) exige UNA
-- sola columna en el ORDER BY, y de un tipo al que se le pueda restar ese
-- offset (timestamp - interval, numero - numero). ORDER BY "timestamp",
-- nombre + RANGE con INTERVAL tira error. Tiene sentido: "20 minutos antes"
-- no significa nada sobre una clave de dos columnas.


-- ---------------------------------------------------------------------
-- EXPERIMENTO (a mano en psql, NO descomentar en este archivo):
--
--   BEGIN;
--   DELETE FROM readings
--   WHERE tag_id = (SELECT tag_id FROM tags WHERE nombre = 'TT-101')
--     AND "timestamp" = '2026-08-24 07:00';
--       -- tiene que decir DELETE 1. Si dice DELETE 0, el filtro esta mal.
--   \i sql/05_promedio_movil.sql     -- o pega solo la consulta de arriba
--   ROLLBACK;
--       -- SIN el BEGIN, psql esta en autocommit y el DELETE es definitivo:
--       -- habria que volver a correr 03_carga.sql para recuperar la fila.
--
-- Oraculo sin la lectura de las 07:00:
--   ts     valor  movil_rows n_rows  movil_range n_range  diferencia
--   06:55  81.33    80.55      5       80.55       5        0.00
--   07:05  81.34    80.85      5       81.01       4       -0.16
--   07:10  81.41    81.09      5       81.11       4       -0.02
--   07:15  81.95    81.27      5       81.51       4       -0.24
--   07:20  80.97    81.40      5       81.42       4       -0.02
--   07:25  80.29    81.19      5       81.19       5        0.00
--
-- Que paso:
--   ROWS  -> sigue promediando 5 lecturas, pero para completarlas va a
--            buscar una MAS VIEJA. A las 07:05 su ventana arranca en 06:40:
--            25 minutos de proceso, no 20. La ventana se estira en el
--            tiempo sin avisar.
--   RANGE -> sigue mirando exactamente 20 minutos. Adentro hay una lectura
--            menos (n_range = 4), pero todas son del periodo correcto.
--   Durante 20 minutos despues del hueco (07:05 a 07:20) difieren; a las
--   07:25 la lectura perdida ya quedo fuera de las dos ventanas y vuelven
--   a coincidir.
--
-- CUAL ES "CORRECTA" para una senal de proceso: RANGE por tiempo.
--   El operador piensa "temperatura promedio de los ultimos 20 minutos",
--   no "de las ultimas 5 muestras". Con ROWS, cada hueco del historiador
--   mete datos mas viejos en el promedio, y justo despues de una falla de
--   comunicacion (cuando mas importa lo reciente) el promedio mira hacia
--   atras.
--   El costo: con huecos, RANGE promedia menos muestras y es mas ruidoso.
--   Por eso conviene mostrar n_range al lado, o poner NULL si baja de un
--   minimo (el mismo CASE del paso 4, pero sobre n_range).
-- ---------------------------------------------------------------------




-- =====================================================================
-- Checklist de este archivo (guia-a-futuro.md, Semana 5):
--   [] Calcular promedio movil de una senal con OVER
--
-- Si entendiste por que el paso 2 NO es un promedio movil y por que en el
-- paso 5 RANGE salta de a 6, entendiste lo dificil. El resto (LAG/LEAD,
-- RANK) es la misma ventana con otra funcion adelante.
-- =====================================================================
