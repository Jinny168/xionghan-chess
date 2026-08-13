from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
import threading
import time

from .game import Game
from .model import Move


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
                 exploration: float = math.sqrt(2.0), seed: int | None = None):
        self.time_limit = max(0.01, float(time_limit))
        self.simulations = simulations
        self.exploration = max(0.0, float(exploration))
        self.random = random.Random(seed)
        self.completed_simulations = 0

    def choose_move(self, game: Game, cancel: threading.Event | None = None) -> Move | None:
        legal = game.rules.legal_moves(game.state)
        if not legal:
            return None
        root = _Node(unexpanded=list(legal))
        deadline = time.monotonic() + self.time_limit
        self.completed_simulations = 0
        while (self.simulations is None and time.monotonic() < deadline) or (
                self.simulations is not None and self.completed_simulations < self.simulations):
            if cancel and cancel.is_set():
                break
            node = root
            state_game = game
            path = [node]
            while node.unexpanded == [] and node.children:
                node = max(node.children, key=lambda child: self._ucb(child, node.visits))
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
        return max(root.children, key=lambda child: child.visits).move if root.children else legal[0]

    def _ucb(self, node: _Node, parent_visits: int) -> float:
        if not node.visits:
            return math.inf
        return node.value / node.visits + self.exploration * math.sqrt(math.log(max(1, parent_visits)) / node.visits)

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
