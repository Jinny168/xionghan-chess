from __future__ import annotations

from functools import lru_cache
import json
import os
from dataclasses import asdict
from pathlib import Path
import random
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


def _offline_captured(game: Game, source: Position, target: Position) -> list[dict]:
    """Ask offline.js which enemy pieces that very move removes."""
    if not shutil.which("node"):
        pytest.skip("Node.js is required for cross-engine parity tests")
    payload = json.dumps({
        "profileId": game.profile.id,
        "options": asdict(game.rules.options),
        "state": _offline_state(game),
        "capturedByMove": {"from": {"row": source.row, "col": source.col},
                           "to": {"row": target.row, "col": target.col}},
    })
    completed = subprocess.run(
        ["node", str(PROBE), str(OFFLINE)], input=payload, text=True,
        capture_output=True, check=True, timeout=30,
    )
    return json.loads(completed.stdout)["capturedByMove"]


def _python_capture_specs(game: Game, color: Color, targets=None) -> list[dict]:
    """Normalise `RulesEngine.capturable_squares` into the offline probe's shape.

    The offline array is keyed by victim square and carries each removal's
    `kind`, so normalising the Python dict to the same shape lets the parity
    gate compare the kind too -- not just which piece died.
    """
    specs = game.rules.capturable_squares(game.state, color, targets=targets)
    normalised = [
        {
            "row": spec.position.row,
            "col": spec.position.col,
            "removals": [
                {
                    "kind": removal.kind.value,
                    "victimId": removal.victim_id,
                    "victimType": removal.victim_type.value,
                    "victimColor": removal.victim_color.value,
                    "victimRow": removal.victim_position.row,
                    "victimCol": removal.victim_position.col,
                    "originRow": removal.origin.row,
                    "originCol": removal.origin.col,
                    "landingRow": removal.landing.row,
                    "landingCol": removal.landing.col,
                }
                for removal in spec.removals
            ],
        }
        for spec in specs.values()
    ]
    return sorted(normalised, key=lambda item: (item["row"], item["col"]))


def _offline_capture_specs(game: Game, color: Color, targets=None) -> list[dict]:
    """Ask offline.js for its `capturableSquares` over the same board and colour."""
    if not shutil.which("node"):
        pytest.skip("Node.js is required for cross-engine parity tests")
    request: dict = {"color": color.value}
    if targets is not None:
        request["targets"] = [{"row": position.row, "col": position.col} for position in targets]
    payload = json.dumps({
        "profileId": game.profile.id,
        "options": asdict(game.rules.options),
        "state": _offline_state(game),
        "capturableSquares": request,
    })
    completed = subprocess.run(
        ["node", str(PROBE), str(OFFLINE)], input=payload, text=True,
        capture_output=True, check=True, timeout=30,
    )
    observed = json.loads(completed.stdout)["capturableSquares"]
    return sorted(observed, key=lambda item: (item["row"], item["col"]))


def test_assassin_parity_when_soft_delete_is_lifted():
    """刺默认软删：两引擎都不生成它的着法；显式 `assassin_appear` 后走法一致。"""
    off = _sparse("desktop_complete", [
        (PieceType.ASSASSIN, Color.RED, 6, 4),
        (PieceType.HORSE, Color.BLACK, 9, 7),
    ])
    assert _targets_from(_assert_parity(off), (6, 4)) == set(), "默认档案里刺不能动"

    on = _sparse("desktop_complete", [
        (PieceType.ASSASSIN, Color.RED, 6, 4),
        (PieceType.HORSE, Color.BLACK, 9, 7),
    ], options={"assassin_appear": True})
    assert _targets_from(_assert_parity(on), (6, 4)) == {(5, 4), (9, 7)}

    blocked = _sparse("desktop_complete", [
        (PieceType.ASSASSIN, Color.RED, 6, 4),
        (PieceType.PAWN, Color.RED, 7, 5),
        (PieceType.HORSE, Color.BLACK, 9, 7),
    ], options={"assassin_appear": True})
    assert _targets_from(_assert_parity(blocked), (6, 4)) == {(5, 4)}

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
    # Row 6 is the middle ("阴山") row: it is **not** enemy territory any more
    # (口径统一为 row ≤ 5 for red), so from there only the diagonals appear when
    # river crossing is on -- the orthogonal two-step needs enemy territory.
    blocked = _sparse("desktop_complete", [(PieceType.ELEPHANT, Color.RED, 6, 4)],
                      options={"elephant_can_cross_river": False})
    _assert_targets(blocked, (6, 4), [(8, 2), (8, 6)])
    crossing = _sparse("desktop_complete", [(PieceType.ELEPHANT, Color.RED, 6, 4)],
                       options={"elephant_can_cross_river": True})
    _assert_targets(crossing, (6, 4), [(4, 2), (4, 6), (8, 2), (8, 6)])
    # One row further in (row 5 = first enemy row) the orthogonal two-step is
    # back: the feature exists, only the boundary moved.
    inside = _sparse("desktop_complete", [(PieceType.ELEPHANT, Color.RED, 5, 4)],
                     options={"elephant_can_cross_river": True})
    _assert_targets(inside, (5, 4), [(3, 2), (3, 4), (3, 6),
                                     (5, 2), (5, 6),
                                     (7, 2), (7, 4), (7, 6)])


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


