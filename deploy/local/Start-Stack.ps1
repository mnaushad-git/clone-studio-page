# The one command for the local stack, from anywhere:
#   powershell -ExecutionPolicy Bypass -File deploy\local\Start-Stack.ps1
# Options: -Integration  real orders into the local Odoo container
#          -Action down | status
# See docs/deployment/local-stack.md.
param(
    [ValidateSet('up', 'down', 'status')][string]$Action = 'up',
    [switch]$Integration
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$envFile = Join-Path $here '.env.local'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker is not installed or not on PATH. See docs/deployment/local-stack.md.'
}

function New-Secret {
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

if (-not (Test-Path $envFile)) {
    $lines = Get-Content (Join-Path $here '.env.local.example') | ForEach-Object {
        if ($_ -match '^[A-Z_]+=$') { "$_$(New-Secret)" } else { $_ }
    }
    [IO.File]::WriteAllLines($envFile, [string[]]$lines)
    Write-Host "Created $envFile with new random secrets."
}

$composeArgs = @('--env-file', $envFile, '-f', (Join-Path $here 'docker-compose.yml'))
if ($Integration) { $composeArgs += @('-f', (Join-Path $here 'docker-compose.integration.yml')) }

function Compose {
    & docker compose @composeArgs @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose $args failed with exit code $LASTEXITCODE" }
}

switch ($Action) {
    'down' { Compose down }
    'status' { Compose ps }
    'up' {
        Compose build
        Compose up -d --wait terrific-postgres terrific-redis
        Compose run --rm terrific-migrate
        Compose run --rm terrific-migrate python -m app.scripts.seed_catalogue --apply
        Compose run --rm terrific-odoo-init
        Get-Content (Join-Path $here '..\odoo\bootstrap.py') -Raw |
            docker compose @composeArgs run --rm -T terrific-odoo-init shell --no-http
        if ($LASTEXITCODE -ne 0) { throw 'Odoo bootstrap failed.' }
        Compose up -d --wait
        Compose ps
    }
}
