# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
datas, binaries, hiddenimports = collect_all("PySide6")
datas += [("../src/xionghan_chess/desktop/resources", "xionghan_chess/desktop/resources")]
a = Analysis(["desktop_entry.py"], pathex=["../src"], binaries=binaries, datas=datas, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="XionghanChess", console=False,
          icon="../src/xionghan_chess/desktop/resources/icon.ico")
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="XionghanChess")
