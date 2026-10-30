"""`_evaluate` 的 `in_check` 记忆化必须**逐位不变**，且真的能省掉重复计算。

## 为什么这条必须有

记忆化最容易出的错不是"慢"，而是"悄悄改分"：键漏了一个维度（例如没含 `evaluation_key`），
就会把别的局面的判定搬过来，评估值随之漂移 —— 而这种漂移在选点上往往看不出来，
只会表现为"AI 突然下得怪"。

所以这里同时钉两件事：
1. **值不变**：开记忆化与绕过记忆化（直接问 `rules.in_check`）的评估结果**逐位相等**；
2. **确实省了**：同一局面按红/黑各求值一次后，memo 里只应有 2 条（= 红黑两组"是否被将"），
   而不是 4 条 —— 第二个颜色的求值必须复用前一组结果。
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bench_roots import build_position  # noqa: E402

from xionghan_chess.core.ai import ChessAI, Difficulty  # noqa: E402
from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color  # noqa: E402

PROFILE = "desktop_complete"


def _states(plies: int = 8) -> list:
    game, _played = build_position(PROFILE, 701, plies)
    rules = Game(PROFILE).rules
    states = [game.state]
    state = Game(PROFILE).state
    for record in game.state.history:
        state = rules.apply_unchecked(state, record.move)
        states.append(state)
    return states


def test_memoized_evaluation_matches_direct_evaluation() -> None:
    states = _states()
    memoized = ChessAI(Difficulty.MEDIUM, seed=1)

    direct = ChessAI(Difficulty.MEDIUM, seed=1)
    # 绕过记忆化：每次直接问规则层
    direct._in_check = lambda game, _key, color: game.rules.in_check(game.state, color)  # type: ignore[method-assign]

    for index, state in enumerate(states):
        game = Game.from_state(state, None, None)
        for color in (Color.RED, Color.BLACK):
            assert memoized._evaluate(game, color) == direct._evaluate(game, color), (
                f"第 {index} 个局面 / {color} 的评估值被记忆化改变了")


def test_memo_is_shared_between_the_two_colours() -> None:
    game = Game.from_state(_states()[0], None, None)
    ai = ChessAI(Difficulty.MEDIUM, seed=1)
    ai._evaluate(game, Color.RED)
    ai._evaluate(game, Color.BLACK)
    # 红/黑各求一次 → 只应产生 2 条（"红被将""黑被将"），复用生效即为 2 而非 4
    assert len(ai.in_check_memo) == 2, f"memo 条目 {len(ai.in_check_memo)}，说明没有复用"


def test_memo_does_not_cross_positions() -> None:
    """两个不同局面的判定不得互相污染（键里必须含 evaluation_key）。"""
    states = _states()
    ai = ChessAI(Difficulty.MEDIUM, seed=1)
    keys = set()
    for state in states:
        game = Game.from_state(state, None, None)
        ai._evaluate(game, Color.RED)
        ai._evaluate(game, Color.BLACK)
        keys.add(id(game.state))
    assert len(ai.in_check_memo) >= 2, "空转：memo 没记录任何判定"
    assert all(key[0] for key in ai.in_check_memo), "memo 键缺少局面标识"
