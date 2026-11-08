# Android 客户端

Android 版是轻量原生客户端。APK 内置离线双人同机棋盘，启动时即使服务器不可达也能进入；AI、网络房间、聊天和 WebSocket 对战由同一 FastAPI 服务提供。应用会定时检查服务器，连接恢复后自动切回完整在线页面。

## 安装

1. 将 `release/匈漢象棋-1.1.0-安卓版.apk` 传到 Android 设备。
2. 允许系统从当前文件管理器安装未知来源应用。
3. 安装并启动“匈汉象棋”。
4. 启动后可直接进行离线双人同机对战；需要 AI 或网络对战时，在“服务器设置”中填写 FastAPI 服务地址。

地址示例：

- Android 模拟器访问开发机：`http://10.0.2.2:8000/`
- 同一局域网手机访问电脑：`http://192.168.1.10:8000/`
- 公网 Docker 服务：`https://chess.example.com/`

应用右上角菜单提供“刷新”“离线同机”“重新连接”和“服务器设置”。服务器不可达时，人机与网络模式会保持禁用；健康检查成功后，在线功能自动恢复，无需重启应用。

## 构建

需要 .NET 9 Android workload：

```powershell
cd android
dotnet publish XionghanChessAndroid.csproj -c Release -f net9.0-android -p:AndroidPackageFormat=apk
```

签名 APK 输出于：

`android/bin/Release/net9.0-android/publish/com.xionghan.chess-Signed.apk`

## 服务端要求

离线双人同机对战不需要服务器。使用 AI、网络房间和聊天时，手机必须能访问 FastAPI 服务的 HTTP/HTTPS 端口，服务端 WebSocket 与页面同源。局域网使用时需允许防火墙放行对应端口；公网部署建议使用 HTTPS/WSS 反向代理，完整步骤见 [LINUX_DEPLOY.md](LINUX_DEPLOY.md)。

## 离线包与题库

Android 是 WebView 壳，断网时跑 `Resources/assets/offline/` 下的离线包（`index.html` +
`offline.js`）。它和 Web 端不是同一份代码：离线包是一份自包含的 JS 引擎，规则与
Python 核心由跨引擎对拍门禁（`tests/test_cross_engine.py`，84 条）保证一致。

**题库是生成物，不要手改。** `offline-puzzles.js` 由脚本从
`src/xionghan_chess/core/data/puzzles.json` 导出：

```bash
python scripts/build_offline_puzzles.py            # 重新生成
python scripts/build_offline_puzzles.py --check    # 校验是否与数据源一致
```

改完题库若忘记重新生成，`tests/test_offline_puzzles.py` 会红。该测试还会用
`scripts/offline_puzzle_probe.cjs` 把每条题面喂给离线引擎，确认**能载入且解法首着
合法**——数据对了不等于引擎认这个 document 结构。

训练入口用 `gameFromDocument()` 载入真实题面（此前的 3 条是手写的「开局走一步」），
判定按 `solution[step]` 逐手比对，答错会 `undo()` 退回题面，多步题支持继续下一手。
