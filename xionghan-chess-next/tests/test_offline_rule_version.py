"""`offline.js` 的规则集版本必须和 Python 侧一致（纯静态，不需要 node）。

## 为什么要有这条

`RULE_VERSION` 是「走法语义」的版本号，两份实现各自持有一个常量：

- Python：`core/profiles.py::RULE_VERSION`
- 离线页：`android/Resources/assets/offline/offline.js::RULE_VERSION`

它有两个出口，任何一个漏改都会静默出错：

1. **位置键前缀** `||opt:rs<N>-...` —— 硬规则（巡禁竖移、兵底线不后退）没有开关，
   只能靠这个前缀把旧规则的重复局面计数挡在外面。JS 写 `rs1` 而 Python 写 `rs2`，
   两侧的 `positionCounts` 就永远对不上：批量对拍只比合法着法，一条都不会红。
2. **棋谱 `ruleVersion`** —— `core/storage.py::game_from_document` 用
   `int(data.get("ruleVersion", 1))` 判断来源版本，缺字段按 1 处理。离线页不写这个
   字段，安卓导出的 `.xhgame` 就会被当成"1.9 时代的棋谱"。

`tests/test_cross_engine.py::test_position_key_matches_offline_byte_for_byte` 能抓住
第 1 类漂移，但那条用例处在"缺 node 判失败"的通道里（见 `tests/conftest.py`）。
本条是纯正则静态检查，不依赖 node，任何环境都能跑，而且**失败信息直指改哪一行**。

断言口径：**比数值，不比字面量**。允许以后把 `RULE_VERSION` 改成 3，只要两边一起改。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from xionghan_chess.core.profiles import RULE_VERSION

OFFLINE_JS = (Path(__file__).resolve().parents[1]
              / "android" / "Resources" / "assets" / "offline" / "offline.js")

# 版本号声明：`const RULE_VERSION=2;`（允许 `const`/`let`/`var` 与空格差异）
_DECLARATION = re.compile(r"\b(?:const|let|var)\s+RULE_VERSION\s*=\s*(\d+)")
# 写死的前缀：`'rs2-` / `"rs3-` 之类
_HARDCODED_PREFIX = re.compile(r"""['"]rs\d""")
# 前缀由常量参与拼接：`'rs'+RULE_VERSION`（内联）或 `const PREFIX='rs'+RULE_VERSION`
_JOINS_RULE_VERSION = re.compile(r"""['"]rs['"]\s*\+\s*RULE_VERSION""")
# `const PREFIX = 'rs' + RULE_VERSION …` —— 允许先抽常量再在 positionKey 里引用
_PREFIX_CONST = re.compile(r"""const\s+(\w+)\s*=\s*['"]rs['"]\s*\+\s*RULE_VERSION""")


def _source() -> str:
    assert OFFLINE_JS.exists(), f"找不到离线页脚本：{OFFLINE_JS}"
    return OFFLINE_JS.read_text(encoding="utf-8")


def _line_number(text: str, offset: int) -> int:
    """字符偏移 → 行号（1 起），只用于拼报错信息。"""
    return text[:offset].count("\n") + 1


def _line_containing(text: str, needle: str) -> tuple[int, str]:
    """首次出现 `needle` 的 (行号, 整行)；找不到返回 `(0, "")`。"""
    for number, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return number, line
    return 0, ""


# --------------------------------------------------------------------------- #
# 1. 常量本身：存在、唯一、与 Python 同值
# --------------------------------------------------------------------------- #


def test_offline_declares_the_constant_exactly_once() -> None:
    """`RULE_VERSION` 只能在文件顶部声明一次 —— 第二处就是第二个真相源。"""
    text = _source()
    matches = list(_DECLARATION.finditer(text))
    assert matches, (
        f"{OFFLINE_JS.name} 里找不到 `const RULE_VERSION=<n>` 声明。\n"
        "  → 改哪一行：文件第 2 行（`'use strict';` 之后）\n"
        f"  → 改什么：加一行 `const RULE_VERSION={RULE_VERSION};`"
        "  —— 位置键前缀与棋谱的 ruleVersion 都从它派生，不能再写死数字。"
    )
    if len(matches) > 1:
        where = "、".join(f"第 {_line_number(text, m.start())} 行" for m in matches)
        pytest.fail(
            f"{OFFLINE_JS.name} 里 RULE_VERSION 被声明了 {len(matches)} 次（{where}），"
            " 只能有一处。\n  → 改什么：删掉多余的那处，只保留文件顶部那一个。",
            pytrace=False,
        )


def test_offline_rule_version_matches_python() -> None:
    """`offline.js` 的 `RULE_VERSION` 必须等于 `core/profiles.py::RULE_VERSION`。"""
    text = _source()
    match = _DECLARATION.search(text)
    assert match, f"{OFFLINE_JS.name} 里找不到 `const RULE_VERSION=<n>` 声明"
    declared = int(match.group(1))
    assert declared == RULE_VERSION, (
        f"规则集版本两侧不一致：offline.js = {declared}，"
        f"core/profiles.py = {RULE_VERSION}。\n"
        f"  → 改哪一行：{OFFLINE_JS.name} 第 {_line_number(text, match.start())} 行\n"
        f"  → 改什么：`const RULE_VERSION={declared};` → `const RULE_VERSION={RULE_VERSION};`\n"
        "  → 为什么：位置键前缀 rs<N> 与棋谱 ruleVersion 必须与 Python 同值，"
        "否则重复局面账本、旧档的版本判断都会静默错。"
    )


# --------------------------------------------------------------------------- #
# 2. 位置键：用常量拼前缀，不许写死
# --------------------------------------------------------------------------- #


def test_no_hardcoded_rule_version_prefix() -> None:
    """全文件不许出现 `'rs2` 这类写死的前缀。"""
    text = _source()
    offenders = []
    for match in _HARDCODED_PREFIX.finditer(text):
        number = _line_number(text, match.start())
        offenders.append(f"第 {number} 行：`{match.group(0)}…`")
    if offenders:
        pytest.fail(
            "offline.js 里出现了写死的规则集版本前缀（'rs2 之类）：\n  "
            + "\n  ".join(offenders)
            + "\n  → 改哪一行：上面列出的行"
            "\n  → 改什么：`'rs2-'` → `'rs'+RULE_VERSION+'-'`"
            "\n  → 为什么：写死之后这个常量就形同虚设，改版本号会漏掉前缀。",
            pytrace=False,
        )


def test_position_key_joins_the_constant() -> None:
    """`positionKey` 的前缀必须由 `RULE_VERSION` 参与拼出（不锁字面写法）。

    允许两种等价形态：
      1. 内联：`'rs'+RULE_VERSION+'-'`
      2. 抽常量：`const PREFIX='rs'+RULE_VERSION+'-'`，`positionKey` 里用 `PREFIX`
    锁死第 1 种会把"等价重构"判成错误（质检实测），那是假红；这里只要求
    "前缀确实由常量派生、且 positionKey 用的是它"。
    """
    text = _source()
    number, line = _line_containing(text, "positionKey(state)")
    assert line, f"{OFFLINE_JS.name} 里找不到 `positionKey(state)` 定义"

    derived = [match.group(1) for match in _PREFIX_CONST.finditer(text)]
    inline = bool(_JOINS_RULE_VERSION.search(line))
    via_const = any(name in line for name in derived)
    assert inline or via_const, (
        f"positionKey 的前缀没有由 RULE_VERSION 拼出（第 {number} 行）。\n"
        "  → 改什么：内联写 `'rs'+RULE_VERSION+'-'`，或先抽 "
        "`const PREFIX='rs'+RULE_VERSION+'-'` 再在 positionKey 里引用它。\n"
        "  → 为什么：这一串进的是重复局面的 key，写死就与 core/rules.py 的 "
        "`f\"rs{RULE_VERSION}-\"` 各走各的，改版本号必然漏一处。"
    )


# --------------------------------------------------------------------------- #
# 3. 棋谱：导出时必须盖版本戳
# --------------------------------------------------------------------------- #


def test_game_document_stamps_rule_version() -> None:
    """导出的 `.xhgame` 必须带 `ruleVersion`，否则被当成 1.9 时代的棋谱。"""
    text = _source()
    number, line = _line_containing(text, "function gameDocument()")
    assert line, f"{OFFLINE_JS.name} 里找不到 `gameDocument()`"
    assert "ruleVersion:RULE_VERSION" in line, (
        f"gameDocument() 没有写 ruleVersion（第 {number} 行）。\n"
        "  → 改哪一行：上面那一行的函数体\n"
        "  → 改什么：返回对象里加 `ruleVersion:RULE_VERSION`（与 `formatVersion:1` 并列）\n"
        "  → 为什么：core/storage.py::game_from_document 用 "
        "`int(data.get(\"ruleVersion\", 1))` 判断来源版本，缺字段等于自称 1.9。"
    )
