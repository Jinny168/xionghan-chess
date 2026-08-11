from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterable

from .model import Color, GameState, Move, Piece, PieceType, Position
from .profiles import RuleOptions, RuleProfile


def archer_star_points(profile: RuleProfile) -> frozenset[Position]:
    """Return the reachable endpoints of the weak-archer diagonal lattice."""
    if profile.rows != 13 or profile.cols != 13 or PieceType.ARCHER not in profile.enabled_piece_types:
        return frozenset()
    return frozenset(
        Position(row, col)
        for row in range(0, profile.rows, 3)
        for col in range(0, profile.cols, 3)
        if (row // 3 + col // 3) % 2 == 0
    )


def archer_star_segments(profile: RuleProfile) -> tuple[tuple[Position, Position], ...]:
    """Return each adjacent diagonal segment in the weak-archer lattice once."""
    points = archer_star_points(profile)
    segments: list[tuple[Position, Position]] = []
    for start in sorted(points, key=lambda item: (item.row, item.col)):
        for dr, dc in ((3, 3), (3, -3)):
            end = Position(start.row + dr, start.col + dc)
            if end in points:
                segments.append((start, end))
    return tuple(segments)


class RulesEngine:
    """Authoritative, side-effect free move validation for every delivery target."""

    def __init__(self, profile: RuleProfile, options: RuleOptions | None = None):
        self.profile = profile
        self.options = options or profile.options

    @property
    def enabled_piece_types(self) -> frozenset[PieceType]:
        return frozenset(kind for kind in self.profile.enabled_piece_types
                         if self.options.piece_enabled(kind))

    def inside(self, pos: Position) -> bool:
        return 0 <= pos.row < self.profile.rows and 0 <= pos.col < self.profile.cols

    @property
    def archer_star_points(self) -> frozenset[Position]:
        return archer_star_points(self.profile) if PieceType.ARCHER in self.enabled_piece_types else frozenset()

    @property
    def archer_star_segments(self) -> tuple[tuple[Position, Position], ...]:
        return archer_star_segments(self.profile) if PieceType.ARCHER in self.enabled_piece_types else ()

    def palace(self, color: Color, pos: Position) -> bool:
        if self.profile.rows == 10:
            rows = range(7, 10) if color is Color.RED else range(0, 3)
            cols = range(3, 6)
        else:
            rows = range(9, 12) if color is Color.RED else range(1, 4)
            cols = range(5, 8)
        return pos.row in rows and pos.col in cols

    def enemy_palace(self, color: Color, pos: Position) -> bool:
        return self.palace(color.opponent, pos)

    def get(self, state: GameState, pos: Position) -> Piece | None:
        return state.piece_at(pos)

    def pseudo_legal(self, state: GameState, move: Move) -> bool:
        if not self.inside(move.source) or not self.inside(move.target) or move.source == move.target:
            return False
        piece = self.get(state, move.source)
        if piece is None or piece.color is not state.turn or piece.type not in self.enabled_piece_types:
            return False
        target = self.get(state, move.target)
        if target and (target.color is piece.color or target.type is PieceType.SHIELD):
            return False
        if move.promotion:
            if piece.type is not PieceType.PAWN or not self.options.pawn_promotion:
                return False
            if move.promotion in {PieceType.PAWN, PieceType.KING} or move.promotion not in self.enabled_piece_types:
                return False
            if not any(p.type is move.promotion for p in state.captured[piece.color]):
                return False
        elif piece.type is PieceType.PAWN and self.options.pawn_promotion and \
                move.target.row == (0 if piece.color is Color.RED else self.profile.rows - 1):
            promotable = [p for p in state.captured[piece.color]
                          if p.type not in {PieceType.PAWN, PieceType.KING}
                          and p.type in self.enabled_piece_types]
            if promotable:
                return False
        if target and self._protected_by_enemy_shield(state, target):
            return False

        validators: dict[PieceType, Callable[[GameState, Piece, Move], bool]] = {
            PieceType.ROOK: self._rook, PieceType.HORSE: self._horse,
            PieceType.ELEPHANT: self._elephant, PieceType.ADVISOR: self._advisor,
            PieceType.KING: self._king, PieceType.CANNON: self._cannon,
            PieceType.PAWN: self._pawn, PieceType.GUARD: self._guard,
            PieceType.ARCHER: self._archer, PieceType.THUNDER: self._thunder,
            PieceType.ARMOR: self._armor, PieceType.ASSASSIN: self._assassin,
            PieceType.SHIELD: self._shield, PieceType.PATROL: self._patrol,
        }
        return validators[piece.type](state, piece, move)

    def is_legal(self, state: GameState, move: Move) -> bool:
        if not self.pseudo_legal(state, move):
            return False
        if not self.options.enforce_self_check:
            return True
        next_state = self.apply_unchecked(state, move, switch_turn=False)
        return not self.in_check(next_state, state.turn)

    def legal_moves(self, state: GameState, color: Color | None = None) -> list[Move]:
        color = color or state.turn
        probe = state if state.turn is color else replace(state, turn=color)
        result: list[Move] = []
        for piece in probe.pieces:
            if piece.color is not color:
                continue
            for row in range(self.profile.rows):
                for col in range(self.profile.cols):
                    move = Move(piece.position, Position(row, col))
                    if self.is_legal(probe, move):
                        result.append(move)
        return result

    def captured_by_move(self, state: GameState, move: Move) -> tuple[Piece, ...]:
        """Return enemy pieces removed by a move, including indirect captures."""
        moving = self.get(state, move.source)
        if moving is None:
            return ()
        after_ids = {piece.id for piece in self.apply_unchecked(state, move, switch_turn=False).pieces}
        return tuple(piece for piece in state.pieces
                     if piece.color is not moving.color and piece.id not in after_ids)

    def apply_unchecked(self, state: GameState, move: Move, switch_turn: bool = True) -> GameState:
        clone = state.clone()
        piece = clone.piece_at(move.source)
        if piece is None:
            return clone
        target = clone.piece_at(move.target)
        removed: list[Piece] = []
        if target:
            clone.pieces.remove(target)
            removed.append(target)
        clone.pieces[clone.pieces.index(piece)] = piece.at(move.target)

        if piece.type is PieceType.ARMOR:
            for captured in self._armor_captures(clone, piece.color):
                if captured in clone.pieces:
                    clone.pieces.remove(captured)
                    removed.append(captured)

        if piece.type is PieceType.ASSASSIN:
            dr, dc = move.target.row - move.source.row, move.target.col - move.source.col
            reverse = Position(move.source.row - dr, move.source.col - dc)
            dragged = clone.piece_at(reverse)
            moved_piece = clone.piece_at(move.target)
            if dragged and dragged.color is not piece.color and dragged.type is not PieceType.SHIELD:
                clone.pieces.remove(dragged)
                removed.append(dragged)
                if moved_piece:
                    clone.pieces.remove(moved_piece)

        if move.promotion and piece.type is PieceType.PAWN and self.options.pawn_promotion:
            promoted = clone.piece_at(move.target)
            if promoted:
                clone.pieces[clone.pieces.index(promoted)] = replace(promoted, type=move.promotion)
                dead = next((p for p in clone.captured[piece.color] if p.type is move.promotion), None)
                if dead:
                    clone.captured[piece.color].remove(dead)
        if switch_turn:
            clone.turn = clone.turn.opponent
        return clone

    def in_check(self, state: GameState, color: Color) -> bool:
        king = next((p for p in state.pieces if p.color is color and p.type is PieceType.KING), None)
        if king is None:
            return True
        opponent = replace(state, turn=color.opponent)
        for piece in opponent.pieces:
            if piece.color is color.opponent:
                move = Move(piece.position, king.position)
                if self.pseudo_legal(opponent, move):
                    return True
        return self._kings_facing(state)

    def checkmate(self, state: GameState, color: Color) -> bool:
        return self.in_check(state, color) and not self.legal_moves(state, color)

    def stalemate(self, state: GameState, color: Color) -> bool:
        return not self.in_check(state, color) and not self.legal_moves(state, color)

    def position_key(self, state: GameState) -> str:
        pieces = sorted((p.color.value, p.type.value, p.position.row, p.position.col) for p in state.pieces)
        return f"{state.turn.value}|" + ";".join(f"{c}:{t}:{r}:{k}" for c, t, r, k in pieces)

    def _clear(self, state: GameState, source: Position, target: Position) -> bool:
        dr = (target.row > source.row) - (target.row < source.row)
        dc = (target.col > source.col) - (target.col < source.col)
        row, col = source.row + dr, source.col + dc
        while (row, col) != (target.row, target.col):
            if self.get(state, Position(row, col)):
                return False
            row, col = row + dr, col + dc
        return True

    def _between(self, state: GameState, source: Position, target: Position) -> int:
        dr = (target.row > source.row) - (target.row < source.row)
        dc = (target.col > source.col) - (target.col < source.col)
        row, col, count = source.row + dr, source.col + dc, 0
        while (row, col) != (target.row, target.col):
            count += self.get(state, Position(row, col)) is not None
            row, col = row + dr, col + dc
        return count

    @staticmethod
    def _line(move: Move) -> bool:
        return move.source.row == move.target.row or move.source.col == move.target.col

    @staticmethod
    def _diagonal(move: Move) -> bool:
        return abs(move.target.row - move.source.row) == abs(move.target.col - move.source.col)

    def _rook(self, state: GameState, piece: Piece, move: Move) -> bool:
        return self._line(move) and self._clear(state, move.source, move.target)

    def _horse(self, state: GameState, piece: Piece, move: Move) -> bool:
        dr, dc = move.target.row - move.source.row, move.target.col - move.source.col
        ar, ac = abs(dr), abs(dc)
        if self.options.horse_straight_three and ((ar == 3 and ac == 0) or (ar == 0 and ac == 3)):
            return self._clear(state, move.source, move.target)
        if (ar, ac) not in {(2, 1), (1, 2)}:
            return False
        leg = Position(move.source.row + (dr // 2 if ar == 2 else 0),
                       move.source.col + (dc // 2 if ac == 2 else 0))
        return self.get(state, leg) is None

    def _elephant(self, state: GameState, piece: Piece, move: Move) -> bool:
        dr, dc = move.target.row - move.source.row, move.target.col - move.source.col
        middle = self.profile.rows // 2
        diagonal = abs(dr) == 2 and abs(dc) == 2
        orthogonal = (abs(dr), abs(dc)) in {(2, 0), (0, 2)}
        if not diagonal and not orthogonal:
            return False
        eye = Position(move.source.row + dr // 2, move.source.col + dc // 2)
        if self.get(state, eye):
            return False
        if diagonal:
            if not self.options.elephant_can_cross_river:
                if piece.color is Color.RED and move.target.row < middle:
                    return False
                if piece.color is Color.BLACK and move.target.row > middle:
                    return False
            if self._diagonal_path_pinched(state, move):
                return False
            return True
        in_enemy_territory = (piece.color is Color.RED and move.source.row <= middle) or \
                             (piece.color is Color.BLACK and move.source.row >= middle)
        return self.options.elephant_can_cross_river and \
            self.options.elephant_gain_jump_two_enemy_territory and in_enemy_territory

    def _advisor(self, state: GameState, piece: Piece, move: Move) -> bool:
        dr, dc = abs(move.target.row - move.source.row), abs(move.target.col - move.source.col)
        diagonal, straight = (dr, dc) == (1, 1), dr + dc == 1
        source_in_palace = self.palace(piece.color, move.source)
        target_in_palace = self.palace(piece.color, move.target)
        if source_in_palace:
            return diagonal and (target_in_palace or self.options.advisor_can_leave_palace) and \
                not self._diagonal_path_pinched(state, move)
        if not self.options.advisor_can_leave_palace and not target_in_palace:
            return False
        if diagonal and self._diagonal_path_pinched(state, move):
            return False
        return diagonal or (straight and self.options.advisor_can_leave_palace and
                            self.options.advisor_gain_straight_outside_palace)

    def _king(self, state: GameState, piece: Piece, move: Move) -> bool:
        dr, dc = abs(move.target.row - move.source.row), abs(move.target.col - move.source.col)
        if max(dr, dc) != 1:
            return False
        source_in_palace = self.palace(piece.color, move.source)
        target_in_palace = self.palace(piece.color, move.target)
        if not self.options.king_can_leave_palace and not target_in_palace:
            return False
        if dr + dc == 1:
            return True
        if source_in_palace and not self.options.king_diagonal_in_palace:
            return False
        if not source_in_palace and self.options.king_lose_diagonal_outside_palace:
            return False
        return not self._diagonal_path_pinched(state, move)

    def _cannon(self, state: GameState, piece: Piece, move: Move) -> bool:
        if not self._line(move):
            return False
        target = self.get(state, move.target)
        return self._between(state, move.source, move.target) == (1 if target else 0)

    def _pawn(self, state: GameState, piece: Piece, move: Move) -> bool:
        dr, dc = move.target.row - move.source.row, move.target.col - move.source.col
        forward = -1 if piece.color is Color.RED else 1
        middle = self.profile.rows // 2
        crossed = move.source.row <= middle if piece.color is Color.RED else move.source.row >= middle
        enemy_base = move.source.row == (0 if piece.color is Color.RED else self.profile.rows - 1)
        if enemy_base and self.options.pawn_full_movement_at_base:
            return abs(dr) + abs(dc) == 1
        distance = abs(dr)
        distance_to_enemy_territory = (
            move.source.row - middle + 1 if piece.color is Color.RED
            else middle - move.source.row + 1
        )
        if self.options.pawn_fast_move_before_enemy_territory and dc == 0 and \
                dr == forward * distance and 1 < distance <= distance_to_enemy_territory:
            if self.get(state, move.target):
                return False
            return all(
                self.get(state, Position(move.source.row + forward * step, move.source.col)) is None
                for step in range(1, distance)
            )
        if dr == forward and dc == 0:
            return True
        if crossed and dr == 0 and abs(dc) == 1:
            return True
        return enemy_base and self.options.pawn_backward_at_base and dr == -forward and dc == 0

    def _jump_over_one(self, state: GameState, move: Move, diagonal: bool) -> bool:
        if not (self._line(move) or (diagonal and self._diagonal(move))):
            return False
        return self.get(state, move.target) is None and self._between(state, move.source, move.target) == 1

    def _guard(self, state: GameState, piece: Piece, move: Move) -> bool:
        return self._jump_over_one(state, move, True) and \
            (not self._diagonal(move) or not self._diagonal_path_pinched(state, move))

    def _archer(self, state: GameState, piece: Piece, move: Move) -> bool:
        if not self._diagonal(move):
            return False
        dr = move.target.row - move.source.row
        dc = move.target.col - move.source.col
        distance = abs(dr)
        step_row = 1 if dr > 0 else -1
        step_col = 1 if dc > 0 else -1
        target = self.get(state, move.target)

        if self.options.archer_enhanced_mode:
            if distance > 3:
                return False
            if target and move.source not in self.archer_star_points:
                return False
        else:
            star_distance = self._nearest_archer_star_distance(
                move.source, step_row, step_col
            )
            if star_distance == 0 or distance > star_distance:
                return False

        if self._diagonal_path_pinched(state, move):
            return False
        for step in range(1, distance):
            position = Position(move.source.row + step * step_row,
                                move.source.col + step * step_col)
            if self.get(state, position):
                return False
        return True

    def _nearest_archer_star_distance(self, source: Position,
                                      step_row: int, step_col: int) -> int:
        for distance in range(1, max(self.profile.rows, self.profile.cols)):
            position = Position(source.row + distance * step_row,
                                source.col + distance * step_col)
            if not self.inside(position):
                return 0
            if position in self.archer_star_points:
                return distance
        return 0

    @staticmethod
    def _position_on_segment(position: Position, start: Position, end: Position) -> bool:
        return min(start.row, end.row) <= position.row <= max(start.row, end.row) and \
            min(start.col, end.col) <= position.col <= max(start.col, end.col) and \
            abs(position.row - start.row) == abs(position.col - start.col)

    def _diagonal_pinched(self, state: GameState, position: Position,
                          step_row: int, step_col: int) -> bool:
        side_a = Position(position.row, position.col + step_col)
        side_b = Position(position.row + step_row, position.col)
        return self.inside(side_a) and self.inside(side_b) and \
            self.get(state, side_a) is not None and self.get(state, side_b) is not None

    def _diagonal_path_pinched(self, state: GameState, move: Move) -> bool:
        if not self._diagonal(move):
            return False
        step_row = 1 if move.target.row > move.source.row else -1
        step_col = 1 if move.target.col > move.source.col else -1
        distance = abs(move.target.row - move.source.row)
        return any(
            self._diagonal_pinched(
                state,
                Position(move.source.row + step * step_row,
                         move.source.col + step * step_col),
                step_row,
                step_col,
            )
            for step in range(distance)
        )

    def _thunder(self, state: GameState, piece: Piece, move: Move) -> bool:
        if not (self._line(move) or self._diagonal(move)):
            return False
        target = self.get(state, move.target)
        if target:
            return max(abs(move.target.row - move.source.row), abs(move.target.col - move.source.col)) == 1 and \
                self._isolated(state, target) and \
                (not self._diagonal(move) or not self._diagonal_path_pinched(state, move))
        return self._clear(state, move.source, move.target) and \
            (not self._diagonal(move) or not self._diagonal_path_pinched(state, move))

    def _armor(self, state: GameState, piece: Piece, move: Move) -> bool:
        return self.get(state, move.target) is None and self._rook(state, piece, move)

    def _assassin(self, state: GameState, piece: Piece, move: Move) -> bool:
        return self.get(state, move.target) is None and self._rook(state, piece, move)

    def _shield(self, state: GameState, piece: Piece, move: Move) -> bool:
        return self._jump_over_one(state, move, False)

    def _patrol(self, state: GameState, piece: Piece, move: Move) -> bool:
        if move.source.row not in {5, 7} or move.target.row != move.source.row:
            return False
        distance = abs(move.target.col - move.source.col)
        if distance == 0 or distance % 2 or not self._clear(state, move.source, move.target):
            return False
        return self.get(state, move.target) is None or distance == 2

    def _isolated(self, state: GameState, target: Piece) -> bool:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            other = self.get(state, Position(target.position.row + dr, target.position.col + dc))
            if other and other.color is target.color:
                return False
        return True

    def _protected_by_enemy_shield(self, state: GameState, target: Piece) -> bool:
        return any(p.type is PieceType.SHIELD and p.color is target.color and
                   max(abs(p.position.row - target.position.row), abs(p.position.col - target.position.col)) == 1
                   for p in state.pieces)

    def _armor_captures(self, state: GameState, color: Color) -> list[Piece]:
        captures: dict[str, Piece] = {}
        directions = ((0, 1), (1, 0), (1, 1), (1, -1))
        for row in range(self.profile.rows):
            for col in range(self.profile.cols):
                for dr, dc in directions:
                    group = [self.get(state, Position(row + i * dr, col + i * dc)) for i in range(3)]
                    if any(p is None for p in group):
                        continue
                    pieces = [p for p in group if p is not None]
                    allies = [p for p in pieces if p.color is color]
                    enemies = [p for p in pieces if p.color is not color]
                    if len(allies) != 2 or len(enemies) != 1 or not any(p.type is PieceType.ARMOR for p in allies):
                        continue
                    if any(p.type is PieceType.SHIELD for p in allies):
                        continue
                    if any(self._adjacent_enemy_shield(state, p) for p in allies):
                        continue
                    if enemies[0].type is not PieceType.SHIELD:
                        captures[enemies[0].id] = enemies[0]
        return list(captures.values())

    def _adjacent_enemy_shield(self, state: GameState, piece: Piece) -> bool:
        return any(p.type is PieceType.SHIELD and p.color is not piece.color and
                   max(abs(p.position.row - piece.position.row), abs(p.position.col - piece.position.col)) == 1
                   for p in state.pieces)

    def _kings_facing(self, state: GameState) -> bool:
        kings = [p for p in state.pieces if p.type is PieceType.KING]
        return len(kings) == 2 and kings[0].position.col == kings[1].position.col and \
            self._clear(state, kings[0].position, kings[1].position)
