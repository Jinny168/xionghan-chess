"""把题库现状与标定口径生成成一份文档（`docs/PUZZLE_LIBRARY.md`）。

为什么用脚本生成而不是手写：难度是**标定算出来的**，手工维护一份清单必然
和 `puzzles.json` 漂。这里生成 + 一条"文档是否过期"的测试，保证改题库后
要么重生成、要么门禁红。

刻意不写时间戳：带时间戳就没法在测试里做逐字比对。
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.puzzles import load_puzzles  # noqa: E402

DOC = ROOT / "docs" / "PUZZLE_LIBRARY.md"
LEVELS = ["beginner", "advanced", "master"]
LEVEL_NAMES = {"beginner": "入门", "advanced": "进阶", "master": "大师"}


def render() -> str:
    puzzles = load_puzzles()
    real = [p for p in puzzles if "drill" not in p.tags]
    drills = [p for p in puzzles if "drill" in p.tags]

    by_level: dict[str, list] = defaultdict(list)
    for puzzle in real:
        by_level[puzzle.difficulty].append(puzzle)

    lines = [
        "# 题库清单（自动生成，勿手改）",
        "",
        "> 本文件由 `scripts/make_puzzle_doc.py` 生成。改题库后请重跑该脚本；",
        "> `tests/test_puzzle_library_doc.py` 会在文档过期时报红。",
        "",
        "## 总览",
        "",
        "| | 条数 | " + " | ".join(f"{LEVEL_NAMES[level]}（{level}）" for level in LEVELS) + " |",
        "|---|---|---|" + "---|" * len(LEVELS),
        f"| 真题（杀题） | **{len(real)}** | " + " | ".join(str(len(by_level[level])) for level in LEVELS) + " |",
        f"| 走法练习（drill） | {len(drills)} | — | — | — |".replace("— | — | — |", "— | — | — |"),
        f"| 合计 | {len(puzzles)} | | | |",
        "",
        "难度是**标定算出来的**，不是按 ply 贴的：按 `(ply, 首着是否一眼可见)` 升序排，",
        "再按 9/7/6 切三档。口径与理由见 `scripts/calibrate_puzzles.py` 的模块注释。",
        "",
        "## 难度 × 长度交叉表",
        "",
        "| 难度 | 3 ply（2 手） | 5 ply（3 手） | 7 ply（4 手） | 合计 |",
        "|---|---|---|---|---|",
    ]
    for level in LEVELS:
        ply = Counter(len(p.solution) for p in by_level[level])
        lines.append(
            f"| {LEVEL_NAMES[level]} | {ply.get(3, 0)} | {ply.get(5, 0)} | {ply.get(7, 0)} | {len(by_level[level])} |"
        )
    total_ply = Counter(len(p.solution) for p in real)
    lines.append(
        f"| **合计** | **{total_ply.get(3, 0)}** | **{total_ply.get(5, 0)}** "
        f"| **{total_ply.get(7, 0)}** | **{len(real)}** |"
    )

    lines += ["", "## 分档清单", ""]
    for level in LEVELS:
        rows = sorted(by_level[level], key=lambda p: (len(p.solution), p.id))
        lines += [
            f"### {LEVEL_NAMES[level]}（{level}）· {len(rows)} 条",
            "",
            "| id | 标题 | ply | 解方手数 |",
            "|---|---|---|---|",
        ]
        for puzzle in rows:
            plies = len(puzzle.solution)
            lines.append(f"| `{puzzle.id}` | {puzzle.title} | {plies} | {(plies + 1) // 2} |")
        lines.append("")

    lines += [
        "## 走法练习（drill）",
        "",
        f"{len(drills)} 条原有题目保留为**走法练习**：它们练的是「这枚子怎么走」，",
        "而不是「找出唯一解」（实测一步杀着法数为 0）。因此：",
        "",
        "- 全部带 `drill` 标签，描述前缀「走法练习：」；",
        "- **不参与每日一题**（`core/daily.py::bucket_of` 过滤），避免对玩家食言；",
        "- 仍留在训练列表里，随时可点。",
        "",
        "## 复现",
        "",
        "```bash",
        "python scripts/author_puzzles.py --plies 3 --limit 500     # 出题",
        "python scripts/puzzle_doctor.py --file build/puzzle_candidates.json  # 体检",
        "python scripts/calibrate_puzzles.py --apply               # 标定并写回",
        "python scripts/build_offline_puzzles.py                   # 重生成离线包",
        "python scripts/make_puzzle_doc.py                         # 更新本文档",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(render(), encoding="utf-8", newline="\n")
    print(f"已生成 {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
