"""难度标定：用**双信号**决定一道题该算哪一档。

两条信号：
1. **ply**（主要）：要看几步才见杀，这是杀题难度的主因。
2. **首着是否"一眼可见"**（次要）：把引擎固定在 1 层，看它随手会不会就选中首着。
   一眼就是正解的题，体感比"要挑一手"的题简单一档。

为什么不用"各档 AI 能不能解出"：
   弱档 AI 自带随机取样（beginner 0.55 / easy 0.35），"解不出"很大程度是
   **故意让它走差**造成的 —— 实测它把 3 条 3 ply 题全判成 master，纯属假信号。

为什么不用"最小深度"：
   实测 d1/d2 会**系统性低估** 3 ply 题：mate-in-2 的第三手要到 d3 才看得到。
   与其为每档题配不同深度阈值，不如用"1 层随手选不选它"这个稳定信号。

分档方式：按 (ply, 不显眼) 升序排，再按设计定稿的 9/7/6 切三档。
   排序而不是拍阈值，好处是**题库增删后仍然给出确定的配额**，
   不会出现"新加 20 道 5 ply，beginner 桶被挤空"。

用法：
    python scripts/calibrate_puzzles.py
    python scripts/calibrate_puzzles.py --apply      # 写回题库
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core import ai as ai_module  # noqa: E402
from xionghan_chess.core.ai import ChessAI, Difficulty  # noqa: E402
from xionghan_chess.core.puzzles import load_puzzles  # noqa: E402
from xionghan_chess.core.storage import game_from_document  # noqa: E402

DATA = ROOT / "src" / "xionghan_chess" / "core" / "data" / "puzzles.json"
# 用 HARD 的配置做底：它的 root_limit=18、quiescence 完整，只把 depth 压到 1/2
PROBE_BASE = Difficulty.HARD
# 只探 1 层：要回答的是"随手一眼会不会选它"，不是"第几层能算到"
PROBE_DEPTH = 1
# 深度探针不需要时间压力：深度本身就是硬上限
PROBE_TIME_LIMIT = 20.0
# 设计定稿的配比（题库扩充时按这个比例切档）
TIER_QUOTA = [("beginner", 9), ("advanced", 7), ("master", 6)]


def _top_move_at_depth(game, depth: int):
    """把引擎固定在 `depth` 层，返回它认为最好的第一手。"""
    original = ai_module.CONFIGS[PROBE_BASE]
    ai_module.CONFIGS[PROBE_BASE] = replace(
        original, depth=depth, time_limit=PROBE_TIME_LIMIT, randomness=0.0)
    try:
        ai = ChessAI(PROBE_BASE, seed=7)
        return ai.choose_move(game)
    finally:
        ai_module.CONFIGS[PROBE_BASE] = original


def obvious_first_move(puzzle) -> bool:
    """引擎随手一层会不会直接选中首着（= 这手"一眼可见"）。"""
    game = game_from_document(puzzle.document)
    move = _top_move_at_depth(game, PROBE_DEPTH)
    return move is not None and move.key() == puzzle.solution[0].key()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 条（0 = 全部生成题）")
    parser.add_argument("--apply", action="store_true", help="把结论写回 puzzles.json")
    args = parser.parse_args()

    puzzles = [item for item in load_puzzles() if item.id.startswith("gen-")]
    if args.limit:
        puzzles = puzzles[: args.limit]

    measured = []
    started = time.monotonic()
    for index, puzzle in enumerate(puzzles, 1):
        obvious = obvious_first_move(puzzle)
        measured.append({"id": puzzle.id, "plies": len(puzzle.solution),
                         "was": puzzle.difficulty, "obvious": obvious})
        if index % 5 == 0 or index == len(puzzles):
            print(f"  已探 {index}/{len(puzzles)}")

    # (ply, 不显眼) 升序：短且一眼可见的最简单
    measured.sort(key=lambda row: (row["plies"], not row["obvious"]))
    rows = []
    cursor = 0
    for level, quota in TIER_QUOTA:
        for row in measured[cursor:cursor + quota]:
            row["calibrated"] = level
            rows.append(row)
        cursor += quota
    for row in measured[cursor:]:          # 超出配额的部分并入最高档
        row["calibrated"] = TIER_QUOTA[-1][0]
        rows.append(row)

    order = {row["id"]: i for i, row in enumerate(measured)}
    rows.sort(key=lambda row: order[row["id"]])
    for index, row in enumerate(rows, 1):
        flag = "" if row["calibrated"] == row["was"] else "  ← 改判"
        print(f"[{index:2d}/{len(rows)}] {row['id']:10s} {row['plies']} ply  "
              f"原={row['was']:9s} 标定={row['calibrated']:9s} "
              f"一眼可见={row['obvious']!s:5s}{flag}")

    elapsed = time.monotonic() - started
    dist = Counter(row["calibrated"] for row in rows)
    drifted = sum(1 for row in rows if row["calibrated"] != row["was"])
    print(f"\n耗时 {elapsed:.0f}s；标定后分布 {dict(dist)}；与原标注不同 {drifted} 条")

    out = ROOT / "build" / "calibration.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"明细 -> {out.relative_to(ROOT)}")

    if args.apply and rows:
        items = json.loads(DATA.read_text(encoding="utf-8"))
        by_id = {row["id"]: row["calibrated"] for row in rows}
        for item in items:
            if item["id"] in by_id:
                item["difficulty"] = by_id[item["id"]]
                item["tags"] = sorted({*item.get("tags", []), "calibrated"})
        DATA.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
        print("已写回题库（记得重生成离线包）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
