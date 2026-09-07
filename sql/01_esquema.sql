-- =====================================================================
-- 01_esquema.sql  -  Semana 4  -  ESQUELETO PARA COMPLETAR
--
-- Responsabilidad: crear la FORMA de la base. Ninguna fila entra aca.
-- (Meter datos es trabajo de 02_staging.sql y 03_carga.sql.)
--
-- Como correrlo, parado en la raiz del repo:
--     psql -U postgres -h localhost -d industrial -f sql/01_esquema.sql
--
-- OJO: la base "industrial" tiene que existir ANTES. No se puede crear una
-- base desde adentro de si misma. Ver guia-sem4.md, Parte 0.
--
-- Este archivo esta escrito SIN acentos a proposito: psql en Windows asume
-- WIN1252 y los .sql con acentos se ven rotos en la consola. Las guias .md
-- si llevan acentos, ahi no hay consola de por medio.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Idempotencia del esquema
--
-- Mientras estas aprendiendo vas a correr este archivo muchas veces. Sin
-- esto, la segunda corrida falla con: relation "tags" already exists.
--
-- TODO: escribi los DROP de las tres tablas y la vista.
--       Pista 1: el orden IMPORTA. No podes borrar tags si readings todavia
--                le apunta con una clave foranea. Va al reves de como se
--                crean: primero lo que depende, ultimo lo que es dependido.
--       Pista 2: la vista se borra con DROP VIEW, no con DROP TABLE.
--       Pista 3: agregales IF EXISTS para que no exploten la primera vez,
--                cuando todavia no hay nada que borrar.
--       Pista 4: existe CASCADE, que borra en cascada lo que dependa. Es
--                comodo y es peligroso. Si lo usas, que sea porque decidiste
--                usarlo, no para tapar un error de orden.
-- ---------------------------------------------------------------------



-- ---------------------------------------------------------------------
-- tags  -  el catalogo. UNA fila por sensor. Se llena desde limites.csv.
--
-- Por que existe: data/sensores_planta.csv repite el texto "TT-101,degC"
-- 144 veces. En una base eso no se guarda 144 veces: se guarda UNA, aca, y
-- las lecturas apuntan con un numero. Eso es normalizar.
--
-- Por que el catalogo sale de limites.csv y no de sensores_planta.csv:
-- limites.csv es la fuente autoritativa (tiene unidad Y descripcion, y es lo
-- que alguien mantiene a mano). El CSV de lecturas es un export: si un
-- sensor no midio nada hoy, no aparece, y no por eso deja de existir.
-- ---------------------------------------------------------------------
CREATE TABLE tags (
    tag_id
        -- TODO: entero autoincremental, y es la PRIMARY KEY de la tabla.
        --       Pista: tenes dos formas en Postgres. SERIAL (la vieja, la
        --       que usa la chuleta de guia-a-futuro.md:133) y
        --       GENERATED ALWAYS AS IDENTITY (la del estandar SQL, la
        --       recomendada desde PG10). Elegi a conciencia, no por inercia,
        --       y deja anotado por que.

    nombre
        -- TODO: el texto "TT-101" del CSV.
        --       Dos preguntas definen las restricciones de esta columna:
        --       puede faltar? puede repetirse?
        --       La respuesta a la SEGUNDA es la que despues necesita el
        --       ON CONFLICT de 03_carga.sql para saber "a este tag ya lo
        --       tengo". Si no pones esa restriccion aca, alla no vas a tener
        --       contra que chocar.

    unidad
        -- TODO: "degC", "bar", "m3/h". Texto obligatorio.

    descripcion
        -- TODO: "Temperatura de salida del reactor". Texto.
        --       Este SI puede quedar vacio sin que se rompa nada. Decidilo
        --       vos: NULL permitido o NOT NULL?
);


