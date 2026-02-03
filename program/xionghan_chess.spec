# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 数据文件列表
datas = [('assets\\sounds\\button.wav', 'assets\\sounds'), ('assets\\sounds\\check.wav', 'assets\\sounds'), ('assets\\sounds\\choose.wav', 'assets\\sounds'), ('assets\\sounds\\drop.wav', 'assets\\sounds'), ('assets\\sounds\\eat.wav', 'assets\\sounds'), ('assets\\sounds\\fc_background_sound.wav', 'assets\\sounds'), ('assets\\sounds\\fc_defeat_sound.wav', 'assets\\sounds'), ('assets\\sounds\\fc_victory_sound.wav', 'assets\\sounds'), ('assets\\sounds\\qq_background_sound.wav', 'assets\\sounds'), ('assets\\sounds\\warn.wav', 'assets\\sounds'), ('assets/sounds/check.wav', 'sounds'), ('assets/sounds/button.wav', 'sounds'), ('assets/sounds/choose.wav', 'sounds'), ('assets/sounds/drop.wav', 'sounds'), ('assets/sounds/eat.wav', 'sounds'), ('assets/sounds/warn.wav', 'sounds'), ('assets/sounds/fc_background_sound.wav', 'sounds'), ('assets/sounds/fc_defeat_sound.wav', 'sounds'), ('assets/sounds/fc_victory_sound.wav', 'sounds'), ('assets/sounds/qq_background_sound.wav', 'sounds'), ('assets\\fonts\\fangsong.ttf', 'assets\\fonts'), ('assets\\fonts\\kaiti.ttf', 'assets\\fonts'), ('assets\\fonts\\msyh.ttc', 'assets\\fonts'), ('assets\\fonts\\simhei.ttf', 'assets\\fonts'), ('assets\\fonts\\simkai.ttf', 'assets\\fonts'), ('assets\\fonts\\xingkai.ttf', 'assets\\fonts'), ('assets/fonts/fangsong.ttf', 'assets/fonts'), ('assets/fonts/kaiti.ttf', 'assets/fonts'), ('assets/fonts/msyh.ttc', 'assets/fonts'), ('assets/fonts/simhei.ttf', 'assets/fonts'), ('assets/fonts/simkai.ttf', 'assets/fonts'), ('assets/fonts/xingkai.ttf', 'assets/fonts'), ('assets\\pics\\1.jpg', 'assets\\pics'), ('assets\\pics\\2.jpg', 'assets\\pics'), ('assets\\pics\\3.jpg', 'assets\\pics'), ('assets\\pics\\4.jpg', 'assets\\pics'), ('assets\\pics\\5.jpg', 'assets\\pics'), ('assets/pics/1.jpg', 'assets'), ('assets/pics/2.jpg', 'assets'), ('assets/pics/3.jpg', 'assets'), ('assets/pics/4.jpg', 'assets'), ('assets/pics/5.jpg', 'assets'), ('assets/docs/help.md', 'assets'), ('assets/docs/about.md', 'assets'), ('../README.md', '.'), ('assets/docs/taunts.json', 'assets'), ('assets/docs/statistics.json', 'assets')]

# 隐藏导入模块列表
hiddenimports = ['program.game', 'program.main', 'program.config.config', 'program.config.settings', 'program.config.statistics', 'program.config.taunts_manager', 'program.config.ai_settings', 'program.controllers.game_io_controller', 'program.controllers.sound_manager', 'program.controllers.input_handler', 'program.controllers.replay_controller', 'program.controllers.ai_manager', 'program.controllers.step_counter', 'program.core.chess_pieces', 'program.core.game_rules', 'program.core.game_state', 'program.ui.chess_board', 'program.ui.game_screen', 'program.ui.menu_screen', 'program.ui.about_screen', 'program.ui.rules_screen', 'program.ui.replay_screen', 'program.ui.network_connect_screen', 'program.ui.dialogs', 'program.ui.button', 'program.ui.scrollbar', 'program.ui.avatar', 'program.utils.game_utils', 'program.lan.network_game', 'program.lan.xhlan', 'program.ai.chess_ai', 'program.ai.mcts.mcts', 'program.ai.mcts.mcts_config', 'program.ai.mcts.mcts_game', 'program.ai.mcts.mcts_pure', 'program.ai.mcts.train', 'program.ai.mcts.play_with_ai', 'program.ai.mcts.UIplay', 'program.ai.mcts.collect', 'program.ai.mcts.my_redis', 'program.ai.mcts.test_state_conversion', 'program.ai.mcts.zip_array', 'pygame', 'pygame.locals', 'json', 'copy', 'math', 'random', 'sys', 'os', 'time', 'threading', 'logging', 'pickle', 'collections', 'functools', 'itertools', 'operator', 'typing', 'dataclasses', 'configparser', 'argparse', 'pathlib', 're', 'datetime', 'zlib', 'base64', 'hashlib', 'urllib.parse', 'urllib.error', 'urllib.request', 'socket', 'select', 'ssl', 'queue', 'contextlib', 'abc', 'enum', 'numbers', 'warnings', 'weakref', 'reprlib', 'pprint', 'heapq', 'bisect', 'array', 'struct', 'codecs', 'encodings', 'stringprep', 'string', 'textwrap', 'unicodedata', 'locale', 'calendar', 'gettext', 'copyreg', 'types', 'inspect', 'dis', 'opcode', 'keyword', 'tokenize', 'token', 'ast', 'symtable', 'optparse', 'getopt', 'pdb', 'bdb', 'cmd', 'shlex', 'importlib', 'pkgutil', 'modulefinder', 'zipimport', 'zipfile', 'tarfile', 'gzip', 'bz2', 'lzma', 'shutil', 'tempfile', 'fnmatch', 'glob', 'email', 'xml', 'plistlib', 'csv', 'logging.handlers', 'logging.config', 'io', 'mimetypes', 'rfc822', 'netrc', 'ftplib', 'poplib', 'imaplib', 'nntplib', 'smtplib', 'uuid', 'socketserver', 'http', 'selectors', 'signal', 'multiprocessing', 'concurrent', 'subprocess', 'dummy_threading', 'dummy_thread', 'asyncio', 'pipes', 'fcntl', 'termios', 'tty', 'pty', 'resource', 'platform', 'errno', 'ctypes', 'ctypes.util', 'ctypes.wintypes', 'msvcrt', '_winapi', 'winsound', 'winreg', 'msilib', 'tkinter', 'tkinter.constants', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.scrolledtext', 'tkinter.simpledialog', 'tkinter.tix', 'tkinter.ttk']

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
    hooksconfig={},
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
