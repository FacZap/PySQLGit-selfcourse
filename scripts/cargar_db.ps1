# Carga los CSV de data/ en la base PostgreSQL "industrial".
#
#   powershell -ExecutionPolicy Bypass -File scripts\cargar_db.ps1
#
# ESQUELETO DE SEMANA 4: los .sql de sql/ los escribis vos (ver guia-sem4.md).
# Este script solo se ocupa de la parte aburrida y repetitiva: encontrar
# psql.exe, arreglar el encoding, y correr los cuatro archivos EN ORDEN desde
# el directorio correcto.
#
# Devuelve 0 si todo paso, 1 si algo fallo. Misma convencion que
# scripts\verificar.ps1.
#
# NUNCA pongas la password aca adentro. Este archivo se commitea.

$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

# Los .sql usan rutas relativas en los \copy (data/limites.csv). Esas rutas se
# resuelven desde el directorio donde CORRE psql, no desde donde vive el .sql.
# El Set-Location de arriba es lo que hace que funcionen: no lo saques.

# psql no viene en el PATH cuando instalas PostgreSQL en Windows con el
# instalador oficial. En esta maquina vive en E:\Program Files\PostgreSQL18\18\bin\
# (la ruta por defecto habria sido C:\Program Files\PostgreSQL\<version>\bin\, pero
# no es la que elegiste al instalar).
$BaseDeDatos = "industrial"
$Usuario     = "postgres"
$Servidor    = "localhost"

$Archivos = @(
    "sql\01_esquema.sql",
    "sql\02_staging.sql",
    "sql\03_carga.sql",
    "sql\04_verificar.sql"
)


function Buscar-Psql {
    <#
    Devuelve la ruta a psql.exe, o $null si no lo encuentra.
    #>

    # TODO: 1) si psql ya esta en el PATH, usa ese y listo.
    #          Pista: Get-Command psql -ErrorAction SilentlyContinue
    #          (mismo patron que usa Invocar-Paso en scripts\verificar.ps1)

    # TODO: 2) si no esta, buscalo en el disco. OJO con la ruta: NO es la
    #          ruta por defecto del instalador. En esta maquina psql vive en
    #              E:\Program Files\PostgreSQL18\18\bin\psql.exe
    #          y el default habria sido C:\Program Files\PostgreSQL\18\bin\.
    #          Pista: armate una lista con las dos raices posibles y recorrela
    #          con Get-ChildItem, dejando comodin en la version:
    #              "E:\Program Files\PostgreSQL18\*\bin\psql.exe"
    #              "C:\Program Files\PostgreSQL\*\bin\psql.exe"
    #          Si aparece mas de una version, quedate con la mas nueva: ordena
    #          por nombre descendente y toma la primera.
    #          Hoy en tu maquina hay una sola: la 18, en E:.

    # TODO: 3) si no aparece por ningun lado, devolve $null. El que llama
    #          decide que hacer; esta funcion solo busca.

    return $null
}


function Invocar-Sql {
    param([string]$RutaPsql, [string]$Archivo)

    Write-Host ""
    Write-Host "==> $Archivo" -ForegroundColor Cyan

    # TODO: invoca psql con los argumentos que corresponden:
    #         -U $Usuario  -h $Servidor  -d $BaseDeDatos  -f $Archivo
    #
    #       Pista 1: psql.exe esta en "E:\Program Files\...", con espacios en
    #                la ruta. Para ejecutarlo hace falta el operador de
    #                llamada:  & $RutaPsql @argumentos
    #
    #       Pista 2: agregale -v ON_ERROR_STOP=1
    #                Por defecto psql, al leer un archivo, si una instruccion
    #                falla SIGUE con la siguiente y termina devolviendo exito.
    #                O sea: el esquema queda a medias y el script te dice que
    #                todo salio bien. Con ON_ERROR_STOP=1 corta en el primer
    #                error y devuelve un exit code distinto de cero, que es lo
    #                que este script necesita para poder avisarte.
    #
    #       Pista 3: revisa $LASTEXITCODE despues de la llamada, igual que
    #                hace scripts\verificar.ps1.

    # TODO: devolve $true si salio bien, $false si fallo.
    return $false
}


# --- Preparacion del entorno ---------------------------------------------

# TODO: setea $env:PGCLIENTENCODING = "UTF8" antes de conectarte.
#       Por que: los CSV de data/ son UTF-8, pero la consola de Windows le
#       dice a psql que hable WIN1252. Sin esto, las descripciones con
#       caracteres no ASCII llegan rotas a la base. Y una vez que entraron
#       rotas, ya entraron: no se arreglan mirando la consulta.

# TODO: la password.
#       Este script NO la pide ni la guarda. Tenes dos caminos, elegi uno y
#       deja anotado cual:
#
#         (a) Dejar que psql la pregunte. Con cuatro archivos te la va a
#             pedir cuatro veces. Molesto pero explicito.
#
#         (b) Setear $env:PGPASSWORD en TU sesion de PowerShell antes de
#             correr este script (no aca adentro). Vive solo mientras la
#             ventana este abierta y no toca ningun archivo.
#
#         (c) Un archivo %APPDATA%\postgresql\pgpass.conf con la linea
#             localhost:5432:*:postgres:tu_password
#             Vive fuera del repo, asi que no hay riesgo de commitearlo. Es
#             lo mas comodo si vas a laburar varios dias seguidos con esto.
#
#       Lo que NO va nunca: la password escrita en este archivo, ni en un
#       .sql, ni en nada que git pueda ver. Es la misma trampa que marca
#       guia-a-futuro.md:97-100.


# --- Corrida --------------------------------------------------------------

$psql = Buscar-Psql
if (-not $psql) {
    Write-Host "psql.exe no encontrado. Instala PostgreSQL o agregalo al PATH." -ForegroundColor Red
    Write-Host "Ver guia-sem4.md, Parte 0." -ForegroundColor Yellow
    exit 1
}

Write-Host "psql: $psql" -ForegroundColor DarkGray

# TODO: recorre $Archivos EN ORDEN llamando a Invocar-Sql, y corta en la
#       primera falla.
#
#       Por que cortar y no seguir (esto es distinto de verificar.ps1, que
#       corre todos los pasos y recien al final reporta): los .sql tienen
#       dependencias entre si. Si 01 fallo, no existen las tablas, y correr 02
#       genera una catarata de errores que no dicen nada sobre el problema
#       real. Un solo error claro vale mas que veinte confusos.
#
#       Guarda cual fallo para poder nombrarlo en el mensaje final.

$fallo = $null

# TODO: el bucle va aca.


Write-Host ""
if ($fallo) {
    Write-Host "RESULTADO: fallo en $fallo" -ForegroundColor Red
    exit 1
}

Write-Host "RESULTADO: base '$BaseDeDatos' cargada" -ForegroundColor Green
exit 0


# --- Antes de correr esto por primera vez ---------------------------------
#
# La base "industrial" tiene que existir. Este script no la crea: no se puede
# crear una base desde adentro de si misma, hace falta conectarse a otra
# primero. Es un paso de una sola vez:
#
#     & "E:\Program Files\PostgreSQL18\18\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE industrial;"
#
# Detalle: no lleva -d. Sin -d, psql se conecta a la base que se llama igual
# que el usuario (postgres), que existe siempre. Desde ahi si podes crear otra.
