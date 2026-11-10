"""陪练档标定：实测「名义取样概率」到底兑现了多少。

设计当初定的口径是"p 是主旋钮，必须可标定"，但 B1 落地后只用单元测试验证过
"取样不含第 1 名"，**没量过真实概率**。这个脚本补上：

    在若干真题局面上重复让 AI 决策，统计
    「选中着法 != 引擎自己排第一的着法」的比例，与 CONFIGS 里的 randomness 对比。

比较对象是**该次搜索自己的 root_scores[0]**，不额外跑一次强引擎 —— 采样偏离
本来就是这个意思：它本来想走 A，被取样机制换成了 B。

用法：
    python scripts/calibrate_ai_practice.py --level beginner --samples 20
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.ai import CONFIGS, ChessAI  # noqa: E402
from xionghan_chess.core.puzzles import load_puzzles  # noqa: E402
from xionghan_chess.core.storage import game_from_document  # noqa: E402


def measure(level: str, samples: int, positions: int) -> dict:
    cfg = CONFIGS[level]
    puzzles = [item for item in load_puzzles() if item.id.startswith("gen-")][:positions]

    deviations = 0
    total = 0
    gaps: list[float] = []
    elapsed = 0.0
    for puzzle in puzzles:
        for index in range(samples):
            game = game_from_document(puzzle.document)
            started = time.monotonic()
            ai = ChessAI(level, seed=10_000 + index)
            move = ai.choose_move(game)
            elapsed += time.monotonic() - started
            if move is None or not ai.root_scores:
                continue
            total += 1
            best_score, best_move, _ = ai.root_scores[0]
            if move.key() != best_move.key():
                deviations += 1
                chosen = next((score for score, m, _ in ai.root_scores if m.key() == move.key()), best_score)
                gaps.append(round(best_score - chosen))
    return {
        "level": level,
        "nominal": cfg.randomness,
        "samples": total,
        "deviations": deviations,
        "observed": deviations / total if total else 0.0,
        "mean_gap": statistics.fmean(gaps) if gaps else 0.0,
        "seconds": elapsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", default="beginner", choices=["beginner", "easy"])
    parser.add_argument("--samples", type=int, default=20, help="每个局面重复决策几次")
    parser.add_argument("--positions", type=int, default=4)
    args = parser.parse_args()

    row = measure(args.level, args.samples, args.positions)
    print(
        f"{row['level']:9s} 名义={row['nominal']:.2f}  "
        f"实测偏离率={row['observed']:.2%}（{row['deviations']}/{row['samples']}）  "
        f"平均分差={row['mean_gap']:.0f}cp  用时={row['seconds']:.0f}s"
    )
    # 判据：实测与名义的差超过 ±0.15 就说明参数没兑现，需要调 p
    if abs(row["observed"] - row["nominal"]) > 0.15:
        print("  ⚠ 偏离超过 ±0.15：名义概率没有兑现，需要检查闸门或窗口")
        return 1
    print("  OK：名义概率基本兑现")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
