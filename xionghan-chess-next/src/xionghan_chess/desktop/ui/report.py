"""复盘报告初版（桌面单端）：聚合 `core.analysis.analyze_game` 的结果。

## 口径

- **轻量非权威（P0-1）**：**不显示精确分值、不用仪表盘/进度条**。呈现面只有
  文字档位（最佳 / 良好 / 欠准 / 失误 / 严重失误）与相对走势描述，并附
  「浅层参考」中性标注。`score`/`scoreLoss`/`winRate` 仍是数据（`key_moves`、
  `curve` 照旧带出），只是不写进给用户看的文案。
- **非权威**：只做归纳描述，不给训练计划或指导句式。文案里不出现
  「你应该 / 你错了 / 建议 / 应当」这类评判或引导句；统一用
  「本局出现 N 处非最佳手」「第 X 手 · 着法 · 档位」这类陈述。
- **离线本地**：本模块不引入任何网络 / 遥测模块（不 import requests / urllib / http）。
- 不改棋谱格式；报告由 analysis 既有输出聚合而成，不重新跑引擎。
- 文案走 `dl()` / `dlf()`（中文原文作 key，英文查 `texts` 词表），本模块不留裸中文字面量。

## 聚合内容

- 失误数：`inaccuracy + mistake + blunder`（`best`/`good` 不计入）；
- 关键手：按 `scoreLoss` 降序取前 N 手（排序用分值，呈现只用档位）；
- 局面曲线：仍聚合起点 / 终点 / 区间（仅用于相对走势归纳，不上屏）；
- 结论段：只归纳失分集中在哪个阶段，不给改进建议。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..texts import PHASE_NAMES, QUALITY_LABELS, dl, dlf

_NON_BEST = ("inaccuracy", "mistake", "blunder")

# 走势描述的判定容差（胜率点差）：只用来决定措辞，绝不写进任何文案。
_TREND_EPS = 5.0


@dataclass(frozen=True, slots=True)
class ReviewReport:
    analyzed_plies: int
    counts: dict[str, int]
    mistake_total: int
    key_moves: list[dict[str, Any]]
    curve: dict[str, float]
    conclusion: str
    lines: list[str] = field(default_factory=list)


def _phase_loss(moves: list[dict[str, Any]]) -> tuple[int, dict[int, int]] | None:
    """按手序三分段统计失分，返回失分最多的阶段序号与各段失分。"""
    n = len(moves)
    if n == 0:
        return None
    bounds = [0, n // 3, (2 * n) // 3, n]
    losses: dict[int, int] = {}
    for index, _phase in enumerate(PHASE_NAMES):
        segment = moves[bounds[index] : bounds[index + 1]]
        losses[index] = sum(int(m.get("scoreLoss", 0)) for m in segment)
    return max(losses, key=losses.get), losses


def _curve_summary(curve: list[float]) -> dict[str, float]:
    if not curve:
        return {"start": 0.0, "end": 0.0, "min": 0.0, "max": 0.0}
    return {
        "start": round(float(curve[0]), 1),
        "end": round(float(curve[-1]), 1),
        "min": round(min(float(v) for v in curve), 1),
        "max": round(max(float(v) for v in curve), 1),
    }


def _conclusion(moves: list[dict[str, Any]]) -> str:
    phase = _phase_loss(moves)
    if phase is None:
        return dl("本局可复盘的手数不足，未形成阶段归纳。")
    top_index, losses = phase
    if losses[top_index] <= 0:
        return dl("本局各阶段失分分布较为平均。")
    return dlf("本局失分集中在{phase}阶段。", phase=dl(PHASE_NAMES[top_index]))


def _trend_phrase(points: list[float]) -> str:
    """把胜率曲线概括成相对走势：只给方向，不给百分比与点数。

    P0-1 要求呈现轻量非权威，所以这里刻意不输出任何数字 —— 判定用的
    `_TREND_EPS` 只影响选哪一句措辞。曲线本身仍留在 `ReviewReport.curve` 里
    供以后的分析使用。
    """
    if len(points) < 2:
        return dl("走势样本不足，未作归纳")
    start, end = float(points[0]), float(points[-1])
    inner = [float(v) for v in points[1:-1]]
    dipped = bool(inner) and min(inner) < min(start, end) - _TREND_EPS
    if dipped and end >= start:
        return dl("中段一度吃紧后转好")
    if dipped:
        return dl("中段一度吃紧，末段仍未回到开局局面")
    if end < start - _TREND_EPS:
        return dl("开局之后逐步转入吃紧")
    if end > start + _TREND_EPS:
        return dl("整体逐步转为宽松")
    return dl("整体大致保持平稳")


def build_report(result: dict[str, Any], top_n: int = 3) -> ReviewReport:
    """从 `analyze_game` 输出聚合复盘报告。"""
    moves = list(result.get("moves", []))
    summary = {key: int(value) for key, value in result.get("summary", {}).items()}
    analyzed = int(result.get("analyzedPlies", len(moves)))

    counts = {key: summary.get(key, 0) for key in QUALITY_LABELS}
    mistake_total = sum(counts[key] for key in _NON_BEST)

    ranked = sorted(
        (m for m in moves if int(m.get("scoreLoss", 0)) > 0),
        key=lambda m: int(m.get("scoreLoss", 0)),
        reverse=True,
    )
    key_moves = [
        {
            "ply": int(m["ply"]),
            "notation": m.get("notation", ""),
            "quality": m.get("quality", ""),
            "quality_label": dl(QUALITY_LABELS.get(m.get("quality", ""), m.get("quality", ""))),
            "score_loss": int(m.get("scoreLoss", 0)),
        }
        for m in ranked[:top_n]
    ]

    curve_points = [float(v) for v in result.get("winRateCurve", [])]
    curve = _curve_summary(curve_points)
    conclusion = _conclusion(moves)

    lines: list[str] = [dlf("本局共复盘 {ply} 手。", ply=analyzed)]
    lines.append(
        dlf(
            "本局出现 {total} 处非最佳手（欠准 {a}、失误 {b}、严重失误 {c}）。",
            total=mistake_total,
            a=counts["inaccuracy"],
            b=counts["mistake"],
            c=counts["blunder"],
        )
    )
    if key_moves:
        lines.append(dl("失分较多的手："))
        for move in key_moves:
            lines.append(
                dlf(
                    "第 {ply} 手 {notation} · {quality}。",
                    ply=move["ply"],
                    notation=move["notation"],
                    quality=move["quality_label"],
                )
            )
    lines.append(dlf("胜率走势：{trend}。", trend=_trend_phrase(curve_points)))
    lines.append(conclusion)
    # 「浅层参考」措辞与 web / webapp 同一句（webapp i18n: analysis.shallow /
    # analysis.shallowHint），不另造说法。
    lines.append(dl("浅层参考：依据本机浅层搜索，仅供参考。"))

    return ReviewReport(
        analyzed_plies=analyzed,
        counts=counts,
        mistake_total=mistake_total,
        key_moves=key_moves,
        curve=curve,
        conclusion=conclusion,
        lines=lines,
    )


def to_text(report: ReviewReport) -> str:
    """导出用纯文本（复制 / 存 txt）；离线本地，不新增网络请求。"""
    return "\n".join(report.lines)
