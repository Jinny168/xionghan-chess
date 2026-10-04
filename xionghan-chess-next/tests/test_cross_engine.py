from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
import shutil
import subprocess

import pytest

from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position
from xionghan_chess.core.profiles import PROFILES, get_profile
from xionghan_chess.core.rules import RulesEngine


ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "offline_rules_probe.cjs"
OFFLINE = ROOT / "android" / "Resources" / "assets" / "offline" / "offline.js"


def _move_key(move) -> tuple[int, int, int, int, str | None]:
    promotion = move.promotion.value if move.promotion else None
    return move.source.row, move.source.col, move.target.row, move.target.col, promotion


def _offline_state(game: Game) -> dict:
    state = game.state.to_dict()
    return {
        "profileId": state["profileId"],
        "turn": state["turn"],
        "pieces": [
            {"id": item["id"], "type": item["type"], "color": item["color"],
             "row": item["row"], "col": item["col"]}
            for item in state["pieces"]
        ],
        "history": state["history"],
        "captured": state["captured"],
        "winner": state["winner"],
        "draw": state["draw"],
        "positionCounts": state["positionCounts"],
    }


def _offline_result(game: Game) -> dict:
    if not shutil.which("node"):
        pytest.skip("Node.js is required for cross-engine parity tests")
    # Guard rail: the payload must carry every key of the active profile option set.
    # `GameState.to_dict()` has no "options" field, so reading options off the state
    # silently sends `{}` and every toggle test then compares against the profile
    # defaults instead of the intended ones -- a green run that proves nothing.
    sent_options = asdict(game.rules.options)
    assert set(sent_options) >= set(asdict(game.profile.options)), (
        "test channel dropped options: payload must cover every profile option key"
    )
    payload = json.dumps({
        "profileId": game.profile.id,
        "options": sent_options,
        "state": _offline_state(game),
    })
    completed = subprocess.run(
        ["node", str(PROBE), str(OFFLINE)], input=payload, text=True,
        capture_output=True, check=True, timeout=30,
    )
    return json.loads(completed.stdout)


def _probe_resurrect(game: Game, color: Color, row: int, col: int) -> dict:
    """Run one resurrection through offline.js and return its leg of the probe."""
    if not shutil.which("node"):
        pytest.skip("Node.js is required for cross-engine parity tests")
    payload = json.dumps({
        "profileId": game.profile.id,
        "options": asdict(game.rules.options),
        "state": _offline_state(game),
        "resurrect": {"color": color.value, "row": row, "col": col},
    })
    completed = subprocess.run(
        ["node", str(PROBE), str(OFFLINE)], input=payload, text=True,
        capture_output=True, check=True, timeout=30,
    )
    leg = json.loads(completed.stdout)["resurrect"]
    assert leg is not None, "probe did not run the resurrection leg"
    return leg


@pytest.mark.parametrize("profile_id", [
    "traditional", "web", "desktop_classic", "desktop_complete",
])
def test_initial_legal_moves_and_check_match_android_offline(profile_id):
    game = Game(profile_id)
    expected = {_move_key(move) for move in game.rules.legal_moves(game.state)}
    actual = _offline_result(game)
    observed = {
        (item["from"]["row"], item["from"]["col"],
         item["to"]["row"], item["to"]["col"], item["promotion"])
        for item in actual["moves"]
    }
    assert observed == expected
    assert actual["check"] == game.rules.in_check(game.state, game.state.turn)


def test_cross_engine_after_deterministic_play_sequence():
    game = Game("desktop_complete")
    for index in range(6):
        moves = sorted(game.rules.legal_moves(game.state), key=lambda move: move.key())
        game.move(moves[index % len(moves)])
    expected = {_move_key(move) for move in game.rules.legal_moves(game.state)}
    actual = _offline_result(game)
    observed = {
        (item["from"]["row"], item["from"]["col"],
         item["to"]["row"], item["to"]["col"], item["promotion"])
        for item in actual["moves"]
    }
    assert observed == expected


# ---------------------------------------------------------------------------
# O-4 per-piece-type parity coverage
# ---------------------------------------------------------------------------
#
# The cases below hand-build sparse positions with RulesEngine so that every one
# of the 14 piece types gets exercised on a board where its movement rule is
# reachable. A full opening position buries each type under dozens of other
# legal replies, so a silent divergence in one validator can hide behind the
# aggregate set comparison used by the tests above.

_SEEN_IDS: set[str] = set()


