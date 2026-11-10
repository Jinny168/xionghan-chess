"""2.0.0 六档配置与档位兼容层（合并后口径）。

master 线（1.7.x）曾把对外压成三档，并把 `easy/expert/master` 归一到 `medium/hard`。
**2.0.0 不采用**：这六档是六个独立档位（深度/预算/取样参数不同，master 还走 MCTS）。
这里钉住的是：合并后仍是六档，兼容层只做大小写归一、绝不并档。
"""

from __future__ import annotations

from xionghan_chess.core.ai import (
    CONFIGS,
    EXPECTED_MOVE_SECONDS,
    LEGACY_DIFFICULTY_ALIASES,
    WATCHDOG_SECONDS,
    ChessAI,
    Difficulty,
    normalize_difficulty,
)


def test_six_tiers_keep_the_2_0_values() -> None:
    beginner = CONFIGS[Difficulty.BEGINNER]
    assert (
        beginner.depth,
        beginner.time_limit,
        beginner.randomness,
        beginner.quiescence_depth,
        beginner.candidate_count,
        beginner.branch_limit,
        beginner.root_limit,
        beginner.sample_margin,
    ) == (2, 0.5, 0.55, 1, 4, 3, 5, 150)

    medium = CONFIGS[Difficulty.MEDIUM]
    assert (
        medium.depth,
        medium.time_limit,
        medium.randomness,
        medium.quiescence_depth,
        medium.candidate_count,
        medium.branch_limit,
        medium.root_limit,
    ) == (6, 5.0, 0.05, 4, 3, 10, 18)

    hard = CONFIGS[Difficulty.HARD]
    assert (hard.depth, hard.time_limit, hard.randomness) == (8, 12.0, 0.0)

    # 这四档是 2.0.0 独立档位，不能被合并掉。
    assert CONFIGS[Difficulty.EASY].time_limit == 1.5
    assert CONFIGS[Difficulty.EXPERT].time_limit == 35.0
    assert CONFIGS[Difficulty.MASTER].time_limit == 12.0
    assert CONFIGS[Difficulty.MASTER].root_limit == 32


def test_aliases_are_identity_not_three_tier_collapse() -> None:
    assert LEGACY_DIFFICULTY_ALIASES == {
        "beginner": "beginner",
        "easy": "easy",
        "medium": "medium",
        "hard": "hard",
        "expert": "expert",
        "master": "master",
    }
    assert normalize_difficulty("EASY") == "easy"
    assert normalize_difficulty("  Expert ") == "expert"
    assert normalize_difficulty("master") == "master"
    assert normalize_difficulty("unknown") == "unknown"

    assert ChessAI("easy").difficulty is Difficulty.EASY
    assert ChessAI("expert").difficulty is Difficulty.EXPERT
    assert ChessAI("master").difficulty is Difficulty.MASTER
    assert ChessAI(Difficulty.MASTER).difficulty is Difficulty.MASTER


def test_expected_and_watchdog_seconds_cover_all_six_tiers() -> None:
    # 2.0.0 的读条分母就是 cap（原行为）；看门狗 cap×1.15。
    for difficulty in Difficulty:
        assert EXPECTED_MOVE_SECONDS[difficulty] == CONFIGS[difficulty].time_limit
        assert WATCHDOG_SECONDS[difficulty] == round(CONFIGS[difficulty].time_limit * 1.15, 3)
        assert WATCHDOG_SECONDS[difficulty] > CONFIGS[difficulty].time_limit