def test_promotion_never_offers_a_soft_deleted_type():
    """阵亡池里只剩"已软删"的子时，两引擎都**不得**把兵升变成它。

    这条守的是 `1571ca8` 里抓到的真分歧：Python 的升变候选按引擎启用集（含 `*_appear`）过滤，
    而 JS 当时只按 `profile.enabled` 过滤 —— 软删刺之后，**JS 会把兵升变成刺**。
    这里构造"池中只有刺"的局面，若任一端仍生成刺升变，`_assert_parity` 会直接报 legalAll mismatch。
    """
    game = _sparse("desktop_complete", [
        (PieceType.KING, Color.RED, 12, 12),
        (PieceType.KING, Color.BLACK, 0, 10),
        (PieceType.PAWN, Color.RED, 1, 3),        # 一步就到红方底线 row 0
    ], kings=False)
    game.state.captured[Color.RED].append(Piece.create(PieceType.ASSASSIN, Color.RED, 0, 0))

    _assert_parity(game)                           # 两引擎 legalAll 必须完全一致

    moves = game.rules.legal_moves(game.state)
    promotions = {m.promotion for m in moves if m.source == Position(1, 3)}
    assert PieceType.ASSASSIN not in promotions, "软删的子不得作为升变目标"
    assert None in promotions, "池里没有可升变类型时，应当允许以兵的身份走到底线"


def test_guard_parity_slides_diagonally():
    """尉＝标准主教：两引擎都必须只给斜线目标、且遇子即停（照面钉住已删）。"""
    game = _sparse("desktop_complete", [
        (PieceType.GUARD, Color.RED, 6, 4),
        (PieceType.PAWN, Color.RED, 8, 6),        # 斜线上挡一枚己方子
        (PieceType.HORSE, Color.BLACK, 2, 0),     # 另一条斜线上的敌子（可吃）
    ])
    targets = _targets_from(_assert_parity(game), (6, 4))
    expected = {(5, 3), (4, 2), (3, 1), (2, 0),                     # 左上：一路通到 (2,0) 的敌子
                (7, 5),                                              # 右下：一步就撞己方兵 (8,6)
                (5, 5), (4, 6), (3, 7), (2, 8), (1, 9), (0, 10),      # 右上整条
                (7, 3), (8, 2), (9, 1), (10, 0)}                      # 左下整条
    assert targets == expected, sorted(targets ^ expected)
    # 正交一律不给
    assert (6, 5) not in targets and (6, 3) not in targets


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


def test_archer_capture_ignores_blockers_parity():
    """射的吃子无视阻挡（位移仍要求路径空），两引擎必须一致。"""
    # 注意：`_sparse` 默认把红王放在 (0,0)，会与这里的射重叠 —— 必须自带王位。
    kings = [(PieceType.KING, Color.RED, 12, 12), (PieceType.KING, Color.BLACK, 0, 10)]
    one = _sparse("desktop_complete", kings + [
        (PieceType.ARCHER, Color.RED, 0, 0),
        (PieceType.PAWN, Color.RED, 1, 1),
        (PieceType.HORSE, Color.BLACK, 3, 3),
    ], kings=False)
    targets = _targets_from(_assert_parity(one), (0, 0))
    assert (3, 3) in targets, "隔 1 子应能吃到"
    assert (2, 2) not in targets, "空着位移被挡应非法"

    two = _sparse("desktop_complete", kings + [
        (PieceType.ARCHER, Color.RED, 0, 0),
        (PieceType.PAWN, Color.RED, 1, 1),
        (PieceType.PAWN, Color.RED, 2, 2),
        (PieceType.HORSE, Color.BLACK, 3, 3),
    ], kings=False)
    assert (3, 3) in _targets_from(_assert_parity(two), (0, 0)), "隔 2 子也应能吃到"


