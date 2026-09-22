-- =====================================================================
-- 03_carga.sql  -  Semana 4  -  ESQUELETO PARA COMPLETAR
--
-- Responsabilidad: traducir el staging crudo (todo TEXT, con el tag como
-- texto) al esquema real (tipado, con tag_id numerico y claves foraneas).
-- Aca es donde el CSV deja de ser un archivo y se vuelve una base de datos.
--
-- Como correrlo, parado en la raiz del repo:
--     psql -U postgres -h localhost -d industrial -f sql/03_carga.sql
--
-- Requiere: 01_esquema.sql y 02_staging.sql ya corridos.
-- =====================================================================


-- =====================================================================
-- EL ORDEN NO ES NEGOCIABLE
--
--     1. tags      <- staging_limites   (crea los tag_id)
--     2. limites   <- staging_limites   (necesita los tag_id del paso 1)
--     3. readings  <- staging_lecturas  (necesita los tag_id del paso 1)
--
-- Si intentas el 3 antes que el 1, la clave foranea te rechaza TODO. Y esta
-- bien que lo haga: para eso la pusiste.
-- =====================================================================


-- =====================================================================
-- IDEMPOTENCIA: la decision que se toma ANTES de escribir el INSERT
--
-- Queres poder correr este archivo dos veces sin duplicar nada. No para ser
-- prolijo: porque lo vas a correr diez veces mientras aprendes, y porque un
-- pipeline real reprocesa un dia que llego tarde y no puede duplicarlo.
--
-- Postgres te da ON CONFLICT, que se lee asi:
--
--     INSERT INTO tabla (...) SELECT ...
--     ON CONFLICT (columnas_de_la_restriccion) DO ALGO
--
-- El "algo" son dos opciones, y elegir mal es un bug silencioso:
--
--   DO NOTHING  -> "ya existe, no lo toques". La fila vieja gana.
--                  Sirve para datos que no cambian: una lectura del pasado
--                  es lo que es. Si el historiador la reenvia, es la misma.
--
--   DO UPDATE   -> "ya existe, pisalo con lo nuevo". La fila nueva gana.
--                  (Esto es lo que se llama UPSERT.)
--                  Sirve para configuracion: si alguien cambio el maximo de
--                  TT-101 en limites.csv, queres el valor NUEVO, no seguir
--                  con el viejo porque "ya existia".
--
-- Y ojo con la tercera opcion, que es no poner nada: entonces el INSERT
-- FALLA con "duplicate key value violates unique constraint". Tambien es una
-- decision valida (fallar fuerte es mejor que duplicar en silencio), pero
-- que sea una decision, no un olvido.
--
-- TODO (decision previa, escribila antes de tipear): cual va en cada uno de
--       los tres INSERT de abajo? Deja el motivo en un comentario.
--       Pista: fijate cual de las tres tablas guarda CONFIGURACION y cuales
--       guardan HECHOS. No se tratan igual.
-- =====================================================================

-- Decision:
--   tags     -> DO UPDATE : catalogo mantenido a mano; si corrigen la unidad o
--                          la descripcion en limites.csv, gana el valor nuevo.
--   limites  -> DO UPDATE : configuracion; un setpoint nuevo pisa al viejo.
--   readings -> DO NOTHING: hechos; una lectura del pasado no cambia, si llega
--                          repetida es la misma.

-- ---------------------------------------------------------------------
-- Paso 1  -  tags
--
-- De staging_limites (6 filas de texto) a tags. Es casi una copia: las
-- columnas tag, unidad y descripcion pasan tal cual (ya son texto). El
-- tag_id NO lo insertas vos: lo genera la tabla sola, para eso lo hiciste
-- autoincremental en 01_esquema.sql.
--
-- TODO: escribi el INSERT INTO tags (...) SELECT ... FROM staging_limites
--       + la clausula ON CONFLICT que decidiste arriba.
--       Pista 1: la columna se llama "tag" en el CSV y "nombre" en la tabla.
--                No es un error mio: el CSV usa el vocabulario del
--                historiador, la base usa el tuyo. Traducir vocabularios es
--                justamente lo que hace este archivo.
--       Pista 2: no listes tag_id entre las columnas del INSERT.
--       Pista 3: el ON CONFLICT necesita saber POR CUAL restriccion chocar.
--                Es la que pusiste en tags.nombre en 01_esquema.sql. Si aca
--                te tira "no unique or exclusion constraint matching the ON
--                CONFLICT specification", el problema no esta aca: esta en
--                que no pusiste esa restriccion en el esquema.
-- ---------------------------------------------------------------------

INSERT INTO tags (nombre, unidad, descripcion)
SELECT tag, unidad, descripcion
FROM staging_limites
ON CONFLICT (nombre) DO UPDATE
    SET unidad      = EXCLUDED.unidad,
        descripcion = EXCLUDED.descripcion;

-- Para cada fila de staging_limites:
--     si nombre no existe en tags:
--         INSERT
--     si nombre ya existe:
--         UPDATE unidad y descripcion

