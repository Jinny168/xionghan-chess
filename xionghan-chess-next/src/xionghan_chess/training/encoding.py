from __future__ import annotations

from ..core.model import Color, GameState, Move, PieceType


BOARD_SIZE = 13
SQUARES = BOARD_SIZE * BOARD_SIZE
PIECE_TYPES = tuple(PieceType)
CHANNELS = len(PIECE_TYPES) * 2 + 1
FEATURE_SIZE = CHANNELS * SQUARES
ACTION_SIZE = SQUARES * SQUARES


def action_index(move: Move) -> int:
    """Stable v1 action id. Promotion is learned from legal-move masking."""
    source = move.source.row * BOARD_SIZE + move.source.col
    target = move.target.row * BOARD_SIZE + move.target.col
    return source * SQUARES + target


def encode_state(state: GameState) -> list[float]:
    """Encode any 10x9/13x13 profile into a fixed 29x13x13 tensor."""
    values = [0.0] * FEATURE_SIZE
    type_index = {kind: index for index, kind in enumerate(PIECE_TYPES)}
    for item in state.pieces:
        color_offset = 0 if item.color is Color.RED else len(PIECE_TYPES)
        channel = color_offset + type_index[item.type]
        values[channel * SQUARES + item.position.row * BOARD_SIZE + item.position.col] = 1.0
    turn_offset = (CHANNELS - 1) * SQUARES
    turn_value = 1.0 if state.turn is Color.RED else -1.0
    values[turn_offset:turn_offset + SQUARES] = [turn_value] * SQUARES
    return values
