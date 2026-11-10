"""出题器：从少量子力的局面里搜「强制杀」，直接产出可入库的题目条目。

为什么必须有它：设计定稿要求每条题满足「首着唯一 + 每手最强 + 对手应着强制」。
手写做不到这三条 —— 现有 13 条题的实测结果是「一步杀着法数全为 0」，
即根本不是杀题（见 `scripts/puzzle_doctor.py` 的报告）。

搜索约定：
- **强制**指对手在这一步只有唯一合法着法。只要出现两个以上应着，这条线就作废
  —— 多步题的强度来自"对手最优抵抗"，给了选择就不再是唯一解。
- 解的形态是交替序列：`[我, 对手, 我, 对手, 我]`（长度为奇数）。
- 用 `game.move()/undo()` 就地回溯，不复制局面（复制一次要序列化整个 state）。

用法：
    python scripts/author_puzzles.py --limit 400 --plies 3
    python scripts/author_puzzles.py --plies 5 --out build/candidates5.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.game import Game, GameError  # noqa: E402
from xionghan_chess.core.model import Color, Move, Piece, PieceType  # noqa: E402
from xionghan_chess.core.storage import game_document  # noqa: E402

# 出题只用红方作为解方（题面固定"轮到你走"），黑方是被杀的一方
SOLVER = Color.RED


def _board_game() -> Game:
    game = Game("web")
    game.state.pieces = []
    return game


def _place_kings(game: Game, black: tuple[int, int], red: tuple[int, int]) -> None:
    game.state.pieces = [
        Piece.create(PieceType.KING, Color.BLACK, *black),
        Piece.create(PieceType.KING, Color.RED, *red),
    ]
    game.state.turn = SOLVER


def _add(game: Game, kind: PieceType, color: Color, row: int, col: int) -> None:
    game.state.pieces.append(Piece.create(kind, color, row, col))


def _legal(game: Game) -> list[Move]:
    return game.rules.legal_moves(game.state, game.state.turn)


def _mated(game: Game) -> bool:
    return game.state.finished or not _legal(game)


def _forced_line(game: Game, player_moves: int, budget: list[int]) -> list[Move] | None:
    """找一条长度为 2n-1 的强制杀线；找不到返回 None。

    `budget[0]` 是全局节点预算 —— 局面一多，没有预算会跑成小时级。
    """
    if player_moves <= 0 or budget[0] <= 0:
        return None
    for move in _legal(game):
        budget[0] -= 1
        if budget[0] <= 0:
            return None
        try:
            game.move(move)
        except (GameError, ValueError):
            continue
        try:
            replies = _legal(game)
            if not replies:
                return [move]  # 一步杀
            if len(replies) != 1:
                continue  # 对手有选择 → 这条线不唯一
            reply = replies[0]
            game.move(reply)
            try:
                tail = _forced_line(game, player_moves - 1, budget)
            finally:
                game.undo(1, allow_finished=True)
            if tail is not None:
                return [move, reply, *tail]
        finally:
            game.undo(1, allow_finished=True)
    return None


def _all_lines(game: Game, player_moves: int, budget: list[int]) -> list[list[Move]]:
    """收集所有能强制完成的**首着**（用来判唯一性）。"""
    lines: list[list[Move]] = []
    for move in _legal(game):
        if budget[0] <= 0:
            break
        budget[0] -= 1
        try:
            game.move(move)
        except (GameError, ValueError):
            continue
        try:
            replies = _legal(game)
            if not replies:
                lines.append([move])
                continue
            if len(replies) != 1:
                continue
            reply = replies[0]
            game.move(reply)
            try:
                tail = _forced_line(game, player_moves - 1, budget)
            finally:
                game.undo(1, allow_finished=True)
            if tail is not None:
                lines.append([move, reply, *tail])
        finally:
            game.undo(1, allow_finished=True)
    return lines


def _valid_start(game: Game) -> bool:
    """题面必须合法：轮到解方走，且解方不是已经死了/把对方将着。"""
    if game.state.finished:
        return False
    if game.rules.in_check(game.state, game.state.turn.opponent):
        return False  # 不该轮到非走子方还被将军
    if not _legal(game):
        return False
    return True


def _random_position(rng: random.Random, attackers: int):
    """在黑方九宫附近随机摆 1-2 个攻子，红王放远处。"""
    game = _board_game()
    black_king = (rng.choice([0, 1, 2]), rng.randint(3, 6))
    red_king = (rng.randint(10, 12), rng.randint(3, 6))
    _place_kings(game, black_king, red_king)

    kinds = [
        PieceType.ROOK,
        PieceType.CANNON,
        PieceType.HORSE,
        PieceType.GUARD,
        PieceType.ARCHER,
        PieceType.THUNDER,
        PieceType.PATROL,
    ]
    for _ in range(attackers):
        kind = rng.choice(kinds)
        for _ in range(12):  # 最多试 12 个落点
            row = rng.randint(0, 5)
            col = rng.randint(0, 12)
            if any(p.position.row == row and p.position.col == col for p in game.state.pieces):
                continue
            _add(game, kind, SOLVER, row, col)
            break
    return game


def _title(kind: str, plies: int, index: int) -> str:
    """标题不许泄露坐标与走法。"""
    return f"{kind}·{plies} 手杀 {index:02d}"


def collect(*, plies: int, limit: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    found: dict[str, dict] = {}
    deadline = time.monotonic() + 240  # 单次运行的时间上限
    for attempt in range(limit):
        if time.monotonic() > deadline:
            break
        game = _random_position(rng, attackers=rng.choice([1, 2]))
        if not _valid_start(game):
            continue
        budget = [4000]
        lines = _all_lines(game, (plies + 1) // 2, budget)
        if len(lines) != 1:  # 必须**恰好一条**强制线
            continue
        line = lines[0]
        if len(line) != plies:
            continue
        document = game_document(_board_game())
        # 重新构建题面文档（上面的 `game` 已经被回溯干净，直接用它的局面）
        document = game_document(game)
        document.pop("snapshots", None)
        document.get("state", {}).pop("positionCounts", None)
        key = document["state"].get("positionKey") or json.dumps(
            [(p.type.value, p.color.value, p.position.row, p.position.col) for p in game.state.pieces], sort_keys=True
        )
        if key in found:
            continue
        found[key] = {
            "id": f"gen-{plies}ply-{len(found) + 1:02d}",
            "title": _title("强制杀", plies, len(found) + 1),
            "difficulty": "beginner" if plies == 3 else "advanced",
            "description": "找出唯一能连续将军的那条路。",
            "document": document,
            "solution": [
                {"from": {"row": m.source.row, "col": m.source.col}, "to": {"row": m.target.row, "col": m.target.col}}
                for m in line
            ],
            "hints": [f"第 {i + 1} 手：先想将军" for i in range((plies + 1) // 2)],
            "tags": ["generated"],
        }
    return list(found.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plies", type=int, default=3, choices=[3, 5, 7])
    parser.add_argument("--limit", type=int, default=400, help="最多尝试多少个随机局面")
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--out", default="build/puzzle_candidates.json")
    args = parser.parse_args()

    started = time.monotonic()
    items = collect(plies=args.plies, limit=args.limit, seed=args.seed)
    elapsed = time.monotonic() - started
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.plies} ply：尝试 {args.limit} 个局面，得到 {len(items)} 条，耗时 {elapsed:.1f}s -> {out}")
    return 0 if items else 1


if __name__ == "__main__":
    raise SystemExit(main())
