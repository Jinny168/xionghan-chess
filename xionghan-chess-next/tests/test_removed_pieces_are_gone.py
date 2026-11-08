"""甲/楯/刺已硬删除：枚举里没有，源码里除存档异常那张表之外不再出现。

## 为什么是"扫源码"而不是 grep 一次

`core/model.py` 的 `REMOVED_PIECE_NAMES` 必须保留 `"armor"/"shield"/"assassin"`
三个键 —— 旧存档打开时要给用户一句人话（「存档包含已移除的兵种：甲/胄」），
没有它只剩 `ValueError: 'armor' is not a valid PieceType`。

但"允许一处"如果只靠人工 grep，下次谁再引入引用也没人拦。所以这里把它固化成用例：
`src/` 里出现这三个标识符的文件**只允许 `core/model.py`**。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from xionghan_chess.core.model import PieceType, UnsupportedSaveError, piece_from_dict

SRC = Path(__file__).resolve().parents[1] / "src"
PATTERN = re.compile(r"ARMOR|SHIELD|ASSASSIN|armor|shield|assassin")
ALLOWED = {Path("xionghan_chess/core/model.py")}


def test_piece_type_has_no_removed_members() -> None:
    values = {item.value for item in PieceType}
    assert values == {
        "king", "rook", "horse", "elephant", "advisor", "cannon", "pawn",
        "guard", "archer", "thunder", "patrol",
    }, f"枚举成员应为 11 型，实际 {sorted(values)}"


def test_removed_piece_names_are_the_only_reference() -> None:
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC)
        if rel in ALLOWED:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PATTERN.search(line):
                offenders.append(f"{rel}:{lineno}: {line.strip()[:80]}")
    assert not offenders, "这三个标识符只允许出现在 core/model.py：\n" + "\n".join(offenders)


def test_old_save_with_removed_piece_raises_a_readable_error() -> None:
    with pytest.raises(UnsupportedSaveError) as excinfo:
        piece_from_dict({"id": "p1", "type": "armor", "color": "red",
                         "row": 6, "col": 3})
    message = str(excinfo.value)
    assert "甲" in message and "1.7.4" in message, message