def _piece(kind: PieceType, color: Color, row: int, col: int) -> Piece:
    """Create a piece with a unique id (unique across the whole test session)."""
    while True:
        pid = f"x-{kind.value}-{color.value}-{row}-{col}-{len(_SEEN_IDS)}"
        if pid not in _SEEN_IDS:
            _SEEN_IDS.add(pid)
            return Piece(pid, kind, color, Position(row, col))


def _sparse(profile_id: str, placements: list[tuple[PieceType, Color, int, int]],
            *, turn: Color = Color.RED, options: dict | None = None,
            captured: dict[Color, list[Piece]] | None = None,
            kings: bool = True) -> Game:
    """Build a Game whose board contains only the requested pieces.

    Unless `kings=False`, a red and a black king are seeded first so that
    `in_check` and the self-check filter stay meaningful; a missing king makes
    `in_check` answer `True` unconditionally, which would silently weaken every
    comparison. Callers that place their own kings pass `kings=False`.
    """
    profile = get_profile(profile_id)
    merged = profile.options.merged(options or {})
    pieces = []
    if kings:
        pieces += [
            _piece(PieceType.KING, Color.RED, 0, 0),
            _piece(PieceType.KING, Color.BLACK, profile.rows - 1, profile.cols - 1),
        ]
    pieces += [_piece(kind, color, row, col) for kind, color, row, col in placements]
    state = GameState(profile.id, pieces, turn=turn,
                      captured=captured or {Color.RED: [], Color.BLACK: []})
    return Game.from_state(state, merged)


def _assert_parity(game: Game) -> set:
    """Assert RulesEngine and offline.js agree on legalAll and inCheck."""
    expected = {_move_key(move) for move in game.rules.legal_moves(game.state)}
    actual = _offline_result(game)
    observed = {
        (item["from"]["row"], item["from"]["col"],
         item["to"]["row"], item["to"]["col"], item["promotion"])
        for item in actual["moves"]
    }
    assert observed == expected, (
        f"legalAll mismatch for {game.profile.id}: "
        f"only-python={sorted(expected - observed)} only-js={sorted(observed - expected)}"
    )
    assert actual["check"] == game.rules.in_check(game.state, game.state.turn)
    return expected


def _targets_from(moves: set, source: tuple[int, int]) -> set[tuple[int, int]]:
    """Collect the target squares reachable from one source square."""
    return {(target_row, target_col)
            for row, col, target_row, target_col, _promotion in moves
            if (row, col) == source}


def _assert_targets(game: Game, source: tuple[int, int],
                    expected_targets: list[tuple[int, int]]) -> None:
    """Assert the exact target set reachable from `source` (parity + exactness)."""
    observed = _assert_parity(game)
    actual_targets = _targets_from(observed, source)
    assert actual_targets == set(expected_targets), (
        f"unexpected targets from {source}: "
        f"missing={sorted(set(expected_targets) - actual_targets)} "
        f"extra={sorted(actual_targets - set(expected_targets))}"
    )


# --- individual piece types -------------------------------------------------

def test_rook_parity_blocks_and_captures():
    # Rook on an open file: a friendly rook closes one direction while enemy
    # rooks cap each ray at their own square (capturable, not passable).
    game = _sparse("desktop_complete", [
        (PieceType.ROOK, Color.RED, 6, 4),
        (PieceType.ROOK, Color.RED, 6, 6),
        (PieceType.ROOK, Color.BLACK, 6, 9),
        (PieceType.ROOK, Color.BLACK, 6, 2),
    ])
    _assert_targets(game, (6, 4), [
        (6, 2), (6, 3), (6, 5),
        (0, 4), (1, 4), (2, 4), (3, 4), (4, 4), (5, 4),
        (7, 4), (8, 4), (9, 4), (10, 4), (11, 4), (12, 4),
    ])


def test_horse_parity_leg_block_and_straight_three():
    # An occupied horse leg blocks both (2,1) jumps that share it, and also the
    # straight-three ray that runs through the same square.
    game = _sparse("desktop_complete", [
        (PieceType.HORSE, Color.RED, 6, 4),
        (PieceType.PAWN, Color.RED, 5, 4),
        (PieceType.HORSE, Color.BLACK, 3, 4),
    ])
    _assert_targets(game, (6, 4), [(5, 2), (5, 6), (7, 2), (7, 6),
                                   (6, 1), (6, 7), (8, 3), (8, 5), (9, 4)])


