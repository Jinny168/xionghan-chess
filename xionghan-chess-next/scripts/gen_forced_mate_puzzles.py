"""出题器：搜索**根局面合法 + 无更短强制胜 + 步步唯一**的强制连杀题（D6 收口）。

## 为什么重写

旧的 `build/_regen_mates_probe.py`（未入库 = 不可复现）有五个缺陷，长出了
gen-34「有 2 手旁杀」、gen-35「根局面黑王已被将军、红首着白吃王」这类假题：

1. `forced_unique()` 要求黑方「恰好一个应手」，一手即杀的红着恰好 0 应手 → 被过滤，
   更短杀既不算解也不算不合格；
2. `root_solutions()` 同源继承该漏洞，唯一性判断看不到更短杀；
3. `forced_unique()` 找到第一条就 return，后续红方节点的多解不暴露；
4. 无「根局面黑方不得已被将军」前置条件；
5. 未入库。

## 三道闸（本脚本的判据）

- **C1 根局面合法**：`not state.finished`、`not in_check(BLACK)`、黑方合法应手 ≥ 1。
- **C2 无更短强制胜**：红方最短取胜手数必须 >= 声明手数（ply）。「取胜」统一定义为
  **黑方无合法应手**（含将死与困毙——本作困毙判走方胜，对 counter 连杀题同样算「更短解」），
  以及**吃王**。检测按 ply 分档：
    * k=1、k=3（红 1~2 手）**穷举**所有红着法（含非将军着法，gen-34 的 `12,8-11,8`
      这种「红帅平移不将军」的 3 ply 旁杀就靠这里抓）；
    * k=5（红 3 手）用**只走将军着法**的红方剪枝（近似判据：稀疏残局里红方非将军着法
      5 ply 内强杀几乎不可能，故剪掉以控成本）。
- **C3 步步唯一**：沿正解线路**遍历全部候选而非首个命中**——每个红方节点「能续出强制
  取胜的红着」恰好 1 个；每个黑方节点合法应手恰好 1 个；末手必须是 `checkmate(BLACK)`
  真将死（困毙不算连杀）。

## 用法

    python scripts/gen_forced_mate_puzzles.py --check          # 校验题库现有 counter 题（C1/C2/C3）
    python scripts/gen_forced_mate_puzzles.py --write           # 搜索并生成 build/cand_mate7.json
    python scripts/gen_forced_mate_puzzles.py --apply           # 把候选外科手术写入 gen-34/gen-35
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

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, GameState, Move, Piece, PieceType, Position  # noqa: E402
from xionghan_chess.core.storage import game_document, game_from_document  # noqa: E402

DATA = ROOT / "src" / "xionghan_chess" / "core" / "data" / "puzzles.json"
CAND7 = ROOT / "build" / "cand_mate7.json"

RED = Color.RED
BLACK = Color.BLACK

# 与 gen-31 同档规则（web profile + 该题 options）。
_BANK = json.loads(DATA.read_text(encoding="utf-8"))
OPTIONS = next(p for p in _BANK if p["id"] == "gen-31")["document"]["options"]

ATTACKERS = [
    PieceType.ROOK,
    PieceType.CANNON,
    PieceType.HORSE,
    PieceType.ARCHER,
    PieceType.ELEPHANT,
    PieceType.PAWN,
    PieceType.THUNDER,
    PieceType.ADVISOR,
]
BLOCKERS = [PieceType.ADVISOR, PieceType.PAWN, PieceType.ELEPHANT, PieceType.ROOK]


# ------------------------------------------------------------------ 局面构造


def game_from_pieces(pieces: list[Piece]) -> Game:
    game = Game("web", option_overrides=OPTIONS)
    state = GameState("web", pieces, turn=RED)
    state.clocks_ms = {RED: 1_200_000, BLACK: 1_200_000}
    game.state = state
    return game


def _document(game: Game) -> dict:
    """固定题面文档：去掉 snapshots / 三次重复记账（防载入即判和，且与 build_puzzles 同口径）。"""
    document = game_document(game)
    document.pop("snapshots", None)
    document.get("state", {}).pop("positionCounts", None)
    return document


def _black_lost(eng, state: GameState) -> bool:
    """红方刚走完（state.turn 已是黑）：黑方输了吗？

    输 = 黑王被吃（吃王）或黑方无合法应手（将死 / 困毙）。困毙在本作判走方胜，
    对 counter 连杀题同样算「更短解」，故与将死一视同仁。
    """
    if not any(p.type is PieceType.KING and p.color is BLACK for p in state.pieces):
        return True
    return not eng.has_any_legal_move(state, BLACK)


def _root_legal(game: Game) -> tuple[bool, str]:
    """C1：根局面合法。"""
    if game.state.finished:
        return False, "题面已是终局"
    if game.rules.in_check(game.state, BLACK):
        return False, "根局面黑方已被将军（轮到红走却黑被将，非法）"
    if not game.rules.has_any_legal_move(game.state, BLACK):
        return False, "根局面黑方无合法应手"
    return True, ""


# ------------------------------------------------------------------ 强制胜搜索


class _Budget(Exception):
    """搜索节点预算耗尽。保守拒绝该候选（无法在预算内确认唯一），不误判为合格。"""


def _forced_win(eng, state: GameState, plies: int, *, king_only: bool, budget: list[int] | None = None) -> bool:
    """轮到红方，红方能否在 `plies` 内强制取胜（黑方终局无合法应手 / 被吃王）。plies 为奇数。

    `king_only=True` 时红方只走将军着法 —— 这是 C2 的 k=5 近似剪枝，不是精确判据。
    `budget` 是可变单元素列表（剩余节点数），耗尽抛 `_Budget`，防止大优局面把 C3 拖成指数级。
    """
    for move in eng.legal_moves(state, RED):
        if budget is not None:
            budget[0] -= 1
            if budget[0] <= 0:
                raise _Budget
        nxt = eng.apply_unchecked(state, move)  # 轮到黑
        if king_only and not eng.in_check(nxt, BLACK):
            continue
        if _black_lost(eng, nxt):
            return True
        if plies <= 1:
            continue
        replies = eng.legal_moves(nxt, BLACK)
        if not replies:
            continue
        if all(
            _forced_win(eng, eng.apply_unchecked(nxt, r), plies - 2, king_only=king_only, budget=budget)
            for r in replies
        ):
            return True
    return False


def _winning_red_moves(eng, state: GameState, plies: int, *, max_need: int = 2) -> list[Move]:
    """红方「能续出强制取胜」的着法（严格，含非将军着法）。用于 C3 唯一性。

    `max_need` 是早停上限：C3 只需判「是否恰好 1」，所以数到 2 个就能确定不唯一，
    不必把大优局面里几十个致胜着法全部展开（那是 gen-34 那种假题被 C3 拖死的根源）。
    """
    out: list[Move] = []
    budget = [200000]
    for move in eng.legal_moves(state, RED):
        nxt = eng.apply_unchecked(state, move)
        if _black_lost(eng, nxt):
            out.append(move)
        elif plies > 1:
            replies = eng.legal_moves(nxt, BLACK)
            if replies and all(
                _forced_win(eng, eng.apply_unchecked(nxt, r), plies - 2, king_only=False, budget=budget)
                for r in replies
            ):
                out.append(move)
        if len(out) >= max_need:
            return out
    return out


def _shortest_win(eng, state: GameState, cap: int = 9) -> int | None:
    """红方最短强制取胜的 ply 数；超过 cap 返回 None。k=1/3 穷举，k>=5 只将军剪枝。"""
    for plies in range(1, cap + 1, 2):
        if _forced_win(eng, state, plies, king_only=plies >= 5, budget=[500000]):
            return plies
    return None


def _unique_line(eng, state: GameState, plies: int) -> list[Move] | None:
    """C3：严格唯一强制线。每个红方节点致胜着法恰 1、每个黑方节点应手恰 1、末手真将死。"""
    wins = _winning_red_moves(eng, state, plies, max_need=2)
    if len(wins) != 1:
        return None
    move = wins[0]
    nxt = eng.apply_unchecked(state, move)
    if plies == 1:
        # 末手必须是真将死（困毙不算连杀）。
        return [move] if eng.checkmate(nxt, BLACK) else None
    replies = eng.legal_moves(nxt, BLACK)
    if len(replies) != 1:
        return None
    reply = replies[0]
    tail = _unique_line(eng, eng.apply_unchecked(nxt, reply), plies - 2)
    return None if tail is None else [move, reply, *tail]


def verify_doc(document: dict, solution: list[dict]) -> tuple[bool, str]:
    """C1+C2+C3 综合校验（真实加载路径）。供 --check 与 --apply 用。"""
    game = game_from_document(document)
    legal, why = _root_legal(game)
    if not legal:
        return False, f"C1 失败：{why}"
    declar = len(solution)
    try:
        shortest = _shortest_win(game.rules, game.state)
        if shortest is not None and shortest < declar:
            return False, f"C2 失败：存在更短强制胜（最短 {shortest} ply < 声明 {declar} ply）"
        line = _unique_line(game.rules, game.state, declar)
    except _Budget:
        return False, "预算耗尽，无法在限内确认唯一（保守拒绝，不假绿）"
    if line is None:
        return False, "C3 失败：正解线路某红方节点不唯一 / 黑方应手不唯一 / 末手非真将死"
    if [m.key() for m in line] != [
        Move(Position(s["from"]["row"], s["from"]["col"]), Position(s["to"]["row"], s["to"]["col"])).key()
        for s in solution
    ]:
        return False, "C3 失败：唯一强制线与给出的 solution 不一致"
    return True, f"C1/C2/C3 通过（最短 {shortest if shortest is not None else '>9'} ply，声明 {declar} ply）"


# ------------------------------------------------------------------ 生成


def _mv_dict(move: Move) -> dict:
    return {"from": {"row": move.source.row, "col": move.source.col}, "to": {"row": move.target.row, "col": move.target.col}}


def _fast_mate_line(eng, state: GameState, plies: int, budget: list[int]) -> list[Move] | None:
    """快速发现候选：红只走将军着法、黑必唯一应手、末手真将死（不查红方唯一性）。"""
    if budget[0] <= 0:
        return None
    budget[0] -= 1
    if plies == 1:
        for move in eng.legal_moves(state, RED):
            if eng.checkmate(eng.apply_unchecked(state, move), BLACK):
                return [move]
        return None
    for move in eng.legal_moves(state, RED):
        if budget[0] <= 0:
            return None
        budget[0] -= 1
        nxt = eng.apply_unchecked(state, move)
        if not eng.in_check(nxt, BLACK):
            continue
        replies = eng.legal_moves(nxt, BLACK)
        if len(replies) != 1:
            continue
        reply = replies[0]
        sub = _fast_mate_line(eng, eng.apply_unchecked(nxt, reply), plies - 2, budget)
        if sub is not None:
            return [move, reply, *sub]
    return None


def _random_pieces(rng: random.Random) -> list[Piece]:
    taken: set[tuple[int, int]] = set()

    def put(kind: PieceType, color: Color, rows: tuple[int, int], cols: tuple[int, int]) -> Piece | None:
        for _ in range(80):
            row, col = rng.randint(*rows), rng.randint(*cols)
            if (row, col) in taken:
                continue
            taken.add((row, col))
            return Piece.create(kind, color, row, col)
        return None

    pieces: list[Piece] = []
    bk = put(PieceType.KING, BLACK, (0, 1), (1, 11))
    rk = put(PieceType.KING, RED, (11, 12), (2, 10))
    if not bk or not rk:
        return []
    pieces += [bk, rk]
    for _ in range(rng.randint(2, 3)):
        p = put(rng.choice(ATTACKERS), RED, (0, 7), (0, 12))
        if p:
            pieces.append(p)
    for _ in range(rng.randint(0, 2)):
        p = put(rng.choice(BLOCKERS), BLACK, (0, 4), (0, 12))
        if p:
            pieces.append(p)
    return pieces


def _entry_from_line(line: list[Move], document: dict, index: int) -> dict:
    hands = (len(line) + 1) // 2
    hints = [f"第 {i + 1} 手：{('先想将军' if i < hands - 1 else '收网')}" for i in range(hands)]
    return {
        "id": f"gen-forced-{len(line)}ply-{index:02d}",
        "title": f"强制杀·{hands} 手 {index:02d}",
        "difficulty": "master" if len(line) >= 7 else "advanced",
        "description": f"对手每步都只有唯一应法，走出唯一的{_hand_cn(hands)}连杀。",
        "document": document,
        "solution": [_mv_dict(m) for m in line],
        "hints": hints,
        "tags": ["generated", f"mate{len(line)}", "counter"],
    }


def _hand_cn(hands: int) -> str:
    return {1: "一手", 2: "两手", 3: "三手", 4: "四手", 5: "五手"}.get(hands, f"{hands} 手")


def search(plies: int, *, tries: int, seed: int, want: int, deadline_s: float) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    found: list[dict] = []
    stats = {"tries": 0, "c1_reject": 0, "no_line": 0, "verify_reject": 0, "elapsed": 0.0}
    started = time.monotonic()
    for t in range(tries):
        if time.monotonic() - started > deadline_s or len(found) >= want:
            break
        stats["tries"] = t + 1
        pieces = _random_pieces(rng)
        if not pieces:
            continue
        game = game_from_pieces(pieces)
        legal, _ = _root_legal(game)
        if not legal:
            stats["c1_reject"] += 1
            continue
        line = _fast_mate_line(game.rules, game.state, plies, [20000])
        if line is None:
            stats["no_line"] += 1
            continue
        document = _document(game)
        ok, _note = verify_doc(document, [_mv_dict(m) for m in line])
        if not ok:
            stats["verify_reject"] += 1
            continue
        found.append(_entry_from_line(line, document, len(found) + 1))
        print(f"  FOUND try={t} ply={plies} pieces={[(p.type.value, p.position.row, p.position.col) for p in pieces]}", flush=True)
    stats["elapsed"] = time.monotonic() - started
    return found, stats


# ------------------------------------------------------------------ main


def _write_candidates() -> int:
    """搜 mate7；搜不出合规 7 ply 就退回 5 ply（同一套闸），返回候选列表。

    7 ply 在稀疏残局里极稀有（实测 3 seed × 数百次零命中、~0.38s/次），故 7 ply
    只做短探测，不足即降 5 ply 长搜。降级情况在 stdout 显式打印，回报里单列。
    """
    for plies, deadline in ((7, 80), (5, 900)):
        for seed in (7, 99, 2026):
            print(f"=== 搜 {plies} ply  seed={seed}  deadline={deadline}s ===", flush=True)
            found, stats = search(plies, tries=200000, seed=seed, want=2, deadline_s=deadline)
            print(f"  统计 {stats}", flush=True)
            if len(found) >= 2:
                CAND7.parent.mkdir(parents=True, exist_ok=True)
                CAND7.write_text(json.dumps(found, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
                print(f"已写出 {CAND7}（{len(found)} 条 {plies} ply）", flush=True)
                return 0
            print(f"  {plies} ply seed={seed} 只搜到 {len(found)} 条，换 seed/档位", flush=True)
    print("所有 seed 都搜不出合规候选", flush=True)
    return 1


def _check_bank() -> int:
    items = json.loads(DATA.read_text(encoding="utf-8"))
    counter = [p for p in items if "counter" in p.get("tags", [])]
    print(f"校验 {len(counter)} 条 counter 题：{ [p['id'] for p in counter] }")
    bad = 0
    for p in counter:
        ok, note = verify_doc(p["document"], p["solution"])
        print(f"  {p['id']} {p['title']}: {'OK' if ok else 'FAIL'}  {note}")
        if not ok:
            bad += 1
    return 1 if bad else 0


def _apply_candidates() -> int:
    """把 build/cand_mate7.json 前两条候选外科手术写入 gen-34/gen-35（其余不动）。"""
    cands = json.loads(CAND7.read_text(encoding="utf-8"))
    if len(cands) < 2:
        print(f"候选不足 2 条（{len(cands)}）")
        return 1
    items = json.loads(DATA.read_text(encoding="utf-8"))
    target_ids = ["gen-34", "gen-35"]
    for pid, cand in zip(target_ids, cands[:2]):
        ok, note = verify_doc(cand["document"], cand["solution"])
        if not ok:
            print(f"{pid} 候选校验失败：{note}")
            return 1
        entry = next(p for p in items if p["id"] == pid)
        declar = len(cand["solution"])
        hands = (declar + 1) // 2
        entry["document"] = cand["document"]
        entry["solution"] = cand["solution"]
        entry["tags"] = ["generated", f"mate{declar}", "counter"]
        entry["description"] = f"对手每步都只有唯一应法，走出唯一的{_hand_cn(hands)}连杀。"
        entry["hints"] = cand["hints"]
        print(f"{pid} 已更新（{hands} 手 {declar} ply）：{note}")
    DATA.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"written {DATA}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="校验题库现有 counter 题（C1/C2/C3）")
    parser.add_argument("--write", action="store_true", help="搜索并生成 build/cand_mate7.json")
    parser.add_argument("--apply", action="store_true", help="把候选写入 gen-34/gen-35")
    args = parser.parse_args()
    if args.check:
        return _check_bank()
    if args.write:
        return _write_candidates()
    if args.apply:
        return _apply_candidates()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
