"""D4 入门档单层软取样：开关、强档零触发与配置快照门禁。

口径（docs/AI_TIERS.md §15）：
- 取样只在 beginner 且 `sample_enabled=True` 时生效；medium/hard 走原路径，
  `CONFIGS` 字段级零 diff、不重标定；
- 开关关闭时与「未引入取样」的路径等价；
- 取样是纯决策层行为，不写 `MoveRecord` / 存档 / PGN（本测试不触及这些结构）。
"""

from __future__ import annotations

import copy

from xionghan_chess.core.ai import CONFIGS, ChessAI, Difficulty
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Move


def _rig(ai: ChessAI, scores: list[float], moves: list[Move]) -> None:
    ai.root_scores = [(score, move, False) for score, move in zip(scores, moves)]
    ai.completed_depth = 2


def test_sample_enabled_defaults_on() -> None:
    """默认行为必须被钉住：软取样开关默认打开。"""
    assert ChessAI(Difficulty.BEGINNER).sample_enabled is True


def test_sample_disabled_returns_none_everywhere() -> None:
    """开关关闭时，任何可取样局面下 `_sample_weaker` 都必须返回 None。"""
    game = Game("web")
    moves = game.rules.legal_moves(game.state, game.state.turn)
    ai = ChessAI(Difficulty.BEGINNER, seed=20261118, sample_enabled=False)
    _rig(ai, [0, -10, -20, -30], moves)

    for _ in range(50):
        assert ai._sample_weaker(game, CONFIGS[ai.difficulty]) is None


def test_sample_disabled_matches_no_sampling_path() -> None:
    """关闭开关后，选点必须等价于无取样路径（只返回搜索最佳着）。"""
    game = Game("web")
    off = ChessAI(Difficulty.BEGINNER, seed=7, sample_enabled=False)
    moves = game.rules.legal_moves(game.state, game.state.turn)
    _rig(off, [0, -10, -20], moves)

    # 关闭时不得从候选池挑任何非最佳着；`choose_move` 仍须给出合法着。
    assert off._sample_weaker(game, CONFIGS[off.difficulty]) is None
    move = off.choose_move(game)
    assert move is not None


def test_medium_hard_never_sample_even_with_ranked_root_scores() -> None:
    """medium/hard 即使摆好可取样的根着法分数，取样层也永不触发。"""
    for level in (Difficulty.MEDIUM, Difficulty.HARD):
        game = Game("web")
        moves = game.rules.legal_moves(game.state, game.state.turn)
        ai = ChessAI(level, seed=1)
        _rig(ai, [0, -10, -20], moves)
        assert ai._sample_weaker(game, CONFIGS[ai.difficulty]) is None, f"{level} 触发了取样"


def test_medium_hard_configs_field_level_zero_diff() -> None:
    """构造实例并走完一手后，medium/hard 的 `CONFIGS` 逐字段零变化。"""
    before = copy.deepcopy(CONFIGS)
    for level in (Difficulty.MEDIUM, Difficulty.HARD):
        engine = ChessAI(level, seed=3)
        engine.choose_move(Game("web"))

    for level in (Difficulty.MEDIUM, Difficulty.HARD):
        after = CONFIGS[level]
        baseline = before[level]
        for field in after.__dataclass_fields__:
            assert getattr(after, field) == getattr(baseline, field), f"{level}.{field} 被改动"
