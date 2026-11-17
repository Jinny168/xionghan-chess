"""把内置题库（core/data/puzzles.json，唯一源）导出成 webapp 能吃的 JS 题库。

## 为什么需要这个脚本

webapp/js/data/puzzles.js 原先是**手写**的 21 条（9 条走法 drill + 12 条 mate），
与 core 的 35 条题库 id 集合只重叠 9 条 —— 同一款游戏，桌面/服务端/网页旧端
练的是一套题，公网门面练的是另一套。更糟的是 webapp 独有的 mate-* 里有引用
已软删棋子（甲/刺）的题。

这里把 core 题库导出成 webapp 现有消费格式（app.js::checkPuzzle 读
`pieces`/`solution`/`level`），于是：
1. 题库单一源（core 35 条），以后 core 加题 webapp 自动同步，不再漂移；
2. 每日一题（daily.js 的本地选题）两端按同一题库 + 同一日期算法选题，
   真正兑现"每日对所有人是同一道题"。

字段映射（core → webapp）：
- `document.state.pieces` → `pieces`（裸棋子数组，webapp 从初始局面重放）
- `solution`（core 已是 from/to 格式）→ `solution`
- `difficulty` → `level`（beginner/advanced/master）
- `description` → `desc`、`hints` → `hints`、`title`/`id` 同名
- `tags` 含 `drill` 的保留 `drill: true` 标记（每日题排除，训练列表仍可见）

**type 统一为 "sequence"**：webapp 的 checkPuzzle 对 `type==='mate'` 走"将死
判定"分支（不比 solution），对其它走"逐步比 solution"分支。core 35 条都有
完整 solution，必须走后者；标成 mate 会让判题口径错位。

用法：
    python scripts/build_web_puzzles.py            # 重新生成
    python scripts/build_web_puzzles.py --check    # 只校验是否与数据源一致
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.puzzles import load_puzzles, move_to_dict  # noqa: E402

DATA = ROOT / "src" / "xionghan_chess" / "core" / "data" / "puzzles.json"
OUTPUT = ROOT / "webapp" / "js" / "data" / "puzzles.js"

HEADER = """/** 由 scripts/build_web_puzzles.py 生成，**请勿手改**。
 * 数据源：src/xionghan_chess/core/data/puzzles.json（与桌面/服务端/网页旧端同一份题库）。
 * 共 {count} 条；每日一题见 ui/daily.js（按本题库 + 本地日期选题）。
 */
export const PUZZLES = """


def build_payload() -> list[dict]:
    payload: list[dict] = []
    for puzzle in load_puzzles():
        state = puzzle.document["state"]
        pieces = [
            {
                "type": item["type"],
                "color": item["color"],
                "row": item["row"],
                "col": item["col"],
            }
            for item in state["pieces"]
        ]
        entry: dict = {
            "id": puzzle.id,
            "title": puzzle.title,
            "level": puzzle.difficulty,
            "desc": puzzle.description,
            "type": "sequence",  # 见模块 docstring：core 题都有 solution，必须走逐步比对分支
            "profileId": puzzle.document.get("profileId", state.get("profileId", "desktop_complete")),
            "turn": state.get("turn", "red"),
            "pieces": pieces,
            "solution": [move_to_dict(move) for move in puzzle.solution],
            "hints": list(puzzle.hints),
        }
        if "drill" in puzzle.tags:
            entry["drill"] = True
        payload.append(entry)
    return payload


def render(payload: list[dict]) -> str:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return HEADER.format(count=len(payload)) + body + ";\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验生成物是否最新")
    args = parser.parse_args()

    payload = build_payload()
    content = render(payload)
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.is_file() else ""
        if current != content:
            print("webapp 题库与数据源不一致，请重新生成：python scripts/build_web_puzzles.py")
            return 1
        print(f"WEB_PUZZLES_OK  {len(payload)} 条")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"已生成 {OUTPUT.relative_to(ROOT)}  {len(payload)} 条  {size_kb:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