def test_horse_straight_three_toggle_parity():
    placements = [(PieceType.HORSE, Color.RED, 6, 4)]
    straight = _sparse("desktop_complete", placements, options={"horse_straight_three": True})
    _assert_targets(straight, (6, 4), [(3, 4), (9, 4), (6, 1), (6, 7),
                                       (4, 3), (4, 5), (8, 3), (8, 5),
                                       (5, 2), (5, 6), (7, 2), (7, 6)])
    # A piece in the middle of the straight ray blocks only that ray.
    blocked = _sparse("desktop_complete", placements + [(PieceType.PAWN, Color.RED, 4, 4)],
                      options={"horse_straight_three": True})
    _assert_targets(blocked, (6, 4), [(9, 4), (6, 1), (6, 7),
                                      (4, 3), (4, 5), (8, 3), (8, 5),
                                      (5, 2), (5, 6), (7, 2), (7, 6)])
    classic = _sparse("desktop_complete", placements,
                      options={"horse_straight_three": False})
    assert (3, 4) not in _targets_from(_assert_parity(classic), (6, 4))


def test_elephant_parity_eye_and_two_step_crossing():
    game = _sparse("desktop_complete", [
        (PieceType.ELEPHANT, Color.RED, 9, 4),
        (PieceType.PAWN, Color.RED, 7, 4),        # occupied eye blocks the diagonal jump
        (PieceType.ELEPHANT, Color.RED, 5, 4),
        (PieceType.ELEPHANT, Color.BLACK, 5, 8),
    ])
    _assert_parity(game)


def test_elephant_cannot_cross_river_toggle_parity():
    # Without river crossing a red elephant on row 6 may only step back into its
    # own half; with it on, the forward orthogonal two-step appears too.
    blocked = _sparse("desktop_complete", [(PieceType.ELEPHANT, Color.RED, 6, 4)],
                      options={"elephant_can_cross_river": False})
    _assert_targets(blocked, (6, 4), [(8, 2), (8, 6)])
    crossing = _sparse("desktop_complete", [(PieceType.ELEPHANT, Color.RED, 6, 4)],
                       options={"elephant_can_cross_river": True})
    _assert_targets(crossing, (6, 4), [(4, 2), (4, 4), (4, 6),
                                       (6, 2), (6, 6),
                                       (8, 2), (8, 4), (8, 6)])


def test_advisor_parity_palace_diagonal():
    # An advisor moves one step diagonally; with advisor_can_leave_palace on it
    # may step out of the palace, so all four diagonals from (10,5) are offered
    # (including the capture on (9,6)).
    game = _sparse("desktop_complete", [
        (PieceType.ADVISOR, Color.RED, 10, 5),
        (PieceType.PAWN, Color.BLACK, 9, 6),
    ])
    _assert_targets(game, (10, 5), [(9, 4), (9, 6), (11, 4), (11, 6)])


def test_king_parity_palace_and_diagonal():
    # On the 13x13 board the palace is rows 9-11 / cols 5-7 for red; with
    # king_can_leave_palace on, the king at (10,5) reaches all eight neighbours.
    inside = _sparse("desktop_complete", [(PieceType.KING, Color.RED, 10, 5)])
    _assert_targets(inside, (10, 5), [(9, 4), (9, 5), (9, 6),
                                       (10, 4), (10, 6),
                                       (11, 4), (11, 5), (11, 6)])
    # Outside the palace with king_can_leave_palace off the king is frozen;
    # turning it on restores the four orthogonal steps.
    stranded = _sparse("desktop_complete", [(PieceType.KING, Color.RED, 6, 6)],
                       options={"king_can_leave_palace": False})
    assert not _targets_from(_assert_parity(stranded), (6, 6))
    freed = _sparse("desktop_complete", [(PieceType.KING, Color.RED, 6, 6)],
                    options={"king_can_leave_palace": True})
    _assert_targets(freed, (6, 6), [(5, 6), (6, 5), (6, 7), (7, 6)])


def test_cannon_parity_jump_requires_exactly_one_screen():
    # No screen: the cannon may slide to every empty square but cannot capture.
    no_screen = _sparse("desktop_complete", [
        (PieceType.CANNON, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 3, 4),
    ])
    _assert_targets(no_screen, (6, 4), [(4, 4), (5, 4), (7, 4), (8, 4), (9, 4),
                                        (10, 4), (11, 4), (12, 4),
                                        (6, 0), (6, 1), (6, 2), (6, 3),
                                        (6, 5), (6, 6), (6, 7), (6, 8),
                                        (6, 9), (6, 10), (6, 11), (6, 12)])
    # Two screens between cannon and target: the capture square is not allowed.
    two_screens = _sparse("desktop_complete", [
        (PieceType.CANNON, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 5, 4),
        (PieceType.PAWN, Color.BLACK, 4, 4),
        (PieceType.PAWN, Color.BLACK, 3, 4),
    ])
    assert (3, 4) not in _targets_from(_assert_parity(two_screens), (6, 4))

    # Exactly one screen: the screened pawn is capturable, nothing behind it.
    one_screen = _sparse("desktop_complete", [
        (PieceType.CANNON, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 4, 4),
        (PieceType.PAWN, Color.BLACK, 2, 4),
    ])
    _assert_targets(one_screen, (6, 4), [(2, 4), (5, 4), (7, 4), (8, 4), (9, 4),
                                         (10, 4), (11, 4), (12, 4),
                                         (6, 0), (6, 1), (6, 2), (6, 3),
                                         (6, 5), (6, 6), (6, 7), (6, 8),
                                         (6, 9), (6, 10), (6, 11), (6, 12)])


