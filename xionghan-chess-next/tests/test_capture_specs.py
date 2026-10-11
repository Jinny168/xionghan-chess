"""Golden capture specs for O-6 (read-side unification).

`RulesEngine.capturable_squares` is now the one function that answers "who can
be captured, and how": `in_check` reads it, and `captured_by_move` shares the
same writer-side predicates it is built from. The cross-engine suite can only
catch the two engines drifting apart -- when both make the same mistake it stays
green -- so these cases pin the *expected* victim, kind, origin and landing.
"""

from __future__ import annotations

import copy

from xionghan_chess.core.model import Color, GameState, Piece, PieceType, Position
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.core.rules import CaptureKind, CaptureSpec, Removal, RulesEngine


def engine() -> RulesEngine:
    return RulesEngine(get_profile("desktop_complete"))


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


def test_g2_armor_line_removes_the_piece_it_never_lands_on():
    armor = piece(PieceType.ARMOR, Color.RED, 6, 3)
    ally = piece(PieceType.ELEPHANT, Color.RED, 6, 5)
    victim = piece(PieceType.KING, Color.BLACK, 6, 6)
    state = board(armor, ally, victim)
    spec = engine().capturable_squares(state, Color.RED)[victim.position]
    assert len(spec.removals) == 1
    removal = spec.removals[0]
    assert removal.kind is CaptureKind.ARMOR_LINE
    assert removal.victim_position == Position(6, 6)
    assert removal.origin == Position(6, 3)
    # The armor squeezes with a landing that is not the square the king stood on.
    assert removal.landing == Position(6, 4)
    assert removal.landing != removal.victim_position


def test_g3_assassin_drag_removes_the_piece_behind_its_origin():
    assassin = piece(PieceType.ASSASSIN, Color.RED, 5, 5)
    victim = piece(PieceType.KING, Color.BLACK, 5, 4)
    state = board(assassin, victim)
    spec = engine().capturable_squares(state, Color.RED)[victim.position]
    assert len(spec.removals) == 1
    removal = spec.removals[0]
    assert removal.kind is CaptureKind.ASSASSIN_DRAG
    assert removal.origin == Position(5, 5)
    assert removal.landing == Position(5, 6)
    assert removal.victim_position == Position(5, 4)


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


def test_g5_capturable_squares_is_blind_to_the_capture_pool():
    red_king, black_king = _far_kings()
    rook = piece(PieceType.ROOK, Color.RED, 5, 0)
    enemy = piece(PieceType.HORSE, Color.BLACK, 5, 4)
    empty = board(red_king, black_king, rook, enemy)
    dead = piece(PieceType.ROOK, Color.RED, 0, 0)
    stocked = board(red_king, black_king, rook, enemy,
                    captured={Color.RED: [dead], Color.BLACK: []})
    assert empty.captured[Color.RED] == []
    assert stocked.captured[Color.RED] != []
    rules = engine()
    # Only the pool differs between the two boards, so a capture the board itself
    # does not show must not appear or vanish with the pool (both directions).
    assert rules.capturable_squares(empty, Color.RED) == rules.capturable_squares(stocked, Color.RED)
    assert rules.capturable_squares(empty, Color.BLACK) == rules.capturable_squares(stocked, Color.BLACK)


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
    """A position that exposes all three capture kinds at once."""
    return board(
        piece(PieceType.KING, Color.RED, 12, 12),
        piece(PieceType.KING, Color.BLACK, 0, 0),
        piece(PieceType.ROOK, Color.RED, 3, 0),      # direct: takes the horse on row 3
        piece(PieceType.HORSE, Color.BLACK, 3, 5),
        piece(PieceType.ARMOR, Color.RED, 6, 3),     # armor_line: squeezes the pawn below
        piece(PieceType.PAWN, Color.RED, 6, 5),
        piece(PieceType.PAWN, Color.BLACK, 6, 6),
        piece(PieceType.ASSASSIN, Color.RED, 9, 4),  # assassin_drag: drags the horse behind it
        piece(PieceType.HORSE, Color.BLACK, 9, 2),
    )


def test_g7_point_query_matches_full_enumeration():
    state = _mixed_capture_board()
    rules = engine()
    full = rules.capturable_squares(state, Color.RED)
    kinds = {removal.kind for spec in full.values() for removal in spec.removals}
    assert {CaptureKind.DIRECT, CaptureKind.ARMOR_LINE, CaptureKind.ASSASSIN_DRAG} <= kinds
    for key in [*full, Position(5, 5), Position(0, 12)]:
        expected = {key: full[key]} if key in full else {}
        assert rules.capturable_squares(state, Color.RED, targets=(key,)) == expected


def test_g8_captured_by_move_matches_capturable_squares_attribution():
    red_king = piece(PieceType.KING, Color.RED, 12, 12)
    black_king = piece(PieceType.KING, Color.BLACK, 0, 0)
    armor = piece(PieceType.ARMOR, Color.RED, 6, 3)
    ally = piece(PieceType.PAWN, Color.RED, 6, 5)
    victim = piece(PieceType.PAWN, Color.BLACK, 6, 6)
    state = board(red_king, black_king, armor, ally, victim)
    rules = engine()
    saw_capture = False
    for move in rules.legal_moves(state):
        moving = rules.get(state, move.source)
        specs = rules.capturable_squares(state, moving.color)
        attributed = {removal.victim_id for spec in specs.values()
                      for removal in spec.removals
                      if removal.origin == move.source and removal.landing == move.target}
        actual = {p.id for p in rules.captured_by_move(state, move)}
        assert attributed == actual, f"move {move.key()} attribution disagrees"
        saw_capture = saw_capture or bool(actual)
    assert saw_capture, "the fixture must include at least one capturing legal move"


def test_g9_capturable_squares_is_pure_and_idempotent():
    state = _mixed_capture_board()
    snapshot = copy.deepcopy(state)
    rules = engine()
    first = rules.capturable_squares(state, Color.RED)
    second = rules.capturable_squares(state, Color.RED)
    assert first == second
    assert state.to_dict() == snapshot.to_dict()
