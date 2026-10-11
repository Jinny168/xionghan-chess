"""P0-F：AI 的「升变池」可见性 —— 修法（方案 C）落地后的契约。

分工（这是本文件反复对照的两层）：

- **候选生成层读池**：`ai.py` `_tactical_moves` 用 `state.captured[moving.color]`
  决定升变候选类型；规则层 `rules.py:96-104` 也要求升变目标 ∈ 池。
- **静态估值层**：`_evaluate` **不直接读池** —— 它的直接方法体与全部下游 helper
  （`_game_phase`／`_mobility_score`／`_activity_score`／`_king_cover`／`_is_developed`／
  `_king_safety`）均无 `captured` 引用。唯一潜在的间接路径是
  `_activity_score → rules.pseudo_legal` 的两条窄分支（`rules.py:98` 带 `promotion` 时；
  `rules.py:100-106` 兵到末排不带 promotion 且池非空时），当前候选/评估路径下不影响
  静态估值。本方案改为**显式**计入池价值（`_pool_value`），把那条隐式路径从"可能"变
  成"明确"。

为什么不把池塞进 `RulesEngine.position_key`（方案 C 的核心决定）：

- `rules.py:286-288` 的 `position_key` 同时喂养**三次重复判和**
  （`game.py:238-240` → `state.position_counts`），且被离线端**逐字镜像**
  （`offline.js:84` `positionKey` → `offline.js:90` `recordPosition`）。
- 把池纳入判和键 = **规则语义变更**（"池不同但盘面相同"不再算同一局面），需产品拍板并
  三端同步，**不在本方案内** → 见 `test_position_key_ignores_capture_pool_guardrail`。
- 但 AI 缓存若继续复用判和键，就会把池不同的两个局面算作同一局面而串用缓存
  （P0-D/P0-E）。故 AI 侧改用池感知的 `evaluation_key`：`rules.py`／`game.py`／
  `offline.js` 各 0 行改动。
"""

from __future__ import annotations

import math
import time

import pytest

from xionghan_chess.core.ai import ChessAI, VALUES, evaluation_key, pool_signature
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position


