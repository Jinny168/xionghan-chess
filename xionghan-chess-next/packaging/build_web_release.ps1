$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ReleaseRoot = Join-Path $ProjectRoot "release"
$productName = -join [char[]](0x5308, 0x6F22, 0x8C61, 0x68CB)
$platformName = -join [char[]](0x7F51, 0x9875, 0x7248)
$PackageName = "$productName-1.3.0-$platformName"
$Stage = Join-Path $ReleaseRoot $PackageName
$Archive = Join-Path $ReleaseRoot "$PackageName.zip"

if (Test-Path -LiteralPath $Stage) {
    Remove-Item -LiteralPath $Stage -Recurse -Force
}
if (Test-Path -LiteralPath $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}

New-Item -ItemType Directory -Path $Stage -Force | Out-Null
foreach ($name in @("web", "locales", "requirements", "deploy", "scripts", "docs")) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot $name) -Destination $Stage -Recurse
}
New-Item -ItemType Directory -Path (Join-Path $Stage "src\xionghan_chess") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot "src\xionghan_chess\__init__.py") -Destination (Join-Path $Stage "src\xionghan_chess")
Copy-Item -LiteralPath (Join-Path $ProjectRoot "src\xionghan_chess\i18n.py") -Destination (Join-Path $Stage "src\xionghan_chess")
foreach ($name in @("core", "service")) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "src\xionghan_chess\$name") -Destination (Join-Path $Stage "src\xionghan_chess") -Recurse
}
foreach ($name in @("pyproject.toml", "README.md")) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot $name) -Destination $Stage
}
Get-ChildItem -LiteralPath $Stage -Directory -Filter "__pycache__" -Recurse |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $Stage -File -Filter "*.pyc" -Recurse |
    Remove-Item -Force

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $Stage,
    $Archive,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)
Copy-Item -LiteralPath $Archive -Destination (Join-Path $ReleaseRoot "$productName-$platformName.zip") -Force
Write-Host "Web release completed: $Archive"