-- ---------------------------------------------------------------------
-- limites  -  el rango sano de cada tag. Tambien sale de limites.csv.
--
-- Por que tabla aparte y no dos columnas mas en tags:
-- son dos cosas distintas. tags dice QUE es el sensor (identidad, no cambia
-- nunca). limites dice COMO se opera hoy (ingenieria de proceso, cambia
-- cuando cambia la receta). Mezclarlas te obliga a tocar el catalogo de
-- sensores cada vez que alguien afloja un setpoint.
--
-- Es una relacion 1 a 1, y eso esta bien: separar por "cada cuanto cambia"
-- es un motivo tan valido como separar por "cuantos hay".
-- ---------------------------------------------------------------------
CREATE TABLE limites (
    tag_id
        -- TODO: aca pasan DOS cosas a la vez y conviene verlas separadas:
        --       (a) es la PRIMARY KEY de esta tabla -> un tag no puede tener
        --           dos juegos de limites al mismo tiempo;
        --       (b) es FOREIGN KEY apuntando a tags(tag_id) -> no podes
        --           definir limites para un sensor que no existe.
        --       Las dos se pueden escribir en la misma linea de columna.

    minimo
        -- TODO: numero. Que tipo? Ver la nota "NUMERIC vs REAL" al final.

    maximo
        -- TODO: idem minimo.

    -- TODO: una restriccion de TABLA (no de columna) que impida guardar un
    --       rango imposible, con minimo mayor o igual al maximo.
    --       Pista: se llama CHECK y va como una linea mas, despues de las
    --       columnas. Ponele nombre propio con la forma
    --           CONSTRAINT limites_rango_valido CHECK (...)
    --       para que el dia que falle, el error de Postgres te diga QUE
    --       regla rompiste y no un ilegible "limites_check1".
);


-- ---------------------------------------------------------------------
-- readings  -  las 864 mediciones. La tabla gorda, la que va a crecer.
-- ---------------------------------------------------------------------
CREATE TABLE readings (
    reading_id
        -- TODO: mismo criterio que elegiste para tags.tag_id. Se consistente.

    tag_id
        -- TODO: entero, obligatorio, FOREIGN KEY a tags(tag_id).
        --       Esta es LA linea que convierte esto en un esquema relacional
        --       y no en tres planillas sueltas: de aca en adelante es
        --       IMPOSIBLE meter una lectura de un tag inexistente. No es una
        --       validacion que escribis vos y algun dia te olvidas de
        --       llamar: la hace el motor, en cada INSERT, siempre.

    "timestamp"
        -- TODO: el momento de la medicion. Tipo TIMESTAMP.
        --
        --       Sobre las comillas dobles: timestamp es TAMBIEN un nombre de
        --       tipo en SQL, asi que hay que escribirlo "timestamp" con
        --       comillas dobles aca y en TODAS las consultas futuras. Es la
        --       via que eligio la chuleta (guia-a-futuro.md:141).
        --       Alternativa igual de valida: llamala medido_en y no peleas
        --       nunca mas. Si la renombras, acordate de renombrarla tambien
        --       en 03_carga.sql, en 04_verificar.sql y en la vista de abajo.

    valor
        -- TODO: el numero medido. Ver "NUMERIC vs REAL" al final.

    calidad
        -- TODO: "Good" / "Bad" / "Uncertain". Texto obligatorio.
        --       Opcional, si te queda tiempo: un CHECK que solo acepte esos
        --       tres valores. Pensa antes si te conviene: el dia que el
        --       historiador invente un cuarto estado, ese CHECK te rechaza
        --       la carga entera.

    -- TODO: una restriccion de tabla que diga "no puede haber dos lecturas
    --       del mismo tag en el mismo instante".
    --       Por que la necesitas SI O SI: sin ella, correr 03_carga.sql dos
    --       veces te deja 1728 filas en vez de 864, y el ON CONFLICT de ese
    --       archivo no tiene contra que chocar. La idempotencia se decide
    --       ACA, en el esquema, no despues a mano con un DELETE.
);


