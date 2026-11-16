"""webapp/i18n.js 结构守卫：zh / en 两块零重复键、且键集相等。

JS 对象字面量遇到重复键**不报错，只是后写生效** —— `analysis.empty` 那次就是
无句号版被带句号版静默覆盖，肉眼很难发现。把"零重复 + 双语对齐"固化成门禁，
比逐个盯着具体键更不容易复发。
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "webapp" / "js" / "i18n.js"

KEY_RE = re.compile(r"^\s*'([^']+)'\s*:", re.M)


def _block(name: str) -> str:
    source = I18N.read_text(encoding="utf-8")
    start = source.index(f"const {name} = {{")
    end = source.find("\nconst ", start + 1)
    assert end > start, f"找不到 {name} 块的结束边界"
    return source[start:end]


def _keys(name: str) -> list[str]:
    return KEY_RE.findall(_block(name))


def test_zh_block_has_no_duplicate_keys() -> None:
    dupes = [key for key, count in Counter(_keys("zh")).items() if count > 1]
    assert not dupes, "zh 块有重复键（后写会静默覆盖）：" + ", ".join(sorted(dupes))


def test_en_block_has_no_duplicate_keys() -> None:
    dupes = [key for key, count in Counter(_keys("en")).items() if count > 1]
    assert not dupes, "en 块有重复键（后写会静默覆盖）：" + ", ".join(sorted(dupes))


def test_zh_and_en_key_sets_are_equal() -> None:
    zh, en = set(_keys("zh")), set(_keys("en"))
    assert zh == en, (
        "双语键集不齐：仅 zh=" + ", ".join(sorted(zh - en)) + "；仅 en=" + ", ".join(sorted(en - zh))
    )
