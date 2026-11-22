"""webapp：分析上限提示的边界（恰好 120 手不得报「只看了前 N 手」）。

`runAnalysis` 只分析前 `CAP` 手（`Math.min(history.length, CAP)`），`finishAnalysis`
在结果被**截断**时补一句「（仅分析前 N 手）」。原先条件是 `results.length >= 120`：
恰好 120 手时全部棋谱都已分析，却照样提示，用户会以为后半盘被跳过了。

桌面侧的口径是 `plies > ANALYSIS_PLY_CAP`（`>`，不是 `>=`）。两端必须一致，
且 `120` 只能有一个来源（`const CAP = 120`），改上限时提示文案跟着走。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "webapp" / "js" / "ui" / "app.js"


def _source() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def _cap() -> int:
    match = re.search(r"^const CAP = (\d+);$", _source(), re.M)
    assert match, "找不到模块级 `const CAP = <n>;`"
    return int(match.group(1))


def test_cap_is_declared_once_at_module_scope() -> None:
    source = _source()
    declarations = re.findall(r"^\s*const CAP = \d+;$", source, re.M)
    assert len(declarations) == 1, "CAP 只应有模块级一处声明，函数内不得再硬编码一份"
    body = _function_body(source, "runAnalysis")
    assert "Math.min(history.length, CAP)" in body, "runAnalysis 必须复用 CAP 截断"
    assert not re.search(r"const CAP = \d+;", body), "runAnalysis 内不应再声明 CAP"


def test_capped_hint_only_fires_when_really_truncated() -> None:
    body = _function_body(_source(), "finishAnalysis")
    match = re.search(r"results\.length\s*(>=?)\s*CAP", body)
    assert match, "finishAnalysis 里找不到基于 CAP 的截断判断"
    operator = match.group(1)
    assert operator == ">", (
        f"截断判断用了 `{operator} CAP`：恰好 {_cap()} 手时全部已分析，不该提示截断"
    )
    assert "t('analysis.capped', { n: CAP })" in body, "提示文案里的手数必须来自 CAP，不得硬编码 120"

    # 边界真值表（用源码里解析出的 CAP，而不是另写一份 120）。
    cap = _cap()
    truth = {cap: False, cap + 1: True}
    for length, expected in truth.items():
        actual = length > cap if operator == ">" else length >= cap
        assert actual is expected, (
            f"{length} 手时提示应为 {expected}，实际 {actual}（CAP={cap}，算子 `{operator}`）"
        )
