"""实例级 config 注入：标定/对拍换参数**不许**改全局 `CONFIGS`。

## 为什么需要这条门禁

标定的前提是"同一份代码、同一套判据、只换预算"。旧实现里 `choose_move`、
`_search`、`_quiescence` 三处各自回头读 `CONFIGS[level]`，于是唯一能换参数的
办法就是运行期改写模块字典：

    CONFIGS[Difficulty.MEDIUM] = replace(CONFIGS[Difficulty.MEDIUM], depth=2)

这个写法有两个后果：① 它改的是**进程级**状态，同进程里并行的对局/分析会串味；
② 它改的是模块字典，一个进程跑完不复位，后续任何测量都带着上一轮的参数。
`ChessAI(..., config=...)` 把参数收进实例，本文件把"注入后全局不变、同参可复现"
两条钉死。

另有一条诊断口径：`zero_depth_moves` 只记"一手都没搜完就没搜"的次数（预算低于
一次排序成本时选点退化成排序首着），**不改行为**。
"""

from __future__ import annotations

import copy
import threading

from xionghan_chess.core.ai import CONFIGS, ChessAI, Difficulty, SearchConfig
from xionghan_chess.core.game import Game

# 便宜但足够走完的配置：depth 1 / 根宽 2 / 分支 1 / 无静态搜索 / 5s 兜底。
# 5s 不是"性能预算"，是"保证深度一定能跑完"——否则用例会随机器负载变红。
CHEAP = SearchConfig(
    depth=1, time_limit=5.0, randomness=0.0, quiescence_depth=0, candidate_count=1, branch_limit=1, root_limit=2
)


def test_injected_config_leaves_global_configs_untouched() -> None:
    """注入 config 跑一次后，`CONFIGS` 必须逐键逐值不变（deepcopy 快照对比）。"""
    before = copy.deepcopy(CONFIGS)

    engine = ChessAI(Difficulty.HARD, seed=0, config=CHEAP)
    move = engine.choose_move(Game("traditional"))

    assert move is not None
    assert CONFIGS == before, "注入 config 污染了全局 CONFIGS —— 标定结果会互相串味"
    # 注入确实生效（不是"碰巧走默认值"）：depth 1 / 无静态搜索 / 根宽 2。
    assert engine.completed_depth == 1
    assert engine.quiescence_depth == 0


def test_same_config_and_seed_reproduce_move_and_depth() -> None:
    """同 config + 同 seed + 同局面跑两次：选点与 completed_depth 必须相同。"""
    config = SearchConfig(
        depth=2, time_limit=60.0, randomness=0.0, quiescence_depth=1, candidate_count=1, branch_limit=3, root_limit=4
    )

    def run() -> tuple[str | None, int]:
        engine = ChessAI(Difficulty.HARD, seed=12345, config=config)
        move = engine.choose_move(Game("traditional"))
        return (move.key() if move else None), engine.completed_depth

    first, second = run(), run()
    assert first == second, f"同参两次结果不同：{first} vs {second}"
    # 相等不能是"两边都退化成 0 层"的空相等 —— 这条同时守着下面 zero_depth 的口径。
    assert first[1] >= 1


def test_zero_depth_moves_counts_cancelled_search() -> None:
    """取消已置位 = 一手都没搜完：`completed_depth == 0` 且计数 +1。"""
    game = Game("desktop_complete")
    cancel = threading.Event()
    cancel.set()

    engine = ChessAI(Difficulty.HARD, seed=0)
    move = engine.choose_move(game, cancel)

    assert move is not None, "取消时仍须返回一个合法着法（行为不变）"
    assert engine.completed_depth == 0
    assert engine.zero_depth_moves == 1


def test_zero_depth_moves_resets_between_calls() -> None:
    """计数是**每次调用**的口径，不是实例累计 —— 否则 benchmark 汇总会重复计。"""
    cancel = threading.Event()
    cancel.set()
    engine = ChessAI(Difficulty.HARD, seed=0, config=CHEAP)

    engine.choose_move(Game("desktop_complete"), cancel)
    assert engine.zero_depth_moves == 1

    engine.choose_move(Game("traditional"))
    assert engine.completed_depth == 1
    assert engine.zero_depth_moves == 0
