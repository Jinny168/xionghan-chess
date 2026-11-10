"""Perft（performance test）：走法生成的规则指纹。

标准 perft：从某局面出发按合法走法递归数叶子节点。合法性与吃将/被将军判定
完全委托给 `RulesEngine`（`legal_moves` / `apply_unchecked`），本模块不做任何
第二套规则判断——它就是"数数器"，所以锚点数值一变即说明规则引擎变了。

`divide` 是逐分支下钻的对照表（Stockfish 口径）：返回每个根着法 → 其子树在
depth-1 层的叶子数，`sum(divide(...).values()) == perft(..., depth)`。两引擎
对不上时，divide 能把分歧立即定位到具体根着法，而不是只报一个总数。
"""

from __future__ import annotations

from xionghan_chess.core.model import GameState

from .rules import RulesEngine


def perft(engine: RulesEngine, state: GameState, depth: int) -> int:
    """`state` 出发走 `depth` 步能到达的不同叶子序数（路径计数，非去重局面数）。"""
    if depth <= 0:
        return 1
    moves = engine.legal_moves(state)
    if depth == 1:
        # 叶层批量计数：叶节点本身不再需要枚举孙着法，len 即答案。
        return len(moves)
    total = 0
    for move in moves:
        total += perft(engine, engine.apply_unchecked(state, move), depth - 1)
    return total


def divide(engine: RulesEngine, state: GameState, depth: int) -> dict[str, int]:
    """每个根着法（`Move.key()`）→ 该子树的 perft(depth-1) 叶子数。

    depth <= 0 时没有根着法可言，返回空表（`perft(..., 0) == 1` 是"空走"约定，
    不适合放进以着法为键的表里）。
    """
    if depth <= 0:
        return {}
    table: dict[str, int] = {}
    for move in engine.legal_moves(state):
        child = engine.apply_unchecked(state, move)
        table[move.key()] = perft(engine, child, depth - 1)
    return table
