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
    """软删甲/楯后，用选项把它们临时打开 —— 本文件测的是**保留下来的规则分支**，不是出场配置。"""
    profile = get_profile("desktop_complete")
    return RulesEngine(profile, profile.options.merged(
        {"armor_appear": True, "shield_appear": True, "assassin_appear": True}))


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




# --------------------------------------------------------------------------
# P0-R2: the assassin drags the king standing behind it into the exchange.
# --------------------------------------------------------------------------





# --------------------------------------------------------------------------
# Controls: a killer on the board must not manufacture checks.
# --------------------------------------------------------------------------



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
