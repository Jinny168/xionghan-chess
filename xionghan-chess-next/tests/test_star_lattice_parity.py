"""星轨锚点的**跨端逐点对拍**（P1-7 硬门禁）。

## 为什么必须逐点比

三端各有一份"选中射 → 四斜向最近星位锚点"的换算：
  · 桌面直接复用 core `RulesEngine._nearest_archer_star_distance`；
  · webapp 的 `star_hints.js` 复用 `webapp/js/core/rules.js` 的同名方法；
  · web 旧树没有这个方法（星点来自服务端序列化），用纯几何版 `star-hints.js`。

只要有一端方向表写错、步长写反、边界差一格，玩家看到的星轨就会和规则锚点错位
——而"看起来有一条线"的单测发现不了。这里把同一组 (points, source, rows, cols)
同时喂给两份 JS，与 Python core 的四方向结果**逐点**相等才放行。

星点集只从 core 的 `archer_star_points()` 取，测试**不重新判定哪些点是星位**。
覆盖：13×13 全部星点 + 全部非星点位置（即整盘 169 格）；另加 10×9 无射盘
（锚点应全空）。缺 node 时按 `tests/_node_guard.py` 硬失败，不许静默 green。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from _node_guard import NODE, module_skip_mark, require_node

from xionghan_chess.core.model import Position
from xionghan_chess.core.profiles import RuleOptions, get_profile
from xionghan_chess.core.rules import RulesEngine, archer_star_points

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "star_hints_probe.mjs"
WEBAPP_MODULE = ROOT / "webapp" / "js" / "ui" / "star_hints.js"
WEB_MODULE = ROOT / "web" / "js" / "star-hints.js"

DIRECTIONS = ((1, 1), (1, -1), (-1, 1), (-1, -1))

if (mark := module_skip_mark()) is not None:
    pytestmark = mark


class _ProbeRules(RulesEngine):
    """只替换星点集与盘面尺寸的只读探针；距离算法**继承 core 原样**。"""

    def __init__(self, points: list[tuple[int, int]], rows: int, cols: int) -> None:
        self.profile = SimpleNamespace(rows=rows, cols=cols)  # type: ignore[assignment]
        self.options = RuleOptions()
        self._points = frozenset(Position(row, col) for row, col in points)

    @property  # type: ignore[override]
    def archer_star_points(self) -> frozenset[Position]:
        return self._points

    def inside(self, pos: Position) -> bool:
        return 0 <= pos.row < self.profile.rows and 0 <= pos.col < self.profile.cols


def _expected(points: list[tuple[int, int]], rows: int, cols: int, source: tuple[int, int]) -> list[list[int]]:
    rules = _ProbeRules(points, rows, cols)
    origin = Position(*source)
    anchors: list[list[int]] = []
    for step_row, step_col in DIRECTIONS:
        distance = rules._nearest_archer_star_distance(origin, step_row, step_col)  # noqa: SLF001
        if distance > 0:
            anchors.append([source[0] + distance * step_row, source[1] + distance * step_col])
    return anchors


def _cases() -> list[dict]:
    stars = sorted((point.row, point.col) for point in archer_star_points(get_profile("desktop_classic")))
    assert len(stars) == 13, f"经典档星点数变了：{stars}（对拍样本需要复核）"
    cases = [
        {
            "points": [{"row": row, "col": col} for row, col in stars],
            "rows": 13,
            "cols": 13,
            "source": {"row": row, "col": col},
        }
        for row in range(13)
        for col in range(13)
    ]
    # 10×9 传统盘没有射：`archer_star_points` 为空，两端口径都必须返回空锚点。
    assert not archer_star_points(get_profile("traditional"))
    cases += [
        {"points": [], "rows": 10, "cols": 9, "source": {"row": row, "col": col}}
        for row in range(10)
        for col in range(9)
    ]
    return cases


def test_js_anchor_rays_match_python_core_point_by_point() -> None:
    require_node()
    cases = _cases()
    payload = json.dumps({"cases": cases})
    result = subprocess.run(
        [NODE or "node", str(PROBE), str(WEBAPP_MODULE), str(WEB_MODULE)],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
    )
    observed = json.loads(result.stdout)
    assert len(observed) == len(cases), f"探针回传 {len(observed)} 组，期望 {len(cases)} 组"

    mismatches: list[str] = []
    for case, got in zip(cases, observed, strict=True):
        points = [(item["row"], item["col"]) for item in case["points"]]
        source = (case["source"]["row"], case["source"]["col"])
        expected = _expected(points, case["rows"], case["cols"], source)
        for side in ("webapp", "web"):
            if got[side] != expected:
                mismatches.append(f"{side} source={source}: 期望 {expected}，实际 {got[side]}")
            if len(got[side]) > 4:
                mismatches.append(f"{side} source={source}: 单帧锚点超过 4 条：{got[side]}")
    assert not mismatches, "跨端锚点不一致：\n" + "\n".join(mismatches[:20])


def test_parity_suite_is_not_vacuous() -> None:
    """样本必须真的覆盖"有锚点"的情形，否则两边都返回空也会假绿。"""
    cases = _cases()
    non_empty = sum(
        1
        for case in cases
        if _expected(
            [(item["row"], item["col"]) for item in case["points"]],
            case["rows"],
            case["cols"],
            (case["source"]["row"], case["source"]["col"]),
        )
    )
    total = sum(
        len(
            _expected(
                [(item["row"], item["col"]) for item in case["points"]],
                case["rows"],
                case["cols"],
                (case["source"]["row"], case["source"]["col"]),
            )
        )
        for case in cases
    )
    assert len(cases) == 259, len(cases)
    # 13 个星点 × 每点至多 4 方向：实际只有 45 个起点能望到星点、合计 96 条锚点。
    assert non_empty >= 40, f"有锚点的样本只有 {non_empty} 组，对拍形同虚设"
    assert total >= 90, f"锚点总数只有 {total} 条，样本覆盖不足"