def test_pawn_charge_toggle_parity():
    """兵冲锋（开关）两引擎一致：开启后过阴山可直线多格，遇子即停、不吃子。"""
    on = _sparse("desktop_complete", [(PieceType.PAWN, Color.RED, 5, 3)],
                 options={"pawn_charge": True})
    targets = _targets_from(_assert_parity(on), (5, 3))
    assert (2, 3) in targets and (0, 3) in targets

    off = _sparse("desktop_complete", [(PieceType.PAWN, Color.RED, 5, 3)])
    assert (2, 3) not in _targets_from(_assert_parity(off), (5, 3))

    blocked = _sparse("desktop_complete", [
        (PieceType.PAWN, Color.RED, 5, 3),
        (PieceType.PAWN, Color.RED, 4, 3),
    ], options={"pawn_charge": True})
    blocked_targets = _targets_from(_assert_parity(blocked), (5, 3))
    assert (2, 3) not in blocked_targets and (4, 3) not in blocked_targets


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
    # The armor starts one step short of the squeeze line on purpose. `_armor_removals`
    # reads lines through the armor's destination square, so a squeeze only exists
    # once the armor has landed at (6,4); starting on (6,4) would leave the line
    # (6,4),(6,5),(6,6) broken by the armor's own departure and capture nothing.
    # 软删甲/楯后，用选项把甲打开（测的是保留的规则分支）
    game = _sparse("desktop_complete", [
        (PieceType.ARMOR, Color.RED, 6, 3),
        (PieceType.PAWN, Color.RED, 6, 5),
        (PieceType.PAWN, Color.BLACK, 6, 6),
    ], options={"armor_appear": True})
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
    ], options={"shield_appear": True})
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


def test_patrol_moves_on_rows_and_columns_parity():
    """巡：横竖同规则，走偶数格，吃子仅限距离 2（不再限制在 5/7 行）。"""
    game = _sparse("desktop_complete", [
        (PieceType.PATROL, Color.RED, 7, 6),
        (PieceType.PATROL, Color.BLACK, 5, 6),
        (PieceType.PAWN, Color.BLACK, 7, 8),
    ])
    # 横向：距离 2 可吃 (7,8)，距离 4/6 必须是空点；纵向同理（距离 2 可吃 (5,6)）
    _assert_targets(game, (7, 6), [(7, 0), (7, 2), (7, 4), (7, 8),
                                   (9, 6), (11, 6), (5, 6)])

    # 黑方另起一局（`_assert_parity` 只列当前行棋方的着法）：
    # 竖走 (1,6)/(3,6)/(7,6)/(9,6)/(11,6)，横走 (5,0)/(5,2)/(5,4) 与吃子 (5,8)
    black = _sparse("desktop_complete", [
        (PieceType.PATROL, Color.BLACK, 5, 6),
        (PieceType.PAWN, Color.RED, 5, 8),
    ], turn=Color.BLACK)
    _assert_targets(black, (5, 6), [(1, 6), (3, 6), (5, 0), (5, 2), (5, 4),
                                    (5, 8), (7, 6), (9, 6), (11, 6)])


def test_patrol_is_not_pinned_to_home_rank_parity():
    """旧口径把巡锁在 5/7 行；新口径下任意行列都能走（偶数格）。"""
    game = _sparse("desktop_complete", [(PieceType.PATROL, Color.RED, 6, 6)])
    targets = _targets_from(_assert_parity(game), (6, 6))
    assert (6, 0) in targets and (6, 12) in targets
    assert (0, 6) in targets and (12, 6) in targets


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
    # Smoke check on the dispatch table. 软删甲/楯后仅 12 类默认在场：
    # 这两类仍留在 `profile.enabled_piece_types`（可回滚），但被 `*_appear=False` 挡在引擎之外。
    profile = PROFILES["desktop_complete"]
    engine = RulesEngine(profile)
    removed = {PieceType.ARMOR, PieceType.SHIELD, PieceType.ASSASSIN}
    for kind in PieceType:
        assert kind in profile.enabled_piece_types, f"{kind} missing from complete profile"
        if kind in removed:
            assert kind not in engine.enabled_piece_types, f"{kind} 已软删，不应进引擎"
        else:
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


def _offline_position_key(game: Game) -> str:
    """Ask offline.js for its `Rules.positionKey` on the very same state."""
    if not shutil.which("node"):
        pytest.skip("Node.js is required for cross-engine parity tests")
    payload = json.dumps({
        "profileId": game.profile.id,
        "options": asdict(game.rules.options),
        "state": _offline_state(game),
        "positionKey": True,
    })
    completed = subprocess.run(
        ["node", str(PROBE), str(OFFLINE)], input=payload, text=True,
        capture_output=True, check=True, timeout=30,
    )
    return json.loads(completed.stdout)["positionKey"]


