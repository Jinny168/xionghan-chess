# 匈汉象棋 1.1.0 Release Notes

发布日期：2026-08-07

## 重点更新

- Windows、Web、Android 统一增加暂停/继续，并由公共核心与联网服务冻结计时。
- Android 保持沉浸式全屏，修复离线 Canvas 在输入命中时被清空导致棋盘不显示的问题。
- 三端统一时限与读秒提醒语义，补齐棋子样式、主题、合法落点、吃子提示和音量设置。
- Web/Android 联网页面新增自动棋谱、历史对局与统计；桌面新增本地棋谱库。
- Web 与 Android 优化 Canvas 尺寸生命周期、拖拽取消、前后台恢复和断线重连。
- 桌面端统一六组菜单，降低最小窗口尺寸并支持隐藏侧栏。

## 兼容性

- Android：API 21+；API 30+ 使用 WindowInsets 沉浸式方案。
- Windows：Windows 10/11 x64。
- Web：当前主流 Chromium、Firefox、Safari；移动端最低布局宽度 360 px。
- 棋谱：继续使用 `.xhgame` formatVersion 1，与 1.0.0 兼容；新增暂停字段对旧文件采用安全默认值。

## 验证基线

- `pytest`：49 项通过。
- Web JS 与 Android 离线 JS：`node --check` 通过。
- Android Debug：编译通过。
- 浏览器实测：1440 × 900 与 390 × 844 无水平溢出，暂停期间时钟稳定。
- Android 离线页：Canvas 点击前后像素尺寸保持一致，棋盘持续可见。
- Android APK 仅打包离线页实际使用的 4 个短音效，最终约 9.4 MB。

## 安装包

构建完成后应生成：

- `release/匈漢象棋-1.1.0-桌面版.exe`
- `release/匈漢象棋-1.1.0-网页版.zip`
- `release/匈漢象棋-1.1.0-安卓版.apk`

同时保留不带版本号的最新版别名，便于固定下载链接更新。
