#!/usr/bin/env python
"""
PyInstaller打包脚本 - 匈汉象棋游戏
用于将Python游戏打包成exe可执行文件
"""
import PyInstaller.__main__

def create_spec_file():
    """创建PyInstaller spec文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 收集声音文件
sounds_datas = [
    (\"sounds/check.wav\", \"sounds\"),
    (\"sounds/move.wav\", \"sounds\"),
    (\"sounds/capture.wav\", \"sounds\")
]

# 收集字体文件
fonts_datas = [
    (\"fonts/fangsong.ttf\", \"fonts\"),
    (\"fonts/kaiti.ttf\", \"fonts\"),
    (\"fonts/msyh.ttc\", \"fonts\"),
    (\"fonts/simhei.ttf\", \"fonts\"),
    (\"fonts/simkai.ttf\", \"fonts\"),
    (\"fonts/xingkai.ttf\", \"fonts\")
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
'''

    with open('xionghan_chess.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print("已创建 spec 文件: xionghan_chess.spec")

def main():
    """主函数，执行打包过程"""
    print("开始打包匈汉象棋游戏...")

    # 检查是否已安装PyInstaller
    try:
        import PyInstaller
        print("PyInstaller 已安装")
    except ImportError:
        print("错误：未找到PyInstaller。请先安装PyInstaller：")
        print("pip install pyinstaller")
        return

    # 创建spec文件
    create_spec_file()

    # 执行PyInstaller打包
    try:
        PyInstaller.__main__.run([
            'xionghan_chess.spec',
            '--clean',
            '--noconfirm'
        ])

        print("打包完成！生成的exe文件位于 dist/XionghanChessGame 文件夹中")
    except Exception as e:
        print(f"打包过程中出现错误: {e}")

if __name__ == "__main__":
    main()