def test_position_key_matches_offline_byte_for_byte():
    """The repetition key is a cross-engine contract, so it has to be identical.

    方案 A folded the capture pool into `position_key`; one character of drift
    between the Python and offline builders would split the two repetition
    ledgers (the JS one counts threefold locally). The pool is non-empty here
    because that segment -- colour-tagged, sorted, `,`-joined -- is exactly what
    a naive mirror is most likely to render differently.
    """
    game = _sparse("desktop_complete", [
        # Two same-type pieces straddling the 1<->2 digit row boundary. Python
        # sorts by the numeric tuple while a plain string sort would order "10"
        # before "2", so this pair is what actually proves the contract (F1); a
        # single-digit-only board passed even with the string-sorted JS.
        (PieceType.ROOK, Color.RED, 2, 0),
        (PieceType.ROOK, Color.RED, 10, 0),
        (PieceType.CANNON, Color.RED, 6, 4),
        (PieceType.PAWN, Color.BLACK, 6, 6),
    ], captured={
        Color.RED: [_piece(PieceType.HORSE, Color.RED, 0, 1),
                    _piece(PieceType.CANNON, Color.RED, 0, 2)],
        Color.BLACK: [_piece(PieceType.PAWN, Color.BLACK, 0, 3)],
    })
    assert game.rules.position_key(game.state) == _offline_position_key(game)


def _old_string_sorted_offline_key(state: dict) -> str:
    """Reproduce the pre-F1 offline.js `positionKey`: whole-string board sort.

    Before F1 the JS engine sorted `"color:type:row:col"` strings, so "10" landed
    before "2" (`'10' < '2'`). A document saved by that engine therefore carries
    keys today's `positionKey` can never reproduce -- exactly the stale ledger a
    load has to recover from.
    """
    board = ";".join(sorted(f"{p['color']}:{p['type']}:{p['row']}:{p['col']}"
                            for p in state["pieces"]))
    pool = ",".join(sorted(f"{color}:{item['type']}"
                           for color in ("red", "black")
                           for item in state["captured"][color]))
    return f"{state['turn']}|{board}||pool:{pool}"


def _probe_load_document(document: dict,
                         then_play: list[tuple[tuple[int, int], tuple[int, int]]]) -> dict:
    """Drive offline.js's DOM-free `gameFromDocument` and return its probe leg.

    `gameFromDocument` is the core `loadGameDocument` delegates to; going through
    it exercises the real load path (validation, ledger rebuild) without a DOM.
    """
    if not shutil.which("node"):
        pytest.skip("Node.js is required for cross-engine parity tests")
    payload = json.dumps({
        "profileId": document["profileId"],
        "options": document["options"],
        "state": document["state"],
        "loadDocument": {
            "document": document,
            "initialMinutes": 20,
            "thenPlay": [{"from": {"row": a, "col": b}, "to": {"row": c, "col": d}}
                         for (a, b), (c, d) in then_play],
        },
    })
    completed = subprocess.run(
        ["node", str(PROBE), str(OFFLINE)], input=payload, text=True,
        capture_output=True, check=True, timeout=30,
    )
    leg = json.loads(completed.stdout)["loadDocument"]
    assert leg["ok"], f"offline.js refused the document: {leg['error']}"
    return leg


