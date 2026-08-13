from __future__ import annotations

from dataclasses import asdict, replace
import time

from xionghan_chess.i18n import normalize_language, t

from .model import Color, GameState, Move, MoveRecord, Piece, PieceType, Position
from .profiles import RuleOptions, RuleProfile, get_profile
from .rules import RulesEngine
from .setup import FirstMove, GameSetup


class GameError(ValueError):
    pass


class Game:
    def __init__(self, profile: RuleProfile | str = "desktop_complete",
                 option_overrides: dict[str, object] | None = None,
                 initial_minutes: int = 20,
                 language: str = "zh-CN",
                 setup: GameSetup | dict | None = None):
        self.language = normalize_language(language)
        self.profile = get_profile(profile) if isinstance(profile, str) else profile
        self.options = self.profile.options.merged(option_overrides)
        self.rules = RulesEngine(self.profile, self.options)
        self.setup = (setup if isinstance(setup, GameSetup)
                      else GameSetup.from_dict(self.profile, self.options, setup))
        self.state = GameState(self.profile.id, self.setup.initial_pieces(self.profile),
                               turn=self.setup.resolved_first_move)
        self.state.clocks_ms = {Color.RED: initial_minutes * 60_000, Color.BLACK: initial_minutes * 60_000}
        self._snapshots: list[dict] = []
        self._record_position()

    @classmethod
    def from_state(cls, state: GameState, option_overrides: dict[str, object] | RuleOptions | None = None,
                   setup: GameSetup | dict | None = None) -> "Game":
        if isinstance(option_overrides, RuleOptions):
            option_overrides = asdict(option_overrides)
        game = cls(state.profile_id, option_overrides, setup=setup)
        game.state = state
        return game

    def _t(self, key: str, **params: object) -> str:
        return t(key, self.language, **params)

    def move(self, move: Move) -> MoveRecord:
        if self.state.finished:
            raise GameError(self._t("error.game_finished"))
        if self.state.paused:
            raise GameError(self._t("error.game_paused"))
        self.tick()
        if self.state.finished:
            raise GameError(self._t("error.turn_timeout"))
        if not self.rules.is_legal(self.state, move):
            raise GameError(self._t("error.illegal_move"))
        self._snapshots.append(self.state.to_dict())
        moving = self.state.piece_at(move.source)
        assert moving is not None
        before_ids = {p.id: p for p in self.state.pieces}
        elapsed = int((time.monotonic() - self.state.turn_started_at) * 1000)
        next_state = self.rules.apply_unchecked(self.state, move)
        after_ids = {p.id for p in next_state.pieces}
        captured = tuple(p for pid, p in before_ids.items() if pid not in after_ids)
        for item in captured:
            next_state.captured[item.color].append(item)
        record = MoveRecord(move, moving.color, moving.type, captured, self.notation(moving, move, captured), elapsed_ms=elapsed)
        next_state.history.append(record)
        next_state.turn_started_at = time.monotonic()
        next_state.pending_draw_offer = None
        self.state = next_state
        self._record_position()
        self._settle_after_move(moving.color, move)
        return record

    def undo(self, plies: int = 1) -> None:
        if plies < 1 or len(self._snapshots) < plies:
            raise GameError(self._t("error.no_undo"))
        snapshot = self._snapshots[-plies]
        del self._snapshots[-plies:]
        self.state = GameState.from_dict(snapshot)
        self.state.turn_started_at = time.monotonic()

    def set_paused(self, paused: bool, color: Color | None = None) -> None:
        if self.state.finished:
            raise GameError(self._t("error.game_finished"))
        if paused == self.state.paused:
            return
        if paused:
            self.tick()
            if self.state.finished:
                return
            self.state.paused = True
            self.state.paused_by = color
        else:
            self.state.paused = False
            self.state.paused_by = None
            self.state.turn_started_at = time.monotonic()

    def resign(self, color: Color) -> None:
        self.state.winner = color.opponent
        self.state.result_reason = "resignation"

    def offer_draw(self, color: Color) -> None:
        if color is not self.state.turn:
            raise GameError(self._t("error.draw_own_turn"))
        self.state.pending_draw_offer = color

    def respond_draw(self, color: Color, accept: bool) -> None:
        if self.state.pending_draw_offer is not color.opponent:
            raise GameError(self._t("error.no_pending_draw"))
        self.state.pending_draw_offer = None
        if accept:
            self.state.draw = True
            self.state.result_reason = "draw_agreement"

    def offer_undo(self, color: Color) -> None:
        if not self.state.history:
            raise GameError(self._t("error.no_undo_move"))
        self.state.pending_undo_offer = color

    def respond_undo(self, color: Color, accept: bool) -> None:
        if self.state.pending_undo_offer is not color.opponent:
            raise GameError(self._t("error.no_pending_undo"))
        self.state.pending_undo_offer = None
        if accept:
            self.undo(2 if len(self._snapshots) >= 2 else 1)

    def resurrect_pawn(self, color: Color, position: Position) -> None:
        if self.state.paused:
            raise GameError(self._t("error.game_paused"))
        if not self.options.pawn_resurrection or color is not self.state.turn:
            raise GameError(self._t("error.resurrect_not_allowed"))
        home_row = 8 if color is Color.RED else 4
        if position.row != home_row or position.col % 2 or self.state.piece_at(position):
            raise GameError(self._t("error.invalid_resurrect_position"))
        dead = next((p for p in self.state.captured[color] if p.type is PieceType.PAWN), None)
        if dead is None or sum(p.type is PieceType.PAWN and p.color is color for p in self.state.pieces) >= 7:
            raise GameError(self._t("error.no_resurrect_pawn"))
        self._snapshots.append(self.state.to_dict())
        self.state.captured[color].remove(dead)
        self.state.pieces.append(Piece.create(PieceType.PAWN, color, position.row, position.col))
        self.state.turn = color.opponent
        self.state.turn_started_at = time.monotonic()

    def tick(self) -> None:
        if self.state.finished or self.state.paused:
            return
        elapsed = int((time.monotonic() - self.state.turn_started_at) * 1000)
        if elapsed >= self.state.clocks_ms[self.state.turn]:
            self.state.clocks_ms[self.state.turn] = 0
            self.state.winner = self.state.turn.opponent
            self.state.result_reason = "timeout"
        else:
            self.state.clocks_ms[self.state.turn] -= elapsed
            self.state.turn_started_at = time.monotonic()

    def notation(self, piece: Piece, move: Move, captured: tuple[Piece, ...]) -> str:
        name = self.profile.display_name_of(piece, self.language)
        action = self._t("notation.capture") if captured else self._t("notation.move")
        return f"{name} {move.source.row + 1},{move.source.col + 1} {action} {move.target.row + 1},{move.target.col + 1}"

    def public_state(self) -> dict:
        data = self.state.to_dict()
        data["profile"] = {"id": self.profile.id, "title": self.profile.title,
                           "rows": self.profile.rows, "cols": self.profile.cols,
                           "options": asdict(self.options),
                           "archerStarPoints": [
                               {"row": point.row, "col": point.col}
                               for point in sorted(self.rules.archer_star_points,
                                                   key=lambda item: (item.row, item.col))
                           ]}
        data["check"] = self.rules.in_check(self.state, self.state.turn) if not self.state.finished else False
        data["setup"] = self.setup.to_dict()
        data["replay"] = [snapshot for snapshot in self._snapshots] + [self.state.to_dict()]
        return data

    def _record_position(self) -> None:
        key = self.rules.position_key(self.state)
        self.state.position_counts[key] = self.state.position_counts.get(key, 0) + 1

    def _settle_after_move(self, mover: Color, move: Move) -> None:
        enemy = mover.opponent
        enemy_king = next((p for p in self.state.pieces if p.type is PieceType.KING and p.color is enemy), None)
        moved = self.state.piece_at(move.target)
        if enemy_king is None:
            self.state.winner, self.state.result_reason = mover, "king_captured"
        elif moved and moved.type is PieceType.KING and self.options.invasion_victory and self.rules.enemy_palace(mover, moved.position):
            self.state.winner, self.state.result_reason = mover, "palace_invasion"
        elif self.rules.checkmate(self.state, enemy):
            self.state.winner, self.state.result_reason = mover, "checkmate"
        elif self.rules.stalemate(self.state, enemy):
            self.state.winner, self.state.result_reason = mover, "stalemate"
        elif self.options.threefold_draw and max(self.state.position_counts.values(), default=0) >= 3:
            self.state.draw, self.state.result_reason = True, "threefold_repetition"
        elif self.options.no_progress_draw_plies and self._no_progress_plies() >= self.options.no_progress_draw_plies:
            self.state.draw, self.state.result_reason = True, "no_progress"

    def _no_progress_plies(self) -> int:
        count = 0
        for record in reversed(self.state.history):
            if record.captured or record.piece_type is PieceType.PAWN:
                break
            count += 1
        return count
