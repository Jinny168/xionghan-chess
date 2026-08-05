$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { py -3.11 -m venv (Join-Path $ProjectRoot ".venv") }
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m pip install -e "$ProjectRoot[desktop,build]"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$release = Join-Path $ProjectRoot "release"
$work = Join-Path $ProjectRoot "build-onefile"
$icon = Join-Path $ProjectRoot "src\xionghan_chess\desktop\resources\icon.ico"
& $Python -m PyInstaller --noconfirm --clean --onefile --name "XionghanChess-3.2.0" --windowed --icon $icon --collect-all PySide6 --add-data "$(Join-Path $ProjectRoot 'src\xionghan_chess\desktop\resources');xionghan_chess\desktop\resources" --paths (Join-Path $ProjectRoot "src") --distpath $release --workpath $work --specpath $work (Join-Path $PSScriptRoot "desktop_entry.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item -LiteralPath (Join-Path $release "XionghanChess-3.2.0.exe") -Destination (Join-Path $release "XionghanChess.exe") -Force
Write-Host "Build completed: $release\XionghanChess-3.2.0.exe"