def test_offline_load_rebuilds_a_stale_repetition_ledger():
    """A `.xhgame` saved by a pre-F1 offline build carries string-sorted ledger
    keys that today's `positionKey` can never reproduce. Loading it must re-derive
    the ledger from the snapshots (mirroring Python's `_rebuild_position_counts`,
    storage.py), otherwise a pre-load repetition is forgotten and the threefold
    draw never fires (漏判).

    Before this fix the loader kept the stored keys verbatim. The assertions
    below are red on that build: the probe has no `gameFromDocument` to call, so
    no `loadDocument` leg is produced at all.

    The board puts two red rooks on rows 2 and 10 -- the 1<->2 digit straddle is
    what makes the old string sort disagree with today's tuple sort (F1), so the
    stored keys really are stale.
    """
    profile = get_profile("desktop_complete")
    pieces = [
        _piece(PieceType.KING, Color.RED, 0, 0),
        _piece(PieceType.KING, Color.BLACK, profile.rows - 1, profile.cols - 1),
        _piece(PieceType.ROOK, Color.RED, 2, 0),     # straddle piece (rows 2 & 10)
        _piece(PieceType.ROOK, Color.RED, 10, 0),    # shuffles rows 10
        _piece(PieceType.ROOK, Color.BLACK, 4, 0),   # shuffles rows 4
    ]
    game = Game.from_state(GameState(profile.id, pieces, turn=Color.RED))

    def play(sr: int, sc: int, tr: int, tc: int) -> None:
        move = next(m for m in game.rules.legal_moves(game.state)
                    if (m.source.row, m.source.col, m.target.row, m.target.col) == (sr, sc, tr, tc))
        game.move(move)

    cycle = [((10, 0), (10, 1)), ((4, 0), (4, 1)), ((10, 1), (10, 0)), ((4, 1), (4, 0))]
    for squares in cycle:                       # the start position is now seen twice
        play(squares[0][0], squares[0][1], squares[1][0], squares[1][1])

    state = game.state.to_dict()
    snapshots = [dict(snapshot) for snapshot in game._snapshots]
    assert len(snapshots) == len(state["history"]) == len(cycle)
    visited = [*snapshots, state]

    # The document as a pre-F1 engine wrote it: old string-sorted keys and no
    # version marker (offline.js never stamps one).
    stale: dict[str, int] = {}
    for snapshot in visited:
        key = _old_string_sorted_offline_key(snapshot)
        stale[key] = stale.get(key, 0) + 1
    document = {
        "formatVersion": 1,
        "profileId": profile.id,
        "options": asdict(profile.options),
        "state": {**state, "positionCounts": stale},
        "snapshots": snapshots,
        "savedAt": "2026-01-01T00:00:00",
    }

    # What the ledger must be once rebuilt: today's pool-aware, tuple-sorted key
    # over every visited position (snapshots are the pre-move states, the live
    # state is the last one).
    expected: dict[str, int] = {}
    for snapshot in visited:
        key = game.rules.position_key(GameState.from_dict(snapshot))
        expected[key] = expected.get(key, 0) + 1
    # Guard: the stored keys really are stale, else this case proves nothing.
    assert set(stale) != set(expected)
    assert max(stale.values()) == 2, "the repetition is pre-load, so its store sits at 2"

    leg = _probe_load_document(document, cycle)

    # 1) The rebuilt ledger is byte-identical to Python's on the same states.
    assert leg["loadedPositionCounts"] == expected
    assert max(leg["loadedPositionCounts"].values()) == 2
    # 2) No stale key survives beside it (a load must not keep two ledgers).
    assert set(leg["loadedPositionCounts"]) == set(expected)
    # 3) A third visit to the start position now draws. Without the rebuild the
    #    third occurrence would file under today's key while the stored one sits
    #    at 2 under the old key, so `settle` never sees the threefold.
    assert leg["draw"] is True
    assert leg["resultReason"] == "threefold_repetition"
    assert max(leg["positionCounts"].values()) == 3


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


# --- O-6 capture specs -------------------------------------------------------
#
# The legal-move parity above compares move *sets*; a divergence that keeps the
# same moves but attributes a different capture kind would slip through. These
# cases compare the whole `capturable_squares` structure -- victim square,
# victim, kind, origin and landing -- on both engines, so "both wrong the same
# way" is the only way they can stay green.


@pytest.mark.parametrize("profile_id", [
    "traditional", "web", "desktop_classic", "desktop_complete",
])
def test_capturable_squares_full_enumeration_parity(profile_id):
    game = Game(profile_id)
    for color in (Color.RED, Color.BLACK):
        assert _python_capture_specs(game, color) == _offline_capture_specs(game, color)
    for index in range(6):
        moves = sorted(game.rules.legal_moves(game.state), key=lambda move: move.key())
        game.move(moves[index % len(moves)])
    for color in (Color.RED, Color.BLACK):
        assert _python_capture_specs(game, color) == _offline_capture_specs(game, color)


def test_capturable_squares_point_query_parity():
    game = Game("desktop_complete")
    for index in range(4):
        moves = sorted(game.rules.legal_moves(game.state), key=lambda move: move.key())
        game.move(moves[index % len(moves)])
    positions = [piece.position for piece in game.state.pieces][:4]
    for color in (Color.RED, Color.BLACK):
        for position in positions:
            assert _python_capture_specs(game, color, targets=(position,)) == \
                _offline_capture_specs(game, color, targets=(position,))


