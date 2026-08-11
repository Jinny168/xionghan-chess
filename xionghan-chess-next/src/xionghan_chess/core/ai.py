from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import math
import os
import random
import threading
import time

from .game import Game
from .model import Color, Move, PieceType, Position


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
    quiescence_depth: int
    candidate_count: int
    branch_limit: int
    root_limit: int


CONFIGS = {
    Difficulty.BEGINNER: SearchConfig(2, 0.45, 0.32, 2, 4, 2, 4),
    Difficulty.EASY: SearchConfig(3, 1.2, 0.12, 3, 3, 4, 5),
    Difficulty.MEDIUM: SearchConfig(4, 3.5, 0.02, 4, 2, 8, 16),
    Difficulty.HARD: SearchConfig(6, 9.0, 0.0, 5, 1, 14, 28),
}

VALUES = {
    PieceType.KING: 50_000, PieceType.ROOK: 900, PieceType.CANNON: 500,
    PieceType.HORSE: 450, PieceType.ELEPHANT: 260, PieceType.ADVISOR: 240,
    PieceType.PAWN: 120, PieceType.GUARD: 520, PieceType.ARCHER: 480,
    PieceType.THUNDER: 650, PieceType.ARMOR: 420, PieceType.ASSASSIN: 430,
    PieceType.SHIELD: 600, PieceType.PATROL: 360,
}

MOBILE_PIECES = {
    PieceType.ROOK, PieceType.HORSE, PieceType.CANNON, PieceType.GUARD,
    PieceType.ARCHER, PieceType.THUNDER, PieceType.ARMOR, PieceType.ASSASSIN,
    PieceType.SHIELD, PieceType.PATROL,
}

