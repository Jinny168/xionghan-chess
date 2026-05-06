#!/usr/bin/env python
"""
PyInstaller打包脚本 - 匈汉象棋游戏
用于将Python游戏打包成exe可执行文件
"""
from pathlib import Path

def collect_resource_files(project_root=".", resource_dir="", extensions=None):
    """
    自动收集指定目录下的资源文件
    
    Args:
        project_root: 项目根目录
        resource_dir: 资源目录名
        extensions: 要收集的文件扩展名列表，None表示收集所有文件
    Returns:
        包含资源文件路径的列表
    """
    collected_files = []
    resource_path = Path(project_root) / resource_dir
    
    if resource_path.exists():
        for file_path in resource_path.rglob("*"):
            if file_path.is_file():
                if extensions is None or file_path.suffix.lower() in extensions:
                    # 相对于项目根目录的路径
                    rel_path = file_path.relative_to(Path(project_root))
                    collected_files.append((str(rel_path), str(rel_path.parent)))
    return collected_files

def create_spec_file():
    """创建PyInstaller spec文件"""
    # 收集声音文件
    sounds_datas = collect_resource_files(".", "assets/sounds", [".wav", ".mp3"])
    # 确保必要的声音文件存在
    required_sounds = [
        ("assets/sounds/check.wav", "sounds"),
        ("assets/sounds/button.wav", "sounds"),
        ("assets/sounds/choose.wav", "sounds"),
        ("assets/sounds/drop.wav", "sounds"),
        ("assets/sounds/eat.wav", "sounds"),
        ("assets/sounds/warn.wav", "sounds"),
        ("assets/sounds/fc_background_sound.wav", "sounds"),
        ("assets/sounds/fc_defeat_sound.wav", "sounds"),
        ("assets/sounds/fc_victory_sound.wav", "sounds"),
        ("assets/sounds/qq_background_sound.wav", "sounds"),
    ]
    # 添加必要的声音文件（如果未通过自动收集找到）
    for sound in required_sounds:
        if sound not in sounds_datas:
            sounds_datas.append(sound)

    # 收集字体文件
    fonts_datas = collect_resource_files(".", "assets/fonts", [".ttf", ".ttc"])
    # 确保必要的字体文件存在 - 修正路径为assets/fonts
    required_fonts = [
        ("assets/fonts/fangsong.ttf", "assets/fonts"),
        ("assets/fonts/kaiti.ttf", "assets/fonts"),
        ("assets/fonts/msyh.ttc", "assets/fonts"),
        ("assets/fonts/simhei.ttf", "assets/fonts"),
        ("assets/fonts/simkai.ttf", "assets/fonts"),
        ("assets/fonts/xingkai.ttf", "assets/fonts")
    ]
    for font in required_fonts:
        if font not in fonts_datas:
            fonts_datas.append(font)

    # 收集图像资源文件 - 修正重复项
    images_datas = collect_resource_files(".", "assets", [".jpg", ".png", ".gif", ".bmp"])
    # 确保必要的图像文件存在 - 移除重复项
    required_images = [
        ("assets/pics/1.jpg", "assets"),
        ("assets/pics/2.jpg", "assets"),
        ("assets/pics/3.jpg", "assets"),
        ("assets/pics/4.jpg", "assets"),
        ("assets/pics/5.jpg", "assets"),
    ]
    for image in required_images:
        if image not in images_datas:
            images_datas.append(image)

    # 收集配置和帮助文档
    doc_datas = [
        ("assets/docs/help.md", "assets"),
        ("assets/docs/about.md", "assets"),
        ("../README.md", "."),  # 从program目录向上一级回到项目根目录
    ]

    # 收集JSON配置文件
    json_datas = [
        ("assets/docs/taunts.json", "assets"),
        ("assets/docs/statistics.json", "assets"),
    ]

    # 收集AI模型文件（如果有）
    ai_datas = collect_resource_files(".", "models", [".pdparams", ".pth", ".onnx", ".pkl"])

    # 收集所有数据文件
    datas = sounds_datas + fonts_datas + images_datas + doc_datas + json_datas + ai_datas

    # 定义游戏模块列表 - 更新为整合后的工具模块
    desktop_modules = [
        'desktop.game',
        'desktop.main',
        'desktop.config.config',
        'desktop.config.settings',
        'desktop.config.statistics',
        'desktop.config.taunts_manager',
        'desktop.config.ai_settings',
        'desktop.controllers.game_io_controller',
        'desktop.controllers.sound_manager',
        'desktop.controllers.input_handler',
        'desktop.controllers.replay_controller',
        'desktop.controllers.ai_manager',
        'desktop.controllers.step_counter',
        'desktop.core.chess_pieces',
        'desktop.core.game_rules',
        'desktop.core.game_state',
        'desktop.ui.chess_board',
        'desktop.ui.game_screen',
        'desktop.ui.menu_screen',
        'desktop.ui.about_screen',
        'desktop.ui.rules_screen',
        'desktop.ui.replay_screen',
        'desktop.ui.network_connect_screen',
        'desktop.ui.dialogs',
        'desktop.ui.button',
        'desktop.ui.scrollbar',
        'desktop.ui.avatar',
        # 更新为整合后的工具模块
        'desktop.utils.game_utils',
        'desktop.lan.network_game',
        'desktop.lan.xhlan',
        'desktop.ai.chess_ai',
        # MCTS模块（只保留纯Python/MCTS相关，不含深度学习框架）
        'desktop.ai.mcts.mcts',
        'desktop.ai.mcts.mcts_config',
        'desktop.ai.mcts.mcts_game',
        'desktop.ai.mcts.mcts_pure',
        'desktop.ai.mcts.train',
        'desktop.ai.mcts.play_with_ai',
        'desktop.ai.mcts.UIplay',
        'desktop.ai.mcts.collect',
        'desktop.ai.mcts.my_redis',
        'desktop.ai.mcts.test_state_conversion',
        'desktop.ai.mcts.zip_array',
    ]

    # 基础库模块列表（移除了深度学习相关库）
    basic_modules = [
        'pygame',
        'pygame.locals',
        'json',
        'copy',
        'math',
        'random',
        'sys',
        'os',
        'time',
        'threading',
        'logging',
        'pickle',
        'collections',
        'functools',
        'itertools',
        'operator',
        'typing',
        'dataclasses',
        'configparser',
        'argparse',
        'pathlib',
        're',
        'datetime',
        'zlib',
        'base64',
        'hashlib',
        'urllib.parse',
        'urllib.error',
        'urllib.request',
        'socket',
        'select',
        'ssl',
        'queue',
        'contextlib',
        'abc',
        'enum',
        'numbers',
        'warnings',
        'weakref',
        'reprlib',
        'pprint',
        'heapq',
        'bisect',
        'array',
        'struct',
        'codecs',
        'encodings',
        'stringprep',
        'string',
        'textwrap',
        'unicodedata',
        'locale',
        'calendar',
        'gettext',
        'copyreg',
        'types',
        'inspect',
        'dis',
        'opcode',
        'keyword',
        'tokenize',
        'token',
        'ast',
        'symtable',
        'optparse',
        'getopt',
        'pdb',
        'bdb',
        'cmd',
        'shlex',
        'importlib',
        'pkgutil',
        'modulefinder',
        'zipimport',
        'zipfile',
        'tarfile',
        'gzip',
        'bz2',
        'lzma',
        'shutil',
        'tempfile',
        'fnmatch',
        'glob',
        'email',
        'xml',
        'plistlib',
        'csv',
        'logging.handlers',
        'logging.config',
        'io',
        'mimetypes',
        'rfc822',
        'netrc',
        'ftplib',
        'poplib',
        'imaplib',
        'nntplib',
        'smtplib',
        'uuid',
        'socketserver',
        'http',
        'selectors',
        'signal',
        'multiprocessing',
        'concurrent',
        'subprocess',
        'dummy_threading',
        'dummy_thread',
        'asyncio',
        'pipes',
        'fcntl',
        'termios',
        'tty',
        'pty',
        'resource',
        'platform',
        'errno',
        'ctypes',
        'ctypes.util',
        'ctypes.wintypes',
        'msvcrt',
        '_winapi',
        'winsound',
        'winreg',
        'msilib',
        'tkinter',
        'tkinter.constants',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.simpledialog',
        'tkinter.tix',
        'tkinter.ttk',
    ]

    # 合并所有隐藏导入模块
    hiddenimports = desktop_modules + basic_modules

    # 生成spec文件内容
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 数据文件列表
datas = {datas}

# 隐藏导入模块列表
hiddenimports = {hiddenimports}

# 排除列表
excludes = [
    'paddle',
    'torch',
    'tensorflow',
    'keras',
    'mxnet',
    'caffe',
    'theano',
    'chainer',
    'paddle.fluid',
    'paddle.nn',
    'paddle.optimizer',
    'torch.nn',
    'torch.optim',
    'torch.utils',
    'torchvision',
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excludes,
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
    icon='icon.ico',  # 使用项目根目录下的图标文件
)
'''

    with open('xionghan_chess.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print(f"已创建 spec 文件: xionghan_chess.spec")
    print(f"收集到 {len(datas)} 个数据文件")

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
        import PyInstaller.__main__
        PyInstaller.__main__.run([
            'xionghan_chess.spec',
            '--clean',
            '--noconfirm'
        ])

        print("打包完成！生成的exe文件位于 dist/XionghanChessGame 文件夹中")
    except Exception as e:
        print(f"打包过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
