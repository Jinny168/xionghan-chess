from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .model import Move, Position
from .game import Game
from .rules import CaptureKind
from .storage import game_document, game_from_document


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

    def exercise(self) -> tuple[frozenset[str], frozenset[str]]:
        """这道题**实际**练到哪些子力、触发哪些吃法。

        从解法反推，不看题目自带的任何声明字段 —— 题面里摆了甲但解法根本不动它，
        对玩家来说等于没覆盖。P1-M 的原始症状正是「标题写着残局训练，实际全是
        开局第一步」，所以判据必须是「解法里出现的子力」，而不是「题面里有这个子」。
        """
        game = game_from_document(self.document)
        pieces: set[str] = set()
        kinds: set[str] = set()
        for step in self.solution:
            mover = game.rules.get(game.state, step.source)
            if mover is not None:
                pieces.add(mover.type.value)
            for victim in game.rules.captured_by_move(game.state, step):
                pieces.add(victim.type.value)
            origin = (step.source.row, step.source.col)
            for spec in game.rules.capturable_squares(game.state, game.state.turn).values():
                for removal in spec.removals:
                    if (removal.origin.row, removal.origin.col) == origin:
                        kinds.add(removal.kind.value)
            # `direct` 只认落点原本站着敌子（同 scripts/build_puzzles.py 的口径）。
            landing = game.rules.get(game.state, step.target)
            if landing is not None and landing.color is not game.state.turn:
                kinds.add(CaptureKind.DIRECT.value)
            # 不再单独调 `is_legal`：`Game.move()` 本身就会校验，重复调一次等于把
            # 将军/终局判定跑两遍（实测 16 题多花 ~15 秒）。非法步在这里停下即可。
            try:
                game.move(step)
            except ValueError:
                break
        return frozenset(pieces), frozenset(kinds)


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
