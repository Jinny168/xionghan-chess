# Android 客户端

Android 版是轻量原生客户端，界面使用与 Web 端相同的页面，规则、AI、房间和 WebSocket 协议均由同一 FastAPI 服务提供，避免移动端复制规则代码。

## 安装

1. 将 `release/XionghanChess-Android-3.2.0.apk` 传到 Android 设备。
2. 允许系统从当前文件管理器安装未知来源应用。
3. 安装并启动“匈汉象棋”。
4. 首次启动输入 FastAPI 服务地址。

地址示例：

- Android 模拟器访问开发机：`http://10.0.2.2:8000/`
- 同一局域网手机访问电脑：`http://192.168.1.10:8000/`
- 公网 Docker 服务：`https://chess.example.com/`

应用右上角菜单提供“刷新”和“服务器设置”，可随时更换地址。

## 构建

需要 .NET 9 Android workload：

```powershell
cd android
dotnet publish XionghanChessAndroid.csproj -c Release -f net9.0-android -p:AndroidPackageFormat=apk
```

签名 APK 输出于：

`android/bin/Release/net9.0-android/publish/com.xionghan.chess-Signed.apk`

## 服务端要求

手机必须能访问 FastAPI 服务的 HTTP/HTTPS 端口，服务端 WebSocket 与页面同源。局域网使用时需允许 Windows 防火墙放行对应端口；公网部署建议使用 HTTPS/WSS 反向代理。
