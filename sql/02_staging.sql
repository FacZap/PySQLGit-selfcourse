-- =====================================================================
-- 02_staging.sql  -  Semana 4  -  ESQUELETO PARA COMPLETAR
--
-- Responsabilidad: traer los CSV crudos ADENTRO de la base, tal cual estan,
-- sin interpretarlos. Nada de tag_id, nada de casteos, nada de limpieza.
-- Eso es 03_carga.sql.
--
-- Como correrlo, PARADO EN LA RAIZ DEL REPO (esto importa, ver abajo):
--     psql -U postgres -h localhost -d industrial -f sql/02_staging.sql
-- =====================================================================


-- =====================================================================
-- POR QUE HACE FALTA UNA ETAPA INTERMEDIA (staging)
--
-- \copy es un embudo tonto, y esta bien que lo sea: agarra la columna 1 del
-- archivo y la mete en la columna 1 de la tabla, la 2 en la 2, etc. No sabe
-- hacer preguntas. Y tu CSV dice "TT-101", mientras que readings quiere un
-- numero (tag_id) que solo se puede averiguar mirando la tabla tags.
--
-- Entonces el CSV aterriza primero en una tabla espejo, con las mismas
-- columnas que el archivo y TODO como TEXT, y recien despues (en 03) un
-- INSERT ... SELECT ... JOIN lo traduce al esquema real.
--
-- Por que TEXT y no los tipos finales: para separar dos fallas distintas.
-- Si staging es TEXT, un \copy que falla es un problema de FORMATO (columnas
-- corridas, separador equivocado). Un cast que falla en 03 es un problema de
-- CONTENIDO (un "N/A" donde iba un numero). Mezclarlos te deja adivinando.
--
-- Es la misma idea que ya usa el proyecto en Python: FuenteCSV lee todo con
-- dtype=str a proposito y deja la coercion de tipos para Limpiador
-- (tagframe/fuentes.py, tagframe/limpieza.py). Mismo criterio, otro motor.
-- =====================================================================


-- =====================================================================
-- \copy  vs  COPY   -  el concepto central de este archivo
--
--   COPY  (comando SQL)      -> lo ejecuta EL SERVIDOR. El servidor abre el
--                               archivo con SU usuario (el del servicio de
--                               Windows), que no ve tu D:\ y encima necesita
--                               permisos de superusuario. Casi nunca es lo
--                               que queres en tu maquina.
--
--   \copy (meta-comando psql) -> lo ejecuta PSQL, o sea el cliente, con TU
--                               usuario y TUS permisos: abre el archivo el
--                               programa que vos corriste, y le manda las
--                               filas al servidor por la misma conexion.
--
-- Para este trabajo: SIEMPRE \copy.
--
-- Tres trampas de \copy, en orden de cuanto tiempo hacen perder:
--
--   1) La ruta es relativa al DIRECTORIO DESDE EL QUE CORRISTE PSQL, no a la
--      ubicacion de este .sql. Por eso arriba dice "parado en la raiz del
--      repo". Si lo corres desde sql/, va a buscar sql/data/... y no existe.
--
--   2) Es meta-comando de psql, no SQL: tiene que entrar en UNA SOLA LINEA.
--      No podes partirlo en varias lineas como harias con un SELECT largo.
--      Si lo partis, psql lee media instruccion y tira un error raro.
--
--   3) No lo pruebes en un cliente que no sea psql. pgAdmin y DBeaver hablan
--      SQL, no meta-comandos de psql: \copy ahi no existe.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Limpiar corridas anteriores
--
-- TODO: DROP de las dos tablas de staging, con IF EXISTS.
--       Estas no tienen dependencias entre si, asi que el orden da igual.
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS staging_limites;
DROP TABLE IF EXISTS staging_lecturas;



-- ---------------------------------------------------------------------
-- staging_limites  -  espejo exacto de data/limites.csv
--
-- Cabecera real del archivo:
--     tag,minimo,maximo,unidad,descripcion
--
-- TODO: CREATE TABLE staging_limites con esas CINCO columnas, en ESE orden,
--       todas TEXT.
--       Pista 1: el orden tiene que coincidir con el del archivo, porque
--                \copy empareja por POSICION, no por nombre.
--       Pista 2: nada de NOT NULL, nada de PRIMARY KEY, nada de CHECK. Una
--                tabla de staging no valida: recibe. Si le pones
--                restricciones, el \copy se corta a la mitad y te quedas sin
--                saber cuantas filas malas habia en total.
-- ---------------------------------------------------------------------

CREATE TABLE staging_limites (
    tag         TEXT,
    minimo      TEXT,
    maximo      TEXT,
    unidad      TEXT,
    descripcion TEXT
);



