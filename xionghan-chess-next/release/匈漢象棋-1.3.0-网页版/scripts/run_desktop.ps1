$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { py -3.11 -m venv (Join-Path $ProjectRoot ".venv") }
& $Python -m pip install -e "$ProjectRoot[desktop]"
& $Python -m xionghan_chess.desktop.app