-- ---------------------------------------------------------------------
-- Indice  -  esto es una DECISION, no un TODO de tipear
--
-- La chuleta de guia-a-futuro.md:146 propone:
--     CREATE INDEX idx_readings_tag_ts ON readings (tag_id, "timestamp");
--
-- Antes de copiarla, pensala: si arriba pusiste UNIQUE (tag_id, "timestamp"),
-- Postgres YA creo por su cuenta un indice sobre esas dos columnas, porque lo
-- necesita para hacer cumplir esa restriccion. Este CREATE INDEX seria un
-- SEGUNDO indice identico: no acelera ninguna consulta y encarece cada
-- INSERT y cada UPDATE (guia-a-futuro.md:300).
--
-- No me creas: comprobalo. Crea la tabla, corre en psql
--     \d readings
-- y mira la lista de indices que ya tiene.
--
-- TODO: decidi si esta linea va o no va, y deja el motivo escrito en un
--       comentario. La decision documentada vale mas que la linea.
-- ---------------------------------------------------------------------



-- ---------------------------------------------------------------------
-- alarmas  -  VISTA, no tabla.
--
-- Que es una vista, en criollo: una consulta guardada con nombre. No ocupa
-- lugar y no guarda filas propias; cada vez que le haces SELECT, se vuelve a
-- calcular sobre las tablas reales.
--
-- Por que vista y no tabla: una alarma no es un dato que alguien mide, es una
-- CONCLUSION sobre un dato (valor fuera de rango). Si manana ingenieria sube
-- el maximo de TT-101 de 95 a 100, una tabla de alarmas te quedaria llena de
-- alarmas viejas que ya no son alarmas y habria que salir a corregirlas. La
-- vista se corrige sola, porque no guardo nada: vuelve a mirar limites.
--
-- TODO: escribi  CREATE VIEW alarmas AS  seguido de un SELECT que cruce las
--       tres tablas y devuelva SOLO las lecturas fuera de rango.
--
--       Pista 1: son dos JOIN sobre readings.
--                readings -> tags     (para tener el nombre "TT-101")
--                readings -> limites  (para tener minimo y maximo)
--
--       Pista 2: la condicion de alarma es
--                    valor < minimo OR valor > maximo
--                ESTRICTO. Ni <= ni >=: el borde exacto NO es alarma, 60.0 y
--                95.0 estan EN rango. Esto no me lo invente: es lo que ya
--                hace Limite.en_alarma en tagstats/modelos.py y lo repite
--                tagframe/analisis.py. Si aca lo escribis con <=, vas a
--                contar mas alarmas que Python y vas a perder una tarde
--                buscando de donde sale la diferencia.
--
--       Pista 3: devolve al menos nombre, "timestamp", valor, minimo, maximo.
--                El que mira una alarma no quiere saber solo QUE se paso,
--                quiere ver DE CUANTO se paso.
--
--       Oraculo: cuando este cargado todo, esta vista tiene que tener
--                exactamente 34 filas (README.md:64).
-- ---------------------------------------------------------------------



-- =====================================================================
-- NUMERIC vs REAL  -  la decision de tipo que mas se paga despues
--
--   REAL / DOUBLE PRECISION -> coma flotante. Rapido, y con error de
--       redondeo inevitable: 0.1 + 0.2 no da exactamente 0.3.
--   NUMERIC -> decimal exacto. Mas lento, sin sorpresas.
--
-- Para un valor de proceso cualquiera de los dos sirve. Para plata, NUMERIC
-- siempre y sin discusion. La chuleta (guia-a-futuro.md:142) usa NUMERIC. Si
-- elegis otra cosa, que sea por un motivo que puedas escribir en una linea.
--
-- Trampa que vas a chocar en Semana 6: NUMERIC llega a Python (via psycopg2)
-- como Decimal, no como float. Decimal y float no se mezclan sin castear.
-- =====================================================================


-- =====================================================================
-- Verificacion de ESTE archivo (Semana 4 se verifica a mano, en psql):
--
--     \dt          -> tiene que listar tags, limites, readings
--     \dv          -> tiene que listar alarmas
--     \d readings  -> mira columnas, la FK, y QUE INDICES quedaron
--
-- Todavia no hay ni una sola fila. Los datos son 02 y 03.
-- =====================================================================
