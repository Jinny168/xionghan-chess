from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
import threading
import time
from collections.abc import Callable

from .game import Game
from .model import Move


# SEE 预处理的候选上限：吃子再多也只估算前 N 个，其余直接进候选。
# 理由：MCTS 的时间盒是 12s，而一次 SEE 约毫秒级；captures 上百个时预处理
# 自己就能吃掉几秒，且这段时间里没有任何 cancel 检查。
SEE_CANDIDATE_LIMIT = 16


@dataclass
class _Node:
    move: Move | None = None
    parent: "_Node | None" = None
    children: list["_Node"] = field(default_factory=list)
    unexpanded: list[Move] | None = None
    visits: int = 0
    value: float = 0.0


class MCTS:
    """Dependency-free UCB1 Monte Carlo search over the shared Game rules."""

    def __init__(self, time_limit: float = 0.35, simulations: int | None = None,
                 exploration: float = math.sqrt(2.0), seed: int | None = None,
                 root_score: Callable[[Game, Move], float] | None = None):
        self.time_limit = max(0.01, float(time_limit))
        self.simulations = simulations
        self.exploration = max(0.0, float(exploration))
        self.random = random.Random(seed)
        self.root_score = root_score
        self.completed_simulations = 0

    def choose_move(self, game: Game, cancel: threading.Event | None = None) -> Move | None:
        # ⚠️ 时间盒必须在**任何预处理之前**开始：原来 `deadline` 建在 SEE 预处理之后，
        # 那段完全不受预算约束（实测 12s 预算跑出过 62.6s），且循环里没有 cancel 检查，
        # 暂停/悔棋都停不下来。这两条一起修。
        deadline = time.monotonic() + self.time_limit
        legal = game.rules.legal_moves(game.state)
        if not legal:
            return None
        # The legacy player expanded from policy priors.  In the dependency-
        # free engine, forcing available captures into the root candidate set
        # provides the equivalent tactical prior while deeper playouts still
        # decide which capture is sound.
        captures = [move for move in legal if game.rules.captured_by_move(game.state, move)]
        candidates = captures or legal
        if captures and self.root_score is not None:
            # 只对前 `SEE_CANDIDATE_LIMIT` 个吃子做 SEE 估算：吃子很多时，预处理本身
            # 就能吃掉几秒。超限/超预算的那些**直接当候选**，不再消耗预算。
            safe: list[Move] = []
            for index, move in enumerate(captures):
                if cancel is not None and cancel.is_set():
                    return None
                if index >= SEE_CANDIDATE_LIMIT or time.monotonic() >= deadline:
                    safe.extend(captures[index:])
                    break
                if self.root_score(game, move) >= 0:
                    safe.append(move)
            candidates = safe or [move for move in legal if move not in captures] or legal
        root = _Node(unexpanded=list(candidates))
        self.completed_simulations = 0
        while (self.simulations is None and time.monotonic() < deadline) or (
                self.simulations is not None and self.completed_simulations < self.simulations):
            if cancel and cancel.is_set():
                break
            node = root
            state_game = game
            path = [node]
            while node.unexpanded == [] and node.children:
                # Values are stored from the root player's perspective.  The
                # opponent therefore minimizes that value while retaining the
                # same UCB exploration pressure.  This mirrors the alternating
                # sign back-propagation used by the legacy pure-MCTS engine.
                maximizing = state_game.state.turn is game.state.turn
                node = max(node.children,
                           key=lambda child: self._ucb(child, node.visits, maximizing))
                state_game = self._apply(state_game, node.move)
                path.append(node)
            if node.unexpanded:
                move = node.unexpanded.pop(self.random.randrange(len(node.unexpanded)))
                state_game = self._apply(state_game, move)
                child = _Node(move=move, parent=node, unexpanded=list(state_game.rules.legal_moves(state_game.state)))
                node.children.append(child)
                node = child
                path.append(node)
            result = self._rollout(state_game, game.state.turn, deadline, cancel)
            for item in path:
                item.visits += 1
                item.value += result
            self.completed_simulations += 1
        return max(root.children, key=lambda child: child.visits).move if root.children else candidates[0]

    def _ucb(self, node: _Node, parent_visits: int, maximizing: bool = True) -> float:
        if not node.visits:
            return math.inf
        exploitation = node.value / node.visits
        if not maximizing:
            exploitation = -exploitation
        return exploitation + self.exploration * math.sqrt(math.log(max(1, parent_visits)) / node.visits)

    @staticmethod
    def _apply(game: Game, move: Move) -> Game:
        return Game.from_state(game.rules.apply_unchecked(game.state, move), game.options, game.setup)

    def _rollout(self, game: Game, root_color, deadline: float, cancel: threading.Event | None) -> float:
        for _ in range(32):
            if cancel and cancel.is_set():
                break
            if time.monotonic() >= deadline:
                break
            if game.state.finished:
                break
            moves = game.rules.legal_moves(game.state)
            if not moves:
                break
            captures = [move for move in moves if game.rules.captured_by_move(game.state, move)]
            game = self._apply(game, self.random.choice(captures or moves))
        if game.state.winner is root_color:
            return 1.0
        if game.state.winner is root_color.opponent:
            return -1.0
        return 0.0
