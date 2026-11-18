"""出题器：搜「解杀 / 垫挡 / 护子 / 兑子 / 转移王」类守题（批次 A / P1-1）。

与 `gen_mate_puzzles.py`（将死题）互补：守题的判据是「轮到玩家走时，
对手下一步就有杀；玩家只有唯一一手能化解，化解后局面回到大致均衡」。

三条硬判据（同时满足才入库）：
1. 玩家执防守方（红），题面轮红走；若轮黑走，黑存在一步将死红 —— 威胁真实存在；
2. 正解首着**不是**将死对方，且走完后黑无法在一步内杀红；
3. 正解后子力差 >= -150（约落后 1.25 兵以内），且**只有这一手**满足前两条
   —— 正解唯一，别的走法要么被杀、要么丢子无补偿（反杀归反击题，不占守题配额）。

 随机摆子 + 规则引擎验证，不做任何手写坐标。种子固定、产物可复现。

用法：
    python scripts/gen_defense_puzzles.py            # 搜到目标数量并打印
    python scripts/gen_defense_puzzles.py --want 6 --seed 7 --out build/defense_candidates.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import (  # noqa: E402
    PIECE_VALUES,
    Color,
    GameState,
    Move,
    Piece,
    PieceType,
)
from xionghan_chess.core.storage import game_document, game_from_document  # noqa: E402

PROFILE = "desktop_complete"
SOLVER = Color.RED
ATTACKER = Color.BLACK

ATTACK_KINDS = (
    PieceType.ROOK,
    PieceType.CANNON,
    PieceType.HORSE,
    PieceType.ARCHER,
    PieceType.THUNDER,
    PieceType.GUARD,
    PieceType.PATROL,
)
DEFEND_KINDS = (
    PieceType.ROOK,
    PieceType.CANNON,
    PieceType.HORSE,
    PieceType.GUARD,
    PieceType.ARCHER,
    PieceType.THUNDER,
    PieceType.PATROL,
)


def _build(pieces: list[Piece]) -> Game:
    game = Game(PROFILE)
    game.state = GameState(PROFILE, pieces, turn=SOLVER)
    # 用与题库加载完全相同的 document 往返口径重建：否则出题期用默认选项搜到的
    # "唯一解"，加载后（desktop_complete 全开选项）可能冒出第二个化解手，
    # 破坏正解唯一性。往返一次，让搜索与实跑同一套规则。
    document = game_document(game)
    document.pop("snapshots", None)
    document.get("state", {}).pop("positionCounts", None)
    return game_from_document(document)


def _random_position(rng: random.Random) -> list[Piece]:
    taken: set[tuple[int, int]] = set()
    pieces: list[Piece] = []

    def put(kind: PieceType, color: Color, rows: tuple[int, int], cols: tuple[int, int]) -> bool:
        for _ in range(40):
            row, col = rng.randint(*rows), rng.randint(*cols)
            if (row, col) in taken:
                continue
            taken.add((row, col))
            pieces.append(Piece.create(kind, color, row, col))
            return True
        return False

    # 红王在红九宫附近，黑王在黑九宫（只提供合法性，不参与杀）
    if not put(PieceType.KING, SOLVER, (9, 11), (5, 7)):
        return []
    if not put(PieceType.KING, ATTACKER, (0, 2), (5, 7)):
        return []
    # 黑攻子 1-2 枚，压在红王附近
    for kind in rng.sample(ATTACK_KINDS, rng.randint(1, 2)):
        if not put(kind, ATTACKER, (5, 11), (2, 10)):
            return []
    # 红守子固定 2 枚大子，让子力差落在「落后 1.25 兵以内」可达的范围，
    # 这样垫挡/护子/转移王（不吃子）的解也能通过均衡判据，而不只剩「王吃子」。
    for kind in rng.sample(DEFEND_KINDS, 2):
        if not put(kind, SOLVER, (7, 12), (2, 10)):
            return []
    return pieces


def _mate_in_one(game: Game, state: GameState, by: Color) -> Move | None:
    """`state.turn` 为 `by` 时，是否存在一步将死对方。"""
    for move in game.rules.legal_moves(state, by):
        nxt = game.rules.apply_unchecked(state, move)
        if game.rules.checkmate(nxt, by.opponent):
            return move
    return None


def _balance(state: GameState) -> int:
    return sum(
        PIECE_VALUES.get(piece.type.value, 0) * (1 if piece.color is SOLVER else -1) for piece in state.pieces
    )


def _action(game: Game, state: GameState, move: Move, threat: Move) -> str:
    """给正解归类，方便人工核对判据②。"""
    king = next(p for p in state.pieces if p.type is PieceType.KING and p.color is SOLVER)
    if game.rules.captured_by_move(state, move):
        return "兑子/护子"
    if move.source == king.position:
        return "转移王"
    if (
        min(move.target.row, threat.target.row)
        <= king.position.row
        <= max(move.target.row, threat.target.row)
        and min(move.target.col, threat.target.col)
        <= king.position.col
        <= max(move.target.col, threat.target.col)
    ):
        return "垫挡"
    return "解将/其他"


def _candidate(game: Game, threat: Move) -> dict | None:
    king = next(p for p in game.state.pieces if p.type is PieceType.KING and p.color is SOLVER)
    savers: list[tuple[Move, GameState]] = []
    for move in game.rules.legal_moves(game.state, SOLVER):
        # 排除「王直接吃掉贴脸威胁子」——那种题战术太单调，留少量即可。
        if move.source == king.position and game.rules.captured_by_move(game.state, move):
            continue
        nxt = game.rules.apply_unchecked(game.state, move)
        # 正解不能是将死对方（那是反击题）
        if game.rules.checkmate(nxt, ATTACKER):
            continue
        # 化解后黑方一步内不得再杀
        if _mate_in_one(game, nxt, ATTACKER) is not None:
            continue
        # 局面回到约落后 1.25 兵以内
        if _balance(nxt) < -150:
            continue
        savers.append((move, nxt))
    if len(savers) != 1:
        return None
    move, _ = savers[0]
    document = game_document(game)
    document.pop("snapshots", None)
    document.get("state", {}).pop("positionCounts", None)
    return {
        "document": document,
        "solution": [
            {
                "from": {"row": move.source.row, "col": move.source.col},
                "to": {"row": move.target.row, "col": move.target.col},
            }
        ],
        "threat": {
            "from": {"row": threat.source.row, "col": threat.source.col},
            "to": {"row": threat.target.row, "col": threat.target.col},
        },
        "action": _action(game, game.state, move, threat),
        "balance": _balance(game.state),
        "pieces": [
            {"type": p.type.value, "color": p.color.value, "row": p.position.row, "col": p.position.col}
            for p in game.state.pieces
        ],
    }


def collect(*, want: int, seed: int, deadline_s: float) -> list[dict]:
    rng = random.Random(seed)
    found: list[dict] = []
    seen: set[str] = set()
    attempts = 0
    deadline = time.monotonic() + deadline_s
    while len(found) < want and time.monotonic() < deadline:
        attempts += 1
        pieces = _random_position(rng)
        if not pieces:
            continue
        game = _build(pieces)
        if game.state.finished:
            continue
        # 判据①：轮黑走时黑有一步杀（红若不处理即输）
        black_turn = replace(game.state, turn=ATTACKER)
        threat = _mate_in_one(game, black_turn, ATTACKER)
        if threat is None:
            continue
        key = json.dumps(
            sorted((p["type"], p["color"], p["row"], p["col"]) for p in _pieces_dict(pieces)), sort_keys=True
        )
        if key in seen:
            continue
        seen.add(key)
        candidate = _candidate(game, threat)
        if candidate is None:
            continue
        found.append(candidate)
        print(
            f"  #{len(found)} {candidate['action']} balance={candidate['balance']} "
            f"sol={candidate['solution'][0]} threat={candidate['threat']}",
            flush=True,
        )
    print(f"尝试 {attempts} 个局面，得到 {len(found)} 条守题")
    return found


def _pieces_dict(pieces: list[Piece]) -> list[dict]:
    return [{"type": p.type.value, "color": p.color.value, "row": p.position.row, "col": p.position.col} for p in pieces]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--want", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20261117)
    parser.add_argument("--deadline", type=float, default=180.0, help="搜索秒数上限")
    parser.add_argument("--out", default="build/defense_candidates.json")
    args = parser.parse_args()
    items = collect(want=args.want, seed=args.seed, deadline_s=args.deadline)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写出 {out} ({len(items)} 条)")
    return 0 if items else 1


if __name__ == "__main__":
    raise SystemExit(main())
