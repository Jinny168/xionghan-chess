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
$productName = -join [char[]](0x5308, 0x6F22, 0x8C61, 0x68CB)
$platformName = -join [char[]](0x684C, 0x9762, 0x7248)
$artifactName = "$productName-1.4.0-$platformName"
& $Python -m PyInstaller --noconfirm --clean --onefile --name $artifactName --windowed --icon $icon --add-data "$(Join-Path $ProjectRoot 'src\xionghan_chess\desktop\resources');xionghan_chess\desktop\resources" --add-data "$(Join-Path $ProjectRoot 'src\xionghan_chess\core\data');xionghan_chess\core\data" --add-data "$(Join-Path $ProjectRoot 'locales');locales" --paths (Join-Path $ProjectRoot "src") --distpath $release --workpath $work --specpath $work (Join-Path $PSScriptRoot "desktop_entry.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item -LiteralPath (Join-Path $release "$artifactName.exe") -Destination (Join-Path $release "$productName-$platformName.exe") -Force
Write-Host "Build completed: $release\$artifactName.exe"
