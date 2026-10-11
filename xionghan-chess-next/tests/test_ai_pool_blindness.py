"""P0-F 现状基线：AI 的「升变池」可见性分层。

结论（本文件把它钉成可复跑的断言）：

- **候选生成层已读池**：`ai.py:333-338` 的 `_tactical_moves` 用
  `state.captured[moving.color]` 决定升变候选的类型集合；规则层
  `rules.py:98` 也要求 `move.promotion` 必须存在于该池中。
- **静态估值层池盲**：`_evaluate`（`ai.py:361-405`）及其全部下游 helper
  （`_game_phase` / `_mobility_score` / `_activity_score` / `_king_cover` /
  `_is_developed` / `_king_safety`）都不读 `state.captured` —— 全文件只有
  `:335`（候选生成）与 `:597`（`captured_by_move`，SEE 用）两处出现 `captured`。
- **`position_key` 不带池**：`rules.py:221-223` 只由 `turn` + 棋子坐标构成，
  因此池不同、盘面相同的两个局面 key 相同，`_evaluate` 的缓存键也随之碰撞。

⚠️ 本文件记录的是【现状基线】，**不是期望行为**。
P0-F 修法落地后（让 `_evaluate` 纳入池价值、让 `position_key` 纳入池），
本文件的每一条断言都必须**改为反向断言**（池必须影响估值 / key 必须不同）。
"""

from __future__ import annotations

import time

from xionghan_chess.core.ai import ChessAI
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Piece, PieceType


BASELINE_NOTE = (
    "【现状基线】该断言记录的是当前实现的行为，不是期望行为；"
    "P0-F 落地后必须改为反向断言（池应影响估值 / key 应不同）"
)


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


def _game_with_pool(captured_red: list[Piece]) -> Game:
    """盘面相同、仅红方「死子池」不同的局面。

    `state.captured[color]` 语义是该方的死子（`game.py:70` 按被吃棋子自身颜色入池，
    `rules.py:98` 升变时按升变方颜色读池），所以这里放红方的死子表示
    「红方已损失一枚车/马，因而可升变成它们」。
    """
    return Game.from_state(GameState(
        "desktop_complete", _board(), turn=Color.RED,
        captured={Color.RED: list(captured_red), Color.BLACK: []},
    ))


def _stocked_pool() -> list[Piece]:
    return [
        _piece(PieceType.ROOK, Color.RED, 0, 0),
        _piece(PieceType.HORSE, Color.RED, 0, 1),
    ]


def _promotion_types(game: Game) -> set[PieceType]:
    """候选生成层为 `game` 产出的升变类型集合（直接调 `ai.py:333-338` 那一层）。"""
    moves = ChessAI()._tactical_moves(game, time.monotonic() + 10, None)
    return {move.promotion for move in moves if move.promotion is not None}


def _assert_fixtures_differ_only_by_pool(empty: Game, stocked: Game) -> None:
    """护卫断言：确保两个局面确实只在 `captured` 上有差异。

    若这条不成立，下面所有「池盲」结论都是假的 —— 它们可能只是盘面不同导致。
    """
    assert [(p.type, p.color, p.position.row, p.position.col) for p in empty.state.pieces] == \
           [(p.type, p.color, p.position.row, p.position.col) for p in stocked.state.pieces]
    assert empty.state.turn is stocked.state.turn is Color.RED
    assert empty.state.captured[Color.RED] == []
    assert {p.type for p in stocked.state.captured[Color.RED]} == {PieceType.ROOK, PieceType.HORSE}
    assert empty.state.captured[Color.BLACK] == stocked.state.captured[Color.BLACK] == []


def test_evaluate_is_pool_blind_baseline():
    """静态估值对池无感：池空 vs 池里有车/马，`_evaluate` 返回**完全相同**的分数。

    【现状基线】不是期望行为；P0-F 落地后必须改为 `!=`（池应影响估值）。
    量化含义：升变是「消耗池中一子 → 盘上兵变为该类型」，`_evaluate` 看不见池的
    减少，故对任何池相关着法系统性高估（棋盘视角 +780 vs 棋盘+池视角 −120）。
    """
    empty = _game_with_pool([])
    stocked = _game_with_pool(_stocked_pool())
    _assert_fixtures_differ_only_by_pool(empty, stocked)

    # 两个独立实例：同一实例会命中按 position_key 建的缓存，从而「因为缓存」而非
    # 「因为池盲」而相等（缓存碰撞那条基线由下面的 test_position_key... 系列单独钉）。
    score_without_pool = ChessAI()._evaluate(empty, Color.RED)
    score_with_pool = ChessAI()._evaluate(stocked, Color.RED)
    assert score_without_pool == score_with_pool, BASELINE_NOTE  # 现状基线：池盲


def test_tactical_moves_reads_promotion_pool_contrast():
    """对照：候选生成层**确实读池** —— 同样的两个局面，升变类型集合不同。

    这条与上一条并置，就把「AI 不知池」精确定位到 `_evaluate` 一层，
    而不是笼统地说「AI 不知道池」。
    """
    empty = _game_with_pool([])
    stocked = _game_with_pool(_stocked_pool())
    _assert_fixtures_differ_only_by_pool(empty, stocked)

    without_pool = _promotion_types(empty)
    with_pool = _promotion_types(stocked)
    # 当前实现（基线）：池空则一个升变候选都生成不出来，池里有车/马则恰好是它们。
    assert without_pool == set(), BASELINE_NOTE
    assert with_pool == {PieceType.ROOK, PieceType.HORSE}, BASELINE_NOTE
    assert without_pool != with_pool  # 候选生成层读池 —— 与 _evaluate 的池盲形成对照


def test_position_key_ignores_capture_pool_baseline():
    """`position_key` 不带池：池不同、盘面相同的两个局面 key **相同**（P0-E 漏池）。

    【现状基线】不是期望行为；P0-F 把池纳入 key 之后，本断言必须改为 `!=`。
    """
    empty = _game_with_pool([])
    stocked = _game_with_pool(_stocked_pool())
    _assert_fixtures_differ_only_by_pool(empty, stocked)

    assert empty.rules.position_key(empty.state) == \
           stocked.rules.position_key(stocked.state), BASELINE_NOTE  # 现状基线：key 漏池


def test_evaluation_cache_collides_across_pools_baseline():
    """上一条的直接后果：同一 `ChessAI` 实例对两个池不同的局面**共用一个缓存项**。

    【现状基线】不是期望行为；P0-F 让 key 纳入池后，两个局面必须各自成键、不再互串。
    """
    ai = ChessAI()
    empty = _game_with_pool([])
    stocked = _game_with_pool(_stocked_pool())

    first = ai._evaluate(empty, Color.RED)
    key = empty.rules.position_key(empty.state)
    assert (key, Color.RED) in ai.evaluation_cache, BASELINE_NOTE
    # 池不同的第二个局面沿用了同一个缓存键 —— 直接返回第一个局面的分数。
    assert ai._evaluate(stocked, Color.RED) == first == ai.evaluation_cache[(key, Color.RED)]  # 现状基线
    assert len(ai.evaluation_cache) == 1, BASELINE_NOTE
