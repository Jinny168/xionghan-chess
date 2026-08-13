from __future__ import annotations

from collections.abc import Callable, Mapping

from .game import Game
from .model import Color, Move, Piece, PieceType, Position


Guard = Callable[[], None]


def static_exchange_score(game: Game, move: Move, values: Mapping[PieceType, int],
                          guard: Guard | None = None, max_depth: int = 10) -> int:
    """Evaluate the forced capture sequence on a move's destination square.

    The exchange is played on cloned authoritative states, so screens, pins,
    x-ray attacks, shield protection, promotion and custom captures keep using
    the shared rules engine instead of a chess-specific attack approximation.
    """
    moving = game.state.piece_at(move.source)
    if moving is None:
        return -values[PieceType.KING]
    captured = game.rules.captured_by_move(game.state, move)
    immediate = sum(values[piece.type] for piece in captured)
    immediate += _promotion_gain(moving, move, values)
    state = game.rules.apply_unchecked(game.state, move)
    child = Game.from_state(state, game.options, game.setup)
    return immediate - _best_recapture(child, move.target, values, guard, max_depth)


def _best_recapture(game: Game, target: Position, values: Mapping[PieceType, int],
                    guard: Guard | None, remaining: int) -> int:
    if remaining <= 0 or game.state.piece_at(target) is None:
        return 0
    best = 0
    for move in _captures_to(game, target, guard):
        if guard:
            guard()
        moving = game.state.piece_at(move.source)
        if moving is None:
            continue
        captured = game.rules.captured_by_move(game.state, move)
        immediate = sum(values[piece.type] for piece in captured)
        immediate += _promotion_gain(moving, move, values)
        state = game.rules.apply_unchecked(game.state, move)
        child = Game.from_state(state, game.options, game.setup)
        reply = _best_recapture(child, target, values, guard, remaining - 1)
        best = max(best, immediate - reply)
    return best


def _captures_to(game: Game, target: Position, guard: Guard | None) -> list[Move]:
    victim = game.state.piece_at(target)
    if victim is None or victim.color is game.state.turn:
        return []
    moves: list[Move] = []
    for piece in game.state.pieces:
        if guard:
            guard()
        if piece.color is not game.state.turn:
            continue
        for move in _moves_to_target(game, piece, target):
            if not game.rules.is_legal(game.state, move):
                continue
            if any(captured.id == victim.id
                   for captured in game.rules.captured_by_move(game.state, move)):
                moves.append(move)
    return moves


def _moves_to_target(game: Game, piece: Piece, target: Position) -> list[Move]:
    if (piece.type is PieceType.PAWN and game.options.pawn_promotion
            and target.row == (0 if piece.color is Color.RED else game.profile.rows - 1)):
        promotions = sorted({
            captured.type for captured in game.state.captured[piece.color]
            if captured.type not in {PieceType.PAWN, PieceType.KING}
            and captured.type in game.rules.enabled_piece_types
        }, key=lambda item: item.value)
        if promotions:
            return [Move(piece.position, target, promotion) for promotion in promotions]
    return [Move(piece.position, target)]


def _promotion_gain(piece: Piece, move: Move, values: Mapping[PieceType, int]) -> int:
    if piece.type is PieceType.PAWN and move.promotion is not None:
        return values[move.promotion] - values[PieceType.PAWN]
    return 0
