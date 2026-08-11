# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\27415\\PycharmProjects\\xionghan-chess\\xionghan-chess-next\\packaging\\desktop_entry.py'],
    pathex=['C:\\Users\\27415\\PycharmProjects\\xionghan-chess\\xionghan-chess-next\\src'],
    binaries=[],
    datas=[('C:\\Users\\27415\\PycharmProjects\\xionghan-chess\\xionghan-chess-next\\src\\xionghan_chess\\desktop\\resources', 'xionghan_chess\\desktop\\resources'), ('C:\\Users\\27415\\PycharmProjects\\xionghan-chess\\xionghan-chess-next\\src\\xionghan_chess\\core\\data', 'xionghan_chess\\core\\data'), ('C:\\Users\\27415\\PycharmProjects\\xionghan-chess\\xionghan-chess-next\\locales', 'locales')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='匈漢象棋-1.2.0-桌面版',
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
    icon=['C:\\Users\\27415\\PycharmProjects\\xionghan-chess\\xionghan-chess-next\\src\\xionghan_chess\\desktop\\resources\\icon.ico'],
)