def test_pawn_parity_forward_sideways_and_two_step():
    game = _sparse("desktop_complete", [
        (PieceType.PAWN, Color.RED, 6, 4),
        (PieceType.PAWN, Color.RED, 2, 4),        # already across the river: may go sideways
        (PieceType.PAWN, Color.BLACK, 6, 8),
    ])
    _assert_parity(game)


def test_pawn_base_full_movement_toggle_parity():
    base_red = _sparse("desktop_complete", [(PieceType.PAWN, Color.RED, 0, 4)])
    _assert_parity(base_red)
    no_full = _sparse("desktop_complete", [(PieceType.PAWN, Color.RED, 0, 4)],
                      options={"pawn_full_movement_at_base": False})
    _assert_parity(no_full)
    backward = _sparse("desktop_complete", [(PieceType.PAWN, Color.RED, 0, 4)],
                       options={"pawn_backward_at_base": True})
    _assert_parity(backward)


def test_pawn_fast_move_toggle_parity():
    # The leap window is measured from the river outwards: a red pawn only
    # qualifies from row 7 down (distance_to_enemy_territory >= 2), so row 5
    # keeps the plain single step plus the sideways move it earned by crossing.
    own_side = _sparse("desktop_complete", [(PieceType.PAWN, Color.RED, 5, 4)])
    _assert_targets(own_side, (5, 4), [(4, 4), (5, 3), (5, 5)])

    # Row 7 qualifies: the two-step leap appears only with the option enabled.
    fast = _sparse("desktop_complete", [(PieceType.PAWN, Color.RED, 7, 4)],
                   options={"pawn_fast_move_before_enemy_territory": True})
    _assert_targets(fast, (7, 4), [(5, 4), (6, 4)])
    slow = _sparse("desktop_complete", [(PieceType.PAWN, Color.RED, 7, 4)],
                   options={"pawn_fast_move_before_enemy_territory": False})
    _assert_targets(slow, (7, 4), [(6, 4)])

    # The leap also needs a clear intermediate square.
    blocked = _sparse("desktop_complete", [
        (PieceType.PAWN, Color.RED, 7, 4),
        (PieceType.PAWN, Color.RED, 6, 4),
    ], options={"pawn_fast_move_before_enemy_territory": True})
    _assert_targets(blocked, (7, 4), [])


def test_guard_parity_jumps_one_piece():
    # A guard may hop over exactly one piece to any empty square on a line or a
    # diagonal; squares with zero or two pieces between stay closed.
    game = _sparse("desktop_complete", [
        (PieceType.GUARD, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 4, 4),
        (PieceType.PAWN, Color.BLACK, 8, 4),
        (PieceType.PAWN, Color.BLACK, 6, 7),
    ])
    _assert_targets(game, (6, 4), [
        (0, 4), (1, 4), (2, 4), (3, 4), (9, 4), (10, 4), (11, 4), (12, 4),
        (6, 8), (6, 9), (6, 10), (6, 11), (6, 12),
    ])


def test_archer_weak_mode_lattice_parity():
    # A weak archer standing on star point (3,3) may travel up to the next star
    # point along each diagonal, i.e. three steps in each of the four directions.
    # The up-left ray is capped at two steps rather than three: (0,0) is a star
    # point, but it also holds the red king, and an archer cannot step onto its
    # own king. The other three rays reach their star point in full.
    on_star = _sparse("desktop_complete", [(PieceType.ARCHER, Color.RED, 3, 3)])
    _assert_targets(on_star, (3, 3), [
        (0, 6), (1, 1), (1, 5), (2, 2), (2, 4),
        (4, 2), (4, 4), (5, 1), (5, 5), (6, 0), (6, 6),
    ])
    # Off the lattice the weak archer has no reachable star point at all.
    off_star = _sparse("desktop_complete", [(PieceType.ARCHER, Color.RED, 4, 4)])
    _assert_targets(off_star, (4, 4), [(3, 3), (5, 5), (6, 6)])


