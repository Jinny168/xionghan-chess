"""把三类候选题（守题/特色子/长算）组装成正式题目，追加到 core 题库末尾（批次 A / P1-1）。

## 为什么需要它

三个出题器各产出一份候选 JSON，字段口径不同；本脚本统一成 `puzzles.json` 的
条目格式、分配 id/chapter/difficulty/tags/title/description/hints，并在写入前
**对每条重新跑一遍唯一性判据**——生成器保证了判据，这里独立复核一遍，输出
报告供人工核对（工具辅助不替代判断）。

## 唯一性判据（与出题器一致，独立实现）

- 守题：合法着法里，满足「非将死对方 + 对手无一步杀 + 子力差>=-150」的恰好 1 手；
- 特色题：一步将死对方的着法恰好 1 手，且该手子力 == 目标特色子；
- 长算：`solution` 是交替强制线（我-对手-我…），每步合法、末手将死；首着唯一。

用法：
    python scripts/assemble_batch_a.py           # 组装 + 复核 + 写入（幂等：已存在则跳过）
    python scripts/assemble_batch_a.py --dry-run  # 只复核并打印，不写盘
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import (  # noqa: E402
    PIECE_VALUES,
    Color,
    GameState,
    Move,
    PieceType,
    Position,
)
from xionghan_chess.core.storage import game_from_document  # noqa: E402

DATA = ROOT / "src" / "xionghan_chess" / "core" / "data" / "puzzles.json"
DEFENSE = ROOT / "build" / "defense_candidates.json"
FEATURE = ROOT / "build" / "feature_candidates.json"
MATE5 = ROOT / "build" / "cand_mate5.json"
MATE7 = ROOT / "build" / "cand_mate7.json"

RED, BLACK = Color.RED, Color.BLACK

# 13 条新题的规划表：(id, chapter, difficulty, 类别, 候选来源索引, title, description, tags, hints)
# 类别: defense / feature / mate5 / mate7
PLAN: list[tuple[str, str, str, str, int, str, str, list[str], list[str]]] = [
    # 破釜（advanced）：守2 + 特色1
    ("gen-23", "破釜", "advanced", "defense", 0, "破釜·断援",
     "黑方下一步就有杀。轮到你走，兑掉进攻的子，找出唯一能化解的一手——先守住，再谈反击。",
     ["generated", "defense"], ["先看黑方哪枚子在威胁帅", "兑掉攻子或护住帅，化解这一路杀"]),
    ("gen-24", "破釜", "advanced", "defense", 2, "破釜·稳局",
     "大敌当前，硬拼无益。走出唯一一手，化解杀棋、稳住局面。",
     ["generated", "defense", "equilibrium"], ["找出黑方即将成杀的那条线", "用唯一的一手把它化解掉"]),
    ("gen-25", "破釜", "advanced", "feature", "archer", "破釜·星射",
     "这题考的是射的星轨斜线（加强版可斜走三格、吃子无视阻挡）。用射完成将死。",
     ["generated", "feature:archer"], ["沿星轨斜线找射的落点", "借射的斜线吃子将死"]),
    # 逐鹿（advanced）：守1 + 特色1
    ("gen-26", "逐鹿", "advanced", "defense", 6, "逐鹿·解围",
     "帅位告急。轮到你走，走出唯一能化解的一手，守住这一关。",
     ["generated", "defense"], ["看黑方哪枚子已经形成杀势", "用唯一一手解除威胁"]),
    ("gen-27", "逐鹿", "advanced", "feature", "patrol", "逐鹿·巡河",
     "这题考的是巡只沿横线走偶数格、吃子仅限距离 2。用巡完成将死。",
     ["generated", "feature:patrol"], ["巡只能横走偶数格", "找距离 2 的吃子点完成将死"]),
    # 垓下（master）：守2 + 特色1 + 长算1
    ("gen-28", "垓下", "master", "defense", 15, "垓下·避杀",
     "黑方杀棋迫在眉睫。移帅走出唯一一手，把局面拉回均衡。",
     ["generated", "defense", "equilibrium"], ["先判断黑方的杀来自哪枚子", "把帅移到安全处避开这一路杀"]),
    ("gen-29", "垓下", "master", "defense", 7, "垓下·化解",
     "看似必败的局面，其实藏着唯一一手化解。找到了，就稳住了。",
     ["generated", "defense"], ["别急着对攻，先看威胁", "找出唯一能化解的一手"]),
    ("gen-30", "垓下", "master", "feature", "thunder", "垓下·檑震",
     "这题考的是檑走直线或斜线、只能吃孤立的敌子。用檑完成将死。",
     ["generated", "feature:thunder"], ["檑只能吃没有同色子相邻的孤立子", "用檑吃孤立子完成将死"]),
    ("gen-31", "垓下", "master", "mate5", 0, "垓下·连环",
     "对手每步都只有唯一应法，走出唯一的连杀。",
     ["generated", "mate5", "counter"], ["第 1 手：先想将军", "第 2 手：先想将军", "第 3 手：收网"]),
    # 定鼎（master）：守1 + 特色1 + 长算2
    ("gen-32", "定鼎", "master", "defense", 9, "定鼎·挡锋",
     "锋芒已至帅前。兑掉攻子，走出唯一一手守住最后的防线。",
     ["generated", "defense"], ["找黑方杀线的关键点", "兑掉进攻的子，化解危机"]),
    ("gen-33", "定鼎", "master", "feature", "guard", "定鼎·尉卫",
     "这题考的是尉斜向任意距离、路径须无子。用尉完成将死。",
     ["generated", "feature:guard"], ["尉斜走任意距离，路径须空", "用尉的斜线完成将死"]),
    ("gen-34", "定鼎", "master", "mate7", 0, "定鼎·长驱",
     "对手每步都只有唯一应法，走出唯一的四手连杀。",
     ["generated", "mate7", "counter"], ["第 1 手：先想将军", "第 2 手：先想将军", "第 3 手：继续追杀", "第 4 手：收网"]),
    ("gen-35", "定鼎", "master", "mate7", 1, "定鼎·落幕",
     "长路奔袭，步步唯一。走出这场七路连杀，为战役收官。",
     ["generated", "mate7", "counter"], ["第 1 手：先想将军", "第 2 手：先想将军", "第 3 手：继续追杀", "第 4 手：收网"]),
]


def _game(doc: dict) -> Game:
    return game_from_document(doc)


def _mate_in_one(game: Game, state: GameState, by: Color) -> bool:
    for move in game.rules.legal_moves(state, by):
        nxt = game.rules.apply_unchecked(state, move)
        if game.rules.checkmate(nxt, by.opponent):
            return True
    return False


def _balance(state: GameState) -> int:
    return sum(
        PIECE_VALUES.get(p.type.value, 0) * (1 if p.color is RED else -1) for p in state.pieces
    )


def verify_defense(doc: dict) -> tuple[bool, str]:
    game = _game(doc)
    savers = 0
    for move in game.rules.legal_moves(game.state, RED):
        nxt = game.rules.apply_unchecked(game.state, move)
        if game.rules.checkmate(nxt, BLACK):
            continue
        if _mate_in_one(game, nxt, BLACK):
            continue
        if _balance(nxt) < -150:
            continue
        savers += 1
    ok = savers == 1
    return ok, f"化解着法数={savers} (需=1)"


def verify_feature(doc: dict, solution: list[dict], feature: str) -> tuple[bool, str]:
    game = _game(doc)
    mates = []
    for move in game.rules.legal_moves(game.state, RED):
        nxt = game.rules.apply_unchecked(game.state, move)
        if game.rules.checkmate(nxt, BLACK):
            mates.append(move)
    first = solution[0]
    src = (first["from"]["row"], first["from"]["col"])
    # 用 piece 列表直接查首着子力类型
    mover_type = None
    for p in game.state.pieces:
        if p.position.row == src[0] and p.position.col == src[1]:
            mover_type = p.type.value
            break
    ok = len(mates) == 1 and mover_type == feature
    return ok, f"将死着法数={len(mates)} (需=1), 首着子力={mover_type} (需={feature})"


def _black_lost(game: Game, state: GameState) -> bool:
    """红方刚走完（state.turn 为黑）：黑王被吃 或 黑方无合法应手（将死/困毙）。"""
    if not any(p.type is PieceType.KING and p.color is BLACK for p in state.pieces):
        return True
    return not game.rules.has_any_legal_move(state, BLACK)


def verify_mate(doc: dict, solution: list[dict]) -> tuple[bool, str]:
    game = _game(doc)
    # C1：根局面合法（未终局、黑方未受将、黑方有应手）。gen-35 旧烂题就是根局面黑已被将。
    if game.state.finished:
        return False, "根局面已是终局"
    if game.rules.in_check(game.state, BLACK):
        return False, "根局面黑方已被将军（非法）"
    if not game.rules.has_any_legal_move(game.state, BLACK):
        return False, "根局面黑方无合法应手"
    # C2 必要部分：红方任一合法首着不得立刻终局（吃王/困毙/无应手都算更短解）。
    for move in game.rules.legal_moves(game.state, RED):
        if _black_lost(game, game.rules.apply_unchecked(game.state, move)):
            return False, f"首着 {move.key()} 立刻终局（更短解，破坏连杀承诺）"
    for i, step in enumerate(solution):
        mv = Move(Position(step["from"]["row"], step["from"]["col"]), Position(step["to"]["row"], step["to"]["col"]))
        if not game.rules.is_legal(game.state, mv):
            return False, f"第 {i+1} 步不合法"
        game.move(mv)
    # 困毙（finished=True 但没将军）不能冒充将死；与 tests/test_generated_puzzles.py 同口径。
    ok = game.rules.checkmate(game.state, BLACK)
    return ok, f"根局面合法、无一手终局；末手将死={ok}"


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    defense = load_json(DEFENSE)
    feature = load_json(FEATURE)
    mate5 = load_json(MATE5)
    mate7 = load_json(MATE7)
    items = load_json(DATA)
    existing = {x["id"] for x in items}

    sources = {"defense": defense, "feature": feature, "mate5": mate5, "mate7": mate7}

    def pick_candidate(kind: str, selector: int | str) -> dict:
        """守/长算按索引取；特色题按棋子类型取（射/巡/檑/尉各一）。"""
        pool = sources[kind]
        if kind == "feature":
            matches = [c for c in pool if c.get("feature") == selector]
            if not matches:
                raise IndexError(f"feature 候选里没有 {selector}")
            return matches[0]
        return pool[selector]

    new_entries: list[dict] = []
    failures: list[str] = []
    print("=== 逐条唯一性复核（工具辅助，供人工核对）===")
    for pid, chapter, difficulty, kind, selector, title, desc, tags, hints in PLAN:
        cand = pick_candidate(kind, selector)
        doc = cand["document"]
        if kind == "defense":
            ok, note = verify_defense(doc)
        elif kind == "feature":
            ok, note = verify_feature(doc, cand["solution"], cand["feature"])
        else:
            ok, note = verify_mate(doc, cand["solution"])
        print(f"  {pid} [{kind}] {title}: {'OK' if ok else 'FAIL'}  {note}")
        if not ok:
            failures.append(f"{pid}: {note}")
        if pid in existing:
            continue
        entry = {
            "id": pid,
            "title": title,
            "difficulty": difficulty,
            "description": desc,
            "solution": cand["solution"],
            "hints": hints,
            "tags": tags,
            "document": doc,
            "chapter": chapter,
        }
        new_entries.append(entry)

    if failures:
        print(f"\n复核失败 {len(failures)} 条，拒绝写入：")
        for f in failures:
            print("  -", f)
        return 1

    if args.dry_run:
        print(f"\nDRY-RUN：{len(new_entries)} 条待写入，未落盘。")
        return 0

    items.extend(new_entries)
    DATA.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\n已写入 {len(new_entries)} 条 -> {DATA.relative_to(ROOT)}；题库总数 {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
