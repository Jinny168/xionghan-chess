"""复盘报告初版（桌面单端）：聚合 `core.analysis.analyze_game` 的结果。

## 口径

- **非权威**：只做归纳描述，不给训练计划或指导句式。文案里不出现
  「你应该 / 你错了 / 建议 / 应当」这类评判或引导句；统一用
  「本局出现 N 处非最佳手」「第 X 手评分下降 Y」这类陈述。
- **离线本地**：本模块不引入任何网络 / 遥测模块（不 import requests / urllib / http）。
- 不改棋谱格式；报告由 analysis 既有输出聚合而成，不重新跑引擎。

## 聚合内容

- 失误数：`inaccuracy + mistake + blunder`（`best`/`good` 不计入）；
- 关键手：按 `scoreLoss` 降序取前 N 手；
- 局面曲线：胜率曲线的起点 / 终点 / 区间 / 三段失分集中阶段；
- 结论段：只归纳失分集中在哪个阶段，不给改进建议。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 分类标签（描述性分类，不是评判句）。
QUALITY_LABELS = {
    "best": "最佳",
    "good": "良好",
    "inaccuracy": "欠准",
    "mistake": "失误",
    "blunder": "严重失误",
}

# 指导 / 评判禁词：测试用正则扫描，文案不得命中。
FORBIDDEN_PHRASES = (
    "你应该",
    "你错了",
    "建议",
    "应当",
    "需要改进",
    "多加练习",
    "下一步应",
    "最好",
    "务必",
    "你需要",
)

_NON_BEST = ("inaccuracy", "mistake", "blunder")
_PHASES = ("开局", "中局", "残局")


@dataclass(frozen=True, slots=True)
class ReviewReport:
    analyzed_plies: int
    counts: dict[str, int]
    mistake_total: int
    key_moves: list[dict[str, Any]]
    curve: dict[str, float]
    conclusion: str
    lines: list[str] = field(default_factory=list)


def _phase_loss(moves: list[dict[str, Any]]) -> tuple[str, dict[str, int]] | None:
    """按手序三分段统计失分，返回失分最多的阶段与各段失分。"""
    n = len(moves)
    if n == 0:
        return None
    bounds = [0, n // 3, (2 * n) // 3, n]
    losses: dict[str, int] = {}
    for index, phase in enumerate(_PHASES):
        segment = moves[bounds[index] : bounds[index + 1]]
        losses[phase] = sum(int(m.get("scoreLoss", 0)) for m in segment)
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


def _conclusion(moves: list[dict[str, Any]], curve: dict[str, float]) -> str:
    phase = _phase_loss(moves)
    if phase is None:
        return "本局可复盘的手数不足，未形成阶段归纳。"
    top_phase, losses = phase
    if losses[top_phase] <= 0:
        return "本局各阶段失分分布较为平均。"
    return f"本局失分集中在{top_phase}阶段。"


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
            "quality_label": QUALITY_LABELS.get(m.get("quality", ""), m.get("quality", "")),
            "score_loss": int(m.get("scoreLoss", 0)),
        }
        for m in ranked[:top_n]
    ]

    curve = _curve_summary(list(result.get("winRateCurve", [])))
    conclusion = _conclusion(moves, curve)

    lines: list[str] = [f"本局共复盘 {analyzed} 手。"]
    lines.append(
        "本局出现 {total} 处非最佳手（欠准 {a}、失误 {b}、严重失误 {c}）。".format(
            total=mistake_total,
            a=counts["inaccuracy"],
            b=counts["mistake"],
            c=counts["blunder"],
        )
    )
    if key_moves:
        lines.append("评分下降较多的手：")
        for move in key_moves:
            lines.append(
                "第 {ply} 手 {notation} 评分下降 {loss}（{quality}）。".format(
                    ply=move["ply"],
                    notation=move["notation"],
                    loss=move["score_loss"],
                    quality=move["quality_label"],
                )
            )
    lines.append(
        "胜率曲线由 {start}% 走到 {end}%，区间 {min}%–{max}%。".format(
            start=curve["start"], end=curve["end"], min=curve["min"], max=curve["max"]
        )
    )
    lines.append(conclusion)

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