def test_capture_kinds_match_across_engines():
    # A crafted board that produces a direct capture, an armor squeeze and an
    # assassin drag at once, so a "captured but with the wrong kind" decision
    # cannot pass the gate.
    # 兵对放在 row 5：row 6 是阴山行，**不再**算敌境，红兵在那里不能横走吃子
    # （旧口径下这枚 direct 吃子靠的正是 row 6 横走，改口径后必须下移一行）。
    # 刺的拖拽吃法已删除，`assassin_drag` 不再产生；这里只要 direct + armor_line：
    # row 6 的一对兵给 `armor_line`（甲走到 (6,4) 凑成三连），row 5 的一对给 `direct`。
    game = _sparse("desktop_complete", [
        (PieceType.ARMOR, Color.RED, 6, 3),
        (PieceType.PAWN, Color.RED, 6, 5),
        (PieceType.PAWN, Color.BLACK, 6, 6),
        (PieceType.PAWN, Color.RED, 5, 5),
        (PieceType.PAWN, Color.BLACK, 5, 6),
    ], options={"armor_appear": True})   # 软删甲：用选项把甲打开
    python = _python_capture_specs(game, Color.RED)
    offline = _offline_capture_specs(game, Color.RED)
    assert python == offline
    kinds = {removal["kind"] for spec in python for removal in spec["removals"]}
    # 刺的「拖拽/同归于尽」已删除，`assassin_drag` 不再产生
    assert {"direct", "armor_line"} <= kinds, kinds
    assert "assassin_drag" not in kinds


# ---------------------------------------------------------------------------
# P0-3: random/exhaustive parity + same-side invariants
# ---------------------------------------------------------------------------
#
# The golden cases above are hand-built and, twice already (F1's single rook,
# F2's promotion-line blindness), a fixture that never reached the bug stayed
# green. This block adds two independent nets on top -- it does not weaken or
# replace any of them:
#
#   1. A fixed, reproducible sample of random *legal* positions compared on the
#      same five legs as the golden cases (`moves`, `check`, `capturableSquares`,
#      `positionKey`, `capturedByMove`). The seed is printed and the sample size
#      is `XH_PARITY_SAMPLES` (default 16), so a red run is reproducible and the
#      suite stays time-bounded.
#   2. Same-side invariants written a different way (a point query must equal the
#      full enumeration restricted to that key; `in_check` must equal the king's
#      point query; `captured_by_move` must equal the capture-spec attribution).
#      These need no JS, so they can still catch a mistake the two engines make
#      *identically* -- exactly what a pure parity gate cannot do.

_ALL_TYPES: tuple[PieceType, ...] = tuple(sorted(PieceType, key=lambda kind: kind.value))
_SAMPLING_PROFILES: tuple[str, ...] = ("traditional", "web", "desktop_classic", "desktop_complete")
PARITY_SEED_BASE = 20261013
PARITY_SAMPLES = max(1, int(os.environ.get("XH_PARITY_SAMPLES", "16")))


def _sample_context(index: int, game: Game) -> str:
    """A reproducible description of one sample, for failure messages."""
    board = ", ".join(
        f"{piece.color.value}:{piece.type.value}@{piece.position.row},{piece.position.col}"
        for piece in sorted(game.state.pieces,
                            key=lambda p: (p.color.value, p.type.value, p.position.row, p.position.col))
    )
    pool = "; ".join(
        f"{color.value}=[{','.join(p.type.value for p in game.state.captured[color])}]"
        for color in (Color.RED, Color.BLACK)
    )
    return (f"\n[XH_PARITY seed={PARITY_SEED_BASE + index} index={index}] "
            f"profile={game.profile.id} turn={game.state.turn.value}\n"
            f"  board: {board}\n  pool: {pool}")