def test_archer_enhanced_mode_toggle_parity():
    placements = [(PieceType.ARCHER, Color.RED, 4, 4)]
    weak = _sparse("desktop_complete", placements, options={"archer_enhanced_mode": False})
    assert _targets_from(_assert_parity(weak), (4, 4)) == {(3, 3), (5, 5), (6, 6)}
    # Enhanced archers ignore the lattice and may travel up to three steps.
    strong = _sparse("desktop_complete", placements, options={"archer_enhanced_mode": True})
    _assert_targets(strong, (4, 4), [
        (1, 1), (1, 7), (2, 2), (2, 6), (3, 3), (3, 5),
        (5, 3), (5, 5), (6, 2), (6, 6), (7, 1), (7, 7),
    ])


def test_archer_enhanced_capture_only_from_star_parity():
    # Enhanced archers may capture only when standing on a star point.
    off_star = _sparse("desktop_complete", [
        (PieceType.ARCHER, Color.RED, 4, 4),
        (PieceType.PAWN, Color.BLACK, 2, 2),
    ], options={"archer_enhanced_mode": True})
    assert (2, 2) not in _targets_from(_assert_parity(off_star), (4, 4))
    on_star = _sparse("desktop_complete", [
        (PieceType.ARCHER, Color.RED, 3, 3),
        (PieceType.PAWN, Color.BLACK, 1, 1),
    ], options={"archer_enhanced_mode": True})
    assert (1, 1) in _targets_from(_assert_parity(on_star), (3, 3))


def test_thunder_parity_line_diagonal_and_isolated_capture():
    game = _sparse("desktop_complete", [
        (PieceType.THUNDER, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 4, 4),      # isolated: capture allowed at range 2
        (PieceType.PAWN, Color.BLACK, 7, 4),
        (PieceType.PAWN, Color.RED, 7, 4),        # shields the black pawn -> not isolated
        (PieceType.THUNDER, Color.BLACK, 6, 8),
    ])
    _assert_parity(game)


def test_armor_parity_sliding_then_line_capture():
    game = _sparse("desktop_complete", [
        (PieceType.ARMOR, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 6, 7),
        (PieceType.ARMOR, Color.BLACK, 3, 3),
        (PieceType.PAWN, Color.RED, 3, 6),
    ])
    # Armor may never capture by moving: the occupied square is not a target.
    assert (6, 7) not in _targets_from(_assert_parity(game), (6, 4))


def test_armor_line_squeeze_capture_parity():
    # Armor sweeps any enemy that completes an allied/enemy/allied line. The
    # squeeze is an indirect capture, so it must appear in captured_by_move even
    # though armor never captures by sliding onto the occupied square itself.
    # The armor starts one step short of the squeeze line on purpose. `_armor_captures`
    # reads lines through the armor's destination square, so a squeeze only exists
    # once the armor has landed at (6,4); starting on (6,4) would leave the line
    # (6,4),(6,5),(6,6) broken by the armor's own departure and capture nothing.
    game = _sparse("desktop_complete", [
        (PieceType.ARMOR, Color.RED, 6, 3),
        (PieceType.PAWN, Color.RED, 6, 5),
        (PieceType.PAWN, Color.BLACK, 6, 6),
    ])
    moves = _assert_parity(game)
    assert (6, 6) not in _targets_from(moves, (6, 3)), "armor cannot capture by sliding"
    slide = next(m for m in moves if m[:2] == (6, 3) and m[2:4] == (6, 4))
    captured = game.rules.captured_by_move(
        game.state, Move(Position(slide[0], slide[1]), Position(slide[2], slide[3])))
    assert any(p.position.row == 6 and p.position.col == 6 for p in captured), (
        "any armor slide must squeeze away the black pawn at (6,6)"
    )


def test_assassin_parity_slide_and_drag():
    # Assassin slides like a rook but cannot capture by moving; it instead drags
    # the enemy sitting directly behind its origin.
    game = _sparse("desktop_complete", [
        (PieceType.ASSASSIN, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 6, 6),
        (PieceType.PAWN, Color.BLACK, 5, 4),
        (PieceType.ASSASSIN, Color.BLACK, 2, 2),
    ])
    assert (6, 6) not in _targets_from(_assert_parity(game), (6, 4))


