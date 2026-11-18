"""出题器：搜「用本作特色子（射/巡/檑/尉）完成唯一将死」的题（批次 A / P1-1）。

与 `gen_mate_puzzles.py` 互补：那里按任意棋子产出一步杀供 webapp 消费，
这里专门锁死**正解首着必须是某枚特色子**，且**全局面只有这一手能将死**
——这样题目描述才能诚实地说"这题考的是〈某条特色规则〉"，而不是摆着射、
实际用炮杀。

四种特色子各搜若干条候选，供人工挑选后写入 core 题库：
  · 射（archer）——星轨斜线 / 加强斜走三格，吃子无视阻挡；
  · 巡（patrol）——只沿横线走偶数格，吃子仅限距离 2；
  · 檑（thunder）——直线或斜线，吃"孤立"的敌子；
  · 尉（guard）——斜向任意距离，路径须无子。

硬判据：
1. 题面轮红走、红非被将，黑王在黑九宫附近；
2. 唯一将死着法的**首着子力 == 目标特色子**（其它走法都不能一步将死）；
3. 局面非终局、棋子数受控（残局密度）。

随机摆子 + 规则引擎验证，种子固定、产物可复现。

用法：
    python scripts/gen_feature_puzzles.py --out build/feature_candidates.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import (  # noqa: E402
    Color,
    GameState,
    Piece,
    PieceType,
)
from xionghan_chess.core.storage import game_document  # noqa: E402

PROFILE = "desktop_complete"
SOLVER = Color.RED
ATTACKER_KING = Color.BLACK

FEATURES = (PieceType.ARCHER, PieceType.PATROL, PieceType.THUNDER, PieceType.GUARD)

RULE_NOTE = {
    "archer": "射的星轨斜线（加强版可斜走三格、吃子无视阻挡）",
    "patrol": "巡只沿横线走偶数格、吃子仅限距离 2",
    "thunder": "檑走直线或斜线、只能吃孤立的敌子",
    "guard": "尉斜向任意距离、路径须无子",
}

SCREEN_KINDS = (
    PieceType.ADVISOR,
    PieceType.ELEPHANT,
    PieceType.PAWN,
    PieceType.CANNON,
    PieceType.HORSE,
    PieceType.ROOK,
)


def _build(pieces: list[Piece]) -> Game:
    game = Game(PROFILE)
    game.state = GameState(PROFILE, pieces, turn=SOLVER)
    return game


def _random_position(rng: random.Random, feature: PieceType) -> list[Piece] | None:
    taken: set[tuple[int, int]] = set()
    pieces: list[Piece] = []

    def put(kind: PieceType, color: Color, rows: tuple[int, int], cols: tuple[int, int]) -> bool:
        for _ in range(80):
            row, col = rng.randint(*rows), rng.randint(*cols)
            if (row, col) in taken:
                continue
            taken.add((row, col))
            pieces.append(Piece.create(kind, color, row, col))
            return True
        return False

    # 黑王（被将方）在黑九宫附近；红王远离、只提供合法性。
    if not put(PieceType.KING, ATTACKER_KING, (0, 2), (5, 7)):
        return None
    if not put(PieceType.KING, SOLVER, (10, 12), (5, 7)):
        return None
    # 目标特色子（红），压在黑王附近的行。
    if not put(feature, SOLVER, (2, 7), (2, 10)):
        return None
    # 1-2 枚红副攻子，帮助形成将死网。
    for kind in rng.sample([k for k in SCREEN_KINDS if k != feature], rng.randint(1, 2)):
        if not put(kind, SOLVER, (2, 9), (1, 11)):
            return None
    # 0-2 枚黑挡子，让将死有"破解"的意味但仍唯一。
    for _ in range(rng.randint(0, 2)):
        kind = rng.choice(SCREEN_KINDS)
        if not put(kind, ATTACKER_KING, (0, 5), (2, 10)):
            return None
    return pieces


def _mate_moves(game: Game) -> list:
    mates = []
    for move in game.rules.legal_moves(game.state, SOLVER):
        nxt = game.rules.apply_unchecked(game.state, move)
        if game.rules.checkmate(nxt, ATTACKER_KING):
            mates.append(move)
    return mates


def collect(*, per_feature: int, seed: int, deadline_s: float) -> list[dict]:
    import time

    rng = random.Random(seed)
    found: list[dict] = []
    per_type: dict[str, int] = {f.value: 0 for f in FEATURES}
    seen: set[tuple] = set()
    attempts = 0
    deadline = time.monotonic() + deadline_s
    while len(found) < per_feature * len(FEATURES) and time.monotonic() < deadline:
        attempts += 1
        feature = FEATURES[len(found) % len(FEATURES)]
        if per_type[feature.value] >= per_feature:
            # 该类型已够，换下一个还没满的类型
            remaining = [f for f in FEATURES if per_type[f.value] < per_feature]
            if not remaining:
                break
            feature = remaining[0]
        pieces = _random_position(rng, feature)
        if not pieces:
            continue
        key = tuple(sorted((p.color.value, p.type.value, p.position.row, p.position.col) for p in pieces))
        if key in seen:
            continue
        seen.add(key)
        game = _build(pieces)
        if game.state.finished or game.rules.in_check(game.state, SOLVER):
            continue
        mates = _mate_moves(game)
        if len(mates) != 1:
            continue
        move = mates[0]
        mover = game.rules.get(game.state, move.source)
        if mover is None or mover.type is not feature:
            continue
        document = game_document(game)
        document.pop("snapshots", None)
        document.get("state", {}).pop("positionCounts", None)
        found.append(
            {
                "feature": feature.value,
                "rule_note": RULE_NOTE[feature.value],
                "document": document,
                "solution": [
                    {"from": {"row": move.source.row, "col": move.source.col},
                     "to": {"row": move.target.row, "col": move.target.col}}
                ],
                "pieces": [
                    {"type": p.type.value, "color": p.color.value, "row": p.position.row, "col": p.position.col}
                    for p in pieces
                ],
            }
        )
        per_type[feature.value] += 1
        print(f"  #{len(found)} {feature.value} sol={found[-1]['solution'][0]}", flush=True)
    print(f"尝试 {attempts} 个局面，得到 {len(found)} 条特色子题；分布 {per_type}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-feature", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261123)
    parser.add_argument("--deadline", type=float, default=180.0)
    parser.add_argument("--out", default="build/feature_candidates.json")
    args = parser.parse_args()
    items = collect(per_feature=args.per_feature, seed=args.seed, deadline_s=args.deadline)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写出 {out} ({len(items)} 条)")
    return 0 if items else 1


if __name__ == "__main__":
    raise SystemExit(main())
