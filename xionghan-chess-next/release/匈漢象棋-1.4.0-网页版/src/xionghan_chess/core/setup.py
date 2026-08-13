from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import secrets
from typing import Any, Iterable

from .model import Color, Piece, PieceType
from .profiles import RuleOptions, RuleProfile


class FirstMove(StrEnum):
    RED = "red"
    BLACK = "black"
    RANDOM = "random"


def slot_id(color: Color, piece_type: PieceType, row: int, col: int) -> str:
    return f"{color.value}:{piece_type.value}:{row}:{col}"


@dataclass(frozen=True, slots=True)
class GameSetup:
    first_move: FirstMove = FirstMove.RED
    resolved_first_move: Color = Color.RED
    red_slots: tuple[str, ...] = ()
    black_slots: tuple[str, ...] = ()

    @classmethod
    def build(cls, profile: RuleProfile, options: RuleOptions,
              first_move: FirstMove | str = FirstMove.RED,
              red_slots: Iterable[str] | None = None,
              black_slots: Iterable[str] | None = None) -> "GameSetup":
        requested = FirstMove(first_move)
        available = {
            color: tuple(
                slot_id(spec.color, spec.type, spec.row, spec.col)
                for spec in profile.pieces
                if spec.color is color and options.piece_enabled(spec.type)
            )
            for color in Color
        }
        selected = {
            Color.RED: tuple(red_slots) if red_slots is not None else available[Color.RED],
            Color.BLACK: tuple(black_slots) if black_slots is not None else available[Color.BLACK],
        }
        for color in Color:
            if len(selected[color]) != len(set(selected[color])):
                raise ValueError(f"{color.value} setup contains duplicate piece slots")
            unknown = set(selected[color]) - set(available[color])
            if unknown:
                raise ValueError(f"{color.value} setup contains unavailable piece slots: {sorted(unknown)}")
            king_prefix = f"{color.value}:{PieceType.KING.value}:"
            if not any(item.startswith(king_prefix) for item in selected[color]):
                raise ValueError(f"{color.value} king must appear")
        if len(selected[Color.RED]) != len(selected[Color.BLACK]):
            raise ValueError("red and black must field the same number of pieces")
        resolved = (secrets.choice(tuple(Color)) if requested is FirstMove.RANDOM
                    else Color(requested.value))
        return cls(requested, resolved, selected[Color.RED], selected[Color.BLACK])

    @classmethod
    def from_dict(cls, profile: RuleProfile, options: RuleOptions,
                  data: dict[str, Any] | None) -> "GameSetup":
        if not data:
            return cls.build(profile, options)
        setup = cls.build(
            profile, options, data.get("firstMove", FirstMove.RED),
            data.get("redSlots"), data.get("blackSlots"),
        )
        resolved = data.get("resolvedFirstMove")
        return cls(setup.first_move, Color(resolved) if resolved else setup.resolved_first_move,
                   setup.red_slots, setup.black_slots)

    def initial_pieces(self, profile: RuleProfile) -> list[Piece]:
        selected = set(self.red_slots) | set(self.black_slots)
        return [
            Piece.create(spec.type, spec.color, spec.row, spec.col)
            for spec in profile.pieces
            if slot_id(spec.color, spec.type, spec.row, spec.col) in selected
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "firstMove": self.first_move.value,
            "resolvedFirstMove": self.resolved_first_move.value,
            "redSlots": list(self.red_slots),
            "blackSlots": list(self.black_slots),
            "handicap": len(self.red_slots) != len(self.black_slots) or False,
        }


def profile_slots(profile: RuleProfile, options: RuleOptions) -> list[dict[str, Any]]:
    return [
        {
            "id": slot_id(spec.color, spec.type, spec.row, spec.col),
            "color": spec.color.value,
            "type": spec.type.value,
            "row": spec.row,
            "col": spec.col,
            "enabled": options.piece_enabled(spec.type),
        }
        for spec in profile.pieces
        if options.piece_enabled(spec.type)
    ]
