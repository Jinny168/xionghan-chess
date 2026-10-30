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
def test_behavior_lock_pawn_crossed_at_row6() -> None:
    """当前行为：红兵站在长城行 row=6 即可**横走**（(6,3) -> (6,4) 合法）。

    文档：`PIECE_RULES.md:52`「**过**长城阴山后可以横走一格」—— 行 6 是长城行本身。
    疑点：`rules.py:610` 用 `crossed = row <= middle(6)`，而
          `rules.py:615-618`（快速行军，row9 -> 最远落行 5）与
          `rules.py:557`（相/象，`target.row < 6`）都把**敌境首行定为 5**。
          → 三处里两处一个口径、一处另一个，即使不看文档代码也不自洽。
    """
    rules = _rules()
    state = _state(_piece(PieceType.PAWN, Color.RED, 6, 3), *_kings_off_column())

    targets = {(m.target.row, m.target.col) for m in _moves_from(state, Position(6, 3))}
    assert (6, 4) in targets, "行 6 的横走若被修掉，本用例应同步改为断言非法"
    assert (6, 2) in targets
    assert (5, 3) in targets  # 前进一格仍正常


def test_behavior_lock_pawn_horizontal_from_row5() -> None:
    """对照组：行 5（敌境首行）横走合法 —— 说明上面那条的差异只发生在行 6。

    文档与另两处口径都认为行 5 起算敌境，这条**不是**偏差，是基准。
    """
    state = _state(_piece(PieceType.PAWN, Color.RED, 5, 3), *_kings_off_column())
    targets = {(m.target.row, m.target.col) for m in _moves_from(state, Position(5, 3))}
    assert (5, 4) in targets


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
def test_behavior_lock_kings_facing_detects_column_only() -> None:
    """当前行为：两王**同一行**且中间无子时 `in_check` 返回 False（同行照面合法）。

    文档：`PIECE_RULES.md:12`「两个汉/汗不能在**同一直线**无遮挡地照面」—— 直线含横向。
    疑点：`rules.py:784-787` 的 `_kings_facing` 只比较 `col`，同行不判。
    """
    rules = _rules()

    same_row = _state(_piece(PieceType.KING, Color.RED, 6, 2),
                      _piece(PieceType.KING, Color.BLACK, 6, 9))
    same_col = _state(_piece(PieceType.KING, Color.RED, 2, 6),
                      _piece(PieceType.KING, Color.BLACK, 9, 6))

    assert rules.in_check(same_row, Color.RED) is False, "同行照面若开始被算作被将，本用例应删除"
    assert rules.in_check(same_col, Color.RED) is True, "同列照面必须仍算被将"


# ---------------------------------------------------------------------------
# ④ 锁「矛盾」本身（不是锁行为）
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason="敌境起始行三处口径不一致：crossed 用 row<=6，快速行军/相用 row<6（首行 5）。"
           "规则定口径后本用例应通过 —— 届时 strict 会让它报错，提醒删除本标记。",
)
def test_enemy_territory_definition_is_consistent() -> None:
    """断言三处「敌人境」判定给出同一个起始行。

    当前会失败（6 vs 5 vs 5）→ 用 `xfail(strict=True)` 标成"已知矛盾"：
      - 矛盾仍在：本用例 xfail（不算失败，但报告里可见）；
      - 矛盾被修好：strict 模式让它**报错**，强制有人回来删标记，不会静默变成"还行"。

    三处口径（均为红方，13 行、middle=6）：
      * `rules.py:610`  `crossed = row <= middle`            → 过界首行 6
      * `rules.py:615`  `distance_to_enemy_territory = row - middle + 1` → 最远落行 5
      * `rules.py:557`  `if target.row < middle: 禁止`        → 敌境为 0..5，首行 5
    """
    boundaries = {
        "crossed (rules.py:610)": MIDDLE_ROW,
        "fast_move (rules.py:615-618)": MIDDLE_ROW - 1,
        "elephant (rules.py:557)": MIDDLE_ROW - 1,
    }
    assert len(set(boundaries.values())) == 1, (
        "三处「敌境起始行」必须一致，当前为：" + repr(boundaries)
    )
