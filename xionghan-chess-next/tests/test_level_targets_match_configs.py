"""脚本目标表 ↔ 产品 `CONFIGS` 的一致性（T6）。

`scripts/level_targets.py` 是标定/测量的输入，`core.ai.CONFIGS` 是产品行为。
两者一旦分叉，测出来的胜率与玩家实际对局就不是同一档——所以逐字段断言。

（`max_nodes` 目前两侧都是 `None`；将来回填时必须同步改这里与 CONFIGS。）
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from level_targets import TARGETS  # noqa: E402

from xionghan_chess.core.ai import CONFIGS, Difficulty  # noqa: E402


def test_each_tier_config_equals_the_product_config() -> None:
    assert set(TARGETS) == {"beginner", "medium", "hard"}
    for key, tier in TARGETS.items():
        assert tier.config() == CONFIGS[Difficulty(key)], (
            f"{key}：level_targets 与 CONFIGS 分叉 —— "
            f"{tier.config()} vs {CONFIGS[Difficulty(key)]}")


def test_candidate_count_is_no_longer_hard_coded() -> None:
    """`Tier.config()` 曾经把 candidate_count 写死为 1，入门的 3 从未生效。"""
    assert TARGETS["beginner"].candidate_count == 3
    assert TARGETS["beginner"].config().candidate_count == 3
    assert TARGETS["medium"].config().candidate_count == 1
    assert TARGETS["hard"].config().candidate_count == 1
