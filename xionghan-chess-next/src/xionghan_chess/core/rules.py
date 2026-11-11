from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Callable, Iterable, Iterator

from .model import Color, GameState, Move, Piece, PieceType, Position
from .profiles import RULE_VERSION, RuleOptions, RuleProfile


class CaptureKind(StrEnum):
    """How a move takes an enemy piece off the board."""

    DIRECT = "direct"  # the landing square is the victim's square
    THREE_LINE = "three_line"  # 己方两子夹一敌子成线（兵，开关控制）
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
    return (removal.kind.value, removal.origin.row, removal.origin.col, removal.landing.row, removal.landing.col)


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
POSITION_KEY_VERSION = 4
# v3：key 里加入**影响合法着法的选项摘要**（`||opt:`）。
# 旧存档的 `positionCounts` 作废：key 不匹配即从 0 计，最坏结果是"已重复 2 次的局面重新计"，
# 不会误判和 —— 反向（沿用旧 key 的计数）才是会误判和的方向。
# v4：摘要里加 `rs2-` 前缀（规则集版本）。**这是硬规则第一次进 key**：
# `pawn_three_line_capture` / `pawn_promotion` / `enforce_self_check` 三位都是**开关**，
# 而 2.0.0 改的是"巡只沿横线走"和"兵底线不再后退"——**没有对应开关**。
# 不加前缀的话，同一盘面在 1.9 与 2.0 下算出**完全相同的 key**：升级用户的中途局
# 会带着旧规则的计数继续跑（`GAME_BREAKING_KEYS` 只管配置，管不到硬规则），
# 三次重复判和就会在新规则下沿用旧规则的账，误判和。
# 与 `RULE_VERSION`（profiles.py，语义版本）的区别：这里只是 key 的**格式标签**，
# 换 key 格式才 +1；语义变了但 key 格式没变时才需要动这个前缀。


def pool_signature(state: GameState) -> str:
    """The pool half of a `position_key`, colour-tagged and sorted.

    A capture pool is game state, not bookkeeping: it fixes which promotions are
    legal (`pseudo_legal`'s pawn-promotion gate below) and how many pawns may be
    revived (`game.py::resurrect_pawn`). Two states sharing a board and side to
    move but holding different pools are therefore *different* positions, so the
    pool is a first-class part of the repetition key -- not an AI-only cache
    extra.
    """
    return ",".join(sorted(f"{color.value}:{piece.type.value}" for color in Color for piece in state.captured[color]))


