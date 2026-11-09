"""S4-2a：运行时预算解耦（`time_scale`）与 `max_nodes` 双账。

## 两个价值锚点

1. **预算必须收进实例**：旧实现 `choose_move` 每次读 `AI_TIME_SCALE` 环境变量，
   同进程交替跑两种预算会互相串。这里用"极快/正常"两档交替跑，并与单独跑逐项对比。
2. **截断必须能归因**：`bound_reason`（本手被截断，不论 depth）与
   `zero_depth_reason`（一手都没搜完）分开记；`wall` / `nodes` / `cancel` 三态。
   判定口径：`wall>0` → 本批不可引用；`zeroDepth>0` → 红；`nodes` 占比 ≤2%。
"""

from __future__ import annotations

import threading

from xionghan_chess.core.ai import (
    ChessAI,
    Difficulty,
    SearchConfig,
    resolve_time_scale,
)
from xionghan_chess.core.game import Game

# 深度小、根宽小：正常预算下一定跑完 d2；极快预算下一定连排序都跑不完。
CFG = SearchConfig(depth=2, time_limit=3.0, randomness=0.0, quiescence_depth=1,
                   candidate_count=1, branch_limit=3, root_limit=4)


def _run(scale: float | None) -> tuple[str | None, int]:
    engine = ChessAI(Difficulty.MEDIUM, seed=11, config=CFG, time_scale=scale)
    game = Game("traditional")
    move = engine.choose_move(game)
    return (move.key() if move else None), engine.completed_depth


def test_resolve_time_scale_precedence_and_env_floor() -> None:
    assert resolve_time_scale(0.25, "9.0") == 0.25          # 实例参数优先
    assert resolve_time_scale(None, "0.05") == 0.1          # 环境变量保留旧下限
    assert resolve_time_scale(None, "2.5") == 2.5
    assert resolve_time_scale(None, None) == 1.0


def test_time_scale_is_instance_local_and_survives_interleaving(monkeypatch) -> None:
    """交替构造极快/正常实例，各自结果必须与单独跑一致（旧实现会串）。"""
    monkeypatch.delenv("AI_TIME_SCALE", raising=False)
    fast = _run(0.0001)     # 3s × 0.0001 = 0.3ms：一手都搜不完
    slow = _run(1.0)        # 跑完 d2
    assert fast[1] == 0
    assert slow[1] == 2

    sequence = [_run(0.0001), _run(1.0), _run(0.0001), _run(1.0)]
    assert sequence == [fast, slow, fast, slow]


def test_instance_time_scale_overrides_environment(monkeypatch) -> None:
    monkeypatch.setenv("AI_TIME_SCALE", "10.0")
    move, depth = _run(0.0001)
    assert depth == 0, "实例参数必须压过环境变量；否则同进程两种预算会互相串"
    assert move is not None


def test_max_nodes_truncates_with_reason() -> None:
    cfg = SearchConfig(depth=3, time_limit=60.0, randomness=0.0, quiescence_depth=1,
                       candidate_count=1, branch_limit=3, root_limit=4, max_nodes=3)
    engine = ChessAI(Difficulty.MEDIUM, seed=0, config=cfg)
    move = engine.choose_move(Game("traditional"))
    assert move is not None
    # 口径：`max_nodes=N` 允许 N 个节点跑完，第 N+1 个进入时才截断。
    assert engine.nodes == 4
    assert engine.completed_depth == 0, "第 1 层根着法都没走完就被节点预算截断"
    assert engine.bound_reason == "nodes"
    assert engine.zero_depth_moves == 1
    assert engine.zero_depth_reason == "nodes"


def test_generous_max_nodes_does_not_bind() -> None:
    cfg = SearchConfig(depth=2, time_limit=30.0, randomness=0.0, quiescence_depth=1,
                       candidate_count=1, branch_limit=3, root_limit=4, max_nodes=100_000)
    engine = ChessAI(Difficulty.MEDIUM, seed=0, config=cfg)
    engine.choose_move(Game("traditional"))
    assert engine.completed_depth == 2
    assert engine.bound_reason is None
    assert engine.zero_depth_reason is None


def test_wall_and_cancel_are_distinguished() -> None:
    wall_cfg = SearchConfig(depth=2, time_limit=1e-9, randomness=0.0, quiescence_depth=1,
                            candidate_count=1, branch_limit=3, root_limit=4)
    wall = ChessAI(Difficulty.MEDIUM, seed=0, config=wall_cfg)
    wall.choose_move(Game("traditional"))
    assert wall.bound_reason == "wall"
    assert wall.zero_depth_reason == "wall"

    cancel = threading.Event()
    cancel.set()
    cancelled = ChessAI(Difficulty.MEDIUM, seed=0, config=CFG)
    cancelled.choose_move(Game("traditional"), cancel)
    assert cancelled.bound_reason == "cancel"
    assert cancelled.zero_depth_reason == "cancel"


def test_max_nodes_is_opt_in_by_default() -> None:
    """默认 `max_nodes=None`：现有 CONFIGS 与所有旧调用行为不变。"""
    assert SearchConfig(1, 1.0, 0.0, 1, 1, 1, 1).max_nodes is None
    engine = ChessAI(Difficulty.BEGINNER)
    assert engine._config.max_nodes is None


def test_cheap_max_nodes_does_not_leak_between_instances() -> None:
    """同进程两个实例（一个有限额、一个无限额）互不影响。"""
    limited = SearchConfig(depth=2, time_limit=30.0, randomness=0.0, quiescence_depth=1,
                           candidate_count=1, branch_limit=3, root_limit=4, max_nodes=3)
    free = SearchConfig(depth=2, time_limit=30.0, randomness=0.0, quiescence_depth=1,
                        candidate_count=1, branch_limit=3, root_limit=4)
    a = ChessAI(Difficulty.MEDIUM, seed=0, config=limited)
    b = ChessAI(Difficulty.MEDIUM, seed=0, config=free)
    a.choose_move(Game("traditional"))
    b.choose_move(Game("traditional"))
    assert a.bound_reason == "nodes"
    assert b.bound_reason is None