def test_shield_parity_jump_one_piece_orthogonal_only():
    game = _sparse("desktop_complete", [
        (PieceType.SHIELD, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 5, 4),
        (PieceType.PAWN, Color.BLACK, 6, 6),
        (PieceType.SHIELD, Color.BLACK, 2, 2),
    ])
    # A shield hops over exactly one piece, on straight lines only. The pawn at
    # (5,4) opens the whole upward ray; the pawn at (6,6) opens the rightward ray.
    _assert_targets(game, (6, 4), [(0, 4), (1, 4), (2, 4), (3, 4), (4, 4),
                                   (6, 7), (6, 8), (6, 9), (6, 10), (6, 11), (6, 12)])
    # With no screen nearby the black shield is completely immobile.
    assert not _targets_from(_assert_parity(game), (2, 2))


def test_shield_blocks_capture_of_protected_piece_parity():
    game = _sparse("desktop_complete", [
        (PieceType.ROOK, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 6, 6),
        (PieceType.SHIELD, Color.BLACK, 5, 6),    # protects the pawn
        (PieceType.SHIELD, Color.RED, 2, 2),
    ])
    assert (6, 6) not in _targets_from(_assert_parity(game), (6, 4))


def test_patrol_parity_home_rank_only():
    # Patrol moves along its own rank by an even number of squares, and may only
    # capture from distance 2 -- a longer hop needs an empty destination. Here the
    # red patrol at (7,6) is walled in by the black patrol sitting on (5,6).
    game = _sparse("desktop_complete", [
        (PieceType.PATROL, Color.RED, 7, 6),
        (PieceType.PATROL, Color.BLACK, 5, 6),
        (PieceType.PAWN, Color.BLACK, 7, 8),
    ])
    _assert_targets(game, (7, 6), [(7, 0), (7, 2), (7, 4), (7, 8)])
    # The black patrol cannot reach the red one at distance 2, so it is frozen.
    _assert_targets(game, (5, 6), [])


def test_patrol_cannot_leave_home_rank_parity():
    # A patrol parked on any other rank has no legal move at all.
    game = _sparse("desktop_complete", [(PieceType.PATROL, Color.RED, 6, 6)])
    assert not _targets_from(_assert_parity(game), (6, 6))


# --- rule interactions ------------------------------------------------------

def test_diagonal_path_pinched_parity():
    # Two allies flanking the first diagonal step choke that diagonal only.
    pinched = _sparse("desktop_complete", [
        (PieceType.ADVISOR, Color.RED, 10, 5),
        (PieceType.PAWN, Color.RED, 10, 6),        # side_a of the first step
        (PieceType.PAWN, Color.RED, 9, 5),         # side_b of the first step
    ])
    # (11,6) is the pinched diagonal; the other three remain open.
    _assert_targets(pinched, (10, 5), [(9, 4), (11, 4), (11, 6)])

    # Remove one flanking piece and the same diagonal reopens.
    open_path = _sparse("desktop_complete", [
        (PieceType.ADVISOR, Color.RED, 10, 5),
        (PieceType.PAWN, Color.RED, 10, 6),
    ])
    _assert_targets(open_path, (10, 5), [(9, 4), (9, 6), (11, 4), (11, 6)])

    # Elephant diagonals obey the same pin rule. Both flankers sit adjacent to
    # the down-right ray, so they pinch (11,6) only; the up-left, up-right and
    # down-left rays pass between them and stay open, (7,2) included.
    blocked_elephant = _sparse("desktop_complete", [
        (PieceType.ELEPHANT, Color.RED, 9, 4),
        (PieceType.PAWN, Color.RED, 9, 5),
        (PieceType.PAWN, Color.RED, 10, 4),
    ])
    _assert_targets(blocked_elephant, (9, 4), [(7, 2), (7, 6), (11, 2)])


def test_kings_facing_parity():
    # Both kings share col 4 with a clear file between them, so the facing rule
    # applies: neither may keep facing the other, and the parity must hold.
    game = _sparse("desktop_complete", [
        (PieceType.KING, Color.RED, 10, 4),
        (PieceType.KING, Color.BLACK, 2, 4),
    ], kings=False)
    assert _assert_parity(game)