def _piece(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    return Piece.create(kind, color, row, col)


def _board() -> list[Piece]:
    """两个变体共用的盘面：除 `captured` 池外完全相同的棋子布局。

    - 红兵在 (1,4)，再进一步到 (0,4) 即触底升变（红方朝 row 0 推进）；
    - 双方王都在 row 12 但**不同列**，避开「照面」与将军噪音，
      保证两个变体的 `in_check`、`_king_safety` 等输入一致。
    """
    return [
        _piece(PieceType.KING, Color.RED, 12, 6),
        _piece(PieceType.KING, Color.BLACK, 12, 0),
        _piece(PieceType.PAWN, Color.RED, 1, 4),
    ]


def _board_with_full_pawn_rank() -> list[Piece]:
    """红方场上已有 7 枚兵 —— `game.py:169` 的复活上限已满。"""
    return _board() + [_piece(PieceType.PAWN, Color.RED, 2, col) for col in (0, 2, 4, 6, 8, 10)]


def _see_board() -> list[Piece]:
    """给 SEE 用的小盘面：红车 (6,4) 可以合法吃掉黑兵 (6,6)。"""
    return [
        _piece(PieceType.KING, Color.RED, 12, 6),
        _piece(PieceType.KING, Color.BLACK, 12, 0),
        _piece(PieceType.ROOK, Color.RED, 6, 4),
        _piece(PieceType.PAWN, Color.BLACK, 6, 6),
    ]


def _game_with_pool(captured_red: list[Piece], *, board: list[Piece] | None = None,
                    options: dict | None = None) -> Game:
    """盘面相同、仅红方「死子池」不同的局面。

    `state.captured[color]` 的语义是**该方的死子**（`game.py:70` 按被吃子自身颜色入池，
    `rules.py:98` 升变时按升变方颜色读池），所以这里放红方的死子表示「红方已损失这些子，
    因而可以把触底的兵升变成它们」。
    """
    return Game.from_state(GameState(
        "desktop_complete", board if board is not None else _board(), turn=Color.RED,
        captured={Color.RED: list(captured_red), Color.BLACK: []},
    ), options)


def _stocked_pool() -> list[Piece]:
    return [
        _piece(PieceType.ROOK, Color.RED, 0, 0),
        _piece(PieceType.HORSE, Color.RED, 0, 1),
    ]


def _mirror(piece: Piece, rows: int) -> Piece:
    return Piece.create(piece.type, piece.color.opponent, rows - 1 - piece.position.row,
                        piece.position.col)


def _promotion_types(game: Game) -> set[PieceType]:
    """候选生成层为 `game` 产出的升变类型集合（直接调 `ai.py` 的 `_tactical_moves`）。"""
    moves = ChessAI()._tactical_moves(game, time.monotonic() + 10, None)
    return {move.promotion for move in moves if move.promotion is not None}


def _expected_pool_value(pool: list[Piece], color: Color, game: Game) -> float:
    """按规则重构的池价值期望（与 `_pool_value` 同一口径，独立写一遍防止自证）。"""
    enabled = game.rules.enabled_piece_types
    total = 0.0
    if game.options.pawn_promotion:
        total += sum(VALUES[piece.type] for piece in pool
                     if piece.type not in {PieceType.PAWN, PieceType.KING}
                     and piece.type in enabled)
    if game.options.pawn_resurrection:
        dead = sum(1 for piece in pool if piece.type is PieceType.PAWN)
        fielded = sum(1 for piece in game.state.pieces
                      if piece.type is PieceType.PAWN and piece.color is color)
        total += min(dead, max(0, 7 - fielded)) * VALUES[PieceType.PAWN]
    return total


def _assert_fixtures_differ_only_by_pool(empty: Game, stocked: Game) -> None:
    """护卫断言：确保两个局面确实只在 `captured` 上有差异。

    若这条不成立，下面所有「池影响估值」的结论都可能只是盘面不同导致的。
    """
    assert [(p.type, p.color, p.position.row, p.position.col) for p in empty.state.pieces] == \
           [(p.type, p.color, p.position.row, p.position.col) for p in stocked.state.pieces]
    assert empty.state.turn is stocked.state.turn is Color.RED
    assert empty.state.captured[Color.RED] == []
    assert {p.type for p in stocked.state.captured[Color.RED]} == {PieceType.ROOK, PieceType.HORSE}
    assert empty.state.captured[Color.BLACK] == stocked.state.captured[Color.BLACK] == []


# --- ① 估值纳入池价值 ---------------------------------------------------------

def test_evaluate_includes_promotion_pool_value():
    """池空 vs 池里有车/马 ⇒ `_evaluate` 的差值**恰为池中可升变子的价值和**。

    修法前两者相等（池盲）；现在差 900+450=1350。断言写成「等于 Σ VALUES(...)」而
    不是写死 1604.925，这样以后调 `VALUES` 不会假红；再单独钉一条 1350 作为 fixture
    不变量，保证这个数字本身是被看到的。
    """
    empty = _game_with_pool([])
    stocked = _game_with_pool(_stocked_pool())
    _assert_fixtures_differ_only_by_pool(empty, stocked)

    # 两个独立实例：同一实例会命中缓存，掩盖真实的估值差异。
    score_without_pool = ChessAI()._evaluate(empty, Color.RED)
    score_with_pool = ChessAI()._evaluate(stocked, Color.RED)

    expected_delta = VALUES[PieceType.ROOK] + VALUES[PieceType.HORSE]
    assert expected_delta == 1350, "fixture 不变量"
    assert score_with_pool - score_without_pool == pytest.approx(expected_delta)


def test_pool_value_matches_rules_derived_expectation():
    """`_pool_value` 与「照规则独立重构的期望」逐项一致（池项整口径）。"""
    for captured in ([], _stocked_pool(),
                     [_piece(PieceType.PAWN, Color.RED, 0, 0)],
                     [_piece(PieceType.CANNON, Color.RED, 0, 0), _piece(PieceType.PAWN, Color.RED, 0, 2)],
                     [_piece(PieceType.KING, Color.RED, 0, 0)]):
        game = _game_with_pool(captured)
        assert ChessAI()._pool_value(game, Color.RED) == pytest.approx(
            _expected_pool_value(captured, Color.RED, game))


# --- ② 候选生成层读池（对照，行为不变）---------------------------------------

def test_tactical_moves_reads_promotion_pool_contrast():
    """对照：候选生成层**确实读池** —— 同样的两个局面，升变类型集合不同。

    这条与 ① 并置，就把「AI 不知池」精确定位在 `_evaluate` 一层，而不是笼统地说
    「AI 不知道池」。
    """
    empty = _game_with_pool([])
    stocked = _game_with_pool(_stocked_pool())
    _assert_fixtures_differ_only_by_pool(empty, stocked)

    without_pool = _promotion_types(empty)
    with_pool = _promotion_types(stocked)
    assert without_pool == set()
    assert with_pool == {PieceType.ROOK, PieceType.HORSE}


# --- ③ 判和键护栏（方案 C 刻意不改）-----------------------------------------

def test_position_key_ignores_capture_pool_guardrail():
    """`position_key` 仍**不含池** —— 这是方案 C 的刻意选择，不是漏改。

    `rules.py:286-288` 的 `position_key` 同时喂养三次重复判和（`game.py:238-240`）且被
    离线端逐字镜像（`offline.js:84`）。把池纳入它属**规则语义变更**，需要产品拍板 +
    三端同步，故本方案**不动它**。本断言是护栏：谁把池"顺手"塞进判和键，这里会红。
    """
    empty = _game_with_pool([])
    stocked = _game_with_pool(_stocked_pool())
    _assert_fixtures_differ_only_by_pool(empty, stocked)

    assert empty.rules.position_key(empty.state) == \
           stocked.rules.position_key(stocked.state)


# --- ④ AI 缓存改为池感知 ------------------------------------------------------

def test_evaluation_cache_is_pool_aware():
    """同一实例对池不同的两局面各成一项，不再复用对方分数（修法前只会有一项）。"""
    engine = ChessAI()
    empty = _game_with_pool([])
    stocked = _game_with_pool(_stocked_pool())

    first = engine._evaluate(empty, Color.RED)
    second = engine._evaluate(stocked, Color.RED)

    assert len(engine.evaluation_cache) == 2
    assert second != first
    assert engine.evaluation_cache[(evaluation_key(empty.rules, empty.state), Color.RED)] == first
    assert engine.evaluation_cache[(evaluation_key(stocked.rules, stocked.state), Color.RED)] == second


def test_transposition_key_is_pool_aware():
    """置换表(TT) 不再跨池命中：池不同的局面必须写进不同的 TT 键。

    修法前两者的 TT 键相同 ⇒ 第二次会命中第一次的条目（更隐蔽的错误）。
    """
    engine = ChessAI()
    empty = _game_with_pool([])
    stocked = _game_with_pool(_stocked_pool())

    engine._search(empty, 1, -math.inf, math.inf, time.monotonic() + 5, None, 0)
    key_empty = evaluation_key(empty.rules, empty.state)
    key_stocked = evaluation_key(stocked.rules, stocked.state)

    assert key_empty in engine.transposition
    assert key_stocked != key_empty
    assert key_stocked not in engine.transposition


def test_see_cache_key_is_pool_aware():
    """SEE 缓存同样以池为键的一部分：同一着法在池不同的两局面上各存一项。"""
    engine = ChessAI()
    move = Move(Position(6, 4), Position(6, 6))
    empty = _game_with_pool([], board=_see_board())
    stocked = _game_with_pool(_stocked_pool(), board=_see_board())

    engine._see_score(empty, move)
    engine._see_score(stocked, move)

    assert len(engine.see_cache) == 2
    assert pool_signature(empty.state) != pool_signature(stocked.state)


# --- ⑤ 规则门控与上限 ---------------------------------------------------------

def test_pool_value_respects_rule_gates():
    """池项受规则开关门控：升变/复活关掉即不计，禁止成为"白给分"。"""
    base = ChessAI()._evaluate(_game_with_pool([]), Color.RED)

    promotion_off = _game_with_pool(_stocked_pool(), options={"pawn_promotion": False})
    assert ChessAI()._evaluate(promotion_off, Color.RED) == pytest.approx(base), \
        "pawn_promotion=False 时升变项必须为 0"

    resurrection_off = _game_with_pool([_piece(PieceType.PAWN, Color.RED, 0, 0)],
                                       options={"pawn_resurrection": False})
    assert ChessAI()._evaluate(resurrection_off, Color.RED) == pytest.approx(base), \
        "pawn_resurrection=False 时复活的兵项必须为 0"


def test_pool_value_never_counts_a_captured_king():
    """池里可能有被吃的王（`VALUES[KING]=50_000`），必须排除，否则分数瞬间爆掉。"""
    with_king = _game_with_pool([_piece(PieceType.KING, Color.RED, 0, 0)])
    assert ChessAI()._pool_value(with_king, Color.RED) == pytest.approx(0.0)
    assert ChessAI()._evaluate(with_king, Color.RED) == pytest.approx(
        ChessAI()._evaluate(_game_with_pool([]), Color.RED))


def test_pool_value_counts_only_revivable_pawns():
    """复活项按 `game.py:169` 的 7 兵上限计，超出上限的死兵不值钱。"""
    one_dead_pawn = [_piece(PieceType.PAWN, Color.RED, 0, 0)]
    room_left = _game_with_pool(one_dead_pawn)
    assert ChessAI()._pool_value(room_left, Color.RED) == pytest.approx(VALUES[PieceType.PAWN])

    full_rank = _game_with_pool(one_dead_pawn, board=_board_with_full_pawn_rank())
    assert ChessAI()._pool_value(full_rank, Color.RED) == pytest.approx(0.0)


# --- ⑥ 镜像对称（连池一起镜像）-----------------------------------------------

def test_evaluate_mirrors_board_and_pool_together():
    """红黑镜像（**含镜像池**）后估值相等：池项没有引入颜色偏置。

    ⚠️ 给 `tests/test_ai_optimization.py::test_evaluation_is_symmetric_when_colors_and_rows_are_mirrored`
    提个醒：那条测试的 `GameState` 未传 `captured`（两池皆空）所以仍成立；一旦谁给它加池，
    **必须连池一起镜像**（红池 → 黑池），否则会假红。
    """
    pieces = _board()
    pool = _stocked_pool()
    game = Game.from_state(GameState(
        "desktop_complete", pieces, turn=Color.RED,
        captured={Color.RED: list(pool), Color.BLACK: []},
    ))
    rows = game.profile.rows
    mirror_game = Game.from_state(GameState(
        "desktop_complete", [_mirror(p, rows) for p in pieces], turn=Color.BLACK,
        captured={Color.BLACK: [_mirror(p, rows) for p in pool], Color.RED: []},
    ))

    assert ChessAI()._evaluate(game, Color.RED) == pytest.approx(
        ChessAI()._evaluate(mirror_game, Color.BLACK))
