-- =====================================================================
-- 06_ranking_alarmas.sql  -  Semana 5  -  ESQUELETO PARA COMPLETAR
--
-- Responsabilidad: el patron "top N por grupo". Las alarmas mas severas de
-- cada equipo, con ROW_NUMBER / RANK / DENSE_RANK, y aprender por que no
-- se puede filtrar una window function en el WHERE.
--
-- Este archivo SOLO LEE. Lo podes correr las veces que quieras.
--
-- Como correrlo, parado en la raiz del repo:
--     psql -U postgres -h localhost -d industrial -f sql/06_ranking_alarmas.sql
--
-- Prerequisito: la vista alarmas de 01_esquema.sql con sus 34 filas.
--
-- Recursos:
--   1. ROW_NUMBER / RANK / DENSE_RANK (tabla "General-Purpose Window
--      Functions"):
--      https://www.postgresql.org/docs/current/functions-window.html
--   2. CTEs (WITH ... AS):
--      https://www.postgresql.org/docs/current/queries-with.html
--   3. Por que la ventana no entra en el WHERE (orden de procesamiento):
--      https://www.postgresql.org/docs/current/sql-select.html
--      -> seccion "Description", la lista numerada de pasos.
--   4. split_part:   https://www.postgresql.org/docs/current/functions-string.html
--      GREATEST/CASE: https://www.postgresql.org/docs/current/functions-conditional.html
--   5. Mode, parte de ROW_NUMBER/RANK:
--      https://mode.com/sql-tutorial/sql-window-functions/
-- =====================================================================


-- =====================================================================
-- DECISION PREVIA  -  que es un "equipo"?
--
-- No hay columna "equipo" en el esquema. Pero los nombres de tag siguen la
-- convencion ISA: LETRAS = que se mide, NUMERO = lazo / equipo.
--
--     TT-101  temperatura  reactor           -> equipo 101
--     PT-204  presion      linea de vapor    -> equipo 204
--     FT-310  caudal       alimentacion      -> equipo 310
--     LT-115  nivel        tanque pulmon     -> equipo 115
--     VT-501  vibracion    MOTOR PRINCIPAL   -> equipo 501  <-+ mismo
--     MT-501  corriente    MOTOR PRINCIPAL   -> equipo 501  <-+ equipo
--
-- (Mira las descripciones en data/limites.csv: VT-501 y MT-501 son el
-- mismo motor.) Asi que 501 es el unico equipo con DOS tags, y es el que
-- hace interesante el ejercicio.
--
-- Para esta semana: derivalo del nombre con split_part.
-- Para pensar (no hace falta hacerlo): lo "correcto" seria una columna
-- equipo en tags, o una tabla equipos. Que cambiaria en 01, 02 y 03?
-- =====================================================================


-- ---------------------------------------------------------------------
-- Paso 1  -  la base: cada alarma con su equipo y su SEVERIDAD
--
-- TODO: un SELECT sobre la vista alarmas que agregue:
--       (a) equipo      -> split_part(nombre, '-', ?)
--       (b) exceso      -> CUANTO se paso del limite, siempre positivo.
--                          Si esta por debajo: minimo - valor.
--                          Si esta por arriba: valor - maximo.
--                          Pista: con CASE sale. Con GREATEST(...) sale en
--                          una linea: pensa que da (minimo - valor) cuando
--                          el valor esta por ARRIBA del maximo.
--       (c) exceso_pct  -> el exceso como % del ancho del rango:
--                              exceso / (maximo - minimo) * 100
--
-- Por que (c) y no solo (b): en el equipo 501 compiten alarmas en mm/s
-- (vibracion) y en A (corriente). "0.85 mm/s" vs "6.3 A" no se pueden
-- ordenar entre si: son peras y manzanas. Como % del rango si.
--
-- Oraculo: 34 filas. Las mas severas de cada tag, en exceso_pct:
--       PT-204  14:20  2.194  -> 23.03 %
--       TT-101  11:20  102.10 -> 20.29 %
--       MT-501  06:40  51.30  -> 15.75 %
--       VT-501  16:55  7.95   -> 11.97 %
-- ---------------------------------------------------------------------

SELECT
    split_part(nombre, '-', 1) AS equipo,
    CASE
        WHEN valor > maximo THEN valor - maximo
        WHEN valor < minimo THEN minimo - valor
    END AS exceso,
    CASE
        WHEN valor > maximo THEN (valor - maximo) / (maximo - minimo) * 100
        WHEN valor < minimo THEN (minimo - valor) / (maximo - minimo) * 100
    END AS exceso_pct
FROM alarmas;

-- ---------------------------------------------------------------------
-- Paso 2  -  ROW_NUMBER vs RANK vs DENSE_RANK, lado a lado
--
-- TODO: sobre el resultado del paso 1 (metelo en un WITH), agrega tres
--       columnas con la MISMA ventana:
--           ROW_NUMBER() OVER (PARTITION BY equipo ORDER BY ... DESC)
--           RANK()       OVER (...)
--           DENSE_RANK() OVER (...)
--       Ordena la salida por equipo y por severidad.
--
-- Parte A: ordena la ventana por exceso_pct exacto.
--       Vas a ver las tres columnas IGUALES. No es un error: con valores
--       exactos no hay empates en este dataset, y sin empates las tres
--       funciones hacen lo mismo.
--
-- Parte B: ordena la ventana por ROUND(exceso_pct) (sin decimales).
--       Ahora si hay empates. Oraculo para el equipo 101 (16 alarmas):
--
--       pct redondeado: 20 20 19 18 16 16 16 15 14 13 12  7  6  6  6  5
--       ROW_NUMBER:      1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
--       RANK:            1  1  3  4  5  5  5  8  9 10 11 12 13 13 13 16
--       DENSE_RANK:      1  1  2  3  4  4  4  5  6  7  8  9 10 10 10 11
--
--       Escribi con tus palabras, en un comentario, que hace cada una con
--       un empate. (RANK "salta" numeros, DENSE_RANK no, ROW_NUMBER inventa
--       un orden. Pero escribilo vos.)
--
-- Sobre el frame: RANK y compania IGNORAN la clausula ROWS/RANGE. Para
-- ellos solo importan PARTITION BY y ORDER BY. Por eso este ejercicio
-- separa "particion" de "frame": aca hay particion y no hay frame.
--
-- Pregunta: en la columna ROW_NUMBER de la parte B, cual de las dos
-- alarmas de 20% es la 1? Es deterministico? (Misma trampa que el paso 5
-- de 05_promedio_movil.sql.) Que agregarias al ORDER BY?
-- ---------------------------------------------------------------------

WITH excesos AS (
    SELECT
        "timestamp" AS ttime,
        split_part(nombre, '-', 1) AS equipo,
        CASE
            WHEN valor > maximo THEN valor - maximo
            WHEN valor < minimo THEN minimo - valor
        END AS exceso,
        CASE
            WHEN valor > maximo THEN
                (valor - maximo) * 100.0 / (maximo - minimo)
            WHEN valor < minimo THEN
                (minimo - valor) * 100.0 / (maximo - minimo)
        END AS exceso_pct
    FROM alarmas
)
SELECT
    ROW_NUMBER() OVER (
        PARTITION BY equipo
        ORDER BY exceso_pct DESC
    ) AS row_num,
    RANK() OVER (
        PARTITION BY equipo
        ORDER BY exceso_pct DESC
    ) AS rank,
    DENSE_RANK() OVER (
        PARTITION BY equipo
        ORDER BY exceso_pct DESC
    ) AS dense_rank,
    equipo,
    ttime,
    exceso,
    exceso_pct
FROM excesos;

-- Iter 3
-- --------------
-- exceso_pct	ROW_NUMBER	RANK	DENSE_RANK
-- 50	1	1	1
-- 50	2	1	1
-- 30	3	3	2
-- 20	4	4	3
-- ROW_NUMBER(): siempre asigna números consecutivos, incluso si hay empates.
-- RANK(): los empates comparten posición y dejan un salto.
-- DENSE_RANK(): los empates comparten posición pero no deja saltos.
-- --------------

-- ---------------------------------------------------------------------
-- Paso 3  -  TOP 3 por equipo  (el patron que vas a usar toda la vida)
--
-- Paso 3a, A PROPOSITO: intenta filtrar en el mismo SELECT.
--       Escribi la consulta con  WHERE RANK() OVER (...) <= 3
--       (o con WHERE ranking <= 3, usando el alias). Correla, y pega el
--       error EXACTO de Postgres en un comentario aca abajo. Despues
--       comenta la consulta rota para que el archivo siga corriendo.
--
-- Por que falla: SQL no se evalua en el orden en que se escribe. El orden
-- logico es (confirmalo en el recurso 3):
--
--       FROM / JOIN  ->  WHERE  ->  GROUP BY  ->  HAVING
--          ->  WINDOW FUNCTIONS  ->  SELECT (alias)  ->  DISTINCT
--          ->  ORDER BY  ->  LIMIT
--
-- Cuando corre el WHERE, el ranking TODAVIA NO EXISTE. Y el alias
-- tampoco: se pone recien en el SELECT. (Por eso el ORDER BY si puede
-- usar el alias: corre despues.)
--
-- Paso 3b: la solucion. Calcula el ranking en un CTE (o subquery) y
-- filtra en la consulta de AFUERA, que ve el ranking como una columna
-- comun y corriente:
--       WITH base AS (...paso 1...),
--            rankeadas AS (SELECT ..., RANK() OVER (...) AS ranking FROM base)
--       SELECT ... FROM rankeadas WHERE ranking <= 3 ...;
--
-- Oraculo (ranking por exceso_pct EXACTO, 9 filas):
--       101  TT-101  11:20  20.29 %   | 204  PT-204  14:20  23.03 %
--       101  TT-101  11:05  19.60 %   | 204  PT-204  14:40  21.69 %
--       101  TT-101  11:00  19.37 %   | 204  PT-204  14:30  21.29 %
--       501  MT-501  06:40  15.75 %
--       501  VT-501  16:55  11.97 %   <- el 501 mezcla dos tags: por eso
--       501  VT-501  16:50  10.42 %      hacia falta el %
--
-- Pregunta de diseno: "top 3" con empates. Con ROUND(exceso_pct) en el
-- equipo 101:  ROW_NUMBER <= 3 -> 3 filas
--              RANK       <= 3 -> 3 filas (20, 20, 19)
--              DENSE_RANK <= 3 -> 4 filas (20, 20, 19, 18)
-- Si el jefe de planta pide "las 3 peores", cual usas? Y si pide "todas
-- las que estan en el podio"? Anotalo.
-- ---------------------------------------------------------------------

-- Paso 3a  -  la version ROTA (comentada a proposito, ver el error abajo)
--
-- WITH base AS (
--     SELECT
--         nombre,
--         "timestamp" AS ttime,
--         split_part(nombre, '-', 2) AS equipo,
--         CASE
--             WHEN valor > maximo THEN (valor - maximo) * 100.0 / (maximo - minimo)
--             WHEN valor < minimo THEN (minimo - valor) * 100.0 / (maximo - minimo)
--         END AS exceso_pct
--     FROM alarmas
-- )
-- SELECT equipo, nombre, ttime, exceso_pct,
--        RANK() OVER (PARTITION BY equipo ORDER BY exceso_pct DESC) AS ranking
-- FROM base
-- WHERE RANK() OVER (PARTITION BY equipo ORDER BY exceso_pct DESC) <= 3;
--
-- Error EXACTO de Postgres:
--     ERROR:  window functions are not allowed in WHERE
--     LINE 16: WHERE RANK() OVER (PARTITION BY equipo ORDER BY exceso_pct DESC...
--             ^
--
-- Y la variante con el alias:
--     ... FROM base WHERE ranking <= 3;
--     ERROR:  column "ranking" does not exist
--     HINT:  Perhaps you meant to reference the column "base.nombre".
--
-- Son el mismo problema visto de dos lados: cuando corre el WHERE, ni la
-- ventana se calculo todavia, ni el alias del SELECT existe.


-- Paso 3b  -  la version que ANDA: el CTE calcula, el SELECT de afuera filtra

WITH base AS (
    SELECT
        nombre,
        "timestamp" AS ttime,
        split_part(nombre, '-', 2) AS equipo,
        CASE
            WHEN valor > maximo THEN (valor - maximo) * 100.0 / (maximo - minimo)
            WHEN valor < minimo THEN (minimo - valor) * 100.0 / (maximo - minimo)
        END AS exceso_pct
    FROM alarmas
),
rankeadas AS (
    SELECT
        equipo,
        nombre,
        ttime,
        exceso_pct,
        RANK() OVER (
            PARTITION BY equipo
            ORDER BY exceso_pct DESC
        ) AS ranking
    FROM base
)
SELECT
    equipo,
    nombre,
    ttime::time AS hora,
    ROUND(exceso_pct, 2) AS exceso_pct
FROM rankeadas
WHERE ranking <= 3
ORDER BY equipo, ranking;

-- Para el SELECT de afuera, "ranking" es una columna comun y corriente que
-- viene del FROM. El WHERE no tiene nada raro que filtrar.


-- Respuesta a la pregunta de diseno (top 3 con empates):
--
--   "las 3 peores"  -> ROW_NUMBER. Queres EXACTAMENTE 3 filas, aunque para
--                      eso haya que romper un empate de forma arbitraria.
--                      (Si te molesta lo arbitrario, desempata en el
--                      ORDER BY: ..., ttime ASC.)
--
--   "todas las del  -> DENSE_RANK. Son los 3 primeros PUESTOS, y si dos
--    podio"            comparten el 1ro, entran las dos. Por eso con
--                      ROUND() en el 101 da 4 filas.
--
--   RANK queda en el medio: comparte puesto pero SALTA numeros, asi que
--   <= 3 te puede dar 3 filas o 4 segun donde caiga el empate. Es el menos
--   predecible de los tres para un "top N" (aunque es el correcto cuando lo
--   que te importa es el numero de puesto en si, como en una competencia).


-- ---------------------------------------------------------------------
-- Paso 4 (bonus)  -  ranking de EQUIPOS, con ventana sobre un GROUP BY
--
-- TODO: cuantas alarmas tiene cada equipo, y rankealos:
--           SELECT equipo, COUNT(*) AS alarmas,
--                  RANK() OVER (ORDER BY COUNT(*) DESC) AS ranking
--           FROM ... GROUP BY equipo;
--
-- Fijate: aca la window function SI va en el mismo SELECT que el
-- GROUP BY, sin CTE. Mira el orden del paso 3: las ventanas corren
-- DESPUES del GROUP BY, asi que ven las 3 filas ya agrupadas.
-- Y fijate que no hay PARTITION BY: sin el, la ventana es todo el
-- resultado.
--
-- Oraculo: 101 -> 16 alarmas -> ranking 1
--          204 ->  9 alarmas -> ranking 2
--          501 ->  9 alarmas -> ranking 2    <- empate natural! compara
--                                              RANK vs ROW_NUMBER aca
--
-- Bonus del bonus: 310 y 115 no aparecen porque no tienen alarmas (la
-- vista solo tiene filas fuera de rango). Hace que aparezcan con 0,
-- partiendo de tags con un LEFT JOIN. Que ranking les da RANK? Y
-- DENSE_RANK? (Esperado: RANK 4 y 4, DENSE_RANK 3 y 3.)
-- Ojo: COUNT(*) cuenta la fila del LEFT JOIN aunque venga vacia. Que
-- tenes que contar en su lugar para que de 0?
-- ---------------------------------------------------------------------




-- =====================================================================
-- Checklist de este archivo (guia-a-futuro.md, Semana 5):
--   [] Ranking de alarmas por equipo con RANK
--
-- Para despues (no hace falta ahora): Postgres tiene dos atajos para
-- "top N por grupo" que vas a ver en codigo ajeno:
--   - DISTINCT ON (equipo) ... ORDER BY equipo, exceso_pct DESC -> top 1
--   - LATERAL (subquery con LIMIT por cada fila de afuera)      -> top N
-- Conviene saber hacerlo primero con ventanas, que es SQL estandar y
-- funciona igual en SQL Server, Oracle y SQLite.
-- =====================================================================
