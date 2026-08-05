$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Project = Join-Path $ProjectRoot "android\XionghanChessAndroid.csproj"
$Publish = Join-Path $ProjectRoot "android\bin\Release\net9.0-android\publish"
$Release = Join-Path $ProjectRoot "release"
$Target = Join-Path $Release "XionghanChess-Android-3.2.0.apk"

dotnet publish $Project -c Release -f net9.0-android -p:AndroidPackageFormat=apk
$SignedApk = Join-Path $Publish "com.xionghan.chess-Signed.apk"
if (-not (Test-Path -LiteralPath $SignedApk)) {
    throw "Signed APK was not produced: $SignedApk"
}
Copy-Item -LiteralPath $SignedApk -Destination $Target -Force
Copy-Item -LiteralPath $SignedApk -Destination (Join-Path $Release "XionghanChess-Android.apk") -Force
Write-Host "Android release completed: $Target"
