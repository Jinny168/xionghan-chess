from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, Piece, PieceType


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
    payload = json.dumps({
        "profileId": game.profile.id,
        "options": game.state.to_dict().get("options", {}),
        "state": _offline_state(game),
    })
    completed = subprocess.run(
        ["node", str(PROBE), str(OFFLINE)], input=payload, text=True,
        capture_output=True, check=True, timeout=30,
    )
    return json.loads(completed.stdout)


def _observed_moves(game: Game) -> set[tuple[int, int, int, int, str | None]]:
    actual = _offline_result(game)
    return {
        (item["from"]["row"], item["from"]["col"],
         item["to"]["row"], item["to"]["col"], item["promotion"])
        for item in actual["moves"]
    }


@pytest.mark.parametrize("profile_id", [
    "traditional", "web", "desktop_classic", "desktop_complete",
])
def test_initial_legal_moves_and_check_match_android_offline(profile_id):
    game = Game(profile_id)
    expected = {_move_key(move) for move in game.rules.legal_moves(game.state)}
    actual = _offline_result(game)
    assert _observed_moves(game) == expected
    assert actual["check"] == game.rules.in_check(game.state, game.state.turn)


def test_cross_engine_after_deterministic_play_sequence():
    game = Game("desktop_complete")
    for index in range(6):
        moves = sorted(game.rules.legal_moves(game.state), key=lambda move: move.key())
        game.move(moves[index % len(moves)])
    expected = {_move_key(move) for move in game.rules.legal_moves(game.state)}
    assert _observed_moves(game) == expected


@pytest.mark.parametrize("piece_type", list(PieceType))
def test_each_piece_type_matches_android_offline(piece_type):
    red_king = Piece.create(PieceType.KING, Color.RED, 11, 6)
    black_king = Piece.create(PieceType.KING, Color.BLACK, 1, 5)
    pieces = [red_king, black_king]
    if piece_type is not PieceType.KING:
        pieces.append(Piece.create(piece_type, Color.RED, 6, 6))
        pieces.append(Piece.create(PieceType.PAWN, Color.BLACK, 6, 8))
        pieces.append(Piece.create(PieceType.PAWN, Color.BLACK, 4, 6))
        pieces.append(Piece.create(PieceType.PAWN, Color.RED, 6, 7))
    state = GameState("desktop_complete", pieces, turn=Color.RED)
    game = Game.from_state(state)
    expected = {_move_key(move) for move in game.rules.legal_moves(game.state)}
    assert _observed_moves(game) == expected
