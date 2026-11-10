"""标定表必须与发布三档逐字段一致（防止改 CONFIGS 忘改标定）。

`PRODUCT_TIERS` 是从 `core.ai.CONFIGS` **派生**的只读视图；这条测试把派生结果
再钉回 CONFIGS，任何人只改一边都会红。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from level_targets import PRODUCT_TIERS  # noqa: E402

from xionghan_chess.core.ai import CONFIGS, PUBLIC_DIFFICULTIES  # noqa: E402


def test_product_tiers_keys_are_exactly_the_public_difficulties() -> None:
    assert tuple(PRODUCT_TIERS) == tuple(value.value for value in PUBLIC_DIFFICULTIES)


def test_every_field_matches_the_current_config() -> None:
    for difficulty in PUBLIC_DIFFICULTIES:
        tier = PRODUCT_TIERS[difficulty.value]
        config = CONFIGS[difficulty]
        assert tier.depth == config.depth
        assert tier.cap == config.time_limit
        assert tier.randomness == config.randomness
        assert tier.quiescence_depth == config.quiescence_depth
        assert tier.candidate_count == config.candidate_count
        assert tier.branch_limit == config.branch_limit
        assert tier.root_limit == config.root_limit
        assert tier.max_nodes == config.max_nodes
