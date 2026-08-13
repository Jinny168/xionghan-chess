# Android v1.4.0 build requirements

This project uses .NET MAUI Android, not Gradle. The authoritative build file is `XionghanChessAndroid.csproj`.

- .NET SDK 9.0.3xx
- Android SDK platform 35
- Android build-tools 35.0.0
- JDK 17 or newer

Build commands:

```powershell
dotnet restore android/XionghanChessAndroid.csproj
dotnet publish android/XionghanChessAndroid.csproj -c Release -f net9.0-android -p:AndroidPackageFormat=apk
```
