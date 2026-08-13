from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any
import time
import uuid


class Color(StrEnum):
    RED = "red"
    BLACK = "black"

    @property
    def opponent(self) -> "Color":
        return Color.BLACK if self is Color.RED else Color.RED


class PieceType(StrEnum):
    KING = "king"
    ROOK = "rook"
    HORSE = "horse"
    ELEPHANT = "elephant"
    ADVISOR = "advisor"
    CANNON = "cannon"
    PAWN = "pawn"
    GUARD = "guard"       # 尉/衛
    ARCHER = "archer"     # 射/䠶
    THUNDER = "thunder"   # 檑/礌
    ARMOR = "armor"       # 甲/胄
    ASSASSIN = "assassin" # 刺/伺
    SHIELD = "shield"     # 楯/碷
    PATROL = "patrol"     # 巡/廵


@dataclass(frozen=True, slots=True, order=True)
class Position:
    row: int
    col: int


@dataclass(frozen=True, slots=True)
class Piece:
    id: str
    type: PieceType
    color: Color
    position: Position

    @classmethod
    def create(cls, type_: PieceType, color: Color, row: int, col: int) -> "Piece":
        return cls(uuid.uuid4().hex[:12], type_, color, Position(row, col))

    def at(self, position: Position) -> "Piece":
        return replace(self, position=position)


@dataclass(frozen=True, slots=True)
class Move:
    source: Position
    target: Position
    promotion: PieceType | None = None

    def key(self) -> str:
        suffix = f"={self.promotion.value}" if self.promotion else ""
        return f"{self.source.row},{self.source.col}-{self.target.row},{self.target.col}{suffix}"


@dataclass(slots=True)
class MoveRecord:
    move: Move
    color: Color
    piece_type: PieceType
    captured: tuple[Piece, ...]
    notation: str
    timestamp: float = field(default_factory=time.time)
    elapsed_ms: int = 0


@dataclass(slots=True)
class GameState:
    profile_id: str
    pieces: list[Piece]
    turn: Color = Color.RED
    history: list[MoveRecord] = field(default_factory=list)
    captured: dict[Color, list[Piece]] = field(
        default_factory=lambda: {Color.RED: [], Color.BLACK: []}
    )
    winner: Color | None = None
    result_reason: str | None = None
    draw: bool = False
    pending_draw_offer: Color | None = None
    pending_undo_offer: Color | None = None
    pending_restart_offer: Color | None = None
    paused: bool = False
    paused_by: Color | None = None
    clocks_ms: dict[Color, int] = field(
        default_factory=lambda: {Color.RED: 20 * 60_000, Color.BLACK: 20 * 60_000}
    )
    turn_started_at: float = field(default_factory=time.monotonic)
    position_counts: dict[str, int] = field(default_factory=dict)

    @property
    def finished(self) -> bool:
        return self.winner is not None or self.draw

    def piece_at(self, position: Position) -> Piece | None:
        return next((p for p in self.pieces if p.position == position), None)

    def clone(self) -> "GameState":
        return GameState.from_dict(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "profileId": self.profile_id,
            "turn": self.turn.value,
            "pieces": [
                {"id": p.id, "type": p.type.value, "color": p.color.value,
                 "row": p.position.row, "col": p.position.col}
                for p in self.pieces
            ],
            "history": [
                {"move": {"from": vars_position(r.move.source), "to": vars_position(r.move.target),
                          "promotion": r.move.promotion.value if r.move.promotion else None},
                 "color": r.color.value, "pieceType": r.piece_type.value,
                 "captured": [piece_to_dict(p) for p in r.captured],
                 "notation": r.notation, "timestamp": r.timestamp, "elapsedMs": r.elapsed_ms}
                for r in self.history
            ],
            "captured": {c.value: [piece_to_dict(p) for p in items] for c, items in self.captured.items()},
            "winner": self.winner.value if self.winner else None,
            "resultReason": self.result_reason,
            "draw": self.draw,
            "pendingDrawOffer": self.pending_draw_offer.value if self.pending_draw_offer else None,
            "pendingUndoOffer": self.pending_undo_offer.value if self.pending_undo_offer else None,
            "pendingRestartOffer": self.pending_restart_offer.value if self.pending_restart_offer else None,
            "paused": self.paused,
            "pausedBy": self.paused_by.value if self.paused_by else None,
            "clocksMs": {c.value: value for c, value in self.clocks_ms.items()},
            "positionCounts": dict(self.position_counts),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameState":
        state = cls(
            profile_id=data["profileId"],
            pieces=[piece_from_dict(p) for p in data["pieces"]],
            turn=Color(data.get("turn", "red")),
            winner=Color(data["winner"]) if data.get("winner") else None,
            result_reason=data.get("resultReason"),
            draw=bool(data.get("draw", False)),
            pending_draw_offer=Color(data["pendingDrawOffer"]) if data.get("pendingDrawOffer") else None,
            pending_undo_offer=Color(data["pendingUndoOffer"]) if data.get("pendingUndoOffer") else None,
            pending_restart_offer=Color(data["pendingRestartOffer"]) if data.get("pendingRestartOffer") else None,
            paused=bool(data.get("paused", False)),
            paused_by=Color(data["pausedBy"]) if data.get("pausedBy") else None,
            clocks_ms={Color(k): int(v) for k, v in data.get("clocksMs", {}).items()} or
                      {Color.RED: 20 * 60_000, Color.BLACK: 20 * 60_000},
            position_counts=dict(data.get("positionCounts", {})),
        )
        state.captured = {
            Color.RED: [piece_from_dict(p) for p in data.get("captured", {}).get("red", [])],
            Color.BLACK: [piece_from_dict(p) for p in data.get("captured", {}).get("black", [])],
        }
        for item in data.get("history", []):
            raw = item["move"]
            state.history.append(MoveRecord(
                Move(Position(**raw["from"]), Position(**raw["to"]),
                     PieceType(raw["promotion"]) if raw.get("promotion") else None),
                Color(item["color"]), PieceType(item["pieceType"]),
                tuple(piece_from_dict(p) for p in item.get("captured", [])), item["notation"],
                float(item.get("timestamp", time.time())), int(item.get("elapsedMs", 0)),
            ))
        return state


def vars_position(pos: Position) -> dict[str, int]:
    return {"row": pos.row, "col": pos.col}


def piece_to_dict(piece: Piece) -> dict[str, Any]:
    return {"id": piece.id, "type": piece.type.value, "color": piece.color.value,
            "row": piece.position.row, "col": piece.position.col}


def piece_from_dict(data: dict[str, Any]) -> Piece:
    return Piece(data["id"], PieceType(data["type"]), Color(data["color"]),
                 Position(int(data["row"]), int(data["col"])))
