from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Callable, Iterable, Iterator

from .model import Color, GameState, Move, Piece, PieceType, Position
from .profiles import PATROL_HOME_ROW, RuleOptions, RuleProfile, XIONGHAN_ROWS


# The patrol is confined to its own starting rank: Black's home rank and Red's
# mirror image of it. Mirroring matches xionghan_side(), so PATROL_HOME_ROW and
# XIONGHAN_ROWS - 1 - PATROL_HOME_ROW are the only two ranks it may occupy.
# Profiles without PieceType.PATROL never place one, so this set is unreachable
# on the 10x9 traditional board.
PATROL_HOME_ROWS = frozenset({PATROL_HOME_ROW, XIONGHAN_ROWS - 1 - PATROL_HOME_ROW})


class CaptureKind(StrEnum):
    """How a move takes an enemy piece off the board."""
    DIRECT = "direct"                        # the landing square is the victim's square
    ARMOR_LINE = "armor_line"                # armor completes an allied/enemy/allied line
    ASSASSIN_DRAG = "assassin_drag"          # assassin drags the enemy behind its origin
    PROMOTION_CONSUME = "promotion_consume"  # reserved; never emitted by capturable_squares


@dataclass(frozen=True, slots=True)
class Removal:
    """A single enemy piece removed by a move, attributed to the move's squares."""
    kind: CaptureKind
    victim_id: str
    victim_type: PieceType
    victim_color: Color
    victim_position: Position
    origin: Position
    landing: Position


@dataclass(frozen=True, slots=True)
class CaptureSpec:
    """Every way the piece standing on `position` can be captured."""
    position: Position
    removals: tuple[Removal, ...]


def _removal_order(removal: Removal) -> tuple[str, int, int, int, int]:
    return (removal.kind.value, removal.origin.row, removal.origin.col,
            removal.landing.row, removal.landing.col)


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


# Bumped whenever the `position_key` string format changes. `core/storage.py`
# stamps it into every saved document, so a load can tell whether a repetition
# ledger was written in the *current* format and re-derive it if not (see
# `game_from_document`). Version 2 is "the key that includes the capture pool".
POSITION_KEY_VERSION = 2


def pool_signature(state: GameState) -> str:
    """The pool half of a `position_key`, colour-tagged and sorted.

    A capture pool is game state, not bookkeeping: it fixes which promotions are
    legal (`pseudo_legal`'s pawn-promotion gate below) and how many pawns may be
    revived (`game.py::resurrect_pawn`). Two states sharing a board and side to
    move but holding different pools are therefore *different* positions, so the
    pool is a first-class part of the repetition key -- not an AI-only cache
    extra.
    """
    return ",".join(sorted(f"{color.value}:{piece.type.value}"
                           for color in Color for piece in state.captured[color]))


