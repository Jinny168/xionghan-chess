from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from typing import Any

from .model import Color, GameState, Piece, PieceType
from .profiles import get_profile
from .setup import GameSetup


FEN_PIECES = {
    "k": PieceType.KING, "r": PieceType.ROOK, "n": PieceType.HORSE,
    "b": PieceType.ELEPHANT, "a": PieceType.ADVISOR, "c": PieceType.CANNON,
    "p": PieceType.PAWN, "w": PieceType.GUARD, "s": PieceType.ARCHER,
    "l": PieceType.THUNDER, "j": PieceType.ARMOR, "i": PieceType.ASSASSIN,
    "u": PieceType.SHIELD, "x": PieceType.PATROL,
}


def migrate_legacy_game(value: str | dict[str, Any]) -> dict[str, Any]:
    """Convert legacy .fen text or its JSON wrapper to GameDocument v1."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("legacy game file is empty")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"position": text}
    elif isinstance(value, dict):
        parsed = value
    else:
        raise ValueError("legacy game content must be text or an object")

    if parsed.get("formatVersion") == 1:
        return parsed
    position = parsed.get("legacyFen") or parsed.get("position")
    if not isinstance(position, str):
        raise ValueError("legacy game is missing its position")

    state = _state_from_fen(position)
    winner = parsed.get("winner")
    if winner in {"red", "black"}:
        state.winner = Color(winner)
    state.draw = bool(parsed.get("draw", False))
    if bool(parsed.get("game_over")) and not state.winner and not state.draw:
        state.draw = True
    state.result_reason = parsed.get("result_reason") or (
        "legacy_import" if state.finished else None
    )

    profile = get_profile(state.profile_id)
    options = profile.options
    setup = GameSetup.build(profile, options)
    converted_at = datetime.now().isoformat(timespec="seconds")
    return {
        "formatVersion": 1,
        "profileId": profile.id,
        "options": asdict(options),
        "setup": setup.to_dict(),
        "state": state.to_dict(),
        "snapshots": [],
        "savedAt": converted_at,
        "source": "legacy-fen",
        "convertedAt": converted_at,
    }


def _state_from_fen(fen: str) -> GameState:
    parts = fen.strip().split()
    if not parts:
        raise ValueError("legacy FEN is empty")
    rows = parts[0].split("/")
    if len(rows) == 10:
        profile_id, columns = "traditional", 9
    elif len(rows) == 13:
        profile_id, columns = "desktop_complete", 13
    else:
        raise ValueError("legacy FEN must contain 10 or 13 rows")

    pieces: list[Piece] = []
    for row_index, encoded in enumerate(rows):
        column = 0
        index = 0
        while index < len(encoded):
            token = encoded[index]
            if token.isdigit():
                end = index + 1
                while end < len(encoded) and encoded[end].isdigit():
                    end += 1
                column += int(encoded[index:end])
                index = end
                continue
            piece_type = FEN_PIECES.get(token.lower())
            if piece_type is None:
                raise ValueError(f"unsupported legacy FEN piece: {token}")
            if column >= columns:
                raise ValueError("legacy FEN row exceeds board width")
            color = Color.RED if token.isupper() else Color.BLACK
            pieces.append(Piece.create(piece_type, color, row_index, column))
            column += 1
            index += 1
        if column != columns:
            raise ValueError(f"legacy FEN row {row_index + 1} has width {column}, expected {columns}")

    for color in Color:
        if not any(piece.type is PieceType.KING and piece.color is color for piece in pieces):
            raise ValueError(f"legacy FEN is missing the {color.value} king")
    turn = Color.RED if len(parts) < 2 or parts[1].lower() in {"r", "red", "w"} else Color.BLACK
    return GameState(profile_id, pieces, turn=turn)
