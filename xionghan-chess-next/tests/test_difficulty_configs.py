"""S4-2b 三档配置与别名归一。

对外只保留 **beginner / medium / hard** 三档；`easy / expert / master` 的枚举与
`CONFIGS` 条目保留（内部/题库/旧存档仍在用），但字符串别名统一归到三档：

    easy → medium、expert → hard、master → hard

`ChessAI` 只在收到**字符串**时归一；显式传 `Difficulty.MASTER` 仍走 MCTS
（内部调用不能被别名吃掉）。
"""

from __future__ import annotations

from xionghan_chess.core.ai import (
    CONFIGS,
    EXPECTED_MOVE_SECONDS,
    LEGACY_DIFFICULTY_ALIASES,
    RANDOM_PICK_WINDOW,
    WATCHDOG_SECONDS,
    ChessAI,
    Difficulty,
    normalize_difficulty,
)
from xionghan_chess.core.game import Game


def test_three_public_tiers_have_the_final_numbers() -> None:
    beginner = CONFIGS[Difficulty.BEGINNER]
    assert (beginner.depth, beginner.time_limit, beginner.randomness,
            beginner.quiescence_depth, beginner.candidate_count,
            beginner.branch_limit, beginner.root_limit,
            beginner.max_nodes) == (1, 3.0, 0.30, 1, 3, 6, 10, None)

    medium = CONFIGS[Difficulty.MEDIUM]
    assert (medium.depth, medium.time_limit, medium.randomness,
            medium.quiescence_depth, medium.candidate_count,
            medium.branch_limit, medium.root_limit,
            medium.max_nodes) == (2, 30.0, 0.0, 4, 1, 10, 18, None)

    hard = CONFIGS[Difficulty.HARD]
    assert (hard.depth, hard.time_limit, hard.randomness,
            hard.quiescence_depth, hard.candidate_count,
            hard.branch_limit, hard.root_limit,
            hard.max_nodes) == (3, 120.0, 0.0, 6, 1, 18, 18, None)


def test_internal_tiers_are_untouched() -> None:
    assert CONFIGS[Difficulty.EASY].time_limit == 1.5
    assert CONFIGS[Difficulty.EXPERT].time_limit == 35.0
    assert CONFIGS[Difficulty.MASTER].time_limit == 12.0
    assert CONFIGS[Difficulty.MASTER].root_limit == 32


def test_legacy_aliases_and_unknown_values() -> None:
    assert LEGACY_DIFFICULTY_ALIASES == {
        "easy": "medium", "expert": "hard", "master": "hard"}
    assert normalize_difficulty("easy") == "medium"
    assert normalize_difficulty("expert") == "hard"
    assert normalize_difficulty("master") == "hard"
    assert normalize_difficulty("hard") == "hard"
    assert normalize_difficulty("unknown") == "unknown"

    assert ChessAI("easy").difficulty is Difficulty.MEDIUM
    assert ChessAI("expert").difficulty is Difficulty.HARD
    assert ChessAI("master").difficulty is Difficulty.HARD
    # 显式枚举必须保留：MASTER 还靠它分发 MCTS。
    assert ChessAI(Difficulty.MASTER).difficulty is Difficulty.MASTER


def test_expected_and_watchdog_seconds() -> None:
    assert EXPECTED_MOVE_SECONDS == {
        Difficulty.BEGINNER: 0.35,
        Difficulty.MEDIUM: 4.2,
        Difficulty.HARD: 15.5,
    }
    assert WATCHDOG_SECONDS == {
        Difficulty.BEGINNER: 3.45,
        Difficulty.MEDIUM: 34.5,
        Difficulty.HARD: 138.0,
    }
    for difficulty in (Difficulty.BEGINNER, Difficulty.MEDIUM, Difficulty.HARD):
        assert WATCHDOG_SECONDS[difficulty] > CONFIGS[difficulty].time_limit
        assert EXPECTED_MOVE_SECONDS[difficulty] < CONFIGS[difficulty].time_limit


def test_beginner_randomness_actually_varies_the_move() -> None:
    """`RANDOM_PICK_WINDOW=300` 的价值锚点：20 个 seed 至少 3 种走法。

    旧窗口 90 + candidate_count 5 时，近优候选太少，实测几乎总选同一手
    （"入门会漏攻击"根本发生不了）。
    """
    assert RANDOM_PICK_WINDOW == 300
    moves = set()
    for seed in range(20):
        move = ChessAI(Difficulty.BEGINNER, seed=seed).choose_move(Game("traditional"))
        assert move is not None
        moves.add(move.key())
    assert len(moves) >= 3, f"20 个 seed 只有 {len(moves)} 种走法：{sorted(moves)}"
