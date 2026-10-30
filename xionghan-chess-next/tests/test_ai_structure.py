"""结构项（开放线 / 车炮同线）必须**零和**、**按枚计价**、且**堵住就不算**。

## 三条容易写错的

1. **零和**：结构项若只给一方加、不给另一方减，`_evaluate(红) + _evaluate(黑)` 就不为 0，
   等于凭空给先手送分 —— 这类错误在选点上看不出来，只会让整体评分缓慢漂移。
2. **按枚计价**：两枚车都在开放列要加两次；写成"每方只加一次"会让第二枚车白站。
3. **堵住不算**：车炮之间有子就不是"同线"，那时候加分会把"堵死"读成"通畅"。

这里全部用**构造局面**直接验，不依赖搜索，因此不受时间/noise 影响。
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bench_roots import build_position  # noqa: E402

from xionghan_chess.core.ai import (  # noqa: E402
    BATTERY_W,
    OPEN_FILE_CANNON_W,
    OPEN_FILE_ROOK_W,
    ChessAI,
    Difficulty,
)
from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, Piece, PieceType  # noqa: E402

PROFILE = "desktop_complete"
AI = ChessAI(Difficulty.MEDIUM, seed=1)


def board(*pieces: tuple[PieceType, Color, int, int]) -> Game:
    """构造一个只含指丁子的局面（两个王总在，免得 `in_check` 走空王分支）。"""
    game = Game(PROFILE)
    game.state.pieces = [
        Piece.create(PieceType.KING, Color.RED, 12, 6),
        Piece.create(PieceType.KING, Color.BLACK, 0, 6),
        *(Piece.create(kind, color, row, col) for kind, color, row, col in pieces),
    ]
    game.state.turn = Color.RED
    return game


def structure(game: Game, color: Color) -> float:
    own, _enemy = AI._pawn_columns(game, color)
    return AI._structure_score(game, color, own)


# ---------------------------------------------------------------------------
# 1) 零和
# ---------------------------------------------------------------------------
def test_evaluation_is_zero_sum_over_real_positions() -> None:
    game, _played = build_position(PROFILE, 703, 50)
    rules = Game(PROFILE).rules
    states, state = [], Game(PROFILE).state
    states.append(state)
    for record in game.state.history:
        state = rules.apply_unchecked(state, record.move)
        states.append(state)

    for index, snapshot in enumerate(states[:50]):
        position = Game.from_state(snapshot, None, None)
        total = AI._evaluate(position, Color.RED) + AI._evaluate(position, Color.BLACK)
        assert abs(total) < 1e-6, f"第 {index} 个局面红+黑 = {total}"


# ---------------------------------------------------------------------------
# 2) 开放线：按枚计价，兵移进该列就不再算
# ---------------------------------------------------------------------------
def test_open_file_rook_counts_once_per_rook() -> None:
    two_rooks = board((PieceType.ROOK, Color.RED, 11, 0), (PieceType.ROOK, Color.RED, 12, 0))
    assert structure(two_rooks, Color.RED) == 2 * OPEN_FILE_ROOK_W


def test_open_file_rook_disappears_when_own_pawn_enters_the_column() -> None:
    open_file = board((PieceType.ROOK, Color.RED, 12, 0), (PieceType.PAWN, Color.RED, 10, 2))
    closed = board((PieceType.ROOK, Color.RED, 12, 0), (PieceType.PAWN, Color.RED, 10, 0))
    assert structure(open_file, Color.RED) - structure(closed, Color.RED) == OPEN_FILE_ROOK_W


def test_open_file_cannon_uses_its_own_weight() -> None:
    cannon = board((PieceType.CANNON, Color.RED, 9, 0))
    assert structure(cannon, Color.RED) == OPEN_FILE_CANNON_W


# ---------------------------------------------------------------------------
# 3) 车炮同线：中间无子才算，堵住不算
# ---------------------------------------------------------------------------
def test_battery_counts_when_the_line_is_clear() -> None:
    clear = board((PieceType.ROOK, Color.RED, 12, 0), (PieceType.CANNON, Color.RED, 8, 0))
    # 开放线部分：车 + 炮各一次
    expected_open = OPEN_FILE_ROOK_W + OPEN_FILE_CANNON_W
    assert structure(clear, Color.RED) == expected_open + BATTERY_W


def test_battery_does_not_count_when_blocked() -> None:
    clear = board((PieceType.ROOK, Color.RED, 12, 0), (PieceType.CANNON, Color.RED, 8, 0))
    blocked = board((PieceType.ROOK, Color.RED, 12, 0), (PieceType.CANNON, Color.RED, 8, 0),
                    (PieceType.PAWN, Color.RED, 10, 0))
    # 兵塞在中间：电池不成立；同时它落在 0 列 → **车和炮**的开放线也一起没了（两枚都要扣）
    assert structure(clear, Color.RED) - structure(blocked, Color.RED) == (
        BATTERY_W + OPEN_FILE_ROOK_W + OPEN_FILE_CANNON_W)


def test_battery_counts_horizontal_and_vertical_once_each() -> None:
    horizontal = board((PieceType.ROOK, Color.RED, 9, 0), (PieceType.CANNON, Color.RED, 9, 5))
    # 9 列无己方兵：车加一次；炮在 5 列无己方兵：加一次；同排中间无子：电池一次
    assert structure(horizontal, Color.RED) == OPEN_FILE_ROOK_W + OPEN_FILE_CANNON_W + BATTERY_W