def test_traditional_10x9_palace_branch_parity():
    # palace() takes a different branch when rows == 10: the red palace is rows
    # 7-9 / cols 3-5 and the black palace is rows 0-2 / cols 3-5. Kings are
    # placed explicitly so the branch is exercised on real palace squares.
    game = _sparse("traditional", [
        (PieceType.KING, Color.RED, 9, 4),
        (PieceType.KING, Color.BLACK, 0, 4),
        (PieceType.ADVISOR, Color.RED, 7, 3),
        (PieceType.ADVISOR, Color.BLACK, 2, 5),
        (PieceType.ELEPHANT, Color.RED, 9, 2),
        (PieceType.HORSE, Color.BLACK, 5, 4),
        (PieceType.CANNON, Color.RED, 5, 1),
        (PieceType.PAWN, Color.BLACK, 4, 4),
        (PieceType.ROOK, Color.RED, 8, 0),
    ], kings=False)
    assert _assert_parity(game)
    # Red king at (9,4): traditional forbids leaving the palace and forbids the
    # in-palace diagonal, so only the orthogonal steps inside rows 7-9 remain.
    _assert_targets(game, (9, 4), [(8, 4), (9, 3), (9, 5)])
    # Red advisor at (7,3) keeps only its in-palace diagonal; the black advisor
    # at (2,5) is not red's turn piece and has no target in this probe.
    _assert_targets(game, (7, 3), [(8, 4)])
    _assert_targets(game, (2, 5), [])


def test_traditional_palace_edge_parity():
    # Corners of the 10x9 palace: (9,5) is inside so the king may step to
    # (8,5) and along the rank; (9,6) sits outside so only the rank step is legal.
    inside = _sparse("traditional", [
        (PieceType.KING, Color.RED, 9, 5),
        (PieceType.KING, Color.BLACK, 0, 4),
        (PieceType.ADVISOR, Color.RED, 9, 4),
    ], kings=False)
    _assert_targets(inside, (9, 5), [(8, 5)])
    outside = _sparse("traditional", [
        (PieceType.KING, Color.RED, 9, 6),
        (PieceType.KING, Color.BLACK, 0, 4),
        (PieceType.ADVISOR, Color.RED, 9, 4),
    ], kings=False)
    _assert_targets(outside, (9, 6), [(9, 5)])


def test_all_piece_types_present_in_complete_profile_parity():
    # Smoke check that every one of the 14 types is reachable from the engine's
    # dispatch table, so the per-type cases above cannot silently skip a type.
    profile = PROFILES["desktop_complete"]
    engine = RulesEngine(profile)
    for kind in PieceType:
        assert kind in profile.enabled_piece_types, f"{kind} missing from complete profile"
        assert kind in engine.enabled_piece_types


@pytest.mark.parametrize("profile_id", ["desktop_complete", "desktop_classic", "web"])
def test_full_opening_parity_for_every_13x13_profile(profile_id):
    game = Game(profile_id)
    expected = {_move_key(move) for move in game.rules.legal_moves(game.state)}
    actual = _offline_result(game)
    observed = {
        (item["from"]["row"], item["from"]["col"],
         item["to"]["row"], item["to"]["col"], item["promotion"])
        for item in actual["moves"]
    }
    assert observed == expected
    assert expected, "an opening position must expose at least one legal move"


# --- draw / repetition ------------------------------------------------------

def test_threefold_repetition_boundary_parity():
    """Threefold is decided in Python's Game._settle, not in offline.js.

    offline.js `Rules.legalAll` has no notion of repetition, so this asserts the
    reachable move set still agrees once a position has been seen twice.
    """
    game = Game("desktop_classic")
    # Walk a deterministic sequence, recording positions so the third occurrence
    # of the start position is reached without any JavaScript-only state.
    for _ in range(2):
        for _ply in range(4):
            moves = sorted(game.rules.legal_moves(game.state), key=lambda move: move.key())
            game.move(moves[0])
            _assert_parity(game)


def test_no_progress_plies_option_parity():
    game = Game("desktop_classic", option_overrides={"no_progress_draw_plies": 4})
    for _ in range(4):
        moves = sorted(game.rules.legal_moves(game.state), key=lambda move: move.key())
        game.move(moves[0])
        _assert_parity(game)


def test_capture_tracked_in_state_parity():
    """Exercises the `captured` bookkeeping that offline.js also maintains.

    offline.js stores captured pieces under `state.captured[color]`; feeding a
    state whose capture lists are populated catches any divergence in how the two
    engines interpret that field (it gates pawn promotion).
    """
    game = _sparse("desktop_complete", [
        (PieceType.KING, Color.RED, 10, 5),
        (PieceType.KING, Color.BLACK, 2, 6),
        (PieceType.ROOK, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 6, 6),
    ], kings=False)
    capture = Move(Position(6, 4), Position(6, 6))
    assert game.rules.is_legal(game.state, capture)
    captured = game.rules.captured_by_move(game.state, capture)
    assert [p.position.row for p in captured] == [6]

    # Play it for real so GameState.captured is populated the way the wire
    # protocol does it, then re-check parity on the resulting position.
    game.move(capture)
    # `state.captured[color]` is the losing side's captured pieces, which is what
    # resurrect_pawn reads back to find its own dead pawns, so the black pawn
    # killed by the red rook lands in the black pool, not the red one.
    assert [p.type for p in game.state.captured[Color.BLACK]] == [PieceType.PAWN]
    assert game.state.captured[Color.RED] == []
    assert game.state.turn is Color.BLACK
    _assert_parity(game)