class RulesEngine:
    """Authoritative, side-effect free move validation for every delivery target."""

    def __init__(self, profile: RuleProfile, options: RuleOptions | None = None):
        self.profile = profile
        self.options = options or profile.options
        # 预计算：`pseudo_legal` 每生成一个着法都要读这个属性（实测 46k 次/5s），
        # 每次重建 frozenset 要付 14 次 `piece_enabled` 的 getattr，累计 1.09s。
        # 安全性：`options` 只在构造时赋值，全仓没有原地修改（改规则会新建引擎）。
        self._enabled_piece_types = frozenset(
            kind for kind in self.profile.enabled_piece_types if self.options.piece_enabled(kind)
        )

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
        if target and target.color is piece.color:
            return False
        if move.promotion:
            if piece.type is not PieceType.PAWN or not self.options.pawn_promotion:
                return False
            if move.promotion in {PieceType.PAWN, PieceType.KING} or move.promotion not in self.enabled_piece_types:
                return False
            if not any(p.type is move.promotion for p in state.captured[piece.color]):
                return False
        elif (
            piece.type is PieceType.PAWN
            and self.options.pawn_promotion
            and move.target.row == (0 if piece.color is Color.RED else self.profile.rows - 1)
        ):
            # Only non-emptiness is needed here, so ask the set directly -- this
            # gate is the one promotion branch that runs on the pseudo_legal hot
            # path, and `promotable_types` skips `promotion_types`' sort.
            if self.promotable_types(state, piece.color):
                return False

        # Every validator shares the (state, piece, move) signature so this table
        # stays homogeneous; a validator that does not need `piece` (rook, horse,
        # cannon, guard, archer, thunder, patrol) simply ignores it.
        validators: dict[PieceType, Callable[[GameState, Piece, Move], bool]] = {
            PieceType.ROOK: self._rook,
            PieceType.HORSE: self._horse,
            PieceType.ELEPHANT: self._elephant,
            PieceType.ADVISOR: self._advisor,
            PieceType.KING: self._king,
            PieceType.CANNON: self._cannon,
            PieceType.PAWN: self._pawn,
            PieceType.GUARD: self._guard,
            PieceType.ARCHER: self._archer,
            PieceType.THUNDER: self._thunder,
            PieceType.PATROL: self._patrol,
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
                    if (
                        piece.type is PieceType.PAWN
                        and self.options.pawn_promotion
                        and row == (0 if color is Color.RED else self.profile.rows - 1)
                    ):
                        promotions = list(self.promotion_types(probe, color))
                        if not promotions:
                            promotions.append(None)
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
        return tuple(piece for piece in self.board_removals(state, move) if piece.color is not moving.color)

    def board_removals(self, state: GameState, move: Move) -> tuple[Piece, ...]:
        """Every piece a move takes off the board, of either colour.

        The single removal producer is `_apply_move`; this reads it back as whole
        pieces so `Game.move()` can log each removal into the matching
        `state.captured` pool.
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
        I capture, and how" -- the indirect three-line sweep below is the same
        predicate `capturable_squares` reads back when it answers the question
        from the other direction.
        """
        clone = state.clone()
        piece = clone.piece_at(move.source)
        assert piece is not None, "apply_move called with a move whose source is empty"
        removals: list[Removal] = []
        target = clone.piece_at(move.target)
        if target:
            clone.pieces.remove(target)
            removals.append(
                Removal(
                    CaptureKind.DIRECT, target.id, target.type, target.color, target.position, move.source, move.target
                )
            )
        clone.pieces[clone.pieces.index(piece)] = piece.at(move.target)

        if self._three_line_mover(piece, move):
            for captured in self._three_line_removals(clone, piece.color, move.target):
                if captured in clone.pieces:
                    clone.pieces.remove(captured)
                    removals.append(
                        Removal(
                            CaptureKind.THREE_LINE,
                            captured.id,
                            captured.type,
                            captured.color,
                            captured.position,
                            move.source,
                            move.target,
                        )
                    )

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

    def capturable_squares(
        self, state: GameState, color: Color, targets: Iterable[Position] | None = None
    ) -> dict[Position, CaptureSpec]:
        """Map every square `color` can capture to the removals that do it.

        The key is the victim's square: a direct capture is filed under the
        square the attacker lands on, while a three-line capture is filed under
        the square its victim occupied. `targets=None` enumerates
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
            captured.type
            for captured in state.captured[color]
            if captured.type not in {PieceType.PAWN, PieceType.KING} and captured.type in self.enabled_piece_types
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
        if (
            piece.type is PieceType.PAWN
            and self.options.pawn_promotion
            and target.row == (0 if piece.color is Color.RED else self.profile.rows - 1)
        ):
            promotions = self.promotion_types(state, piece.color)
            if promotions:
                return [Move(piece.position, target, promotion) for promotion in promotions]
        return [Move(piece.position, target)]

    def _capture_removals(self, state: GameState, color: Color, victim: Piece) -> list[Removal]:
        """Every move by `color` that removes `victim`, direct or indirect.

        The candidate attackers are copied verbatim from the direct/indirect
        scans this replaces, so the point query stays the same order of work: a
        piece that can land on the victim, or a pawn whose landing completes a
        three-cell line through it.

        A direct capture is tested through `moves_to_target`, not a single bare
        move: a pawn taking on its promotion rank only has legal *promotion*
        moves, so asking about the bare move would miss the capture whenever the
        pool is non-empty -- and with it a king capture masquerading as no check.
        """
        removals: list[Removal] = []
        for piece in state.pieces:
            if piece.color is not color:
                continue
            if any(self.pseudo_legal(state, move) for move in self.moves_to_target(state, piece, victim.position)):
                removals.append(
                    Removal(
                        CaptureKind.DIRECT,
                        victim.id,
                        victim.type,
                        victim.color,
                        victim.position,
                        piece.position,
                        victim.position,
                    )
                )
            if not self._three_line_enabled(piece):
                continue
            # 受害者两侧各 2 格都要列：落点可以在窗口的任意一端，于是它离受害者最远 2 格，
            # 而离**兵的起点**仍只有一格 —— 位移判据管的是后者，不是前者。
            landings = []
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                for step in (1, 2):
                    for sign in (1, -1):
                        square = Position(
                            victim.position.row + sign * step * dr, victim.position.col + sign * step * dc
                        )
                        if self.inside(square):
                            landings.append(square)
            for landing in landings:
                if self.get(state, landing) is not None:
                    continue
                move = Move(piece.position, landing)
                if not self._three_line_mover(piece, move):
                    continue
                if not self.pseudo_legal(state, move):
                    continue
                after = self.apply_unchecked(state, move, switch_turn=False)
                if victim.id not in {p.id for p in after.pieces}:
                    removals.append(
                        Removal(
                            CaptureKind.THREE_LINE,
                            victim.id,
                            victim.type,
                            victim.color,
                            victim.position,
                            piece.position,
                            landing,
                        )
                    )
        return removals

    def _assert_capture_specs(self, found: dict[Position, CaptureSpec], color: Color) -> None:
        """Contract checks that hold for every capture spec (`python -O` skips)."""
        for key, spec in found.items():
            assert spec.position == key, "a spec is keyed by its victim's square"
            assert spec.removals == tuple(sorted(spec.removals, key=_removal_order)), (
                "removals must be sorted by the deterministic order"
            )
            for removal in spec.removals:
                assert removal.kind is not CaptureKind.PROMOTION_CONSUME, (
                    "capturable_squares never reports a pool-consuming promotion"
                )
                assert removal.victim_color is color.opponent, "every removal hits the opposing side"
                assert removal.victim_position == key, "a removal's victim square is the spec's key"

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
        return f"{state.turn.value}|{board}||pool:{pool_signature(state)}||opt:{self._option_digest()}"

    def _option_digest(self) -> str:
        """影响合法着法/吃子的选项摘要。

        为什么 key 里要有它：`positionCounts` 会随存档/导入/网络带进选项不同的新对局，
        那些计数是按**旧选项**算的。不含摘要时，两种不同规则下的同一盘面会共用一份计数。
        只挑"改变合法着法"的字段，避免无谓抖动。

        `rs{规则集版本}-` 里的版本号取 `profiles.RULE_VERSION`（2.0.0 = 2），
        不是另起一个常量：**走法语义一变就必须换账本**，让它跟语义版本同源，
        下次改规则的人就不可能只改一处、忘了这里。
        """
        return (
            f"rs{RULE_VERSION}-"
            f"p3l{int(self.options.pawn_three_line_capture)}"
            f"-promo{int(self.options.pawn_promotion)}"
            f"-self{int(self.options.enforce_self_check)}"
        )

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
            # 直走三格：默认可吃子；开"仅可移动"后是纯机动手段。
            # 口径与兵冲锋一致 —— 落点有子就整着不合法（不是"吃掉但不计入胜负"）。
            if self.options.horse_straight_three_move_only and self.get(state, move.target) is not None:
                return False
            return self._clear(state, move.source, move.target)
        if (ar, ac) not in {(2, 1), (1, 2)}:
            return False
        # 别马腿只管日字这一路；直走三格没有"马腿"概念，不受这个开关影响。
        if not self.options.horse_blocked_by_leg:
            return True
        leg = Position(move.source.row + (dr // 2 if ar == 2 else 0), move.source.col + (dc // 2 if ac == 2 else 0))
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
        in_enemy_territory = (piece.color is Color.RED and move.source.row < middle) or (
            piece.color is Color.BLACK and move.source.row > middle
        )
        return (
            self.options.elephant_can_cross_river
            and self.options.elephant_gain_jump_two_enemy_territory
            and in_enemy_territory
        )

    def _advisor(self, state: GameState, piece: Piece, move: Move) -> bool:
        dr, dc = abs(move.target.row - move.source.row), abs(move.target.col - move.source.col)
        diagonal, straight = (dr, dc) == (1, 1), dr + dc == 1
        source_in_palace = self.palace(piece.color, move.source)
        target_in_palace = self.palace(piece.color, move.target)
        if source_in_palace:
            return (
                diagonal
                and (target_in_palace or self.options.advisor_can_leave_palace)
                and not self._diagonal_path_pinched(state, move)
            )
        if not self.options.advisor_can_leave_palace and not target_in_palace:
            return False
        if diagonal and self._diagonal_path_pinched(state, move):
            return False
        return diagonal or (
            straight and self.options.advisor_can_leave_palace and self.options.advisor_gain_straight_outside_palace
        )

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
        # 曾经这里有一条 `if enemy_base and pawn_full_movement_at_base: return 四向一格` 的早返回。
        # 2.0.0 把它删了：它真正多给的只有"后退一格"（横走本就被下面的 `crossed` 放行），
        # 而"后退"现在由 `pawn_backward_at_base`（默认关）单独管 —— 两个开关管一件事，
        # 谁关谁开都说不清，底线兵到底能不能退在旧配置下根本推不出来。
        distance = abs(dr)
        distance_to_enemy_territory = (
            move.source.row - middle + 1 if piece.color is Color.RED else middle - move.source.row + 1
        )
        if (
            self.options.pawn_fast_move_before_enemy_territory
            and dc == 0
            and dr == forward * distance
            and 1 < distance <= distance_to_enemy_territory
        ):
            if self.get(state, move.target):
                return False
            return all(
                self.get(state, Position(move.source.row + forward * step, move.source.col)) is None
                for step in range(1, distance)
            )
        # 敌阵冲锋（开关）：过阴山后沿直线任意格前进，不吃子、路径须全空。
        # 放在"前进一格"之前，否则只会被一格判定截住。
        #
        # **只在能走通时返回 True，走不通就落到下面的常规判定**：
        # 早期写成"落点有子一律 return False"，于是开启冲锋后，过河兵**连正前方一格吃子
        # 都被禁掉**（冲锋的"不吃子"把常规吃子吞了）。实测后果：升变位的兵无法吃子，
        # 连带 `in_check` 漏判（test_capture_specs 的 g5/g12 就是这条）。
        # 现在：多格冲锋仍不吃子；一格吃子交回常规分支处理。
        if self.options.pawn_charge and dc == 0 and dr == forward * distance and distance >= 1:
            if crossed and self.get(state, move.target) is None:
                if all(
                    self.get(state, Position(move.source.row + forward * step, move.source.col)) is None
                    for step in range(1, distance)
                ):
                    return True
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
        """尉：**斜向任意距离**，路径必须无子（标准主教）；落点有敌子即吃。

        夹逼口径与其它斜走子一致（`_diagonal_path_pinched`），不经 `_jump_over_one`。
        """
        if not self._diagonal(move):
            return False
        if self._diagonal_path_pinched(state, move):
            return False
        return self._clear(state, move.source, move.target)

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
            star_distance = self._nearest_archer_star_distance(move.source, step_row, step_col)
            if star_distance == 0 or distance > star_distance:
                return False

        if self._diagonal_path_pinched(state, move):
            return False
        # 位移仍要求路径无子；**吃子无视阻挡**（射程/星点/夹逼三项不变）。
        if target is None:
            for step in range(1, distance):
                position = Position(move.source.row + step * step_row, move.source.col + step * step_col)
                if self.get(state, position):
                    return False
        return True

    def _nearest_archer_star_distance(self, source: Position, step_row: int, step_col: int) -> int:
        # A diagonal needs at most max(rows, cols) - 1 steps to leave the board,
        # so this exclusive bound always covers the whole ray.
        search_steps = max(self.profile.rows, self.profile.cols)
        for distance in range(1, search_steps):
            position = Position(source.row + distance * step_row, source.col + distance * step_col)
            if not self.inside(position):
                return 0
            if position in self.archer_star_points:
                return distance
        return 0

    @staticmethod
    def _position_on_segment(position: Position, start: Position, end: Position) -> bool:
        return (
            min(start.row, end.row) <= position.row <= max(start.row, end.row)
            and min(start.col, end.col) <= position.col <= max(start.col, end.col)
            and abs(position.row - start.row) == abs(position.col - start.col)
        )

    def _diagonal_pinched(self, state: GameState, position: Position, step_row: int, step_col: int) -> bool:
        side_a = Position(position.row, position.col + step_col)
        side_b = Position(position.row + step_row, position.col)
        return (
            self.inside(side_a)
            and self.inside(side_b)
            and self.get(state, side_a) is not None
            and self.get(state, side_b) is not None
        )

    def _diagonal_path_pinched(self, state: GameState, move: Move) -> bool:
        if not self._diagonal(move):
            return False
        step_row = 1 if move.target.row > move.source.row else -1
        step_col = 1 if move.target.col > move.source.col else -1
        distance = abs(move.target.row - move.source.row)
        return any(
            self._diagonal_pinched(
                state,
                Position(move.source.row + step * step_row, move.source.col + step * step_col),
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
            return (
                max(abs(move.target.row - move.source.row), abs(move.target.col - move.source.col)) == 1
                and self._isolated(state, target)
                and (not self._diagonal(move) or not self._diagonal_path_pinched(state, move))
            )
        return self._clear(state, move.source, move.target) and (
            not self._diagonal(move) or not self._diagonal_path_pinched(state, move)
        )

    def _patrol(self, state: GameState, piece: Piece, move: Move) -> bool:
        """巡：**只沿横线**走偶数格；吃子仅限距离 2。

        竖线禁行是**硬规则**（不进 `GameOptions`，红黑同一条判据）：巡的职责是沿巡道
        横向巡逻，一旦允许竖走，它就能从阴山一侧直贯对方底线，"巡"这个身份就没了。
        判据只认"起点终点同行"，**不查 {5,7} 行白名单** —— 残局摆子会把它放在任意行，
        白名单会让残局里的巡凭空失效。
        """
        if move.target.row != move.source.row:
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

    def _three_line_enabled(self, piece: Piece) -> bool:
        """这枚子是否有资格结算"三连吃子"：只有兵，且需开关开启（默认关）。

        与"这一着走多远"无关，只回答"种类 + 开关"；位移判据在 `_three_line_mover`。
        """
        return piece.type is PieceType.PAWN and self.options.pawn_three_line_capture

    def _three_line_mover(self, piece: Piece, move: Move) -> bool:
        """这一着是否**真的**结算三连吃子。

        三个条件缺一不可：兵、开关开启、**这一着位移不超过一格**。

        为什么要看位移：快速行军能一次跨 n 格（`_pawn` 的 `1 < distance`），
        敌阵冲锋（`pawn_charge`）同样能长距离直线走。两者本身"落点必须为空、不吃子"，
        但三连吃子是**结算阶段**的旁吃，若不拦，就会出现"一着位移 5 格顺便吃掉一枚子"
        —— 实测存在，且 `PIECE_RULES.md` 的「移动超过一格时不能吃子」管不住它。

        判据按**着法位移**而不是"走了哪个分支"：快速行军与冲锋共用一个上限，
        将来加别的多格走法也自动受约束；而兵的前进一格、横走一格都是位移 1，不会被误伤。
        """
        if not self._three_line_enabled(piece):
            return False
        return max(abs(move.target.row - move.source.row), abs(move.target.col - move.source.col)) <= 1

    def _three_line_removals(self, state: GameState, color: Color, landing: Position) -> list[Piece]:
        """三连吃子：**只结算落点所在的线**。

        口径（规则作者定稿）：
        - 三子**紧挨**（相邻，窗口步长 1，天然满足）；
        - 这条线上**恰好三子**：窗口两端的外侧邻格若有子（实际连成 4 子或 5 子），**不结算**；
        - **两枚我方 + 一枚敌方**，**任意顺序**（兵兵敌 / 兵敌兵 / 敌兵兵 都算）；
        - 至少一枚是兵，且**移动的那枚兵必须在这个窗口里**；
        - **被吃的那枚不能是将/帅**（否则等于一步无声吃王，见循环里的注释）；
        - `pawn_three_line_capture` 开启（默认关）；
        - **这一着位移不超过一格**（判据在 `_three_line_mover`，调用前已拦）。

        为什么按落点枚举而不是全盘扫描：全盘扫描会把"移动前就已存在的线"一并收割 ——
        走一步无关的兵，远处已成线的敌子也会被吃，这既反直觉也让"能吃到"与"实际吃到"分叉。

        "恰好三子"为什么要在窗口外再查两格：不查的话，一条 4 子/5 子的长线里
        每个"两我一敌"的 3 格窗口都会各算一次，玩家摆出的明明是"四子相连"，
        却按"三子相连"被吃 —— 实测成立，且加长一条线反而更容易吃，与这条规则的
        识别特征（眼看"三子相连"）相反。
        """
        if not self.options.pawn_three_line_capture:
            return []
        captures: dict[str, Piece] = {}
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            # 落点可能落在窗口的第 1/2/3 格 → 3 个偏移；4 向共 12 个窗口
            for offset in (-2, -1, 0):
                # 窗口两端的外侧邻格：任一有子 → 这条线上其实连了 4 子以上，不算三连。
                # `get()` 对越界返回 None（`GameState.piece_at` 逐个比对坐标），
                # 所以贴边窗口不需要额外判 `inside`。
                before = Position(landing.row + (offset - 1) * dr, landing.col + (offset - 1) * dc)
                after = Position(landing.row + (offset + 3) * dr, landing.col + (offset + 3) * dc)
                if self.get(state, before) is not None or self.get(state, after) is not None:
                    continue
                group = [
                    self.get(state, Position(landing.row + (offset + i) * dr, landing.col + (offset + i) * dc))
                    for i in range(3)
                ]
                present = [p for p in group if p is not None]
                if len(present) != 3:
                    continue
                allies = [p for p in present if p.color is color]
                enemies = [p for p in present if p.color is not color]
                if len(allies) != 2 or len(enemies) != 1:
                    continue
                if not any(p.type is PieceType.PAWN for p in allies):
                    continue
                if not any(p.position == landing for p in allies):
                    continue
                # 将/帅不吃：三连是"围住一枚敌子"，把王围进去等于一步无声吃王（走之前对方
                # 并未被将，玩家没有预警）。规则作者裁定排除，`capturable_squares` 走同一条
                # 结算，因此"王不会被三连吃"在攻击图上也自动一致（`in_check` 不会误判）。
                if enemies[0].type is PieceType.KING:
                    continue
                captures[enemies[0].id] = enemies[0]
        return list(captures.values())

    def _kings_facing(self, state: GameState) -> bool:
        """两王同一**直线**（同列或同行）且中间无子 → 照面，计入被将。"""
        kings = [p for p in state.pieces if p.type is PieceType.KING]
        if len(kings) != 2:
            return False
        same_line = kings[0].position.col == kings[1].position.col or kings[0].position.row == kings[1].position.row
        return same_line and self._clear(state, kings[0].position, kings[1].position)
