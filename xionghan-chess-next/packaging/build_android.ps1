$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Project = Join-Path $ProjectRoot "android\XionghanChessAndroid.csproj"
$Publish = Join-Path $ProjectRoot "android\bin\Release\net9.0-android\publish"
$Release = Join-Path $ProjectRoot "release"
$productName = -join [char[]](0x5308, 0x6F22, 0x8C61, 0x68CB)
$platformName = -join [char[]](0x5B89, 0x5353, 0x7248)
$Target = Join-Path $Release "$productName-1.3.0-$platformName.apk"
$AndroidSdkRoot = "C:\Program Files (x86)\Android\android-sdk"
$Aapt2ToolPath = $null
if (Test-Path -LiteralPath (Join-Path $AndroidSdkRoot "build-tools")) {
    $Aapt2ToolPath = Get-ChildItem -LiteralPath (Join-Path $AndroidSdkRoot "build-tools") -Directory |
        Sort-Object { [version]$_.Name } -Descending |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "aapt2.exe") } |
        Select-Object -First 1 -ExpandProperty FullName
}

$PublishArgs = @("publish", $Project, "-c", "Release", "-f", "net9.0-android", "-p:AndroidPackageFormat=apk")
if ($Aapt2ToolPath) {
    $PublishArgs += "-p:Aapt2ToolPath=$Aapt2ToolPath"
}
dotnet clean $Project -c Release -f net9.0-android
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
dotnet @PublishArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$SignedApk = Join-Path $Publish "com.xionghan.chess-Signed.apk"
if (-not (Test-Path -LiteralPath $SignedApk)) {
    throw "Signed APK was not produced: $SignedApk"
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$ApkArchive = [System.IO.Compression.ZipFile]::OpenRead($SignedApk)
$ApkArchive.Dispose()
Copy-Item -LiteralPath $SignedApk -Destination $Target -Force
Copy-Item -LiteralPath $SignedApk -Destination (Join-Path $Release "$productName-$platformName.apk") -Force
Write-Host "Android release completed: $Target"