-- ---------------------------------------------------------------------
-- staging_lecturas  -  espejo exacto de data/sensores_planta.csv
--
-- Cabecera real del archivo:
--     timestamp,tag,valor,unidad,calidad
--
-- TODO: CREATE TABLE staging_lecturas, esas cinco columnas, todas TEXT.
--       Ojo de nuevo con "timestamp": si la nombras igual que en el CSV, van
--       las comillas dobles. Como esta tabla es descartable, tenes permiso
--       para llamarla ts y ahorrarte las comillas. Decidilo vos.
-- ---------------------------------------------------------------------

CREATE TABLE staging_lecturas (
    ts      TEXT,   -- se llama ts y no "timestamp": tabla descartable, no vale
                    -- la pena arrastrar comillas dobles en cada consulta
    tag     TEXT,
    valor   TEXT,
    unidad  TEXT,
    calidad TEXT
);



-- =====================================================================
-- La carga en si
--
-- Sintaxis general (documentacion: https://www.postgresql.org/docs/current/sql-copy.html)
--
--     \copy nombre_de_tabla FROM 'ruta/al/archivo.csv' WITH (opciones)
--
-- Las opciones que te importan hoy:
--     FORMAT csv     -> interpreta comillas y comas como CSV, no como texto plano
--     HEADER true    -> la PRIMERA linea es la cabecera: saltearla, no cargarla
--
-- TODO: escribi los dos \copy, uno por cada tabla de staging.
--       Recorda: una sola linea cada uno, ruta relativa a la raiz del repo,
--       o sea empezando por  data/
--
-- Como saber que salio bien: psql te contesta con la cantidad de filas.
-- Tiene que decir COPY 6 y COPY 864.
--
--   Si dice COPY 0    -> el archivo estaba vacio, o solo tenia cabecera.
--   Si dice COPY 7    -> te olvidaste HEADER true y cargaste la cabecera
--                        como si fuera un dato.
--   Si tira "could not open file" -> estas parado en el directorio
--                        equivocado. cd a la raiz del repo.
-- =====================================================================

\copy staging_limites FROM 'data/limites.csv' WITH (FORMAT csv, HEADER true)
\copy staging_lecturas FROM 'data/sensores_planta.csv' WITH (FORMAT csv, HEADER true)





-- =====================================================================
-- TRAMPA: data/sensores_sucios.csv NO se carga aca. A proposito.
--
-- Ese archivo tiene esta fila (data/sensores_sucios.csv:9):
--     2026-08-24T06:00:00,PT-204,4,82,bar,Good
-- Es un decimal escrito con coma y sin comillas ("4,82"), asi que trae SEIS
-- campos para una tabla de CINCO columnas. \copy corta la carga entera con
--     ERROR: extra data after last expected column
--
-- Y no hay forma de decirle "saltea esa y segui": \copy es todo o nada. No
-- tiene el equivalente del on_bad_lines="warn" que si tiene pandas y que ya
-- usa FuenteCSV (tagframe/fuentes.py).
--
-- Esa es exactamente la division del trabajo: los datos sucios se limpian en
-- Python, ANTES de que toquen la base. La base recibe datos que ya son
-- validos. Es el orden ingesta -> validacion -> storage que plantea
-- guia-a-futuro.md:309 para Semana 6.
--
-- Si igual queres verlo fallar (vale la pena, es 30 segundos):
--     \copy staging_lecturas FROM 'data/sensores_sucios.csv' WITH (FORMAT csv, HEADER true)
-- Mira el error, entendelo, y despues acordate de vaciar staging_lecturas
-- antes de seguir con 03.
-- =====================================================================


-- =====================================================================
-- TRAMPA: un \copy exitoso NO garantiza que haya datos.
--
--     \copy staging_lecturas FROM 'data/sensores_vacio.csv' WITH (FORMAT csv, HEADER true)
--
-- Ese archivo tiene solo la cabecera. Responde COPY 0: sin error, sin filas.
-- Moraleja: "no fallo" y "funciono" no son lo mismo. Por eso existe
-- 04_verificar.sql, que compara contra numeros esperados en vez de confiar
-- en la ausencia de errores.
-- =====================================================================


-- =====================================================================
-- Verificacion de ESTE archivo, antes de pasar a 03:
--
--     SELECT COUNT(*) FROM staging_limites;    -- tiene que dar 6
--     SELECT COUNT(*) FROM staging_lecturas;   -- tiene que dar 864
--     SELECT * FROM staging_lecturas LIMIT 5;  -- mira que las columnas no
--                                              -- quedaron corridas
--
-- Ese LIMIT 5 no es decorativo: si el separador o el orden de columnas
-- estuviera mal, los COUNT igual darian bien y vos no te enterarias hasta
-- tres archivos despues.
-- =====================================================================
