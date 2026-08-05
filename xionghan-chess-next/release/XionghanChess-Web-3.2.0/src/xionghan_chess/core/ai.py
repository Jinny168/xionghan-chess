from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import os
import random
import threading
import time

from .game import Game
from .model import Color, Move, PieceType


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass(frozen=True, slots=True)
class SearchConfig:
    depth: int
    time_limit: float
    randomness: float


CONFIGS = {
    Difficulty.BEGINNER: SearchConfig(1, 0.25, 0.45),
    Difficulty.EASY: SearchConfig(2, 0.8, 0.18),
    Difficulty.MEDIUM: SearchConfig(3, 2.5, 0.05),
    Difficulty.HARD: SearchConfig(5, 7.0, 0.0),
}

VALUES = {
    PieceType.KING: 50_000, PieceType.ROOK: 900, PieceType.CANNON: 500,
    PieceType.HORSE: 450, PieceType.ELEPHANT: 260, PieceType.ADVISOR: 240,
    PieceType.PAWN: 120, PieceType.GUARD: 520, PieceType.ARCHER: 480,
    PieceType.THUNDER: 650, PieceType.ARMOR: 420, PieceType.ASSASSIN: 430,
    PieceType.SHIELD: 600, PieceType.PATROL: 360,
}


class SearchTimeout(Exception):
    pass


class Bound(StrEnum):
    EXACT = "exact"
    LOWER = "lower"
    UPPER = "upper"


@dataclass(frozen=True, slots=True)
class TTEntry:
    depth: int
    score: float
    bound: Bound
    best_move: Move | None


