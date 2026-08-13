$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { py -3.11 -m venv (Join-Path $ProjectRoot ".venv") }
& $Python -m pip install -e $ProjectRoot
$Port = if ($env:PORT) { $env:PORT } else { "8000" }
& $Python -m uvicorn xionghan_chess.service.app:app --host 0.0.0.0 --port $Port

