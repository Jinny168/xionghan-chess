# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 收集声音文件
sounds_datas = [
    ("sounds/check.wav", "sounds"),
    ("sounds/move.wav", "sounds"),
    ("sounds/capture.wav", "sounds")
]

# 收集字体文件
fonts_datas = [
    ("fonts/fangsong.ttf", "fonts"),
    ("fonts/kaiti.ttf", "fonts"),
    ("fonts/msyh.ttc", "fonts"),
    ("fonts/simhei.ttf", "fonts"),
    ("fonts/simkai.ttf", "fonts"),
    ("fonts/xingkai.ttf", "fonts")
]

# 收集所有数据文件
datas = sounds_datas + fonts_datas

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='XionghanChessGame',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False以隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # 可以在这里添加图标文件路径
)