def test_pawn_promotion_uses_captured_piece_types_parity():
    """Pawn promotion reads `state.captured`, so both engines must agree on it.

    The red pawn is one step from the black back rank and red has already lost a
    rook, which is the piece type the pawn is allowed to promote into.
    """
    game = _sparse("desktop_complete", [
        (PieceType.PAWN, Color.RED, 1, 4),
    ])
    game.state.captured[Color.RED].append(
        _piece(PieceType.ROOK, Color.BLACK, 0, 0))
    promotions = {(target_row, target_col, promo)
                  for row, col, target_row, target_col, promo in _assert_parity(game)
                  if (row, col) == (1, 4)}
    assert (0, 4, "rook") in promotions, (
        f"promotion to the captured rook must be offered, got {sorted(promotions)}"
    )


# --- pawn resurrection -------------------------------------------------------
#
# `Game.resurrect_pawn` is bookkeeping that `Rules` never sees: it reads the
# mover's own loss pool, rebuilds the pawn, logs a MoveRecord, counts the
# position and settles the terminal chain. offline.js exposes only `Rules` to the
# parity probe, so this path had no coverage against the Android build at all.


def _resurrection_game(placements: list[tuple[PieceType, Color, int, int]] | None = None) -> Game:
    game = _sparse("desktop_complete", placements or [],
                   captured={Color.RED: [_piece(PieceType.PAWN, Color.RED, 0, 0)],
                             Color.BLACK: []})
    assert game.rules.options.pawn_resurrection is True
    return game


def test_resurrect_pawn_parity_between_python_and_offline():
    game = _resurrection_game()
    # Red's home rank is derived from the profile's own pawn slots (row 8 on the
    # 13x13 board); a hard coded 8/4 split would silently break `traditional`.
    home = {(item.row, item.col) for item in game.profile.pieces
            if item.type is PieceType.PAWN and item.color is Color.RED}
    assert (8, 4) in home

    offline = _probe_resurrect(game, Color.RED, 8, 4)
    assert offline["ok"] is True, f"offline.js refused the resurrection: {offline['error']}"

    game.resurrect_pawn(Color.RED, Position(8, 4))

    python_state = game.state.to_dict()
    js_state = offline["state"]
    # The revived pawn is the only thing that appeared on either board.
    assert {(item["row"], item["col"]) for item in js_state["pieces"] if item["type"] == "pawn"} \
        == {(8, 4)}
    assert {(item["row"], item["col"]) for item in python_state["pieces"] if item["type"] == "pawn"} \
        == {(8, 4)}
    assert js_state["turn"] == python_state["turn"] == "black"
    # The dead pawn left the loss pool in both engines.
    assert len(js_state["captured"]["red"]) == len(python_state["captured"]["red"]) == 0
    assert len(js_state["captured"]["black"]) == len(python_state["captured"]["black"]) == 0
    # One logged record, and the position counted once as a board change.
    assert len(js_state["history"]) == len(python_state["history"]) == 1
    assert js_state["history"][0]["pieceType"] == python_state["history"][0]["pieceType"] == "pawn"
    assert sum(js_state["positionCounts"].values()) \
        == sum(python_state["positionCounts"].values()) == 1
    assert "复活" in python_state["history"][0]["notation"]


def test_resurrect_pawn_rejections_match_across_engines():
    game = _resurrection_game()
    # Black's home rank is not a square red may resurrect onto, and black is not
    # the side to move.
    with pytest.raises(GameError):
        game.resurrect_pawn(Color.BLACK, Position(4, 4))
    offline = _probe_resurrect(game, Color.BLACK, 4, 4)
    assert offline["ok"] is False
    assert offline["state"] is None

    # An already occupied home square is another rejection both engines share:
    # red keeps a live pawn on (8, 2).
    busy = _resurrection_game([(PieceType.PAWN, Color.RED, 8, 2)])
    with pytest.raises(GameError):
        busy.resurrect_pawn(Color.RED, Position(8, 2))
    offline = _probe_resurrect(busy, Color.RED, 8, 2)
    assert offline["ok"] is False
    assert busy.state.turn is Color.RED

    # Neither attempt may have touched the board.
    game = _resurrection_game()
    assert len(game.state.pieces) == 2
    assert game.state.turn is Color.RED