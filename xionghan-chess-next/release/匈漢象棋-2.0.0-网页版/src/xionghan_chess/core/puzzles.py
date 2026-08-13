from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .model import Move, Position
from .game import Game
from .storage import game_document


@dataclass(frozen=True, slots=True)
class Puzzle:
    id: str
    title: str
    difficulty: str
    description: str
    document: dict[str, Any]
    solution: tuple[Move, ...]
    hints: tuple[str, ...]
    tags: tuple[str, ...] = ()

    def summary(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "difficulty": self.difficulty,
                "description": self.description, "tags": list(self.tags),
                "steps": len(self.solution)}

    def payload(self, reveal: bool = False) -> dict[str, Any]:
        data = self.summary() | {"document": self.document, "hints": list(self.hints)}
        if reveal:
            data["solution"] = [move_to_dict(move) for move in self.solution]
        return data


def move_to_dict(move: Move) -> dict[str, Any]:
    return {"from": {"row": move.source.row, "col": move.source.col},
            "to": {"row": move.target.row, "col": move.target.col}}


def _move(data: dict[str, Any]) -> Move:
    return Move(Position(**data["from"]), Position(**data["to"]))


def load_puzzles(path: str | Path | None = None) -> list[Puzzle]:
    source = Path(path) if path else Path(__file__).with_name("data") / "puzzles.json"
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("puzzle collection must be a list")
    puzzles: list[Puzzle] = []
    seen: set[str] = set()
    for item in raw:
        puzzle_id = str(item["id"])
        if puzzle_id in seen:
            raise ValueError(f"duplicate puzzle id: {puzzle_id}")
        seen.add(puzzle_id)
        if "document" in item:
            document = dict(item["document"])
        else:
            game = Game(str(item.get("profileId", "desktop_complete")))
            for raw_move in item.get("positionMoves", []):
                game.move(_move(raw_move))
            document = game_document(game)
        puzzles.append(Puzzle(
            puzzle_id, str(item["title"]), str(item["difficulty"]),
            str(item.get("description", "")), document,
            tuple(_move(move) for move in item["solution"]),
            tuple(str(hint) for hint in item.get("hints", [])),
            tuple(str(tag) for tag in item.get("tags", [])),
        ))
    return puzzles


def puzzle_by_id(puzzle_id: str, path: str | Path | None = None) -> Puzzle:
    puzzle = next((item for item in load_puzzles(path) if item.id == puzzle_id), None)
    if puzzle is None:
        raise KeyError(puzzle_id)
    return puzzle
