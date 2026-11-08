# -*- mode: python ; coding: utf-8 -*-
# ⚠️ 已废弃，不要用于发版：本文件 `collect_all("PySide6")` 会把整个 site-packages
# 里的 PySide6（含 194 MB 的 Qt6WebEngineCore 等）全部打进产物 —— 这正是历史上
# 「手动补齐依赖才造出 163 MB EXE」的来源。
# 正式构建请用 `packaging/build_windows.spec`（含 S2-6 的 Qt 裁剪，实测 55 MB），
# 由 `packaging/build_windows.ps1` 调用。保留本文件只为追溯。
from PyInstaller.utils.hooks import collect_all
datas, binaries, hiddenimports = collect_all("PySide6")
datas += [("../src/xionghan_chess/desktop/resources", "xionghan_chess/desktop/resources")]
a = Analysis(["desktop_entry.py"], pathex=["../src"], binaries=binaries, datas=datas, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="XionghanChess", console=False,
          icon="../src/xionghan_chess/desktop/resources/icon.ico")
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="XionghanChess")
