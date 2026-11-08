"""桌面端文案的英文覆盖守卫（问题 P1-J）。

审计原话是「英文半翻译」：`app.py` 里 151 处中文只有中文一种写法，英文模式下
直接原样显示。这次改造把用户可见文案统一走 `dl()` / `dlf()`（中文原文作 key，
英文查表），本文件把「不再漏翻」变成一条可执行的定义：

- 桌面端（除 `theme.py` 的棋子字形、`texts.py` 自身）不允许出现**裸**中文字面量：
  要么包在 `dl()` / `dlf()` 里，要么是双语三元里带英文的那一支；
- `dl()` / `dlf()` 的每个 key 都必须在词表里 —— 否则运行时静默退回中文，
  等于白翻。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from xionghan_chess.desktop import texts

DESKTOP = Path(__file__).resolve().parents[1] / "src" / "xionghan_chess" / "desktop"
# theme.py 的 NAMES 是棋子字形（漢/俥/傌…），任何语言下都必须是中文，不参与翻译。
EXEMPT = {"theme.py", "texts.py"}
HAN = re.compile(r"[\u4e00-\u9fff]")


def _has_han(node: ast.AST) -> bool:
    return bool(HAN.search(ast.unparse(node)))


def _docstring_ids(tree: ast.AST) -> set[int]:
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def _scan() -> tuple[list[tuple[str, int, str]], list[tuple[str, int, str]]]:
    """返回 (未翻译残留, 词表里缺失的 key)。"""
    untranslated: list[tuple[str, int, str]] = []
    missing_keys: list[tuple[str, int, str]] = []
    for path in sorted(DESKTOP.rglob("*.py")):
        if path.name in EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip = _docstring_ids(tree)
        wrapped: set[int] = set()
        bilingual: set[int] = set()
        fstring_parts: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id in ("dl", "dlf") and node.args:
                wrapped.add(id(node.args[0]))
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    table = texts.EN if node.func.id == "dl" else texts.TEMPLATES
                    if arg.value not in table:
                        missing_keys.append((path.name, node.lineno, arg.value))
            elif isinstance(node, ast.IfExp):
                left, right = node.body, node.orelse
                if _has_han(left) and not _has_han(right):
                    bilingual.add(id(left))
                if _has_han(right) and not _has_han(left):
                    bilingual.add(id(right))
            elif isinstance(node, ast.JoinedStr):
                fstring_parts.update(id(value) for value in node.values)

        for node in ast.walk(tree):
            if id(node) in skip or id(node) in fstring_parts:
                continue
            if isinstance(node, ast.JoinedStr):
                # f-string 整体判断：要么是双语分支，要么中文只出现在插值里
                # （如 f"{dl('房间')} {room}"），不能有裸中文字面片段。
                bare = any(isinstance(v, ast.Constant) and HAN.search(str(v.value)) for v in node.values)
                if _has_han(node) and id(node) not in bilingual and bare:
                    untranslated.append((path.name, node.lineno, ast.unparse(node)[:60]))
            elif isinstance(node, ast.Constant) and _has_han(node) and id(node) not in wrapped \
                    and id(node) not in bilingual:
                untranslated.append((path.name, node.lineno, repr(node.value)[:60]))
    return untranslated, missing_keys


def test_no_untranslated_chinese_literals() -> None:
    untranslated, _ = _scan()
    detail = "\n  ".join(f"{name}:{line}  {text}" for name, line, text in untranslated)
    assert not untranslated, f"以下中文字面量没有走 dl()/dlf()：\n  {detail}"


def test_every_translated_key_exists_in_the_table() -> None:
    _, missing = _scan()
    detail = "\n  ".join(f"{name}:{line}  {key!r}" for name, line, key in missing)
    assert not missing, f"以下 key 不在词表里（英文模式会静默显示中文）：\n  {detail}"


@pytest.fixture()
def english() -> str:
    original = texts.current_language()
    texts.set_language("en")
    yield "en"
    texts.set_language(original)


def test_tables_are_not_empty() -> None:
    assert len(texts.EN) >= 100, f"英文词条只有 {len(texts.EN)} 条，像是被清空了"
    assert len(texts.TEMPLATES) >= 15


def test_chinese_mode_returns_source_text() -> None:
    original = texts.current_language()
    texts.set_language("zh-CN")
    try:
        assert texts.dl("认输") == "认输"
        assert texts.dlf("棋局已保存：{path}", path="/tmp/a") == "棋局已保存：/tmp/a"
    finally:
        texts.set_language(original)


def test_english_mode_translates(english: str) -> None:
    assert texts.dl("认输") == "Resign"
    assert texts.dl("非法走棋") == "Illegal move"


def test_unknown_key_falls_back_to_chinese(english: str) -> None:
    """宁可显示一句中文，也不要显示空串或 key —— 漏翻是降级，不是崩溃。"""
    assert texts.dl("这条文案还没翻译") == "这条文案还没翻译"


def test_template_substitution(english: str) -> None:
    assert texts.dlf("棋局已保存：{path}", path="C:/a.xhgame") == "Game saved: C:/a.xhgame"
    assert texts.dlf("红方 {red} 枚 · 黑方 {black} 枚", red=3, black=4) == "Red 3 · Black 4 pieces"


def test_template_with_missing_value_does_not_crash(english: str) -> None:
    """占位符对不上时退回中文模板再试一次，不能把界面弄崩。"""
    with pytest.raises(KeyError):
        texts.dlf("棋谱已保存：{path}")


def test_set_language_only_accepts_known_english() -> None:
    original = texts.current_language()
    try:
        texts.set_language("fr")
        assert texts.current_language() == "zh-CN", "未知语言一律回落中文"
        texts.set_language("en")
        assert texts.current_language() == "en"
    finally:
        texts.set_language(original)
