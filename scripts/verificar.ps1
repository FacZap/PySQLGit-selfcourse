# Verificacion local: lo mismo que correria un CI antes de aceptar un cambio.
#
#   powershell -ExecutionPolicy Bypass -File scripts\verificar.ps1
#
# Devuelve 0 si todo pasa, 1 si algo falla. Las herramientas que no estan
# instaladas se avisan y se saltean, no rompen la corrida.

$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

$fallas = @()

function Invocar-Paso {
    param([string]$Titulo, [string]$Comando, [string[]]$Argumentos)

    Write-Host ""
    Write-Host "==> $Titulo" -ForegroundColor Cyan

    if (-not (Get-Command $Comando -ErrorAction SilentlyContinue)) {
        Write-Host "    OMITIDO: '$Comando' no esta instalado (pip install -r requirements-dev.txt)" -ForegroundColor Yellow
        return
    }

    & $Comando @Argumentos
    if ($LASTEXITCODE -ne 0) {
        $script:fallas += $Titulo
        Write-Host "    FALLO" -ForegroundColor Red
    }
    else {
        Write-Host "    OK" -ForegroundColor Green
    }
}

Invocar-Paso -Titulo "ruff (lint)" -Comando "ruff" -Argumentos @("check", ".")
Invocar-Paso -Titulo "black (formato)" -Comando "black" -Argumentos @("--check", ".")
Invocar-Paso -Titulo "pytest (pruebas)" -Comando "python" -Argumentos @("-m", "pytest")

Write-Host ""
if ($fallas.Count -gt 0) {
    Write-Host "RESULTADO: fallaron $($fallas.Count) paso(s): $($fallas -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host "RESULTADO: todo verde" -ForegroundColor Green
exit 0
