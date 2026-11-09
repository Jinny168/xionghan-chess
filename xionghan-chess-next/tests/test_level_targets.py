"""三档目标参数表的守卫（`scripts/level_targets.py`）。

这张表是测量/标定的输入：从它生成 `SearchConfig`。S4-2b 之后三档数值与
`core.ai.CONFIGS` 一致（由 `test_level_targets_match_configs.py` 钉住）；
这里继续守字段级细节（candidate_count、cap、max_nodes 占位）。
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

    assert (beginner.cap, medium.cap, hard.cap) == (3.0, 30.0, 120.0)
    assert (beginner.candidate_count, medium.candidate_count,
            hard.candidate_count) == (3, 1, 1)
    assert beginner.randomness == 0.30
    assert medium.randomness == hard.randomness == 0.0


def test_config_injection_and_max_nodes_sentinel() -> None:
    medium = TARGETS["medium"]
    # 三档都暂不启用 max_nodes（中局节点数无可靠测量）。
    assert medium.config().max_nodes is None
    assert medium.config(cap=300.0).time_limit == 300.0
    assert medium.config(max_nodes=1234).max_nodes == 1234
    assert TARGETS["beginner"].config().max_nodes is None
    assert TARGETS["hard"].config().max_nodes is None


def test_tier_config_is_frozen_and_does_not_touch_global_configs() -> None:
    from xionghan_chess.core.ai import CONFIGS, Difficulty

    before = dict(CONFIGS)
    config = TARGETS["hard"].config()
    assert config.depth == 3
    assert CONFIGS == before
    assert CONFIGS[Difficulty.HARD].depth == config.depth == 3
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
