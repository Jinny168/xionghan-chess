"""Golden values for the indirect-kill rule (audit P0-R1 / P0-R2, item R-1).

The cross-engine suite can only catch the two engines drifting apart. When both
reporters make the same mistake it stays green, so these cases pin the
*expected* value of `in_check` itself: a king may leave the board without any
attacker ever being able to move onto its square, and the engine still has to
report the side as being in check rather than ending the game silently.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.core.rules import RulesEngine

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "offline_rules_probe.cjs"
OFFLINE = ROOT / "android" / "Resources" / "assets" / "offline" / "offline.js"


def engine() -> RulesEngine:
    return RulesEngine(get_profile("desktop_complete"))


def board(*pieces, turn=Color.RED) -> GameState:
    return GameState("desktop_complete", list(pieces), turn=turn)


def _state_dict(state: GameState) -> dict:
    data = state.to_dict()
    return {
        "profileId": data["profileId"],
        "turn": data["turn"],
        "pieces": [
            {"id": item["id"], "type": item["type"], "color": item["color"],
             "row": item["row"], "col": item["col"]}
            for item in data["pieces"]
        ],
        "history": data["history"],
        "captured": data["captured"],
        "winner": data["winner"],
        "draw": data["draw"],
        "positionCounts": data["positionCounts"],
    }


def _probe(payload: dict) -> dict:
    if not shutil.which("node"):
        pytest.skip("Node.js is required for the offline engine check")
    completed = subprocess.run(
        ["node", str(PROBE), str(OFFLINE)],
        input=json.dumps(payload), text=True, capture_output=True, check=True, timeout=30,
    )
    return json.loads(completed.stdout)


def _offline_check(state: GameState, color: Color) -> bool:
    """Ask offline.js for its verdict on the very same board and side."""
    return _probe({"profileId": "desktop_complete", "state": _state_dict(state),
                   "checkFor": color.value})["check"]


# --------------------------------------------------------------------------
# P0-R1: the armor completes a three-cell line and squeezes the king out.
# --------------------------------------------------------------------------

def _armor_position() -> GameState:
    return board(
        Piece.create(PieceType.ARMOR, Color.RED, 6, 3),
        Piece.create(PieceType.ELEPHANT, Color.RED, 6, 5),
        Piece.create(PieceType.KING, Color.BLACK, 6, 6),
    )


def test_armor_line_capture_reports_check_in_both_engines():
    state = _armor_position()
    # The armor only becomes lethal once it has stepped to (6,4), so at rest no
    # attacker can move onto the king's square -- yet the king is doomed, and
    # both engines have to say "in check" or the game ends without a word.
    assert engine().in_check(state, Color.BLACK) is True
    assert _offline_check(state, Color.BLACK) is True
    # Confirm the shape that makes the case worth having: replaying the move
    # through `apply_unchecked` really does remove the king.
    armor = state.pieces[0]
    after = engine().apply_unchecked(state, Move(armor.position, Position(6, 4)), switch_turn=False)
    assert not any(p.type is PieceType.KING for p in after.pieces)
    assert [p.type for p in engine().captured_by_move(state, Move(armor.position, Position(6, 4)))] \
        == [PieceType.KING]


# --------------------------------------------------------------------------
# P0-R2: the assassin drags the king standing behind it into the exchange.
# --------------------------------------------------------------------------

def test_assassin_exchange_reports_check_in_both_engines():
    state = board(
        Piece.create(PieceType.ASSASSIN, Color.RED, 5, 5),
        Piece.create(PieceType.KING, Color.BLACK, 5, 4),
    )
    assert engine().in_check(state, Color.BLACK) is True
    assert _offline_check(state, Color.BLACK) is True
    assassin = state.pieces[0]
    after = engine().apply_unchecked(state, Move(assassin.position, Position(5, 6)), switch_turn=False)
    assert not any(p.type is PieceType.KING for p in after.pieces)
    assert [p.type for p in engine().captured_by_move(state, Move(assassin.position, Position(5, 6)))] \
        == [PieceType.KING]


# --------------------------------------------------------------------------
# Controls: a killer on the board must not manufacture checks.
# --------------------------------------------------------------------------

def test_armor_that_cannot_form_a_line_leaves_the_opponent_safe():
    state = board(
        Piece.create(PieceType.ARMOR, Color.RED, 0, 0),
        Piece.create(PieceType.KING, Color.BLACK, 6, 6),
    )
    assert engine().in_check(state, Color.BLACK) is False
    assert _offline_check(state, Color.BLACK) is False


def test_assassin_that_cannot_reach_the_mirror_square_leaves_the_opponent_safe():
    # The assassin would kill by dragging whatever stands directly behind it, so
    # the mirrored square (10,10) has to be unreachable: it sits on a diagonal
    # from the assassin, and no enemy stands behind the black king either.
    state = board(
        Piece.create(PieceType.ASSASSIN, Color.RED, 5, 5),
        Piece.create(PieceType.KING, Color.BLACK, 0, 0),
    )
    assert engine().in_check(state, Color.BLACK) is False
    assert _offline_check(state, Color.BLACK) is False


# --------------------------------------------------------------------------
# R-5: the probe has to expose more than legal moves and check.
# --------------------------------------------------------------------------

def test_probe_exposes_captured_by_move_and_terminal_legs():
    state = board(
        Piece.create(PieceType.ROOK, Color.RED, 5, 0),
        Piece.create(PieceType.PAWN, Color.BLACK, 5, 4),
        Piece.create(PieceType.KING, Color.RED, 11, 6),
        Piece.create(PieceType.KING, Color.BLACK, 1, 5),
    )
    payload = _state_dict(state)
    result = _probe({
        "profileId": "desktop_complete",
        "state": payload,
        "capturedByMove": {"from": {"row": 5, "col": 0}, "to": {"row": 5, "col": 4}},
        "checkmate": True,
        "stalemate": True,
    })
    assert [captured["type"] for captured in result["capturedByMove"]] == ["pawn"]
    # Neither side is stalemated or mated here; both engines must agree that.
    assert result["checkmate"] is _terminal_flag(state, Color.RED, "checkmate")
    assert result["stalemate"] is _terminal_flag(state, Color.RED, "stalemate")


def _terminal_flag(state: GameState, color: Color, kind: str) -> bool:
    rules = engine()
    moves = len(rules.legal_moves(state, color))
    in_check = rules.in_check(state, color)
    return (in_check and moves == 0) if kind == "checkmate" else (not in_check and moves == 0)
