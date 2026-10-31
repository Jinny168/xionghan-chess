"""Golden capture specs for O-6 (read-side unification).

`RulesEngine.capturable_squares` is now the one function that answers "who can
be captured, and how": `in_check` reads it, and `captured_by_move` shares the
same writer-side predicates it is built from. The cross-engine suite can only
catch the two engines drifting apart -- when both make the same mistake it stays
green -- so these cases pin the *expected* victim, kind, origin and landing.
"""

from __future__ import annotations

import copy

from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.core.rules import CaptureKind, CaptureSpec, Removal, RulesEngine


def engine() -> RulesEngine:
    """软删的甲/楯/刺用选项临时打开 —— 本文件测的是**保留下来的规则分支**，不是出场配置。"""
    profile = get_profile("desktop_complete")
    return RulesEngine(profile, profile.options.merged(
        {"armor_appear": True, "shield_appear": True, "assassin_appear": True}))


def piece(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    return Piece.create(kind, color, row, col)


def board(*pieces: Piece, turn: Color = Color.RED,
          captured: dict[Color, list[Piece]] | None = None) -> GameState:
    return GameState("desktop_complete", list(pieces), turn=turn,
                     captured=captured or {Color.RED: [], Color.BLACK: []})


def _far_kings() -> tuple[Piece, Piece]:
    """Kings parked in opposite corners so they neither block nor face each other."""
    return (piece(PieceType.KING, Color.RED, 12, 0),
            piece(PieceType.KING, Color.BLACK, 0, 12))


def test_g1_direct_capture_is_filed_under_the_landing_square():
    red_king, black_king = _far_kings()
    rook = piece(PieceType.ROOK, Color.RED, 5, 0)
    pawn = piece(PieceType.PAWN, Color.BLACK, 5, 4)
    state = board(red_king, black_king, rook, pawn)
    specs = engine().capturable_squares(state, Color.RED)
    assert list(specs) == [pawn.position]
    assert specs[pawn.position] == CaptureSpec(
        pawn.position,
        (Removal(CaptureKind.DIRECT, pawn.id, PieceType.PAWN, Color.BLACK,
                 pawn.position, Position(5, 0), Position(5, 4)),),
    )






def test_g4_capturable_squares_never_emits_a_pool_consume():
    red_king, black_king = _far_kings()
    rook = piece(PieceType.ROOK, Color.RED, 5, 0)
    pawn = piece(PieceType.PAWN, Color.BLACK, 5, 4)
    dead = piece(PieceType.ROOK, Color.RED, 0, 0)
    state = board(red_king, black_king, rook, pawn,
                  captured={Color.RED: [dead], Color.BLACK: []})
    specs = engine().capturable_squares(state, Color.RED)
    removals = [removal for spec in specs.values() for removal in spec.removals]
    assert removals, "the fixture must capture at least one piece"
    assert all(removal.kind is not CaptureKind.PROMOTION_CONSUME for removal in removals)


def test_g5_capturable_squares_result_is_independent_of_the_capture_pool():
    red_king, black_king = _far_kings()
    # An ordinary capture ...
    rook = piece(PieceType.ROOK, Color.RED, 5, 0)
    enemy = piece(PieceType.HORSE, Color.BLACK, 5, 4)
    # ... and a promotion-rank capture: a red pawn taking a black piece on row 0,
    # where a stocked pool makes the bare move illegal (only the promotion
    # variant reaches the square). This is the shape that used to make the
    # *result* depend on the pool (F2).
    pawn = piece(PieceType.PAWN, Color.RED, 1, 6)
    crowned = piece(PieceType.HORSE, Color.BLACK, 0, 6)
    pieces = (red_king, black_king, rook, enemy, pawn, crowned)
    # The two boards share the very same pieces, so the specs compare field for
    # field (ids included); only `captured` differs.
    empty = board(*pieces)
    dead = piece(PieceType.ROOK, Color.RED, 0, 0)
    stocked = board(*pieces, captured={Color.RED: [dead], Color.BLACK: []})
    assert empty.captured[Color.RED] == []
    assert stocked.captured[Color.RED] != []
    rules = engine()
    # `capturable_squares` is blind to the capture pool: a promotion capture is
    # filed exactly like any other direct capture, so nothing may appear or
    # vanish with the pool (checked in both directions). The pool-aware witness
    # for "these two states really differ" lives in the repetition key
    # `position_key` (方案 A), not in the capture reader.
    assert rules.capturable_squares(empty, Color.RED) == rules.capturable_squares(stocked, Color.RED)
    assert rules.capturable_squares(empty, Color.BLACK) == rules.capturable_squares(stocked, Color.BLACK)
    # ... and the promotion-rank capture is in both, i.e. the pool hid nothing.
    assert crowned.position in rules.capturable_squares(empty, Color.RED)
    assert crowned.position in rules.capturable_squares(stocked, Color.RED)


def test_g6_in_check_is_the_boolean_of_the_point_query():
    rules = engine()
    red_king = piece(PieceType.KING, Color.RED, 12, 12)
    attacked_king = piece(PieceType.KING, Color.BLACK, 5, 4)
    attacker = piece(PieceType.ROOK, Color.RED, 5, 0)
    threatened = board(red_king, attacked_king, attacker)
    hit = rules.capturable_squares(threatened, Color.RED, targets=(attacked_king.position,))
    verdict = rules.in_check(threatened, Color.BLACK)
    assert hit, "the rook shares the king's rank with a clear path"
    assert isinstance(verdict, bool)
    assert verdict is True
    assert verdict is bool(hit)

    safe_king = piece(PieceType.KING, Color.BLACK, 5, 4)
    far_rook = piece(PieceType.ROOK, Color.RED, 0, 0)
    safe = board(red_king, safe_king, far_rook)
    safe_hit = rules.capturable_squares(safe, Color.RED, targets=(safe_king.position,))
    safe_verdict = rules.in_check(safe, Color.BLACK)
    assert not safe_hit
    assert isinstance(safe_verdict, bool)
    assert safe_verdict is False
    assert safe_verdict is bool(safe_hit)


def _mixed_capture_board() -> GameState:
    """同时暴露两种现存吃法：`direct`（落点吃）与 `three_line`（兵三连）。

    甲/楯/刺硬删除后，间接吃法只剩"兵三连"，且必须打开
    `pawn_three_line_capture`（默认关）。
    """
    return board(
        piece(PieceType.KING, Color.RED, 12, 12),
        piece(PieceType.KING, Color.BLACK, 0, 0),
        piece(PieceType.ROOK, Color.RED, 3, 0),      # direct: takes the horse on row 3
        piece(PieceType.HORSE, Color.BLACK, 3, 5),
        piece(PieceType.PAWN, Color.RED, 6, 3),      # three_line: 两兵夹一敌子
        piece(PieceType.PAWN, Color.RED, 6, 5),
        piece(PieceType.PAWN, Color.BLACK, 6, 6),
    )






def test_g9_capturable_squares_is_pure_and_idempotent():
    state = _mixed_capture_board()
    snapshot = copy.deepcopy(state)
    rules = engine()
    first = rules.capturable_squares(state, Color.RED)
    second = rules.capturable_squares(state, Color.RED)
    assert first == second
    assert state.to_dict() == snapshot.to_dict()






def test_g12_promotion_rank_check_is_not_hidden_by_a_stocked_pool():
    # The golden shape of F2: a red pawn already on its promotion rank (row 0)
    # bears on the black king sharing that rank. `pseudo_legal` forces a
    # promotion there whenever the pool can supply one, so the bare step
    # (1,6)->(0,6) is ILLEGAL with a stocked pool and legal with an empty one.
    #
    # BEFORE the fix `_capture_removals` probed that single bare move, so the
    # threat vanished the moment the pool was non-empty: `in_check(stocked, BLACK)`
    # returned False -- a genuine check reported as none. AFTER the fix it probes
    # every `moves_to_target` variant (the promotion move), so the check is seen
    # in both states. `test_g5` pins the same blindness for `capturable_squares`;
    # this case pins the consequence that actually matters, `in_check`.
    red_king = piece(PieceType.KING, Color.RED, 12, 0)
    black_king = piece(PieceType.KING, Color.BLACK, 0, 6)
    pawn = piece(PieceType.PAWN, Color.RED, 1, 6)
    empty = board(red_king, black_king, pawn)
    dead = piece(PieceType.ROOK, Color.RED, 0, 1)
    stocked = board(red_king, black_king, pawn,
                    captured={Color.RED: [dead], Color.BLACK: []})
    rules = engine()

    # Root cause, pinned: the bare step's legality flips with the pool.
    bare = Move(Position(1, 6), Position(0, 6))
    assert rules.pseudo_legal(empty, bare) is True
    assert rules.pseudo_legal(stocked, bare) is False     # forced promotion

    # The reader must not inherit that flip: the king is in check either way.
    assert rules.in_check(empty, Color.BLACK) is True
    assert rules.in_check(stocked, Color.BLACK) is True   # was False before the fix
