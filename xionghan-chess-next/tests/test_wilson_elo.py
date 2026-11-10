"""Wilson 95% 与 Elo 映射：小样本判据的唯一实现。

判据（S4-2a 定稿）：`点估计 ≥0.60 且 Wilson 下界 ≥0.50`。
这两条都读同一份闭式结果，所以先把数值钉死（技术侧已实算）：

    32/50 → (0.5014, 0.7586)   Elo +100.0
    21/32 → (0.4831, 0.7959)   Elo +112.3
    22/32 → (0.5143, 0.8205)   Elo +137.0
     0/50 → (0.0000, 0.0714)   Elo None（不是 inf）
    50/50 → (0.9286, 1.0000)   Elo None
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.benchmark import elo_from_win_rate, wilson_interval

CASES = [
    (32, 50, 0.5014, 0.7586, 100.0),
    (31, 50, 0.4815, 0.7414, 85.0),
    (21, 32, 0.4831, 0.7959, 112.3),
    (22, 32, 0.5143, 0.8205, 137.0),
    (60, 100, 0.5020, 0.6906, 70.4),
    (35, 50, 0.5625, 0.8090, 147.2),
]


@pytest.mark.parametrize("wins,games,low,high,elo", CASES)
def test_wilson_and_elo_match_the_pinned_values(wins: int, games: int, low: float, high: float, elo: float) -> None:
    actual_low, actual_high = wilson_interval(wins, games)
    assert actual_low == pytest.approx(low, abs=5e-4)
    assert actual_high == pytest.approx(high, abs=5e-4)
    assert elo_from_win_rate(wins / games) == pytest.approx(elo, abs=0.1)


def test_boundaries_do_not_produce_negative_or_infinite_values() -> None:
    low, high = wilson_interval(0, 50)
    assert low == 0.0
    assert high == pytest.approx(0.0714, abs=5e-4)
    assert elo_from_win_rate(0.0) is None

    low, high = wilson_interval(50, 50)
    assert low == pytest.approx(0.9286, abs=5e-4)
    assert high == 1.0
    assert elo_from_win_rate(1.0) is None

    assert wilson_interval(0, 0) == (0.0, 0.0)


def test_invalid_win_counts_are_rejected() -> None:
    with pytest.raises(ValueError):
        wilson_interval(51, 50)
    with pytest.raises(ValueError):
        wilson_interval(-1, 50)


def test_calibration_gate_matches_the_stated_thresholds() -> None:
    """n=32 门槛 22 胜、n=64 门槛 40 胜；21/32 与 39/64 必须不过。"""
    for wins, games in ((22, 32), (40, 64)):
        low, _high = wilson_interval(wins, games)
        assert wins / games >= 0.60 and low >= 0.50, (wins, games, low)
    for wins, games in ((21, 32), (39, 64)):
        low, _high = wilson_interval(wins, games)
        assert wins / games < 0.60 or low < 0.50, (wins, games, low)
