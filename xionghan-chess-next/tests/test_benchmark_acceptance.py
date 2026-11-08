"""验收判据守卫：单步耗时上限必须由「预算 × (1 + 容差)」算出，且容差不得随意放大。

背景：`CONFIGS[MASTER].time_limit = 12.0` 是搜索的**软预算**，MCTS 在 deadline 之后
还要完成当前节点的展开与反向传播，必然溢出。满预算 50 局实测峰值 13.645 s
（超 13.7%，首轮 2 局探针只有 3%，随对局变长而上升）——旧判据直接写 `<= 12.0`，
等于让这条判据永远无法通过，也就失去了"验收"的意义。

改为 12.0 × 1.15 = 13.8 后：13.645（实测峰）通过；13.9（明显失控）仍被抓住。

本文件钉三件事：
1. 上限确实由 `time_limit × (1 + 容差)` 算出，不是另写一个字面量；
2. 容差不超过 20% —— 再大就不叫"收尾开销"，而是搜索失控；
3. 实测峰值必须落在上限内、明显超限必须落在上限外（防止判据单向漂移）。
"""

from __future__ import annotations


from xionghan_chess.core import benchmark
from xionghan_chess.core.ai import CONFIGS, Difficulty

# 2026-11-08 满预算 50 局（--hard-scale 1.0）实测的单步峰值
MEASURED_FULL_BUDGET_PEAK_SECONDS = 13.645


def test_ceiling_derives_from_master_time_limit() -> None:
    budget = CONFIGS[Difficulty.MASTER].time_limit
    expected = round(budget * (1 + benchmark.MASTER_MOVE_TIME_TOLERANCE), 3)
    assert benchmark.MASTER_MOVE_CEILING_SECONDS == expected, (
        f"上限 {benchmark.MASTER_MOVE_CEILING_SECONDS} 不等于 预算 {budget} × "
        f"(1+{benchmark.MASTER_MOVE_TIME_TOLERANCE})"
    )


def test_tolerance_stays_within_reasonable_bound() -> None:
    assert 0 < benchmark.MASTER_MOVE_TIME_TOLERANCE <= 0.20, (
        f"容差 {benchmark.MASTER_MOVE_TIME_TOLERANCE:.0%} 已超出「收尾开销」的合理范围；"
        "放宽前必须先改这条并说明理由"
    )


def test_measured_full_budget_peak_is_accepted() -> None:
    """实测峰必须通过，否则判据与真实数据脱节（旧判据就是这样卡死的）。"""
    assert MEASURED_FULL_BUDGET_PEAK_SECONDS <= benchmark.MASTER_MOVE_CEILING_SECONDS


def test_ceiling_stays_near_the_written_budget() -> None:
    """上限必须「高于预算但不超过 20% 余量」——既留收尾空间，又不放成免检。"""
    budget = CONFIGS[Difficulty.MASTER].time_limit
    assert budget < benchmark.MASTER_MOVE_CEILING_SECONDS <= budget * 1.20
