"""D7 漏杀判据：**走子前**枚举一步杀，漏杀 = 有杀着却走了别的（哪怕那手也能赢但更慢）。

旧实现 `_has_mate_in_one` 恒 `return False`，且调用点在 `game.move()` **之后**——判的其实是
"假设还能再走一步有没有杀"，不是"刚才漏没漏"。本组测试钉死正确口径：

- 有一步杀、走了别的 → 记 missed_mate（含"更慢也能赢"的着法，定义所然）；
- 无一步杀（只有 mate-in-2/3）、走非最短赢法 → **不记**（判据只认 mate-in-1，不判最短）；
- 优先级 hang > missed_capture > missed_mate。
"""

from __future__ import annotations

import inspect

from xionghan_chess.core.benchmark import _classify_blunder, mate_in_one_moves
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position


def _game(pieces: list[Piece], turn: Color = Color.RED) -> Game:
    return Game.from_state(GameState("traditional", pieces, turn=turn))


def _p(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    return Piece.create(kind, color, row, col)


def _mv(src_row: int, src_col: int, dst_row: int, dst_col: int) -> Move:
    return Move(Position(src_row, src_col), Position(dst_row, dst_col))


def _p1() -> list[Piece]:
    """P1：黑王(0,4)、红王(9,3)、红车(3,0)、红双马(2,2)(2,6) —— 红方有 2 个一步杀。"""
    return [
        _p(PieceType.KING, Color.BLACK, 0, 4),
        _p(PieceType.KING, Color.RED, 9, 3),
        _p(PieceType.ROOK, Color.RED, 3, 0),
        _p(PieceType.HORSE, Color.RED, 2, 2),
        _p(PieceType.HORSE, Color.RED, 2, 6),
    ]


def test_t1_mate_in_one_moves_nonempty_on_mate_position() -> None:
    """T1（防占位）：确有 mate-in-1 的局面，`mate_in_one_moves` 必须非空。

    P1 实测 2 个杀着（3,0-0,0 / 3,0-3,4），故断言 `>= 1`（不是 ==1）。
    """
    game = _game(_p1())
    mates = mate_in_one_moves(game.rules, game.state, Color.RED)
    assert len(mates) >= 1, "有一步杀的局面却枚举为空 —— 判据仍是空壳"


def test_t2_no_mate_in_one_returns_empty() -> None:
    """T2：无一步杀局面（标准开局）返回空列表。"""
    game = Game("traditional")
    assert mate_in_one_moves(game.rules, game.state, Color.RED) == []


def test_t3_mate_ignored_by_unrelated_move_recorded() -> None:
    """T3：有一步杀、走了完全无关的一手（马 2,2-3,4）→ 记 missed_mate。"""
    game = _game(_p1())
    blunder, _ = _classify_blunder(game, _mv(2, 2, 3, 4))
    assert blunder == "missed_mate"


def test_t4_mate_ignored_by_slower_win_recorded() -> None:
    """T4：有一步杀、走了另一个"也能赢但更慢"的着法（王 9,3-8,3）→ 仍记 missed_mate。"""
    game = _game(_p1())
    blunder, _ = _classify_blunder(game, _mv(9, 3, 8, 3))
    assert blunder == "missed_mate"


def test_t5_no_mate_in_one_no_missed_mate_record() -> None:
    """T5（边界）：无一步杀、只有 mate-in-2，走非最短赢法（王 9,4-9,3）→ **不记**。

    钉死"只认 mate-in-1、不判是否走最短"这一口径。
    """
    game = _game(
        [
            _p(PieceType.KING, Color.BLACK, 0, 4),
            _p(PieceType.KING, Color.RED, 9, 4),
            _p(PieceType.ROOK, Color.RED, 3, 0),
        ]
    )
    assert mate_in_one_moves(game.rules, game.state, Color.RED) == []
    blunder, _ = _classify_blunder(game, _mv(9, 4, 9, 3))
    assert blunder is None, f"无一步杀却被记漏杀：{blunder}"


def test_t6_mate_in_one_moves_is_not_placeholder() -> None:
    """T6（防占位第二道）：源码断言函数体不得只剩 `return []`/`pass`。

    D7 的根因就是"函数恒 return False 的占位"。这里要求源码里真的出现着法枚举与将死判定。
    """
    src = inspect.getsource(mate_in_one_moves)
    assert "legal_moves" in src, "mate_in_one_moves 没有枚举合法着法 —— 疑似仍是空壳"
    assert "checkmate" in src, "mate_in_one_moves 没有将死判定 —— 疑似仍是空壳"


def test_t7a_missed_capture_beats_missed_mate() -> None:
    """T7-a 优先级：P1 + 黑车(3,7)（红车可白吃）；走车 3,0-1,0 → 记 missed_capture（mc 与 mm 同时成立）。"""
    game = _game(_p1() + [_p(PieceType.ROOK, Color.BLACK, 3, 7)])
    blunder, _ = _classify_blunder(game, _mv(3, 0, 1, 0))
    assert blunder == "missed_capture", f"应记漏吃却记了 {blunder}"


def test_t7b_hang_beats_missed_mate() -> None:
    """T7-b 优先级：P1 + 黑车(2,4)（可吃红马）；走车 3,0-1,0 → 记 hang（hang 与 mm 同时成立）。"""
    game = _game(_p1() + [_p(PieceType.ROOK, Color.BLACK, 2, 4)])
    blunder, _ = _classify_blunder(game, _mv(3, 0, 1, 0))
    assert blunder == "hang", f"应记送子却记了 {blunder}"


def test_t7c_hang_dominates_all() -> None:
    """T7-c 优先级：P1 + 黑车(3,7) + 黑车(2,4) 三因同时 → 记 hang。"""
    game = _game(_p1() + [_p(PieceType.ROOK, Color.BLACK, 3, 7), _p(PieceType.ROOK, Color.BLACK, 2, 4)])
    blunder, _ = _classify_blunder(game, _mv(3, 0, 1, 0))
    assert blunder == "hang", f"应记送子却记了 {blunder}"
