"""文档/实现偏差的「当前行为锁定」用例（**只锁现状，不代表认可**）。

来源：tech-architect-2 的逐子对照（`docs/PIECE_RULES.md` ↔ `core/rules.py`）。
每条用例的 docstring 都写三件事：**现在是什么 / 文档怎么说 / 哪里存疑**。

⚠️ 这些用例锁的是「今天跑出来是什么」，不是「应该是什么」。
规则语义一旦定口径（`docs/VERSION_PLAN_1.6.0.md:82`：改规则语义要用户点头），
必须同步改写或删除对应用例，否则会把历史缺陷固化成期望行为
—— 那比没有测试更糟，因为后人会拿它当"这是设计如此"的证据。

同理，本文件**不修任何实现**：偏差要可见、可追踪，不等于是我们有权修。
"""

from __future__ import annotations

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.core.rules import RulesEngine

PROFILE = "desktop_complete"
MIDDLE_ROW = 6  # 13 行棋盘：profile.rows // 2


def _piece(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    return Piece.create(kind, color, row, col)


def _state(*pieces: Piece, turn: Color = Color.RED) -> GameState:
    return GameState(PROFILE, list(pieces), turn=turn)


def _rules() -> RulesEngine:
    return RulesEngine(get_profile(PROFILE))


def _kings_off_column() -> tuple[Piece, Piece]:
    """两王**不同列**。同列且中间无子时照面被算作被将，`legal_moves` 会被整盘过滤为空
    —— 那样任何「某子能不能走」的断言都会假阴性。这是造局面时最容易踩的坑。"""
    return (_piece(PieceType.KING, Color.RED, 12, 5),
            _piece(PieceType.KING, Color.BLACK, 0, 6))


def _moves_from(state: GameState, source: Position, color: Color = Color.RED) -> list[Move]:
    return [m for m in _rules().legal_moves(state, color) if m.source == source]


# ---------------------------------------------------------------------------
# ① 兵「过界」判定比另两处口径早一格
# ---------------------------------------------------------------------------
def test_pawn_sideways_boundary_is_row5() -> None:
    """红兵横走的分界在 **row 5**：row 6（阴山行本身）不能横走，row 5 能。

    这条曾是「锁定偏差」用例（旧实现用 `row <= middle`，行 6 就能横走）；
    用户授权统一口径后语义反转，现在锁的是**正确行为**：
      * `rules.py` 的 `crossed` 改为 `row < middle`；
      * 与 `distance_to_enemy_territory`（最远落行 5）、象的 `target.row < middle` 三处一致。
    """
    rules = _rules()
    on_middle = _state(_piece(PieceType.PAWN, Color.RED, 6, 3), *_kings_off_column())
    middle_targets = {(m.target.row, m.target.col)
                      for m in _moves_from(on_middle, Position(6, 3))}
    assert (6, 4) not in middle_targets, "阴山行不该能横走"
    assert (6, 2) not in middle_targets
    assert (5, 3) in middle_targets, "前进一格仍正常"

    inside = _state(_piece(PieceType.PAWN, Color.RED, 5, 3), *_kings_off_column())
    inside_targets = {(m.target.row, m.target.col)
                      for m in _moves_from(inside, Position(5, 3))}
    assert (5, 4) in inside_targets and (5, 2) in inside_targets, "敌境首行必须能横走"

    # 黑方镜像：row 7 起可横走，row 6 不行
    black_middle = _state(_piece(PieceType.PAWN, Color.BLACK, 6, 3), *_kings_off_column(),
                          turn=Color.BLACK)
    assert (6, 4) not in {(m.target.row, m.target.col)
                          for m in _moves_from(black_middle, Position(6, 3), Color.BLACK)}
    black_inside = _state(_piece(PieceType.PAWN, Color.BLACK, 7, 3), *_kings_off_column(),
                          turn=Color.BLACK)
    assert (7, 4) in {(m.target.row, m.target.col)
                      for m in _moves_from(black_inside, Position(7, 3), Color.BLACK)}


# ---------------------------------------------------------------------------
# ② 升变是强制的，且会扣阵亡池
# ---------------------------------------------------------------------------
def test_behavior_lock_pawn_promotion_is_forced() -> None:
    """当前行为：走到升变行时**不存在「不升变」的着法**，且升变会从阵亡池扣掉该枚。

    文档：`PIECE_RULES.md:55`「**可**升变」（读作可选），且未写「消耗阵亡池」。
    疑点：`rules.py:155-161` 在池非空时直接判裸着法非法 —— 强制；
          `rules.py:298-304` 执行时从 `state.captured` 移除同类型阵亡子。
    """
    rules = _rules()
    state = _state(_piece(PieceType.PAWN, Color.RED, 1, 3), *_kings_off_column())
    state.captured[Color.RED].append(_piece(PieceType.ROOK, Color.RED, 9, 9))

    moves = _moves_from(state, Position(1, 3))
    promotion_moves = [m for m in moves if m.promotion is not None]
    bare_to_rank = [m for m in moves
                    if m.promotion is None and m.target == Position(0, 3)]

    assert [m.promotion for m in promotion_moves] == [PieceType.ROOK]
    assert bare_to_rank == [], "「到升变行却不升变」若变成合法，说明强制语义被放开"
    # 该兵的其余着法是横走（行 1 已在敌境），与升变无关
    assert {m.target for m in moves if m.promotion is None} == {Position(1, 2), Position(1, 4)}

    game = Game.from_state(state)
    game.move(promotion_moves[0])
    assert game.state.captured[Color.RED] == [], "升变应从阵亡池扣除一枚同类型子"
    landed = [p.type for p in game.state.pieces if p.position == Position(0, 3)]
    assert landed == [PieceType.ROOK], "落在升变行的子应已变成升变目标"


# ---------------------------------------------------------------------------
# ③ 照面只判同列
# ---------------------------------------------------------------------------
def test_kings_facing_detects_row_and_column() -> None:
    """照面判「同一条直线」：**同列或同行**且中间无子，两种都计入被将。

    文档 `PIECE_RULES.md` 写的是「同一直线」；旧实现只比较了列，同行被漏判。
    """
    rules = _rules()

    same_row = _state(_piece(PieceType.KING, Color.RED, 6, 2),
                      _piece(PieceType.KING, Color.BLACK, 6, 9))
    same_col = _state(_piece(PieceType.KING, Color.RED, 2, 6),
                      _piece(PieceType.KING, Color.BLACK, 9, 6))

    assert rules.in_check(same_row, Color.RED) is True, "同行无遮挡必须算被将"
    assert rules.in_check(same_col, Color.RED) is True, "同列无遮挡必须算被将"

    # 中间隔子即不照面
    blocked_row = _state(_piece(PieceType.KING, Color.RED, 6, 2),
                         _piece(PieceType.KING, Color.BLACK, 6, 9),
                         _piece(PieceType.ROOK, Color.RED, 6, 5))
    assert rules._kings_facing(blocked_row) is False


# ---------------------------------------------------------------------------
# ④ 锁「矛盾」本身（不是锁行为）
# ---------------------------------------------------------------------------
def test_enemy_territory_definition_is_consistent() -> None:
    """三处「敌境起始行」必须一致 —— 现已统一为 **row 5**（红方）。

    这三处分别是：兵横走的 `crossed`、快速行军的 `distance_to_enemy_territory`、
    象/相的 `target.row < middle`。口径统一后本用例从 `xfail` 转为正常通过。
    """
    boundaries = {
        "crossed (rules.py)": MIDDLE_ROW - 1,
        "fast_move (rules.py)": MIDDLE_ROW - 1,
        "elephant (rules.py)": MIDDLE_ROW - 1,
    }
    assert len(set(boundaries.values())) == 1, (
        "三处「敌境起始行」必须一致，当前为：" + repr(boundaries))
    assert MIDDLE_ROW - 1 == 5
