"""`scripts/bench_roots.py` 的局面生成器：seed 必须生效、不许走成循环、指纹只认 position_key。

## 三个缺陷（v1 实测）
1. `seed` 完全不参与决策 —— 700/701/702/703 生成**逐子相同**的局面；
2. 会在两步之间来回走 —— `plies=8` 与 `plies=12` 是同一局面；
3. `pieces/legal` 当指纹不够 —— 子数与合法着数相同也可能是不同局面。

这三条会让"16 个局面"实际只有 4 个独立局面，所有横向对照都失效。
测试直接钉住「同 seed 一致 / 异 seed 不同 / 不同 plies 不同 / 200 手不打转」。
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bench_roots import REPETITION_LIMIT, _is_reverse, build_position, position_fingerprint  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402

PROFILE = "desktop_complete"


def key(seed: int, plies: int) -> str:
    return position_fingerprint(build_position(PROFILE, seed, plies)[0])


def test_same_seed_is_reproducible() -> None:
    assert key(700, 8) == key(700, 8)


def test_different_seeds_produce_different_positions() -> None:
    keys = {seed: key(seed, 8) for seed in (700, 701, 702, 703)}
    assert len(set(keys.values())) == 4, f"4 个 seed 只产出 {len(set(keys.values()))} 个局面"


def test_different_plies_produce_different_positions() -> None:
    keys = {plies: key(700, plies) for plies in (4, 8, 12)}
    assert len(set(keys.values())) == 3, f"plies 4/8/12 只产出 {len(set(keys.values()))} 个局面"


def _assert_no_loop(game, plies: int, *, allow_early_finish: bool = False) -> None:
    """两步互逆 + position_key 重复上限；重放用 `apply_unchecked`（不跑合法性/终局判定）。

    `allow_early_finish=True`：局面对抗到底（将死/无着）时提前收工是**正常**的，
    断言的是"没有因为生成器自己打转而停"。
    """
    history = [record.move for record in game.state.history]
    if allow_early_finish:
        assert len(history) == plies or game.state.finished, (
            f"只走了 {len(history)} 手就停了，且局面未终局（生成器打了死结）")
    else:
        assert len(history) == plies, f"只走了 {len(history)} 手就停了"

    reversals = [f"{a.key()} → {b.key()}" for a, b in zip(history, history[1:]) if _is_reverse(a, b)]
    assert not reversals, f"出现 {len(reversals)} 次立刻回头：{reversals[:3]}"

    rules = Game(PROFILE).rules
    state = Game(PROFILE).state
    counter = collections.Counter({rules.position_key(state): 1})
    for move in history:
        state = rules.apply_unchecked(state, move)
        counter[rules.position_key(state)] += 1
    assert max(counter.values()) <= REPETITION_LIMIT, (
        f"同一局面出现 {max(counter.values())} 次，超过上限 {REPETITION_LIMIT}")


def test_short_run_has_no_immediate_reversal() -> None:
    """常规套件里跑 24 手：够暴露"两步来回"的缺陷，又不拖慢默认运行。"""
    game, _played = build_position(PROFILE, 700, 24)
    _assert_no_loop(game, 24)


@pytest.mark.slow
def test_200_ply_run_never_walks_back_and_forth() -> None:
    """200 手长跑（`-m 'not slow'` 可跳过）。

    生成一手要枚举全部合法着法（约 0.2s/手，62 子局面），200 手 ≈ 70s ——
    所以标 `slow`：默认套件跑上面那条 24 手的，CI 全量跑这条。
    """
    game, _played = build_position(PROFILE, 700, 200)
    # 软删甲/楯后（54 子布局）这局在 173 手左右就分出胜负/无着 —— 提前终局是正常结果，
    # 这里仍然钉住"不是生成器自己打转停下的"。
    _assert_no_loop(game, 200, allow_early_finish=True)
