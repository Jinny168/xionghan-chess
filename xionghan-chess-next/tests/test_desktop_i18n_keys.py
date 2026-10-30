"""桌面端 i18n key 覆盖测试（问题 P1-I / 计划项 S1-8）。

## 挡的是什么

`test_locale_keys_are_paired` 只保证 zh 与 en **成对**（两边有同样的 key），
但「两边都缺同一个 key」它发现不了。而桌面端一旦用到不存在的 key，`t()`
会把 key 原样返回 —— 玩家界面上直接出现 `desktop.start_training` 这种裸 key。

这一条把「代码里用到的 key」与「语言包里的 key」直接对上，两侧都查：
字面量、三元表达式两个分支，以及 f-string 的前缀族（`f"profile.{p.id}"`）。

## 为什么要断言「扫到了足够多的 key」

如果哪天 AST 扫描逻辑写错（比如 `t` 被重命名、或参数结构变了），扫描会悄悄
返回空集合，而「空集合 ⊆ 语言包」永远成立 —— 测试变成一条永远绿的废测试。
所以下面显式要求扫到的字面量 key 数量不低于一个下限。
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

DESKTOP = Path(__file__).resolve().parents[1] / "src" / "xionghan_chess" / "desktop"
LOCALES = Path(__file__).resolve().parents[1] / "locales"

# 扫描结果的下限：当前实测 124 个。留余量，只用来识别「扫描器失效」。
MIN_LITERAL_KEYS = 100


def _flat_keys(locale_file: Path) -> set[str]:
    def walk(node: object, prefix: str = "") -> list[str]:
        if isinstance(node, dict):
            out: list[str] = []
            for key, value in node.items():
                out.extend(walk(value, f"{prefix}.{key}" if prefix else str(key)))
            return out
        return [prefix]

    return set(walk(json.loads(locale_file.read_text(encoding="utf-8"))))


def _t_calls() -> list[tuple[str, ast.Call]]:
    """桌面端所有 `t(...)` / `xxx.t(...)` 调用，带上文件名。"""
    calls: list[tuple[str, ast.Call]] = []
    for path in sorted(DESKTOP.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            name = (func.id if isinstance(func, ast.Name)
                    else func.attr if isinstance(func, ast.Attribute) else "")
            if name == "t":
                calls.append((path.name, node))
    return calls


def _literal_keys() -> dict[str, set[str]]:
    """`t("a.b")` 与三元 `t("x" if c else "y")` 里的常量 key。"""
    found: dict[str, set[str]] = {}

    def add(key: str, where: str) -> None:
        found.setdefault(key, set()).add(where)

    for where, call in _t_calls():
        arg = call.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            add(arg.value, where)
        elif isinstance(arg, ast.IfExp):
            for branch in (arg.body, arg.orelse):
                if isinstance(branch, ast.Constant) and isinstance(branch.value, str):
                    add(branch.value, where)
    return found


def _dynamic_prefixes() -> dict[str, set[str]]:
    """f-string 的常量前缀，例如 `f"profile.{p.id}"` -> `profile.`。"""
    prefixes: dict[str, set[str]] = {}
    for where, call in _t_calls():
        arg = call.args[0]
        if not isinstance(arg, ast.JoinedStr) or not arg.values:
            continue
        head = arg.values[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str) and "." in head.value:
            prefixes.setdefault(head.value, set()).add(where)
    return prefixes


def test_scanner_actually_finds_keys() -> None:
    """防「扫描器静默失效」：扫到的 key 数必须达到下限。"""
    found = _literal_keys()
    assert len(found) >= MIN_LITERAL_KEYS, f"只扫到 {len(found)} 个 key，扫描逻辑可能失效"


def test_every_literal_key_exists_in_both_locales() -> None:
    found = _literal_keys()
    problems: list[str] = []
    for locale_file in sorted(LOCALES.glob("*.json")):
        keys = _flat_keys(locale_file)
        missing = {key: where for key, where in found.items() if key not in keys}
        for key, where in sorted(missing.items()):
            problems.append(f"{locale_file.name}: 缺 {key!r}（用于 {', '.join(sorted(where))}）")
    assert not problems, "代码用到但语言包里没有的 key：\n  " + "\n  ".join(problems)


def test_dynamic_key_families_have_matching_entries() -> None:
    """f-string 族的常量前缀必须能找到同族 key（防止整族被改名后静默失效）。"""
    prefixes = _dynamic_prefixes()
    assert prefixes, "没有扫到任何动态 key —— 若代码结构变了，请更新本测试的扫描规则"
    keys = _flat_keys(LOCALES / "zh-CN.json")
    problems = [
        f"{prefix!r}（用于 {', '.join(sorted(where))}）在语言包里没有任何同族 key"
        for prefix, where in sorted(prefixes.items())
        if not any(key.startswith(prefix) for key in keys)
    ]
    assert not problems, "\n  ".join(problems)
