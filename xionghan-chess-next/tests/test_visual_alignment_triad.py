"""三端视觉对齐清单的**漂移守卫**（P1-8）。

## 它守什么

清单 `docs/visual_alignment_ledger.json` 把「桌面 / web 旧树 / webapp」三套渲染器的
视觉参数逐项列成数据。本用例做两件事：

1. **片段存在性 + 数值**：每端的 `lit` 模板（含一个 `{}` 占位符）必须在源码里原样出现，
   且从片段里取到的数必须等于清单记录的 `value`；
2. **一致性分级**：`compare=true` 的行按三端数值的最大极差判档
   （≤ aligned → `aligned`，≤ minor → `minor`，否则 `drift`），必须与清单记的
   `verdict` 相同。

于是「只改了一端、三端悄悄分叉」会在这里变红，而不是等美术回来返工；
「把三端对齐了」同样会红 —— 必须**显式**更新清单与叙述文档，
让漂移从「不知不觉」变成「写进评审」。

## 为什么用字面片段而不是『按语义解析』

三套渲染器语言不同（QPainter / 两棵 canvas 树），语义解析器本身就会成为第四份实现。
字面片段最笨也最耐用：改一个字，片段不匹配，测试点名到文件。
正则元字符由本用例 `re.escape` 转义，清单里可以写原生代码、不必手写转义。

## 为什么不做恒等断言

清单记录的是**现状快照**，不是「应该相等」的理想值。三端确实存在设计差异
（如 webapp 无位图路径、桌面投影是径向渐变而网页是 canvas 阴影），
把这些强行断言成相等，只会得到一个假绿的门禁。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs" / "visual_alignment_ledger.json"
DOC_PATH = ROOT / "docs" / "VISUAL_ALIGNMENT_TRIAD.md"
ENDS = ("desktop", "web", "webapp")


def _ledger() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def _template_regex(lit: str) -> re.Pattern[str] | None:
    """把含单个 `{}` 的代码片段模板变成「字面 + 一个数值捕获组」的正则。

    不含占位符的片段只做字面存在性检查（返回 `None`），用于「形态」类条目。
    """
    if lit.count("{}") == 0:
        return None
    assert lit.count("{}") == 1, f"lit 模板最多含一个占位符：{lit!r}"
    head, tail = lit.split("{}")
    # 允许以点开头的写法（源码里大量 `*.5` / `*.06`），否则 `.{}` 只能抠到整数部分。
    return re.compile(re.escape(head) + r"(-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+))" + re.escape(tail))


def _source(path: Path) -> str:
    assert path.exists(), f"清单指向的渲染器不存在：{path}"
    return path.read_text(encoding="utf-8")


def _matches(spec: dict, end: str) -> list[str]:
    path = ROOT / (spec.get("file") or _ledger()["default_files"][end])
    regex = _template_regex(spec["lit"])
    if regex is None:  # 纯形态片段：只要字面在，就算命中
        assert spec["lit"] in _source(path), (
            f"{path.relative_to(ROOT).as_posix()} 里找不到形态片段 {spec['lit']!r}。\n"
            "要么渲染器结构变了，要么清单过期 —— 先更新清单与文档，再改代码。"
        )
        return []
    found = regex.findall(_source(path))
    assert found, (
        f"{path.relative_to(ROOT).as_posix()} 里找不到片段 {spec['lit']!r}。\n"
        "要么渲染器结构变了，要么清单过期 —— 先更新清单与文档，再改代码。"
    )
    return found


def _observed_value(spec: dict, end: str) -> tuple[float, float]:
    """返回 (源码里的原值, 归一化后的可比量)。"""
    found = _matches(spec, end)
    index = int(spec.get("index", 0))
    assert len(found) > index, (
        f"{end}：片段 {spec['lit']!r} 只命中 {len(found)} 处，清单要取第 {index + 1} 处。"
    )
    raw = float(found[index])
    return raw, raw * float(spec.get("scale", 1.0))


def _graded_verdict(values: dict[str, float], tol: dict[str, float]) -> str:
    spread = max(values.values()) - min(values.values())
    if spread <= tol["aligned"]:
        return "aligned"
    if spread <= tol["minor"]:
        return "minor"
    return "drift"


ROWS = _ledger()["rows"]


@pytest.mark.parametrize("row_id", [row["id"] for row in ROWS])
def test_row_matches_ledger(row_id: str) -> None:
    """逐行核对：片段在、数值对、分级与清单一致。"""
    data = _ledger()
    row = next(item for item in data["rows"] if item["id"] == row_id)
    values: dict[str, float] = {}

    for end in ENDS:
        spec = row["ends"].get(end)
        if not spec:
            continue
        if spec.get("value") is None:  # 只做形态存在性：命中即可，数值不参与比较
            _matches(spec, end)
            continue
        raw, normalized = _observed_value(spec, end)
        assert abs(raw - float(spec["raw"])) <= 1e-6, (
            f"{row['id']}（{row['name']}）/{end} 的原值变了："
            f"清单记 {spec['raw']}，源码现在是 {raw:g}。\n"
            "视觉参数是用户可见契约：请同时更新清单、叙述文档与另外两端，再提交。"
        )
        values[end] = normalized

    if not row["compare"]:
        assert row["verdict"] == "form", (
            f"{row['id']} 标了 compare=false 却写了分级 {row['verdict']!r}；"
            "不可比的行只能记 form"
        )
        return

    assert len(values) >= 2, f"{row['id']} 标了 compare=true 但可比的端不足 2 个"
    observed_verdict = _graded_verdict(values, data["tolerance"])
    assert observed_verdict == row["verdict"], (
        f"{row['id']}（{row['name']}）三端分叉档位变了：清单记 {row['verdict']!r}，"
        f"实测 {observed_verdict!r}（{ {k: round(v, 3) for k, v in values.items()} }）。\n"
        "若不是有意对齐/分叉，说明有一端被单独改了。"
    )


def test_ledger_covers_the_agreed_items_and_doc() -> None:
    """清单不许被悄悄抽空：条目数、可比条目数、文档对照都钉住。"""
    data = _ledger()
    rows = data["rows"]
    assert len(rows) >= 12, "清单条目被删减了：P1-8 约定至少 12 项"
    assert len({row["id"] for row in rows}) == len(rows), "清单里 id 重复"
    comparable = [row for row in rows if row["compare"]]
    assert len(comparable) >= 6, "可比条目少于 6，门禁已经形同空跑"

    doc = DOC_PATH.read_text(encoding="utf-8")
    for row in rows:
        assert row["id"] in doc, f"{row['id']} 没有写进 {DOC_PATH.name}：清单与叙述文档必须成对更新"
        assert row["name"] in doc, f"{row['id']} 的名称「{row['name']}」没有出现在叙述文档里"


def test_every_end_has_at_least_one_row() -> None:
    """三端都要被覆盖：否则「对齐清单」可以只盯着自己顺手的那一端。"""
    data = _ledger()
    covered = {end for row in data["rows"] for end, spec in row["ends"].items() if spec}
    assert covered == set(ENDS), f"端点覆盖不全，缺 {set(ENDS) - covered}"
