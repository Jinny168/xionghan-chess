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


# 1.8.0 调整开局布局前的槽位 → 现在的槽位。
#
# 为什么必须在读取层迁移：`GameSetup.red_slots/black_slots` 把坐标编进了字符串，
# 而 `.xhgame` 存档与 `puzzles.json` 都把这份列表原样存下来。位置一改，旧存档里的
# `red:advisor:12:6`（旧：将在右侧的士）就成了非法槽位，直接抛 ValueError ——
# 玩家存档与整份题库会同时打不开。所以这里做**前向迁移**：读到旧 id 就换成新 id，
# 存回去时自然写成新布局。
LEGACY_SLOT_ALIASES: dict[str, str] = {
    # 尉与士在 1.7.4~1.8.0 期间是对调的：尉 (11,5)/(1,5)、士 (12,6)/(0,6)
    "red:guard:11:5": "red:guard:12:6",
    "black:guard:1:5": "black:guard:0:6",
    "red:advisor:12:6": "red:advisor:11:5",
    "black:advisor:0:6": "black:advisor:1:5",
}


def _piece_type_of(slot: str) -> PieceType | None:
    parts = slot.split(":")
    if len(parts) != 4:
        return None
    try:
        return PieceType(parts[1])
    except ValueError:
        return None


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
            # 1) 旧布局的槽位 id 迁移到当前布局（见 LEGACY_SLOT_ALIASES）
            remapped = tuple(LEGACY_SLOT_ALIASES.get(item, item) for item in selected[color])
            # 2) 该档案根本没启用的兵种（如精简模式没有尉）直接丢弃，而不是报"非法槽位"
            enabled = set(available[color])
            selected[color] = tuple(
                item for item in remapped
                if item in enabled
                or (kind := _piece_type_of(item)) is None
                or options.piece_enabled(kind)
            )
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
