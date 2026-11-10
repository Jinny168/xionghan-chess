"""题库文档必须与题库一致 —— 过期就红。

难度是标定算出来的，手工维护清单必然和 `puzzles.json` 漂。
把"重生成文档"变成门禁的一部分，比指望人记得重跑脚本可靠。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from make_puzzle_doc import DOC, render  # noqa: E402


def test_puzzle_library_doc_exists() -> None:
    assert DOC.exists(), "docs/PUZZLE_LIBRARY.md 不存在，跑 scripts/make_puzzle_doc.py"


def test_puzzle_library_doc_is_up_to_date() -> None:
    current = DOC.read_text(encoding="utf-8")
    expected = render()
    assert current == expected, (
        "docs/PUZZLE_LIBRARY.md 已过期 —— 题库改过但没重生成文档。跑 `python scripts/make_puzzle_doc.py` 后再提交。"
    )