CENTRAL_WEIGHTS = {
    PieceType.KING: -1.0, PieceType.ROOK: 1.4, PieceType.CANNON: 1.8,
    PieceType.HORSE: 2.8, PieceType.ELEPHANT: .8, PieceType.ADVISOR: .5,
    PieceType.PAWN: 1.4, PieceType.GUARD: 1.7, PieceType.ARCHER: 1.8,
    PieceType.THUNDER: 2.4, PieceType.ARMOR: 1.8, PieceType.ASSASSIN: 2.2,
    PieceType.SHIELD: 1.0, PieceType.PATROL: 1.2,
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
        self.killers: dict[int, list[Move]] = {}
        self.evaluation_cache: dict[tuple[str, Color], float] = {}
        self.principal_move: Move | None = None
        self.root_scores: list[tuple[float, Move]] = []
        self.completed_depth = 0
        self.quiescence_depth = CONFIGS[self.difficulty].quiescence_depth

    def choose_move(self, game: Game, cancel: threading.Event | None = None) -> Move | None:
        cfg = CONFIGS[self.difficulty]
        time_scale = max(0.1, float(os.getenv("AI_TIME_SCALE", "1.0")))
        deadline = time.monotonic() + cfg.time_limit * time_scale
        legal = game.rules.legal_moves(game.state)
        if not legal:
            return None
        initial_order = self._order(game, legal)
        initial_order = sorted(initial_order, key=lambda move: self._root_bias(game, move) < -100)
        best = initial_order[0]
        search_moves = initial_order[:cfg.root_limit]
        self.transposition.clear()
        self.history.clear()
        self.killers.clear()
        self.evaluation_cache.clear()
        self.principal_move = None
        self.root_scores = []
        self.completed_depth = 0
        try:
            for depth in range(1, cfg.depth + 1):
                score, candidate = self._root(game, search_moves, depth, deadline, cancel)
                if candidate is not None:
                    best = candidate
                    self.principal_move = candidate
                    self.completed_depth = depth
                    search_moves = [move for _, move in self.root_scores[:cfg.root_limit]]
                if abs(score) >= VALUES[PieceType.KING]:
                    break
        except SearchTimeout:
            pass
        if cfg.randomness and self.root_scores and self.random.random() < cfg.randomness:
            best_score = self.root_scores[0][0]
            candidates = [move for score, move in self.root_scores[:cfg.candidate_count]
                          if best_score - score <= 90]
            if len(candidates) > 1:
                return self.random.choice(candidates)
        return best

    def _root(self, game: Game, moves: list[Move], depth: int, deadline: float,
              cancel: threading.Event | None) -> tuple[float, Move | None]:
        ordered = self._order(game, moves, self.principal_move)
        ordered = sorted(ordered, key=lambda move: self._root_bias(game, move) < -100)
        alpha, beta, best_move = -math.inf, math.inf, None
        scores: list[tuple[float, Move]] = []
        for move in ordered:
            self._guard(deadline, cancel)
            child = Game.from_state(game.rules.apply_unchecked(game.state, move), game.options)
            score = -self._search(child, depth - 1, -beta, -alpha, deadline, cancel, 1)
            scores.append((score, move))
            if score > alpha:
                alpha, best_move = score, move
        self.root_scores = sorted(scores, key=lambda item: item[0], reverse=True)
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

        if depth <= 0:
            return self._quiescence(game, alpha, beta, deadline, cancel, ply,
                                    self.quiescence_depth)
        moves = game.rules.legal_moves(game.state)
        if not moves:
            return -VALUES[PieceType.KING] + ply

        value = -math.inf
        best_move = None
        ordered = self._order(game, moves, entry.best_move if entry else None, ply)
        if not game.rules.in_check(game.state, game.state.turn):
            ordered = ordered[:CONFIGS[self.difficulty].branch_limit]
        for move in ordered:
            self._guard(deadline, cancel)
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
                    killers = self.killers.setdefault(ply, [])
                    if move not in killers:
                        killers.insert(0, move)
                        del killers[2:]
                break

        bound = Bound.EXACT
        if value <= original_alpha:
            bound = Bound.UPPER
        elif value >= original_beta:
            bound = Bound.LOWER
        previous = self.transposition.get(key)
        if previous is None or depth >= previous.depth:
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

        moves = legal if legal is not None else (
            game.rules.legal_moves(game.state) if in_check else self._tactical_moves(game, deadline, cancel)
        )
        if in_check and not moves:
            return -VALUES[PieceType.KING] + ply
        tactical = moves if in_check else [
            move for move in moves
            if move.promotion is not None or self._capture_value(game, move) > 0
        ]
        for move in self._order(game, tactical, ply=ply):
            self._guard(deadline, cancel)
            child = Game.from_state(game.rules.apply_unchecked(game.state, move), game.options)
            score = -self._quiescence(child, -beta, -alpha, deadline, cancel,
                                      ply + 1, remaining - 1)
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha

    def _tactical_moves(self, game: Game, deadline: float,
                        cancel: threading.Event | None) -> list[Move]:
        state = game.state
        enemies = [piece for piece in state.pieces if piece.color is state.turn.opponent]
        tactical: list[Move] = []
        seen: set[Move] = set()
        for moving in state.pieces:
            self._guard(deadline, cancel)
            if moving.color is not state.turn:
                continue
            for target in enemies:
                if not self._attack_geometry(moving, target):
                    continue
                move = Move(moving.position, target.position)
                if move not in seen and game.rules.is_legal(state, move):
                    tactical.append(move)
                    seen.add(move)
            if moving.type is PieceType.PAWN and game.options.pawn_promotion:
                final_row = 0 if moving.color is Color.RED else game.profile.rows - 1
                promotion_types = {piece.type for piece in state.captured[moving.color]
                                   if piece.type not in {PieceType.PAWN, PieceType.KING}}
                for col in range(game.profile.cols):
                    for promotion in promotion_types:
                        move = Move(moving.position, Position(final_row, col), promotion)
                        if move not in seen and game.rules.is_legal(state, move):
                            tactical.append(move)
                            seen.add(move)
            if moving.type in {PieceType.ARMOR, PieceType.ASSASSIN}:
                for row in range(game.profile.rows):
                    self._guard(deadline, cancel)
                    for col in range(game.profile.cols):
                        move = Move(moving.position, Position(row, col))
                        if move in seen or not game.rules.is_legal(state, move):
                            continue
                        if self._capture_value(game, move):
                            tactical.append(move)
                            seen.add(move)
        return tactical

    def _evaluate(self, game: Game, color: Color) -> float:
        cache_key = (game.rules.position_key(game.state), color)
        cached = self.evaluation_cache.get(cache_key)
        if cached is not None:
            return cached
        score = 0.0
        center_r, center_c = (game.profile.rows - 1) / 2, (game.profile.cols - 1) / 2
        for piece in game.state.pieces:
            sign = 1 if piece.color is color else -1
            central = max(0, min(game.profile.rows, game.profile.cols) / 2 -
                          abs(piece.position.row - center_r) - abs(piece.position.col - center_c))
            positional = central * CENTRAL_WEIGHTS[piece.type]
            if piece.type is PieceType.PAWN:
                advance = (piece.position.row if piece.color is Color.BLACK
                           else game.profile.rows - 1 - piece.position.row)
                positional += advance * 5
                if advance > (game.profile.rows - 1) / 2:
                    positional += 22
            elif piece.type in MOBILE_PIECES and self._is_developed(game, piece):
                positional += 13
            if piece.type is PieceType.KING:
                positional += 32 if game.rules.palace(piece.color, piece.position) else -18
                positional += self._king_cover(game, piece.color) * 7
            score += sign * (VALUES[piece.type] + positional)

        own_attacks, own_pressure = self._activity_score(game, color)
        enemy_attacks, enemy_pressure = self._activity_score(game, color.opponent)
        score += (own_attacks - enemy_attacks) * 5
        score += (own_pressure - enemy_pressure) * .18
        if game.rules.in_check(game.state, color.opponent):
            score += 150
        if game.rules.in_check(game.state, color):
            score -= 210
        if len(self.evaluation_cache) >= 50_000:
            self.evaluation_cache.clear()
        self.evaluation_cache[cache_key] = score
        return score

    def _activity_score(self, game: Game, color: Color) -> tuple[int, float]:
        probe = game.state if game.state.turn is color else replace(game.state, turn=color)
        attacks = 0
        pressure = 0.0
        allies = [piece for piece in probe.pieces if piece.color is color]
        enemies = [piece for piece in probe.pieces if piece.color is color.opponent]
        for moving in allies:
            for target in enemies:
                if not self._attack_geometry(moving, target):
                    continue
                if not game.rules.pseudo_legal(probe, Move(moving.position, target.position)):
                    continue
                attacks += 1
                capture = VALUES[target.type]
                attacker = VALUES[moving.type]
                pressure += capture + max(0, capture - attacker) * .35
        return attacks, pressure

    @staticmethod
    def _attack_geometry(moving, target) -> bool:
        dr = abs(target.position.row - moving.position.row)
        dc = abs(target.position.col - moving.position.col)
        if moving.type in {PieceType.ROOK, PieceType.CANNON}:
            return dr == 0 or dc == 0
        if moving.type is PieceType.HORSE:
            return (dr, dc) in {(2, 1), (1, 2), (3, 0), (0, 3)}
        if moving.type is PieceType.ELEPHANT:
            return (dr, dc) in {(2, 2), (2, 0), (0, 2)}
        if moving.type in {PieceType.ADVISOR, PieceType.KING}:
            return max(dr, dc) == 1
        if moving.type is PieceType.PAWN:
            return dr + dc == 1
        if moving.type is PieceType.ARCHER:
            return dr == dc
        if moving.type is PieceType.THUNDER:
            return dr == 0 or dc == 0 or dr == dc
        if moving.type is PieceType.PATROL:
            return dr == 0 and dc == 2
        return False

    def _is_developed(self, game: Game, piece) -> bool:
        return not any(spec.color is piece.color and spec.type is piece.type and
                       spec.row == piece.position.row and spec.col == piece.position.col
                       for spec in game.profile.pieces)

    @staticmethod
    def _king_cover(game: Game, color: Color) -> int:
        king = next((piece for piece in game.state.pieces
                     if piece.color is color and piece.type is PieceType.KING), None)
        if king is None:
            return 0
        return sum(
            piece.color is color and piece is not king and
            abs(piece.position.row - king.position.row) <= 1 and
            abs(piece.position.col - king.position.col) <= 1
            for piece in game.state.pieces
        )

    def _root_bias(self, game: Game, move: Move) -> float:
        bias = 0.0
        moving = game.state.piece_at(move.source)
        if moving is None:
            return bias
        previous = next((record for record in reversed(game.state.history)
                         if record.color is moving.color), None)
        if previous and previous.move.source == move.target and previous.move.target == move.source:
            bias -= 150
            if not self._capture_value(game, move):
                bias -= 45
        if self._is_developed(game, moving):
            initial_target = any(spec.color is moving.color and spec.type is moving.type and
                                 spec.row == move.target.row and spec.col == move.target.col
                                 for spec in game.profile.pieces)
            if initial_target:
                bias -= 28
        return bias

    def _capture_value(self, game: Game, move: Move) -> int:
        return sum(VALUES[piece.type] for piece in game.rules.captured_by_move(game.state, move))

    def _order(self, game: Game, moves: list[Move], preferred: Move | None = None,
               ply: int = 0) -> list[Move]:
        def score(move: Move) -> int:
            if preferred == move:
                return 10_000_000
            moving = game.state.piece_at(move.source)
            capture = self._capture_value(game, move)
            value = capture * 16 - (VALUES[moving.type] if moving and capture else 0)
            if moving:
                value += self.history.get((moving.type, move.target.row, move.target.col), 0)
                center_r = (game.profile.rows - 1) / 2
                center_c = (game.profile.cols - 1) / 2
                source_distance = abs(move.source.row - center_r) + abs(move.source.col - center_c)
                target_distance = abs(move.target.row - center_r) + abs(move.target.col - center_c)
                value += int((source_distance - target_distance) * CENTRAL_WEIGHTS[moving.type] * 18)
                if moving.type is PieceType.PAWN:
                    forward = -1 if moving.color is Color.RED else 1
                    value += (move.target.row - move.source.row) * forward * 32
                if not self._is_developed(game, moving):
                    leaves_initial = not any(
                        spec.color is moving.color and spec.type is moving.type and
                        spec.row == move.target.row and spec.col == move.target.col
                        for spec in game.profile.pieces
                    )
                    if leaves_initial and moving.type in MOBILE_PIECES:
                        value += 180
            killers = self.killers.get(ply, [])
            if move in killers:
                value += 4_000 - killers.index(move) * 500
            child = game.rules.apply_unchecked(game.state, move)
            if game.rules.in_check(child, child.turn):
                value += 900
            return value

        return sorted(moves, key=score, reverse=True)

    @staticmethod
    def _guard(deadline: float, cancel: threading.Event | None) -> None:
        if time.monotonic() >= deadline or (cancel and cancel.is_set()):
            raise SearchTimeout