def _random_game_once(rng: random.Random, target: PieceType) -> Game | None:
    """One random-placement attempt that must include a `target` piece."""
    candidates = [pid for pid in _SAMPLING_PROFILES
                  if target in get_profile(pid).enabled_piece_types]
    profile = get_profile(rng.choice(candidates or list(_SAMPLING_PROFILES)))
    rows, cols = profile.rows, profile.cols
    enabled = tuple(sorted(profile.enabled_piece_types, key=lambda kind: kind.value))

    squares = [(row, col) for row in range(rows) for col in range(cols)]
    rng.shuffle(squares)
    occupied: set[Position] = set()
    pieces: list[Piece] = []

    def place(kind: PieceType, color: Color, row: int, col: int) -> bool:
        position = Position(row, col)
        if position in occupied:
            return False
        occupied.add(position)
        pieces.append(_piece(kind, color, row, col))
        return True

    def place_random(kind: PieceType, color: Color) -> bool:
        while squares:
            row, col = squares.pop()
            if place(kind, color, row, col):
                return True
        return False

    # Both kings first: a missing king makes `in_check` answer `True`
    # unconditionally and silently weaken every comparison.
    for color in (Color.RED, Color.BLACK):
        if not place_random(PieceType.KING, color):
            return None

    # The one piece type this sample is responsible for exercising. The king is
    # already covered by the mandatory pair, so it never gets a second copy --
    # a board with two kings of one colour has no meaning for `in_check`.
    if target is not PieceType.KING and \
            not place_random(target, rng.choice((Color.RED, Color.BLACK))):
        return None

    # A handful of extra pieces, so ranks/files/adjacency get rough coverage.
    # Kings are excluded for the same reason: at most one per colour.
    extra_types = [kind for kind in enabled if kind is not PieceType.KING]
    for _ in range(rng.randint(2, 6)):
        if not extra_types:
            break
        if not place_random(rng.choice(extra_types), rng.choice((Color.RED, Color.BLACK))):
            break

    # Seed promotion-line pressure: a pawn on its promotion rank and one a step
    # short, which is where F2 lived.
    if PieceType.PAWN in enabled:
        for color, rank in ((Color.RED, 0), (Color.BLACK, rows - 1)):
            step = rank + 1 if color is Color.RED else rank - 1
            for row in (rank, step):
                if 0 <= row < rows and rng.random() < 0.5:
                    place(PieceType.PAWN, color, row, rng.randrange(cols))

    # Non-empty capture pools: the pool gates mandatory promotion, so both the
    # empty and the stocked pool have to be exercised.
    pool_types = [kind for kind in enabled if kind is not PieceType.KING]
    captured: dict[Color, list[Piece]] = {Color.RED: [], Color.BLACK: []}
    for color in (Color.RED, Color.BLACK):
        if pool_types and rng.random() < 0.5:
            for _ in range(rng.randint(1, 2)):
                captured[color].append(_piece(rng.choice(pool_types), color, 0, 0))

    state = GameState(profile.id, pieces, turn=rng.choice((Color.RED, Color.BLACK)),
                      captured=captured)
    game = Game.from_state(state)
    # Keep the sample *legal*: the side that just moved may not have left its own
    # king capturable, and the side to move needs at least one legal reply.
    if game.rules.in_check(state, state.turn.opponent):
        return None
    if not game.rules.legal_moves(state):
        return None
    return game


@lru_cache(maxsize=None)
def _random_game(index: int) -> Game:
    """Deterministic legal random position for sample `index`, seed printed above."""
    target = _ALL_TYPES[index % len(_ALL_TYPES)]
    seed = PARITY_SEED_BASE + index
    for attempt in range(64):
        game = _random_game_once(random.Random(seed + attempt * 1_000_003), target)
        if game is not None:
            return game
    raise AssertionError(
        f"no legal random position for index={index} seed={seed} after 64 attempts"
    )


def _offline_full_probe(game: Game, check_for: Color, capture_color: Color,
                        captured_move: Move | None) -> dict:
    """One offline.js call that returns every parity leg for the same board."""
    if not shutil.which("node"):
        pytest.skip("Node.js is required for cross-engine parity tests")
    sent_options = asdict(game.rules.options)
    assert set(sent_options) >= set(asdict(game.profile.options)), (
        "test channel dropped options: payload must cover every profile option key"
    )
    payload: dict = {
        "profileId": game.profile.id,
        "options": sent_options,
        "state": _offline_state(game),
        "checkFor": check_for.value,
        "capturableSquares": {"color": capture_color.value},
        "positionKey": True,
    }
    if captured_move is not None:
        payload["capturedByMove"] = {
            "from": {"row": captured_move.source.row, "col": captured_move.source.col},
            "to": {"row": captured_move.target.row, "col": captured_move.target.col},
            "promotion": captured_move.promotion.value if captured_move.promotion else None,
        }
    completed = subprocess.run(
        ["node", str(PROBE), str(OFFLINE)], input=json.dumps(payload), text=True,
        capture_output=True, check=True, timeout=60,
    )
    return json.loads(completed.stdout)


