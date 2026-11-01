"""`scripts/make_shortcut.py` 的回归守卫。

来由：该脚本一度在本机稳定抛 `OSError: [WinError -2147024809] 参数错误`
（`SHParseDisplayName` 解析 PIDL 时失败），而 `release/README.md` 把它写成
"建快捷方式的标准做法" —— 文档与工具脱节，用户照着做会直接报错。

本测试不关心 IDList 有没有写成功（那是优化项），只钉住两件**用户可感知**的事：
1. 命令必须正常退出，不能崩；
2. 产出的 .lnk 里**确实写着目标路径**（从字节里找 UTF-16LE 串，不依赖 pywin32）。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "make_shortcut.py"

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="快捷方式是 Windows 概念")


def test_make_shortcut_writes_target_and_does_not_crash(tmp_path: Path) -> None:
    lnk = tmp_path / "测试 快捷方式.lnk"
    target = Path(sys.executable)            # 一定存在的 exe，且路径带空格/中文时也能验
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(lnk), str(target)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, f"脚本崩了：\nstdout={result.stdout}\nstderr={result.stderr}"
    assert "created:" in result.stdout
    assert lnk.is_file(), "没有产出 .lnk"
    assert lnk.stat().st_size > 200, f"lnk 只有 {lnk.stat().st_size} 字节，像是半截文件"

    blob = lnk.read_bytes()
    assert str(target).encode("utf-16-le") in blob, (
        "lnk 里找不到目标路径 —— SetPath 没写进去，这个快捷方式是坏的")
