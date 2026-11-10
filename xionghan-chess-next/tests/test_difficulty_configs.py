"""三档契约（2026-11 并档后）。

对外只有 `beginner / medium / hard`；`easy / expert / master` 三个枚举成员保留，
只为旧配置/旧存档能载入，其 `CONFIGS` 条目是**同一对象别名**——不是复制数值。

B′ 档位表：depth 写成真能达到的 1/2/3，缩根宽/分支让深度装进 cap（2/5/12s）。
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.ai import (
    CONFIGS,
    EXPECTED_MOVE_SECONDS,
    LEGACY_DIFFICULTY_ALIASES,
    PREFIX_MAX,
    PUBLIC_DIFFICULTIES,
    WATCHDOG_SECONDS,
    ChessAI,
    Difficulty,
    normalize_difficulty,
)


def test_three_public_tiers_keep_the_current_values() -> None:
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
    ) == (1, 2.0, 0.55, 1, 4, 6, 14, 150)

    medium = CONFIGS[Difficulty.MEDIUM]
    assert (
        medium.depth,
        medium.time_limit,
        medium.randomness,
        medium.quiescence_depth,
        medium.candidate_count,
        medium.branch_limit,
        medium.root_limit,
    ) == (2, 5.0, 0.0, 2, 1, 3, 5)

    hard = CONFIGS[Difficulty.HARD]
    assert (hard.depth, hard.time_limit, hard.randomness, hard.branch_limit, hard.root_limit) == (3, 12.0, 0.0, 8, 10)


def test_legacy_enum_configs_are_the_same_objects_not_copies() -> None:
    """`is` 断言防复制：复制数值会立刻制造两份真相。"""
    assert CONFIGS[Difficulty.EASY] is CONFIGS[Difficulty.BEGINNER]
    assert CONFIGS[Difficulty.EXPERT] is CONFIGS[Difficulty.HARD]
    assert CONFIGS[Difficulty.MASTER] is CONFIGS[Difficulty.HARD]


def test_public_difficulties_is_the_single_source() -> None:
    assert PUBLIC_DIFFICULTIES == (Difficulty.BEGINNER, Difficulty.MEDIUM, Difficulty.HARD)


def test_legacy_aliases_map_into_three_tiers() -> None:
    assert LEGACY_DIFFICULTY_ALIASES == {
        "beginner": "beginner",
        "easy": "beginner",
        "medium": "medium",
        "hard": "hard",
        "expert": "hard",
        "master": "hard",
    }
    assert normalize_difficulty("EASY") == "beginner"
    assert normalize_difficulty("  Expert ") == "hard"
    assert normalize_difficulty("master") == "hard"
    assert normalize_difficulty("unknown") == "unknown"

    assert ChessAI("easy").difficulty is Difficulty.BEGINNER
    assert ChessAI("expert").difficulty is Difficulty.HARD
    assert ChessAI("master").difficulty is Difficulty.HARD
    # 显式枚举仍保留（研究/基准路径），字符串才是产品入口。
    assert ChessAI(Difficulty.MASTER).difficulty is Difficulty.MASTER


def test_unknown_difficulty_still_raises() -> None:
    with pytest.raises(ValueError):
        ChessAI("legendary")


def test_expected_and_watchdog_seconds_cover_public_tiers_and_aliases() -> None:
    assert EXPECTED_MOVE_SECONDS[Difficulty.BEGINNER] == 0.7
    assert EXPECTED_MOVE_SECONDS[Difficulty.MEDIUM] == 3.0
    assert EXPECTED_MOVE_SECONDS[Difficulty.HARD] == 7.0
    for difficulty in Difficulty:
        assert WATCHDOG_SECONDS[difficulty] == round(PREFIX_MAX + CONFIGS[difficulty].time_limit * 1.15, 3)
        assert WATCHDOG_SECONDS[difficulty] > CONFIGS[difficulty].time_limit


def test_watchdog_includes_the_uninterruptible_prefix() -> None:
    """看门狗 = 前缀 0.78 + cap×1.15；cap 2.0 时必须留到 3.08s（p95≈2.5s 是合法手）。

    B′ 后 beginner cap 已是 2.0；medium/hard 为 5.0/12.0。
    """
    assert WATCHDOG_SECONDS[Difficulty.BEGINNER] == pytest.approx(PREFIX_MAX + 2.0 * 1.15)
    assert PREFIX_MAX + 2.0 * 1.15 > 2.5, "cap 2.0 的 p95 合法手不能被看门狗误杀"
    assert WATCHDOG_SECONDS[Difficulty.MEDIUM] == pytest.approx(PREFIX_MAX + 5.0 * 1.15)
    assert WATCHDOG_SECONDS[Difficulty.HARD] == pytest.approx(PREFIX_MAX + 12.0 * 1.15)