class RulesEngine:
    """Authoritative, side-effect free move validation for every delivery target."""

    def __init__(self, profile: RuleProfile, options: RuleOptions | None = None):
        self.profile = profile
        self.options = options or profile.options
        # 预计算：`pseudo_legal` 每生成一个着法都要读这个属性（实测 46k 次/5s），
        # 每次重建 frozenset 要付 14 次 `piece_enabled` 的 getattr，累计 1.09s。
        # 安全性：`options` 只在构造时赋值，全仓没有原地修改（改规则会新建引擎）。
        self._enabled_piece_types = frozenset(
            kind for kind in self.profile.enabled_piece_types
            if self.options.piece_enabled(kind))

    @property
    def enabled_piece_types(self) -> frozenset[PieceType]:
        return self._enabled_piece_types

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
        # 楯不再绝对免疫：它可以被吃，只有「四正相邻的同阵营楯」能保护它
        # （保护判定见 `_protected_by_enemy_shield`）。
        # 尉的照面钉住：与敌方尉同一横/竖线、中间无子，且自己是沿线遇到的第一个子 → 不能动。
        # 两尉互照 → 双方都被钉住（各自由对方的尉钉）。
        if self._pinned_by_guard(state, piece):
            return False
        if target and target.color is piece.color:
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
            # Only non-emptiness is needed here, so ask the set directly -- this
            # gate is the one promotion branch that runs on the pseudo_legal hot
            # path, and `promotable_types` skips `promotion_types`' sort.
            if self.promotable_types(state, piece.color):
                return False
        if target and self._protected_by_enemy_shield(state, target):
            return False

        # Every validator shares the (state, piece, move) signature so this table
        # stays homogeneous; a validator that does not need `piece` (rook, horse,
        # cannon, guard, archer, thunder, shield, patrol) simply ignores it.
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

    def _iter_legal(self, probe: GameState, color: Color) -> Iterator[Move]:
        """枚举 `color` 的全部合法着法（`legal_moves` 与 `has_any_legal_move` 的唯一来源）。"""
        for piece in probe.pieces:
            if piece.color is not color:
                continue
            for row in range(self.profile.rows):
                for col in range(self.profile.cols):
                    target = Position(row, col)
                    promotions: list[PieceType | None] = [None]
                    if (piece.type is PieceType.PAWN and self.options.pawn_promotion
                            and row == (0 if color is Color.RED else self.profile.rows - 1)):
                        promotions = self.promotion_types(probe, color) or [None]
                    for promotion in promotions:
                        move = Move(piece.position, target, promotion)
                        if self.is_legal(probe, move):
                            yield move

    def legal_moves(self, state: GameState, color: Color | None = None) -> list[Move]:
        color = color or state.turn
        probe = state if state.turn is color else replace(state, turn=color)
        return list(self._iter_legal(probe, color))

    def has_any_legal_move(self, state: GameState, color: Color | None = None) -> bool:
        """是否**存在**至少一个合法着法（命中即返回，不枚举全部）。

        `legal_moves()` 要跑满 62 枚 × 13×13 个目标点（实测 257ms/次），而
        `_settle` 每次落子都要问一句"对方还有没有着法"。这里用同一个生成器
        短路取第一个 —— 语义与 `bool(legal_moves(...))` 完全等价，但常规局面
        只需扫到第一个能走的子。
        """
        color = color or state.turn
        probe = state if state.turn is color else replace(state, turn=color)
        return next(self._iter_legal(probe, color), None) is not None

    def captured_by_move(self, state: GameState, move: Move) -> tuple[Piece, ...]:
        """Return enemy pieces removed by a move, including indirect captures."""
        moving = self.get(state, move.source)
        if moving is None:
            return ()
        return tuple(piece for piece in self.board_removals(state, move)
                     if piece.color is not moving.color)

    def board_removals(self, state: GameState, move: Move) -> tuple[Piece, ...]:
        """Every piece a move takes off the board, of either colour.

        The single removal producer is `_apply_move`; this reads it back as whole
        pieces so `Game.move()` can log each removal into the matching
        `state.captured` pool. It is wider than `capturable_squares` in exactly
        one way: an assassin exchange also removes the assassin itself, so the
        mover's own piece is present here (it lands in its own side's pool).
        `captured_by_move` is this same set narrowed to the enemy.
        """
        if self.get(state, move.source) is None:
            return ()
        _, removals = self._apply_move(state, move)
        removed_ids = {removal.victim_id for removal in removals}
        return tuple(piece for piece in state.pieces if piece.id in removed_ids)

    def apply_unchecked(self, state: GameState, move: Move, switch_turn: bool = True) -> GameState:
        if self.get(state, move.source) is None:
            return state.clone()
        clone, _ = self._apply_move(state, move)
        if switch_turn:
            clone.turn = clone.turn.opponent
        return clone

    def _apply_move(self, state: GameState, move: Move) -> tuple[GameState, list[Removal]]:
        """Clone `state`, play `move`, and report every enemy piece it removes.

        This is the single writer behind both `apply_unchecked` and
        `captured_by_move`, so a move has exactly one implementation of "what do
        I capture, and how" -- the indirect armor/assassin sweeps below are the
        same predicates `capturable_squares` reads back when it answers the
        question from the other direction.
        """
        clone = state.clone()
        piece = clone.piece_at(move.source)
        removals: list[Removal] = []
        target = clone.piece_at(move.target)
        if target:
            clone.pieces.remove(target)
            removals.append(Removal(CaptureKind.DIRECT, target.id, target.type,
                                    target.color, target.position, move.source, move.target))
        clone.pieces[clone.pieces.index(piece)] = piece.at(move.target)

        if piece.type is PieceType.ARMOR:
            for captured in self._armor_removals(clone, piece.color):
                if captured in clone.pieces:
                    clone.pieces.remove(captured)
                    removals.append(Removal(CaptureKind.ARMOR_LINE, captured.id, captured.type,
                                            captured.color, captured.position,
                                            move.source, move.target))

        if move.promotion and piece.type is PieceType.PAWN and self.options.pawn_promotion:
            promoted = clone.piece_at(move.target)
            if promoted:
                clone.pieces[clone.pieces.index(promoted)] = replace(promoted, type=move.promotion)
                dead = next((p for p in clone.captured[piece.color] if p.type is move.promotion), None)
                if dead:
                    clone.captured[piece.color].remove(dead)
        return clone, removals

    def in_check(self, state: GameState, color: Color) -> bool:
        king = next((p for p in state.pieces if p.color is color and p.type is PieceType.KING), None)
        if king is None:
            return True
        threatened = self.capturable_squares(state, color.opponent, targets=(king.position,))
        return bool(threatened) or self._kings_facing(state)

    def capturable_squares(self, state: GameState, color: Color,
                           targets: Iterable[Position] | None = None) -> dict[Position, CaptureSpec]:
        """Map every square `color` can capture to the removals that do it.

        The key is the victim's square: a direct capture is filed under the
        square the attacker lands on, while an armor squeeze or an assassin drag
        is filed under the square its victim occupied. `targets=None` enumerates
        the whole board and exists for the HUD and the cross-engine parity gate
        -- it is not a hot path. `targets=(k,)` is a point query that only looks
        at the attackers which could reach `k`, keeping `in_check` the same order
        of work as the direct-plus-indirect scan it replaces.

        The function is pure: it never mutates `state` or its pieces, and two
        calls with the same arguments return equal specs. Its *result* is blind
        to the capture pool -- a pawn capturing on its promotion rank is filed as
        an ordinary direct capture, the same whether the pool is empty or not, so
        a caller that must ignore the pool can rely on it. The pool is still read
        internally (`moves_to_target`) to model the mandatory promotion; it never
        changes which removals exist and never yields a pool-consuming promotion.
        """
        probe = state if state.turn is color else replace(state, turn=color)
        if targets is None:
            victims = [piece.position for piece in state.pieces if piece.color is color.opponent]
        else:
            victims = list(targets)
        found: dict[Position, CaptureSpec] = {}
        for position in victims:
            victim = self.get(state, position)
            if victim is None or victim.color is not color.opponent:
                continue
            removals = self._capture_removals(probe, color, victim)
            if not removals:
                continue
            removals.sort(key=_removal_order)
            found[position] = CaptureSpec(position, tuple(removals))
        if __debug__:
            self._assert_capture_specs(found, color)
        return found

    def promotable_types(self, state: GameState, color: Color) -> set[PieceType]:
        """The types `color`'s pawns may promote into right now, unordered.

        The capture pool gates promotion, so this is exactly the set
        `pseudo_legal`'s promotion branch reads back. It is the one place the
        predicate lives: `promotion_types` wraps it sorted for candidate
        generation, the `pseudo_legal` gate only needs non-emptiness, and
        `ai.py`'s tactical scan iterates it as an unordered set -- none of them
        may hand-roll the set again.
        """
        return {
            captured.type for captured in state.captured[color]
            if captured.type not in {PieceType.PAWN, PieceType.KING}
            and captured.type in self.enabled_piece_types
        }

    def promotion_types(self, state: GameState, color: Color) -> list[PieceType]:
        """`promotable_types` sorted -- the deterministic order candidate
        generation, MCTS and SEE iterate in."""
        return sorted(self.promotable_types(state, color), key=lambda item: item.value)

    def moves_to_target(self, state: GameState, piece: Piece, target: Position) -> list[Move]:
        """Every `Move` that carries `piece` onto `target`, one per promotion.

        A pawn stepping onto its promotion rank must promote whenever the pool
        offers a promotable type (`pseudo_legal`'s gate), so that square is
        reachable *only* through a promotion move -- a bare `Move(from, to)` is
        illegal there and would silently hide a capture (and thus a check). This
        is the shared constructor behind `_capture_removals` and `ai_see`'s
        recapture scan; neither may hand-roll the variant list again.
        """
        if (piece.type is PieceType.PAWN and self.options.pawn_promotion
                and target.row == (0 if piece.color is Color.RED else self.profile.rows - 1)):
            promotions = self.promotion_types(state, piece.color)
            if promotions:
                return [Move(piece.position, target, promotion) for promotion in promotions]
        return [Move(piece.position, target)]

    def _capture_removals(self, state: GameState, color: Color, victim: Piece) -> list[Removal]:
        """Every move by `color` that removes `victim`, direct or indirect.

        The candidate attackers are copied verbatim from the direct/indirect
        scans this replaces, so the point query stays the same order of work: a
        piece that can land on the victim, an armor whose landing could complete
        a three-cell line through it, or the assassin landing that mirrors it.

        A direct capture is tested through `moves_to_target`, not a single bare
        move: a pawn taking on its promotion rank only has legal *promotion*
        moves, so asking about the bare move would miss the capture whenever the
        pool is non-empty -- and with it a king capture masquerading as no check.
        """
        removals: list[Removal] = []
        for piece in state.pieces:
            if piece.color is not color:
                continue
            if any(self.pseudo_legal(state, move)
                   for move in self.moves_to_target(state, piece, victim.position)):
                removals.append(Removal(CaptureKind.DIRECT, victim.id, victim.type,
                                        victim.color, victim.position,
                                        piece.position, victim.position))
            if piece.type is PieceType.ARMOR:
                landings = []
                for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                    for step in (1, 2):
                        for sign in (1, -1):
                            square = Position(victim.position.row + sign * step * dr,
                                              victim.position.col + sign * step * dc)
                            if self.inside(square):
                                landings.append(square)
            else:
                continue
            for landing in landings:
                if self.get(state, landing) is not None:
                    continue
                move = Move(piece.position, landing)
                if not self.pseudo_legal(state, move):
                    continue
                after = self.apply_unchecked(state, move, switch_turn=False)
                if victim.id not in {p.id for p in after.pieces}:
                    removals.append(Removal(CaptureKind.ARMOR_LINE, victim.id, victim.type,
                                            victim.color, victim.position,
                                            piece.position, landing))
        return removals

    def _assert_capture_specs(self, found: dict[Position, CaptureSpec], color: Color) -> None:
        """Contract checks that hold for every capture spec (`python -O` skips)."""
        for key, spec in found.items():
            assert spec.position == key, "a spec is keyed by its victim's square"
            assert spec.removals == tuple(sorted(spec.removals, key=_removal_order)), \
                "removals must be sorted by the deterministic order"
            for removal in spec.removals:
                assert removal.kind is not CaptureKind.PROMOTION_CONSUME, \
                    "capturable_squares never reports a pool-consuming promotion"
                assert removal.victim_color is color.opponent, \
                    "every removal hits the opposing side"
                assert removal.victim_position == key, \
                    "a removal's victim square is the spec's key"

    def checkmate(self, state: GameState, color: Color) -> bool:
        return self.in_check(state, color) and not self.has_any_legal_move(state, color)

    def stalemate(self, state: GameState, color: Color) -> bool:
        return not self.in_check(state, color) and not self.has_any_legal_move(state, color)

    def position_key(self, state: GameState) -> str:
        """Repetition key for one position, used by the threefold-draw ledger.

        Format contract, mirrored byte-for-byte by `offline.js`
        `Rules.positionKey` (a drift here splits the two repetition ledgers):

            "<turn>|<board>||pool:<pool>"

          - `<turn>`: `red` or `black`.
          - `<board>`: every piece as `color:type:row:col`, sorted, joined by `;`.
          - `||pool:` then `pool_signature(state)`: every captured piece as
            `color:type`, sorted, joined by `,` (empty string when no pool).

        The pool is part of the key because it changes the legal moves (which
        promotions are offered, how many pawns can be revived), so the same
        board with a different pool is a different position. Piece ids are
        deliberately excluded: they are regenerated per game, so keying on them
        would make the key never repeat and the draw could never fire.
        """
        pieces = sorted((p.color.value, p.type.value, p.position.row, p.position.col) for p in state.pieces)
        board = ";".join(f"{color}:{kind}:{row}:{col}" for color, kind, row, col in pieces)
        return f"{state.turn.value}|{board}||pool:{pool_signature(state)}"

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
        # 与兵/快速行军同一口径：阴山行本身不算敌境（红 row ≤ 5、黑 row ≥ 7）。
        in_enemy_territory = (piece.color is Color.RED and move.source.row < middle) or \
                             (piece.color is Color.BLACK and move.source.row > middle)
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
        # 阴山（中间行）本身**不算**进入敌境：红方 row ≤ 5、黑方 row ≥ 7 才可横走。
        # 与 `distance_to_enemy_territory`（最远落行 5）和象的 `target.row < middle` 同一口径。
        crossed = move.source.row < middle if piece.color is Color.RED else move.source.row > middle
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
        # A diagonal needs at most max(rows, cols) - 1 steps to leave the board,
        # so this exclusive bound always covers the whole ray.
        search_steps = max(self.profile.rows, self.profile.cols)
        for distance in range(1, search_steps):
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
        """甲：**只移动不吃子**。前后左右一格，且前方可像车一样直行（路径需空）。"""
        if self.get(state, move.target) is not None:
            return False
        forward = -1 if piece.color is Color.RED else 1
        dr = move.target.row - move.source.row
        dc = move.target.col - move.source.col
        if dc == 0 and dr * forward > 0:
            return self._rook(state, piece, move)      # 前方车式（多格直行）
        if dc == 0 and dr == -forward:
            return True                                 # 后一格
        return dr == 0 and abs(dc) == 1                 # 左右一格

    def _assassin(self, state: GameState, piece: Piece, move: Move) -> bool:
        """刺：**走**只有前进一格（与兵同）；**吃**是斜向任意距离（受斜向夹逼）。"""
        target = self.get(state, move.target)
        dr = move.target.row - move.source.row
        dc = move.target.col - move.source.col
        if target is None:
            forward = -1 if piece.color is Color.RED else 1
            return dc == 0 and dr == forward
        if not self._diagonal(move):
            return False
        return self._clear(state, move.source, move.target) and \
            not self._diagonal_path_pinched(state, move)

    def _shield(self, state: GameState, piece: Piece, move: Move) -> bool:
        return self._jump_over_one(state, move, False)

    def _patrol(self, state: GameState, piece: Piece, move: Move) -> bool:
        """巡：横竖**同规则**（不再绑死在 5/7 行），走偶数格；吃子仅限距离 2。"""
        if move.target.row != move.source.row and move.target.col != move.source.col:
            return False
        distance = abs(move.target.row - move.source.row) + abs(move.target.col - move.source.col)
        if distance == 0 or distance % 2 or not self._clear(state, move.source, move.target):
            return False
        return self.get(state, move.target) is None or distance == 2

    def _isolated(self, state: GameState, target: Piece) -> bool:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            other = self.get(state, Position(target.position.row + dr, target.position.col + dc))
            if other and other.color is target.color:
                return False
        return True

    def _pinned_by_guard(self, state: GameState, piece: Piece) -> bool:
        """`piece` 是否被敌方尉「照面钉住」。

        沿四个正方向看**第一个**遇到的棋子：若那是敌方（= `piece` 所属方的尉）的尉，
        则 `piece` 被钉住，任何着法都不合法。照面不跨越任何棋子，所以只看第一个。
        """
        for guard in state.pieces:
            if guard.type is not PieceType.GUARD or guard.color is piece.color:
                continue
            if guard.position.row != piece.position.row and guard.position.col != piece.position.col:
                continue
            if self._clear(state, guard.position, piece.position):
                return True
        return False

    def _protected_by_enemy_shield(self, state: GameState, target: Piece) -> bool:
        """同阵营的楯是否在**四正**（前后左右）贴着 `target`。

        口径从"八向相邻"收窄到"四正"：斜贴不再提供保护。注意楯本身也算"同阵营邻子"，
        所以两个楯四正相邻时会互相保护（此时仍然吃不到）。
        """
        return any(p.type is PieceType.SHIELD and p.color is target.color and
                   abs(p.position.row - target.position.row) + abs(p.position.col - target.position.col) == 1
                   for p in state.pieces)

    def _armor_removals(self, state: GameState, color: Color) -> list[Piece]:
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
        """两王同一**直线**（同列或同行）且中间无子 → 照面，计入被将。"""
        kings = [p for p in state.pieces if p.type is PieceType.KING]
        if len(kings) != 2:
            return False
        same_line = (kings[0].position.col == kings[1].position.col
                     or kings[0].position.row == kings[1].position.row)
        return same_line and self._clear(state, kings[0].position, kings[1].position)
