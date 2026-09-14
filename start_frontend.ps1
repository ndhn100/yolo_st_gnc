param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Khong tim thay venv. Hay tao moi truong Python va cai requirements.txt truoc.'
}
& $projectPython (Join-Path $PSScriptRoot 'src\web_app.py') --port $Port
exit $LASTEXITCODE