-- ---------------------------------------------------------------------
-- Paso 2  -  limites
--
-- Aca aparecen las dos cosas nuevas de este archivo: el JOIN que resuelve el
-- tag_id, y los casts de texto a numero.
--
-- El JOIN, en criollo: staging_limites tiene el texto "TT-101"; vos necesitas
-- el numero que tags le asigno. Eso se resuelve cruzando las dos tablas por
-- el unico dato que comparten, que es el nombre:
--
--     FROM staging_limites s
--     JOIN tags t ON t.nombre = s.tag
--
-- Fijate lo que acaba de pasar: buscaste una traduccion "texto -> id" con un
-- JOIN, no con un bucle. Eso es pensar en conjuntos, y es la diferencia
-- mental entre Semana 3 y Semana 4.
--
-- Los casts: staging tiene TEXT, limites quiere numeros. Se convierte con
--     s.minimo::NUMERIC
-- (la sintaxis :: es de Postgres; el estandar es CAST(s.minimo AS NUMERIC) y
-- las dos hacen lo mismo).
--
-- TODO: escribi el INSERT INTO limites (...) SELECT ... FROM ... JOIN ...
--       + los casts + el ON CONFLICT.
--       Pista: si el cast falla con "invalid input syntax for type numeric",
--       mira QUE fila lo hizo fallar antes de tocar el SQL. En limites.csv no
--       deberia pasar (son seis filas escritas a mano), y si pasa, el dato
--       esta mal, no la consulta.
-- ---------------------------------------------------------------------

INSERT INTO limites (tag_id, minimo, maximo)
SELECT t.tag_id, s.minimo::NUMERIC, s.maximo::NUMERIC
FROM staging_limites s
JOIN tags t ON t.nombre = s.tag
ON CONFLICT (tag_id) DO UPDATE
    SET minimo = EXCLUDED.minimo,
        maximo = EXCLUDED.maximo;



-- ---------------------------------------------------------------------
-- Paso 3  -  readings
--
-- Mismo patron que el paso 2, con dos diferencias: son 864 filas en vez de 6,
-- y hay un cast mas interesante.
--
-- El timestamp: el CSV trae "2026-08-24T06:00:00", que es ISO-8601. Postgres
-- lo entiende sin ayuda con un cast a TIMESTAMP. Es la contracara de lo que
-- hace tagframe/limpieza.py con format="ISO8601": el mismo formato, la misma
-- decision, otro motor.
--
-- Y aca esta la trampa de este archivo:
--
--   Postgres NO tiene un "errors=coerce". Si UNA sola fila no se puede
--   castear, no falla esa fila: falla el INSERT ENTERO y no entra ninguna de
--   las 864. Todo o nada.
--
--   Por eso funciona con sensores_planta.csv (que ya esta limpio) y por eso
--   sensores_sucios.csv necesita pasar antes por tagframe. La base no es el
--   lugar donde se limpia: es el lugar donde se guarda lo que ya esta limpio.
--
-- La unidad: fijate que readings NO tiene columna unidad, aunque el CSV la
-- traiga. Es a proposito: la unidad ya vive en tags, una sola vez. Guardarla
-- tambien en cada lectura seria repetir 864 veces un dato que no cambia, y
-- abrir la puerta a que un dia no coincidan. Eso se llama anomalia de
-- actualizacion, y evitarla es medio punto de por que existe la normalizacion.
--
-- TODO: escribi el INSERT INTO readings (...) SELECT ... FROM ... JOIN ...
--       + los casts (TIMESTAMP y NUMERIC) + el ON CONFLICT.
--       Pista: el ON CONFLICT de esta tabla choca contra DOS columnas
--       juntas, no una. Es la restriccion UNIQUE (tag_id, "timestamp") de
--       01_esquema.sql.
-- ---------------------------------------------------------------------

INSERT INTO readings(tag_id, "timestamp", valor, calidad)
SELECT t.tag_id, s.ts::TIMESTAMP, s.valor::NUMERIC, s.calidad
FROM staging_lecturas s
JOIN tags t ON t.nombre = s.tag
ON CONFLICT (tag_id, "timestamp") DO NOTHING;

-- ---------------------------------------------------------------------
-- Limpieza del staging
--
-- Ya cumplio: los datos estan en las tablas de verdad. Dejarlo ahi es dejar
-- una copia desactualizada de todo, esperando a que alguien la confunda con
-- el dato bueno.
--
-- Sin IF EXISTS a proposito, al reves que en 02: si llegaste hasta aca las
-- dos tablas existen si o si. Que falle fuerte si no estan.
--
-- (Si estas debugueando y todavia queres mirarlas, comenta esta parte. Pero
-- que quede comentada a proposito, con una nota, no olvidada.)
--
-- Consecuencia a tener presente: despues de esto, 03 solo no se puede volver
-- a correr, porque el staging ya no existe. La prueba de idempotencia del
-- checklist es correr 02 + 03 dos veces, y que readings siga en 864.
-- ---------------------------------------------------------------------

DROP TABLE staging_limites;
DROP TABLE staging_lecturas;



-- =====================================================================
-- Verificacion de ESTE archivo (el detalle esta en 04_verificar.sql):
--
--     SELECT COUNT(*) FROM tags;      -- 6
--     SELECT COUNT(*) FROM readings;  -- 864
--
-- Y despues, LA prueba que importa: corre este mismo archivo OTRA VEZ.
--
--     psql -U postgres -h localhost -d industrial -f sql/03_carga.sql
--
-- Si readings sigue en 864, tu ON CONFLICT esta bien.
-- Si te dio 1728, te falto el ON CONFLICT (o te falto la restriccion UNIQUE
-- en el esquema, que es lo mismo mirado desde el otro lado).
--
-- Ojo: para la segunda corrida vas a tener que volver a correr 02_staging.sql
-- primero, porque el DROP de arriba se llevo las tablas de staging. Ese ida y
-- vuelta es justamente lo que resuelve scripts/cargar_db.ps1.
-- =====================================================================
