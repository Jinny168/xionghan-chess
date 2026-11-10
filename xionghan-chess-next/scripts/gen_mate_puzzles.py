"""用规则引擎生成「一步杀」排局，并逐题验证。

思路：随机摆出稀疏局面，枚举走子，筛出「走完即将死对方」的着法。
只保留杀法唯一或极少、且用到了特色棋子的局面。

产物：webapp/js/data/mate-puzzles.json
"""

from __future__ import annotations

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
from xionghan_chess.core.rules import RulesEngine  # noqa: E402

OUT = ROOT / "webapp" / "js" / "data" / "mate-puzzles.json"

# 攻方可用的棋子：优先展示变体特色
ATTACK_TYPES = [
    PieceType.ARCHER,
    PieceType.THUNDER,
    PieceType.GUARD,
    PieceType.CANNON,
    PieceType.HORSE,
    PieceType.ROOK,
    PieceType.PAWN,
    PieceType.ARMOR,
    PieceType.ASSASSIN,
    PieceType.ELEPHANT,
    PieceType.ADVISOR,
]

TITLES = {
    PieceType.ARCHER: "星轨封喉",
    PieceType.THUNDER: "檑震中军",
    PieceType.GUARD: "尉卫跃杀",
    PieceType.CANNON: "重炮锁宫",
    PieceType.HORSE: "卧槽绝杀",
    PieceType.ROOK: "俥压九宫",
    PieceType.PAWN: "兵临城下",
    PieceType.ARMOR: "甲胄合击",
    PieceType.ASSASSIN: "刺客同归",
    PieceType.ELEPHANT: "相眼封门",
    PieceType.ADVISOR: "仕角抽将",
}


CN_NAMES = {
    "archer": "射",
    "thunder": "檑",
    "guard": "尉",
    "cannon": "炮",
    "horse": "马",
    "rook": "车",
    "pawn": "兵",
    "armor": "甲",
    "assassin": "刺",
    "elephant": "相",
    "advisor": "仕",
    "king": "帅",
    "shield": "楯",
    "patrol": "巡",
}


def build(profile_id: str, pieces: list[Piece], turn: Color) -> Game:
    game = Game(profile_id)
    state = GameState(profile_id, pieces, turn=turn)
    state.clocks_ms = {Color.RED: 1_200_000, Color.BLACK: 1_200_000}
    game.state = state
    return game


def random_position(rng: random.Random, attacker: Color) -> list[Piece] | None:
    taken: set[tuple[int, int]] = set()
    pieces: list[Piece] = []

    def put(kind: PieceType, color: Color, row_range, col_range) -> bool:
        for _ in range(60):
            row = rng.randint(*row_range)
            col = rng.randint(*col_range)
            if (row, col) in taken:
                continue
            taken.add((row, col))
            pieces.append(Piece.create(kind, color, row, col))
            return True
        return False

    defender = Color.BLACK if attacker is Color.RED else Color.RED
    king_zone = (0, 4) if attacker is Color.RED else (8, 12)
    home_zone = (8, 12) if attacker is Color.RED else (0, 4)

    if not put(PieceType.KING, defender, king_zone, (3, 9)):
        return None
    if not put(PieceType.KING, attacker, home_zone, (3, 9)):
        return None

    kinds = rng.sample(ATTACK_TYPES, rng.randint(2, 4))
    for kind in kinds:
        if not put(kind, attacker, (max(0, king_zone[0] - 1), min(12, king_zone[1] + 3)), (0, 12)):
            return None
    # 守方给一两枚挡子，避免过于空洞
    for _ in range(rng.randint(0, 2)):
        kind = rng.choice([PieceType.ADVISOR, PieceType.SHIELD, PieceType.GUARD, PieceType.ARMOR, PieceType.PAWN])
        if not put(kind, defender, (max(0, king_zone[0] - 1), min(12, king_zone[1] + 3)), (2, 10)):
            return None
    return pieces


def main() -> None:
    rng = random.Random(1024)
    profile_id = "desktop_complete"
    profile = Game(profile_id).profile
    engine = RulesEngine(profile, profile.options)

    found: list[dict] = []
    seen: set[tuple] = set()
    attempts = 0
    per_type: dict[str, int] = {}
    # 每种棋子最多两道，保证类型分布
    while len(found) < 12 and attempts < 20000:
        attempts += 1
        attacker = rng.choice([Color.RED, Color.BLACK])
        pieces = random_position(rng, attacker)
        if not pieces:
            continue
        key = tuple(sorted((p.color.value, p.type.value, p.position.row, p.position.col) for p in pieces))
        if key in seen:
            continue
        seen.add(key)
        game = build(profile_id, pieces, attacker)
        if engine.in_check(game.state, attacker):
            continue
        legal = engine.legal_moves(game.state)
        mates = []
        for move in legal:
            nxt = engine.apply_unchecked(game.state, move)
            defender = Color.BLACK if attacker is Color.RED else Color.RED
            if engine.in_check(nxt, defender) and not engine.legal_moves(nxt, defender):
                mates.append(move)
        if not 1 <= len(mates) <= 2:
            continue
        move = mates[0]
        mover = next(p for p in pieces if p.position.row == move.source.row and p.position.col == move.source.col)
        if mover.type not in TITLES:
            continue
        if per_type.get(mover.type.value, 0) >= 2:
            continue
        per_type[mover.type.value] = per_type.get(mover.type.value, 0) + 1
        found.append(
            {
                "id": f"mate-{mover.type.value}-{len(found) + 1}",
                "title": TITLES[mover.type],
                "level": "tactics",
                "desc": f"用{CN_NAMES.get(mover.type.value, mover.type.value)}一步将死。",
                "profileId": profile_id,
                "type": "mate",
                "turn": attacker.value,
                "pieces": [
                    {"type": p.type.value, "color": p.color.value, "row": p.position.row, "col": p.position.col}
                    for p in pieces
                ],
                "solution": [
                    {
                        "from": {"row": m.source.row, "col": m.source.col},
                        "to": {"row": m.target.row, "col": m.target.col},
                        "promotion": m.promotion.value if m.promotion else None,
                    }
                    for m in mates
                ],
                "hint": f"注意{mover.type.value}的杀法，目标是把对方主帅困死。",
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"尝试 {attempts} 次，生成 {len(found)} 道一步杀")
    print("类型分布", per_type)
    for p in found:
        print(" ", p["id"], p["title"], "解法数", len(p["solution"]))


if __name__ == "__main__":
    main()
