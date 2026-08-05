$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ReleaseRoot = Join-Path $ProjectRoot "release"
$PackageName = "XionghanChess-Web-3.2.0"
$Stage = Join-Path $ReleaseRoot $PackageName
$Archive = Join-Path $ReleaseRoot "$PackageName.zip"

if (Test-Path -LiteralPath $Stage) {
    Remove-Item -LiteralPath $Stage -Recurse -Force
}
if (Test-Path -LiteralPath $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}

New-Item -ItemType Directory -Path $Stage -Force | Out-Null
foreach ($name in @("web", "requirements", "deploy", "scripts", "docs")) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot $name) -Destination $Stage -Recurse
}
New-Item -ItemType Directory -Path (Join-Path $Stage "src\xionghan_chess") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot "src\xionghan_chess\__init__.py") -Destination (Join-Path $Stage "src\xionghan_chess")
foreach ($name in @("core", "service")) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "src\xionghan_chess\$name") -Destination (Join-Path $Stage "src\xionghan_chess") -Recurse
}
foreach ($name in @("pyproject.toml", "README.md")) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot $name) -Destination $Stage
}

Compress-Archive -LiteralPath $Stage -DestinationPath $Archive -CompressionLevel Optimal
Write-Host "Web release completed: $Archive"
