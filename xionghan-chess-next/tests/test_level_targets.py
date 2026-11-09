"""三档目标参数表的守卫（`scripts/level_targets.py`）。

这张表是 S4-2a 的输入：测量/标定都从它生成 `SearchConfig`，**不读 `CONFIGS`**
（后者数值属 S4-2b）。表被改错时，测出来的 `max_nodes` 与标定胜率都会偏，
但报告本身不会报错——所以把关键字段钉在这里。
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from level_targets import TARGETS, Tier  # noqa: E402


def test_three_tiers_match_the_design_table() -> None:
    assert set(TARGETS) == {"beginner", "medium", "hard"}
    beginner, medium, hard = TARGETS["beginner"], TARGETS["medium"], TARGETS["hard"]

    assert (beginner.depth, beginner.root_limit, beginner.branch_limit,
            beginner.quiescence_depth) == (1, 10, 6, 1)
    assert (medium.depth, medium.root_limit, medium.branch_limit,
            medium.quiescence_depth) == (2, 18, 10, 4)
    assert (hard.depth, hard.root_limit, hard.branch_limit,
            hard.quiescence_depth) == (3, 18, 18, 6)

    assert (beginner.cap, medium.cap, hard.cap) == (2.0, 15.0, 60.0)
    assert beginner.randomness == 0.30
    assert medium.randomness == hard.randomness == 0.0


def test_config_injection_and_max_nodes_sentinel() -> None:
    medium = TARGETS["medium"]
    assert medium.config().max_nodes == medium.max_nodes == 500
    assert medium.config(cap=300.0).time_limit == 300.0
    assert medium.config(max_nodes=None).max_nodes is None
    assert medium.config(max_nodes=1234).max_nodes == 1234
    # 入门/高级在测量回填前不启用预算。
    assert TARGETS["beginner"].config().max_nodes is None
    assert TARGETS["hard"].config().max_nodes is None


def test_tier_config_is_frozen_and_does_not_touch_global_configs() -> None:
    from xionghan_chess.core.ai import CONFIGS, Difficulty

    before = dict(CONFIGS)
    config = TARGETS["hard"].config()
    assert config.depth == 3
    assert CONFIGS == before
    assert CONFIGS[Difficulty.HARD].depth != config.depth, (
        "目标值（d3）与当前 CONFIGS（d8）必须不同：S4-2b 才改全局表")
    assert isinstance(TARGETS["hard"], Tier)


def test_candidate_selection_prefers_largest_passing_and_flags_bracket() -> None:
    from measure_node_budget import choose_candidate

    all_pass = [
        {"max_nodes": 1000, "passes_internal": True},
        {"max_nodes": 800, "passes_internal": True},
        {"max_nodes": 600, "passes_internal": True},
    ]
    selected, bracketed = choose_candidate(all_pass)
    assert selected is not None and selected["max_nodes"] == 1000, "全过取 c50（候选最大）"
    assert bracketed is False, "没有失败候选 = 上界没夹住"

    mixed = [
        {"max_nodes": 1000, "passes_internal": False},
        {"max_nodes": 800, "passes_internal": True},
        {"max_nodes": 600, "passes_internal": True},
    ]
    selected, bracketed = choose_candidate(mixed)
    assert selected is not None and selected["max_nodes"] == 800
    assert bracketed is True

    failed = [{"max_nodes": 100, "passes_internal": False}]
    assert choose_candidate(failed) == (None, False)
