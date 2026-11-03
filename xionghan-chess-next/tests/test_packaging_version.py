"""打包版本资源必须与 `__version__` 同步。

EXE 之前**没有任何版本资源**（FileVersion / FileDescription 全空），
资源管理器里悬浮只显示文件名，用户看不出自己跑的是哪一版 —— 这就是
「快捷方式提示还写着 1.7.5」那类问题的温床。

现在 `packaging/version_info.txt` 提供这些字段，本文件保证它不会和代码版本漂开。
"""

from __future__ import annotations

import re
from pathlib import Path

from xionghan_chess import __version__

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "packaging" / "version_info.txt"
SPEC = ROOT / "packaging" / "build_windows.spec"


def test_version_info_matches_the_package_version() -> None:
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r"filevers=\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", text)
    assert match, "version_info.txt 缺少 filevers"
    packed = ".".join(match.group(1, 2, 3))
    assert packed == __version__, (
        f"version_info 写的是 {packed}，代码是 {__version__} —— 升版本时漏改打包资源")


def test_product_strings_carry_the_version() -> None:
    text = VERSION_FILE.read_text(encoding="utf-8")
    assert f"匈汉象棋 {__version__} 桌面版" in text, "FileDescription 没带版本号"
    assert f"匈漢象棋-{__version__}-桌面版.exe" in text, "OriginalFilename 没带版本号"


def test_spec_uses_the_version_file() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    assert 'version=os.path.join(SPECPATH, "version_info.txt")' in spec, \
        "spec 没挂版本资源，打出来的 EXE 又会是空的"
