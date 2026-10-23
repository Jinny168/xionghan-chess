# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（Windows / onefile）。

## 为什么从命令行改成 spec

阶段2 S2-6 原本的计划是用 `--exclude-module` 裁掉未使用的 Qt 模块。**实测这条路无效**：

- 46 个 `--exclude-module PySide6.QtXxx` 全加上，产物 73,458,712 B；
  一个都不加，产物 73,542,180 B —— 差 83 KB，属压缩噪声；
- 两次构建的 Analysis TOC 里，`Qt6Qml.dll` / `Qt6Quick.dll` / `Qt6Pdf.dll` /
  `opengl32sw.dll` 一个都没少。

原因：`--exclude-module` 只影响 **import 图分析**，而 PySide6 的 hook 是按
site-packages 里的实际文件**直接收**二进制与数据的，不走 import 判定。
要真的裁掉，只能在 `Analysis` 之后过滤 `a.binaries` / `a.datas` —— 这只能在
spec 里做，命令行的开关没有对应能力。

## 判断哪些能删的依据（实测，不是猜测）

构造一个完整 `MainWindow`（跑完字体注册、音频初始化、棋盘、线程池全装配链）
之后，`sys.modules` 里只有 6 个 Qt 子模块：
`QtCore` `QtGui` `QtWidgets` `QtNetwork` `QtWebSockets` `QtMultimedia`。
不在这 6 个里的 Qt 二进制，本程序运行期不会加载。

## 刻意**不删**的东西（都有理由，别顺手加进 DROP 列表）

- `avcodec-63.dll` / `avformat-63.dll` / `avutil-61.dll` / `swscale-10.dll`：
  Qt Multimedia 在 Windows 上默认走 FFmpeg 后端，BGM 是 OGG，删了就没声音。
- `libcrypto-3-x64.dll` / `libssl-3-x64.dll`：`QtNetwork` 的 HTTPS 依赖它们，
  删了「连服务器」与「检查更新」全废。
- `PySide6/translations/*_zh_CN.qm`：Qt 自带对话框的按钮文字（确定/取消/是/否）
  来自 Qt 翻译文件。删掉它们，中文界面里的消息框会退回英文。
- `plugins/` 整体：`platforms/qwindows.dll`（没有它程序起不来）、
  `imageformats/`（webp/jpeg 头像）、`styles/` 都在这里。
"""

import os

# SPECPATH 是 PyInstaller 注入的全局变量（本 spec 所在目录 = packaging/）。
PROJECT = os.path.dirname(SPECPATH)
ENTRY = os.path.join(SPECPATH, "desktop_entry.py")

# 产物文件名由构建脚本通过环境变量传入，避免 PS 与 spec 各写一份版本号。
EXE_NAME = os.environ.get("XIONGHAN_EXE_NAME", "XionghanChess")

# 只在非加载模块里出现的 Qt 二进制（见模块 docstring 的实测依据）。
# `opengl32sw.dll` 是软件 OpenGL 回退实现，19.7 MB —— 本程序是 QWidget 光栅绘制，
# 不走 OpenGL；它只在显卡驱动缺失且程序请求 OpenGL 时才被用到。
DROP_BINARIES = {
    "opengl32sw.dll",
    "Qt6Quick.dll", "Qt6Qml.dll", "Qt6Pdf.dll", "Qt6OpenGL.dll",
    "Qt6Designer.dll", "Qt6Charts.dll", "Qt6Sql.dll", "Qt6Svg.dll",
    "Qt6Bluetooth.dll", "Qt6Nfc.dll", "Qt6Positioning.dll", "Qt6SerialPort.dll",
    "Qt6Sensors.dll", "Qt6StateMachine.dll", "Qt6TextToSpeech.dll",
    "Qt6VirtualKeyboard.dll", "Qt6RemoteObjects.dll", "Qt6Scxml.dll",
    "Qt6NetworkAuth.dll", "Qt6HttpServer.dll", "Qt6Concurrent.dll",
    # 对应的 Python 绑定（.pyd）：留着会变成「dll 没了、import 还在」的坏状态。
    "QtQuick.pyd", "QtQml.pyd", "QtPdf.pyd", "QtOpenGL.pyd", "QtDesigner.pyd",
    "QtCharts.pyd", "QtSql.pyd", "QtSvg.pyd", "QtUiTools.pyd", "QtHelp.pyd",
    "QtTest.pyd", "QtBluetooth.pyd", "QtPositioning.pyd", "QtSerialPort.pyd",
    "QtSensors.pyd", "QtStateMachine.pyd", "QtTextToSpeech.pyd",
    "QtRemoteObjects.pyd", "QtScxml.pyd", "QtNetworkAuth.pyd",
    "QtHttpServer.pyd", "QtConcurrent.pyd", "QtQmlModels.pyd",
}

datas = [
    (os.path.join(PROJECT, "src", "xionghan_chess", "desktop", "resources"),
     os.path.join("xionghan_chess", "desktop", "resources")),
    (os.path.join(PROJECT, "src", "xionghan_chess", "core", "data"),
     os.path.join("xionghan_chess", "core", "data")),
    (os.path.join(PROJECT, "locales"), "locales"),
]

a = Analysis(
    [ENTRY],
    pathex=[os.path.join(PROJECT, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# ---- S2-6 过滤：只留运行期真的会加载的 Qt 二进制 ----
_dropped = []
_kept = []
for entry in a.binaries:
    name = os.path.basename(entry[0])
    if name in DROP_BINARIES:
        _dropped.append(name)
    else:
        _kept.append(entry)
a.binaries = _kept
print(f"[S2-6] 裁掉 {len(_dropped)} 个未使用 Qt 二进制：{', '.join(sorted(set(_dropped)))}")

# ---- S2-6 过滤：Qt 翻译只留中文与英文 ----
_qt_translations = [entry for entry in a.datas
                    if entry[0].replace("\\", "/").startswith("PySide6/translations/")]
a.datas = [
    entry for entry in a.datas
    if not (entry[0].replace("\\", "/").startswith("PySide6/translations/")
            and not entry[0].endswith(("_zh_CN.qm", "_en.qm")))
]
print(f"[S2-6] Qt 翻译 {len(_qt_translations)} 个 -> "
      f"{len([e for e in a.datas if e[0].replace(chr(92), '/').startswith('PySide6/translations/')])} 个")

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT, "src", "xionghan_chess", "desktop", "resources", "icon.ico"),
)
