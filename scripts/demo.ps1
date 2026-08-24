# Recorrido rapido por lo que hace el CLI. Sirve para la demo y para chequear
# a mano que nada se rompio despues de un cambio.
#
#   powershell -ExecutionPolicy Bypass -File scripts\demo.ps1

Set-Location (Split-Path $PSScriptRoot -Parent)

function Mostrar {
    param([string]$Titulo, [string[]]$Argumentos)
    Write-Host ""
    Write-Host "=== $Titulo" -ForegroundColor Cyan
    Write-Host "> python -m tagstats $($Argumentos -join ' ')" -ForegroundColor DarkGray
    python -m tagstats @Argumentos
    Write-Host "(codigo de salida: $LASTEXITCODE)" -ForegroundColor DarkGray
}

Mostrar "1. Resumen completo del turno" @("data/sensores_planta.csv", "-l", "data/limites.csv")
Mostrar "2. Un solo tag, en JSON" @("data/sensores_planta.csv", "-l", "data/limites.csv", "-t", "TT-101", "-f", "json")
Mostrar "3. Solo la ventana de la excursion" @("data/sensores_planta.csv", "-l", "data/limites.csv", "-t", "TT-101", "--desde", "2026-08-24T11:00", "--hasta", "2026-08-24T12:30")
Mostrar "4. Descartando muestras de calidad mala" @("data/sensores_planta.csv", "-l", "data/limites.csv", "--solo-confiables")
Mostrar "5. CSV sucio: corta y explica por que" @("data/sensores_sucios.csv", "-l", "data/limites.csv")
Mostrar "6. El mismo CSV sucio, tolerante" @("data/sensores_sucios.csv", "-l", "data/limites.csv", "--tolerante")
Mostrar "7. CSV sin filas" @("data/sensores_vacio.csv")
