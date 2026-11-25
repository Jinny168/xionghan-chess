"""35 道真题的非权威「为什么」解析（文案与题库数据分离）。

数据来自 `core/data/puzzle_explanations.json`，由 `scripts/gen_puzzle_explanations.py`
从创意侧文案生成；本模块只负责读取并拼成可直接追加到提示链末尾的一句。
13 条 drill 没有对应解析，返回 None —— 显示层据此决定不追加。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import cast

_DATA = Path(__file__).with_name("data") / "puzzle_explanations.json"


@lru_cache(maxsize=1)
def load() -> dict[str, dict[str, str]]:
    """解析表（题 id → {key_move, why}）。只在本进程首次调用时读盘。"""
    return cast("dict[str, dict[str, str]]", json.loads(_DATA.read_text(encoding="utf-8")))


def hint_for(puzzle_id: str) -> str | None:
    """返回作为**最后一条提示**追加的解析文字；无对应解析（drill）返回 None。

    语气由文案侧负责（不报分值、不用指令式措辞）；这里不做任何前缀包装。
    """
    item = load().get(puzzle_id)
    if not item:
        return None
    return f"{item['key_move']}\n{item['why']}"