@pytest.mark.parametrize("index", range(PARITY_SAMPLES))
def test_random_position_cross_engine_parity(index):
    game = _random_game(index)
    context = _sample_context(index, game)
    print(f"[XH_PARITY] seed={PARITY_SEED_BASE + index} index={index} profile={game.profile.id}")
    state = game.state
    rules = game.rules

    legal = sorted(rules.legal_moves(state), key=lambda move: move.key())
    assert legal, f"random sample must have at least one legal move{context}"
    expected_moves = {_move_key(move) for move in legal}
    first_move = legal[0]

    result = _offline_full_probe(game, state.turn, state.turn, first_move)

    observed_moves = {
        (item["from"]["row"], item["from"]["col"], item["to"]["row"],
         item["to"]["col"], item["promotion"])
        for item in result["moves"]
    }
    assert observed_moves == expected_moves, (
        f"legalAll mismatch{context}\n"
        f"  only-python={sorted(expected_moves - observed_moves)}\n"
        f"  only-js={sorted(observed_moves - expected_moves)}"
    )

    assert result["check"] is rules.in_check(state, state.turn), f"check mismatch{context}"
    assert result["positionKey"] == rules.position_key(state), (
        f"positionKey mismatch{context}\n"
        f"  python={rules.position_key(state)!r}\n  js={result['positionKey']!r}"
    )
    python_specs = _python_capture_specs(game, state.turn)
    assert result["capturableSquares"] == python_specs, (
        f"capturableSquares mismatch{context}\n"
        f"  python={python_specs}\n  js={result['capturableSquares']}"
    )
    python_captured = sorted((piece.type.value, piece.color.value)
                             for piece in rules.captured_by_move(state, first_move))
    js_captured = sorted((item["type"], item["color"]) for item in result["capturedByMove"])
    assert js_captured == python_captured, (
        f"capturedByMove mismatch for {first_move.key()}{context}\n"
        f"  python={python_captured}\n  js={js_captured}"
    )


@pytest.mark.parametrize("index", range(PARITY_SAMPLES))
def test_random_position_same_side_invariants(index):
    """Self-consistency checks that hold without the JS engine.

    A parity gate can only catch the two engines drifting apart; these identities
    are stated in a different shape, so a mistake both engines share still has a
    chance of failing here.
    """
    game = _random_game(index)
    context = _sample_context(index, game)
    state = game.state
    rules = game.rules
    king_pieces = [piece for piece in state.pieces if piece.type is PieceType.KING]
    assert len(king_pieces) == 2, f"sample must hold exactly two kings{context}"
    kings = {piece.color: piece.position for piece in king_pieces}
    assert set(kings) == {Color.RED, Color.BLACK}, f"sample must keep both kings{context}"

    for color in (Color.RED, Color.BLACK):
        full = rules.capturable_squares(state, color)

        # G6: `in_check(color)` is the *opponent's* point query on `color`'s king
        # (or the facing-kings rule) -- the querying colour and the threatened
        # king are opposite, which is exactly what `in_check` reads.
        own_king = kings[color]
        point = rules.capturable_squares(state, color.opponent, targets=(own_king,))
        expected_check = bool(point) or rules._kings_facing(state)
        assert rules.in_check(state, color) is expected_check, (
            f"in_check != king point query for {color.value}{context}\n"
            f"  point={point}\n  kings_facing={rules._kings_facing(state)}"
        )

        # G7: a point query is exactly the full enumeration restricted to that key.
        for key in (kings[color.opponent], *list(full)[:2], Position(0, 0)):
            restricted = {key: full[key]} if key in full else {}
            assert rules.capturable_squares(state, color, targets=(key,)) == restricted, (
                f"point query != full enumeration at {key} for {color.value}{context}"
            )

        # G8: `captured_by_move` agrees with the capture-spec attribution.
        for move in sorted(rules.legal_moves(state, color), key=lambda item: item.key()):
            attributed = {
                removal.victim_id
                for spec in full.values() for removal in spec.removals
                if removal.origin == move.source and removal.landing == move.target
            }
            actual = {piece.id for piece in rules.captured_by_move(state, move)}
            assert attributed == actual, (
                f"capture attribution != captured_by_move for {move.key()} "
                f"({color.value}){context}\n"
                f"  attributed={sorted(attributed)}\n  actual={sorted(actual)}"
            )


def test_random_sample_set_covers_every_piece_type():
    """The random sample must actually reach the piece types it claims to.

    Sample `index` force-includes `_ALL_TYPES[index % 14]`, so the default run
    (16 samples) is guaranteed to exercise all 14 types; a smaller
    `XH_PARITY_SAMPLES` still asserts coverage for the samples that exist,
    instead of silently testing the same few boards forever.
    """
    seen: set[PieceType] = set()
    for index in range(PARITY_SAMPLES):
        seen |= {piece.type for piece in _random_game(index).state.pieces}
    required = set(_ALL_TYPES[:min(PARITY_SAMPLES, len(_ALL_TYPES))])
    missing = required - seen
    assert not missing, (
        f"{PARITY_SAMPLES} samples never exercised: {sorted(kind.value for kind in missing)}"
    )