class ChessAI:
    def __init__(self, difficulty: Difficulty | str = Difficulty.MEDIUM, seed: int | None = None):
        self.difficulty = Difficulty(difficulty)
        self.random = random.Random(seed)
        self.transposition: dict[str, TTEntry] = {}
        self.history: dict[tuple[PieceType, int, int], int] = {}
        self.principal_move: Move | None = None

    def choose_move(self, game: Game, cancel: threading.Event | None = None) -> Move | None:
        cfg = CONFIGS[self.difficulty]
        time_scale = max(0.1, float(os.getenv("AI_TIME_SCALE", "1.0")))
        deadline = time.monotonic() + cfg.time_limit * time_scale
        legal = game.rules.legal_moves(game.state)
        if not legal:
            return None
        best = legal[0]
        self.transposition.clear()
        self.history.clear()
        self.principal_move = None
        try:
            for depth in range(1, cfg.depth + 1):
                score, candidate = self._root(game, legal, depth, deadline, cancel)
                if candidate is not None:
                    best = candidate
                    self.principal_move = candidate
                if abs(score) >= VALUES[PieceType.KING]:
                    break
        except SearchTimeout:
            pass
        if cfg.randomness and self.random.random() < cfg.randomness:
            candidates = legal[:]
            self.random.shuffle(candidates)
            return candidates[0]
        return best

    def _root(self, game: Game, moves: list[Move], depth: int, deadline: float,
              cancel: threading.Event | None) -> tuple[float, Move | None]:
        ordered = self._order(game, moves, self.principal_move)
        alpha, beta, best_move = -math.inf, math.inf, None
        for move in ordered:
            self._guard(deadline, cancel)
            child = Game.from_state(game.rules.apply_unchecked(game.state, move), game.options)
            score = -self._search(child, depth - 1, -beta, -alpha, deadline, cancel, 1)
            if score > alpha:
                alpha, best_move = score, move
        return alpha, best_move

    def _search(self, game: Game, depth: int, alpha: float, beta: float, deadline: float,
                cancel: threading.Event | None, ply: int) -> float:
        self._guard(deadline, cancel)
        key = game.rules.position_key(game.state)
        original_alpha = alpha
        original_beta = beta
        entry = self.transposition.get(key)
        if entry and entry.depth >= depth:
            if entry.bound is Bound.EXACT:
                return entry.score
            if entry.bound is Bound.LOWER:
                alpha = max(alpha, entry.score)
            else:
                beta = min(beta, entry.score)
            if alpha >= beta:
                return entry.score

        moves = game.rules.legal_moves(game.state)
        if not moves:
            return -VALUES[PieceType.KING] + ply
        if depth <= 0:
            return self._quiescence(game, alpha, beta, deadline, cancel, ply, 3, moves)

        value = -math.inf
        best_move = None
        for move in self._order(game, moves, entry.best_move if entry else None):
            child = Game.from_state(game.rules.apply_unchecked(game.state, move), game.options)
            score = -self._search(child, depth - 1, -beta, -alpha, deadline, cancel, ply + 1)
            if score > value:
                value, best_move = score, move
            alpha = max(alpha, value)
            if alpha >= beta:
                moving = game.state.piece_at(move.source)
                if moving and game.state.piece_at(move.target) is None:
                    history_key = (moving.type, move.target.row, move.target.col)
                    self.history[history_key] = self.history.get(history_key, 0) + depth * depth
                break

        bound = Bound.EXACT
        if value <= original_alpha:
            bound = Bound.UPPER
        elif value >= original_beta:
            bound = Bound.LOWER
        self.transposition[key] = TTEntry(depth, value, bound, best_move)
        return value

    def _quiescence(self, game: Game, alpha: float, beta: float, deadline: float,
                    cancel: threading.Event | None, ply: int, remaining: int,
                    legal: list[Move] | None = None) -> float:
        self._guard(deadline, cancel)
        in_check = game.rules.in_check(game.state, game.state.turn)
        stand_pat = self._evaluate(game, game.state.turn)
        if remaining <= 0:
            return stand_pat
        if not in_check:
            if stand_pat >= beta:
                return beta
            alpha = max(alpha, stand_pat)

        moves = legal if legal is not None else game.rules.legal_moves(game.state)
        if in_check and not moves:
            return -VALUES[PieceType.KING] + ply
        tactical = moves if in_check else [move for move in moves if self._capture_value(game, move) > 0]
        for move in self._order(game, tactical):
            child = Game.from_state(game.rules.apply_unchecked(game.state, move), game.options)
            score = -self._quiescence(child, -beta, -alpha, deadline, cancel,
                                      ply + 1, remaining - 1)
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha

    def _evaluate(self, game: Game, color: Color) -> float:
        score = 0.0
        center_r, center_c = (game.profile.rows - 1) / 2, (game.profile.cols - 1) / 2
        for piece in game.state.pieces:
            sign = 1 if piece.color is color else -1
            central = max(0, 8 - abs(piece.position.row - center_r) - abs(piece.position.col - center_c))
            score += sign * (VALUES[piece.type] + central * 2)
            if piece.type is PieceType.PAWN:
                advance = (piece.position.row if piece.color is Color.BLACK
                           else game.profile.rows - 1 - piece.position.row)
                score += sign * advance * 3
        if game.rules.in_check(game.state, color.opponent):
            score += 80
        if game.rules.in_check(game.state, color):
            score -= 100
        return score

    def _capture_value(self, game: Game, move: Move) -> int:
        return sum(VALUES[piece.type] for piece in game.rules.captured_by_move(game.state, move))

    def _order(self, game: Game, moves: list[Move], preferred: Move | None = None) -> list[Move]:
        def score(move: Move) -> int:
            if preferred == move:
                return 10_000_000
            moving = game.state.piece_at(move.source)
            capture = self._capture_value(game, move)
            value = capture * 16 - (VALUES[moving.type] if moving and capture else 0)
            if moving:
                value += self.history.get((moving.type, move.target.row, move.target.col), 0)
            child = game.rules.apply_unchecked(game.state, move)
            if game.rules.in_check(child, child.turn):
                value += 8_000
            return value

        return sorted(moves, key=score, reverse=True)

    @staticmethod
    def _guard(deadline: float, cancel: threading.Event | None) -> None:
        if time.monotonic() >= deadline or (cancel and cancel.is_set()):
            raise SearchTimeout
