"""按根着法打印搜索统计 —— **只读**测量工具，不改任何产品代码。

## 为什么需要它

目前团队里所有"改前/改后"的对照都在**各测各的局面**：一边 62 子 / 108 着、
一边 59 子 / 113 着，数字互相引用就会得出相反结论（trunc 到底是 0 还是 12）。
这个脚本把三件事固定下来，让换机器也能复现同一把尺子：

1. **局面生成**：`--profile/--seed/--plies` 固定，走子策略写死为
   「每步取合法着法列表的**中位**（按 `move.key()` 排序）」，跳过会直接终局的走法；
2. **测量口径**：临时覆盖 `QUIESCENCE_NODE_LIMIT`（只在**本进程**内）、
   `AI_TIME_SCALE` 走产品自己的环境变量读取路径，不碰 `CONFIGS`；
3. **provenance**：把上面每个参数的实际取值（含 `AI_TIME_SCALE` 及其来源）打进输出，
   否则这组数字无法被引用。

## 逐根数据是怎么来的（不改产品代码）

`_root` 的循环里先 `apply_unchecked(state, move)` 再用该 child 调 `_search(depth-1, ..., ply=1)`。
本脚本在运行时包两层：`rules.apply_unchecked` 记下"最近一次应用的着法"，
`_search` 在 `ply == 1` 的**入口**读它（此时深层递归还没开始，读到的就是根着法），
并记录 `qnodes` / `quiescence_truncations` 的增量与耗时。同一着法在多轮迭代加深里会被
调用多次，输出时**按着法求和**。

⚠️ 不能用 `child.state.history[-1]` 认根着法：`apply_unchecked` 走的是"纯状态变换"，
**不写 history**，那里读到的是上一手真实对局记录（会把所有根着法错记成同一个）。

这样既不复制 `_root` 的搜索逻辑（避免漂移），也不需要改 `core/ai.py`。

用法::

    python scripts/bench_roots.py --profile desktop_complete --seed 700 --plies 10
    python scripts/bench_roots.py --cap 10 --json
    python scripts/bench_roots.py --cap inf        # 等于关掉上限（阳性对照用）

`--cap 10 / 80 / inf` 三次跑出来的 `trunc` 应当**单调**（这是"上限真的在生效"的自检）。

## 可复现性：哪些字段稳定、哪些不稳定（实测）

引擎是**时间受限**搜索（`time_limit` 是墙钟），所以同一命令重复跑：

- **稳定**（逐次完全相同）：`pieces` / `legal` / `depth` / `trunc` / `fallbacks` / `move`，
  以及逐根的 `move`、`root` 序号；
- **不稳定**（随机器负载波动）：`nodes` / `qnodes` / `ms`。

实测 `--plies 6` 连跑 5 次：`move`/`depth`/`trunc` 五次全同，`nodes` 在 74–106 之间浮动。

## ⚠️ 负载敏感性：**"边界态"结论必须独占进程跑**

技术侧实测过一次会**直接翻转结论**的环境因素（同一局面、同一参数）：

| 运行环境 | depth | nodes | 选点 | 重复 |
|---|---|---|---|---|
| 同进程内先跑过一次 D1（有前序负载/缓存热） | **1** | 75–90 | `4,6-4,3` | 3/3 |
| 无并发负载的干净进程 | **2** | 108–111 | `6,1-6,6` | 4/4 |

nodes 差约 **25%** —— 足以让"刚好跨过 depth 2"变成"停在 depth 1"，连**选点**都会变。

所以：

- 凡结论是「**差一层 / 差一手 / 刚好达标**」这类边界判断，**必须在不跑别的东西的干净进程里跑**，
  并且同一批局面**在同一次进程启动内连续测完**（避免"前几个局面把机器跑热"）；
- 报告里要注明**是否单进程独占**（并发：无 / 有），否则这组数不能与别处比较；
- 本脚本**不做并发检测、也不自动串行化**：`--json` 的 `provenance` 里只记录参数，
  运行环境由调用者自己保证并声明。若你看到两次结果差 20% 以上而参数完全一致，**先怀疑负载**，
  再怀疑改动。

### 干净进程只是"可比"，不是"通过"

**干净进程只保证两组数可比；通过判据还必须带负载复测**，且余量门槛抬到 **≥25%**：

- **桌面态**：边跑 25ms 落子动画 / 250ms 刷新；
- **服务端态**：两个房间并发（AI 与登录 PBKDF2 同池）。

原因：桌面端 AI 与渲染同进程、服务端与登录同线程池 —— 理想环境里 21% 的余量，
到用户机器上会被直接吃掉。**只在空载下过线，不算过线。**
**任何声称"时间受限搜索的 nodes 逐次相同"的工具，要么不是时间受限，要么在缓存结果。**
要横向对照，请比稳定字段，或用 `--cap` 的单调性当判据。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.ai import CONFIGS, ChessAI, Difficulty  # noqa: E402
from xionghan_chess.core.game import Game, GameError  # noqa: E402
from xionghan_chess.core.model import Color, Piece, PieceType  # noqa: E402
import xionghan_chess.core.ai as ai_module  # noqa: E402

POSITION_POLICY = "每步取合法着法列表中位（按 move.key() 排序），跳过会立刻终局的吃王着法"


def build_dense_position(profile: str) -> tuple[Game, list[str]]:
    """`--scenario dense`：交错密集局面（红黑相间 6×6）。

    用途是**阳性对照**：正常对局里单次静态搜索很少超过 80 节点，`--cap` 调到多少
    `trunc` 都是 0，看不出上限有没有生效；这个局面里每一步吃子都会打开下一处吃子，
    单次静态搜索能轻松破百，于是 `--cap 10/40/80/inf` 的 `trunc` 呈单调。
    """
    game = Game(profile)
    pieces = [
        Piece.create(PieceType.KING, Color.RED, game.profile.rows - 1, 6),
        Piece.create(PieceType.KING, Color.BLACK, 0, 6),
    ]
    for row in range(3, 9):
        for col in range(3, 9):
            color = Color.RED if (row + col) % 2 == 0 else Color.BLACK
            pieces.append(Piece.create(PieceType.PAWN, color, row, col))
    game.state.pieces = pieces
    game.state.turn = Color.RED
    return game, []


def build_position(profile: str, seed: int, plies: int) -> tuple[Game, list[str]]:
    """固定种子 + 固定走子策略地推进 `plies` 手。

    注意：这里的 `seed` **不参与**走子（策略是确定性的中位选择），它只用于给
    AI 播种；真正的随机性来自 `CONFIGS[difficulty].randomness`（在 provenance 里标注）。
    """
    game = Game(profile)
    played: list[str] = []
    for _ in range(plies):
        legal = game.rules.legal_moves(game.state)
        if not legal or game.state.finished:
            break
        safe = [move for move in legal
                if (piece := game.state.piece_at(move.target)) is None
                or piece.type is not PieceType.KING]
        pool = sorted(safe or legal, key=lambda move: move.key())
        try:
            game.move(pool[len(pool) // 2])      # 中位
        except GameError:
            break
        played.append(game.state.history[-1].move.key())
    return game, played


def instrument(ai: ChessAI, rules) -> dict[str, dict[str, float]]:
    """给一个 `ChessAI` 实例装上"按根着法记账"的 `_search` 包装。"""
    rows: dict[str, dict[str, float]] = {}
    last_applied: dict[str, object] = {"move": None}
    original_search = ai._search
    original_apply = rules.apply_unchecked

    def apply_wrapped(state, move, **kwargs):
        last_applied["move"] = move
        return original_apply(state, move, **kwargs)

    def search_wrapped(game, depth, alpha, beta, deadline, cancel, ply, allow_null=True):
        started = time.perf_counter()
        qnodes_before = ai.qnodes
        trunc_before = ai.quiescence_truncations
        move = last_applied["move"] if ply == 1 else None
        try:
            return original_search(game, depth, alpha, beta, deadline, cancel, ply, allow_null)
        finally:
            if move is not None:
                key = move.key()
                row = rows.setdefault(key, {"qnodes": 0.0, "trunc": 0.0, "ms": 0.0, "calls": 0.0})
                row["qnodes"] += ai.qnodes - qnodes_before
                row["trunc"] += ai.quiescence_truncations - trunc_before
                row["ms"] += (time.perf_counter() - started) * 1000
                row["calls"] += 1

    rules.apply_unchecked = apply_wrapped      # 仅本进程内生效
    ai._search = search_wrapped               # type: ignore[method-assign]
    return rows


def parse_cap(raw: str) -> float:
    text = raw.strip().lower()
    if text in ("inf", "infinity", "∞", "none", "0"):
        return float("inf")
    return float(int(text))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按根着法打印搜索统计（只读）")
    parser.add_argument("--profile", default="desktop_complete")
    parser.add_argument("--seed", type=int, default=700)
    parser.add_argument("--plies", type=int, default=10)
    parser.add_argument("--difficulty", default=Difficulty.MEDIUM.value)
    parser.add_argument("--cap", default="80", help="临时覆盖 QUIESCENCE_NODE_LIMIT（80 / 10 / inf）")
    parser.add_argument("--budget-scale", type=float, default=1.0,
                        help="作用于 time_limit 的测量缩放（通过 AI_TIME_SCALE 环境变量）")
    parser.add_argument("--scenario", default="played", choices=("played", "dense"),
                        help="played=按中位策略走 --plies 手；dense=交错密集局面（阳性对照）")
    parser.add_argument("--json", action="store_true", help="机器可读输出")
    args = parser.parse_args(argv)

    # ---- 测量口径（只在本进程内生效）----
    env_scale_before = os.environ.get("AI_TIME_SCALE")
    os.environ["AI_TIME_SCALE"] = str(args.budget_scale)
    cap_value = parse_cap(args.cap)
    ai_module.QUIESCENCE_NODE_LIMIT = cap_value

    difficulty = Difficulty(args.difficulty)
    if args.scenario == "dense":
        game, played = build_dense_position(args.profile)
    else:
        game, played = build_position(args.profile, args.seed, args.plies)

    ai = ChessAI(difficulty, seed=args.seed)
    rows = instrument(ai, game.rules)
    started = time.perf_counter()
    choice = ai.choose_move(game)
    wall = time.perf_counter() - started

    order = {move.key(): index for index, (_s, move, _t) in enumerate(ai.root_scores)}
    table = []
    for key, row in rows.items():
        table.append({
            "root": order.get(key, -1),
            "move": key,
            "qnodes": int(row["qnodes"]),
            "trunc": int(row["trunc"]),
            "ms": round(row["ms"]),
            "calls": int(row["calls"]),
        })
    table.sort(key=lambda item: (item["root"] if item["root"] >= 0 else 10**6, item["move"]))

    scale = os.environ.get("AI_TIME_SCALE", "1.0")
    provenance = {
        "profile": args.profile,
        "seed": args.seed,
        "plies": args.plies,
        "difficulty": difficulty.value,
        "cap": ("inf" if math.isinf(cap_value) else int(cap_value)),
        "budget_scale": args.budget_scale,
        "AI_TIME_SCALE": scale,
        "AI_TIME_SCALE_source": "--budget-scale" if scale == str(args.budget_scale)
                                else ("env(覆盖)" if env_scale_before else "default"),
        "time_limit": CONFIGS[difficulty].time_limit * float(scale),
        "randomness": CONFIGS[difficulty].randomness,
        "scenario": args.scenario,
        "position_policy": POSITION_POLICY,
        "determinism": ("pieces/legal/depth/trunc/move 与逐根 move 稳定；"
                        "nodes/qnodes/ms 受墙钟限制会波动"),
        "played": played,
    }
    summary = {
        "pieces": len(game.state.pieces),
        "legal": len(game.rules.legal_moves(game.state)),
        "nodes": ai.nodes,
        "qnodes": ai.qnodes,
        "depth": ai.completed_depth,
        "trunc": ai.quiescence_truncations,
        "fallbacks": ai.no_candidate_fallbacks,
        "move": choice.key() if choice else None,
        "wall": round(wall, 2),
    }

    if args.json:
        print(json.dumps({"roots": table, "summary": summary, "provenance": provenance},
                         ensure_ascii=False, indent=2))
        return 0

    header = f"{'root':>4}  {'move':<12}{'qnodes':>7}{'trunc':>7}{'ms':>7}{'calls':>7}"
    print(header)
    for row in table:
        print(f"{row['root']:>4}  {row['move']:<12}{row['qnodes']:>7}{row['trunc']:>7}"
              f"{row['ms']:>7}{row['calls']:>7}")
    if table:
        trunc_values = [row["trunc"] for row in table]
        print(f"（逐根 ms 中位 {statistics.median(r['ms'] for r in table):.0f}，"
              f"trunc 非零根 {sum(1 for value in trunc_values if value)}/{len(trunc_values)}）")

    print("summary: " + " ".join(f"{key}={value}" for key, value in summary.items()))
    print("provenance: " + " ".join(f"{key}={value}" for key, value in provenance.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
