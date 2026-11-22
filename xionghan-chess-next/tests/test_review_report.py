"""E2 复盘报告初版门禁。

覆盖：
- 聚合数字与 `analysis` 模块输出一致（失误数、关键手排序、曲线区间）；
- 文案不含指导 / 评判句式（禁词正则扫描）；
- 报告路径不引入网络模块（requests / urllib / http / socket）；
- 结论只做阶段归纳，不给训练计划。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from xionghan_chess.desktop import texts
from xionghan_chess.desktop.ui import report as report_module

ROOT = Path(__file__).resolve().parents[1]

# 指导 / 评判禁词：报告文案不得命中（测试侧数据，不进 src 守卫扫描范围）。
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


def _result() -> dict:
    return {
        "analyzedPlies": 6,
        "summary": {"best": 2, "good": 1, "inaccuracy": 1, "mistake": 1, "blunder": 1},
        "winRateCurve": [50.0, 48.0, 40.0, 35.0, 30.0, 28.0],
        "moves": [
            {"ply": 1, "notation": "漢六進一", "quality": "best", "scoreLoss": 0},
            {"ply": 2, "notation": "車八平七", "quality": "good", "scoreLoss": 15},
            {"ply": 3, "notation": "炮二平五", "quality": "inaccuracy", "scoreLoss": 120},
            {"ply": 4, "notation": "馬三進四", "quality": "mistake", "scoreLoss": 300},
            {"ply": 5, "notation": "卒五進一", "quality": "blunder", "scoreLoss": 500},
            {"ply": 6, "notation": "相三進五", "quality": "best", "scoreLoss": 0},
        ],
    }


def test_aggregated_numbers_match_analysis() -> None:
    rep = report_module.build_report(_result())
    # 失误数 = 欠准 + 失误 + 严重失误；best/good 不计入。
    assert rep.mistake_total == 3
    assert rep.counts == {"best": 2, "good": 1, "inaccuracy": 1, "mistake": 1, "blunder": 1}
    assert rep.analyzed_plies == 6
    # 关键手按 loss 降序取前 3。
    assert [m["ply"] for m in rep.key_moves] == [5, 4, 3]
    assert [m["score_loss"] for m in rep.key_moves] == [500, 300, 120]
    # 曲线区间与起终点。
    assert rep.curve == {"start": 50.0, "end": 28.0, "min": 28.0, "max": 50.0}


def test_report_text_has_no_authoritative_phrasing() -> None:
    rep = report_module.build_report(_result())
    blob = "\n".join(rep.lines) + "\n" + rep.conclusion + "\n" + report_module.to_text(rep)
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in blob, f"报告文案命中指导/评判禁词：{phrase}"


def test_conclusion_is_descriptive_only() -> None:
    rep = report_module.build_report(_result())
    assert rep.conclusion.strip().endswith("。")
    # 归纳句只能落在阶段标签上，不出现动作指令。
    assert any(phase in rep.conclusion for phase in texts.PHASE_NAMES)


def test_report_path_has_no_network_import() -> None:
    source = Path(report_module.__file__).read_text(encoding="utf-8")
    for module in ("requests", "urllib", "http", "socket", "aiohttp"):
        assert not re.search(rf"^\s*(import|from)\s+{module}\b", source, re.MULTILINE), (
            f"报告路径引入了网络模块：{module}"
        )


def test_empty_result_does_not_raise() -> None:
    rep = report_module.build_report({"analyzedPlies": 0, "summary": {}, "moves": [], "winRateCurve": []})
    assert rep.mistake_total == 0
    assert rep.key_moves == []
    assert rep.conclusion


@pytest.mark.parametrize(
    ("curve", "expected"),
    [
        # 无中段凹陷、起终点基本持平
        ([50.0, 51.0, 50.0, 49.0, 50.0], "整体大致保持平稳"),
        # 容差边界：中段只回落 4 点，不构成"吃紧"（把 _TREND_EPS 调小会红）
        ([50.0, 48.0, 46.0, 49.0, 51.0], "整体大致保持平稳"),
        # 中段凹陷超过容差，末段回到开局附近
        ([50.0, 45.0, 30.0, 28.0, 40.0, 50.0], "中段一度吃紧后转好"),
        # 无凹陷、单调下行
        ([50.0, 48.0, 46.0, 44.0, 42.0, 40.0], "开局之后逐步转入吃紧"),
        # 中段凹陷且末段仍低于开局
        ([50.0, 45.0, 30.0, 28.0, 40.0, 42.0], "中段一度吃紧，末段仍未回到开局局面"),
        # 无凹陷、单调上行
        ([40.0, 42.0, 44.0, 46.0, 48.0, 50.0], "整体逐步转为宽松"),
        # 一个点不足以谈走势
        ([50.0], "走势样本不足，未作归纳"),
    ],
)
def test_trend_phrase_matches_curve_shape(curve: list[float], expected: str) -> None:
    """`_TREND_EPS` 决定措辞分支，必须被钉住：呈现面没有百分比可复核。

    文字准确性完全压在阈值上，用户又无法自己验算，所以这里直接把六种曲线形状
    与断言到的那句话对齐；调阈值或改判定顺序，至少有一条会红。
    """
    report = report_module.build_report(
        {"analyzedPlies": 0, "summary": {}, "moves": [], "winRateCurve": curve}
    )
    trend_lines = [line for line in report.lines if line.startswith("胜率走势：")]
    assert trend_lines == [f"胜率走势：{expected}。"], f"曲线 {curve} 选错了措辞"
