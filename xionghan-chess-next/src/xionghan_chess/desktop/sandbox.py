"""推演沙盘：局面副本上的自由试走，关闭即弃。

三条硬约束（与复盘/权威对局的边界，改这个文件前先读完）：

1. **绝不写回权威 Game**。这里的 Game 是 `state.clone()` 之后的独立实例，
   连 `history` / `positionCounts` / 时钟都重新起算。调用方拿到的只是副本；
   `app.board.move_requested` 那条链路永远不经过本模块。
2. **不进棋谱、不改规则版本**。沙盘不产出 `.xhgame`，不碰 `RULE_VERSION`；
   试走的每一步只活在沙盘自己的 `_snapshots` 里。
3. **不做 AI、不摆任意局面**。沙盘从"当前回看节点"取一个真实局面起步，
   双方都由玩家自由落子 —— 这正是"选中即高亮合法点"最适合当老师的地方。

为什么时钟给 24h 哨兵而不是复用真实余量：`Game.move()` 会 `tick()` 扣时钟，
真实余量只有几分钟，慢慢试走会被判超时而污染体验。24h 足够长，且**不消费
权威时钟**（权威 state 根本没传进来）。
"""

from __future__ import annotations

import time
from dataclasses import asdict

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color
from xionghan_chess.core.setup import GameSetup

# 沙盘时钟哨兵：24 小时。只用于让 tick() 不误判超时，不代表任何真实对局时间。
SANDBOX_CLOCK_MS = 86_400_000


def build_sandbox_game(game: Game) -> Game:
    """从任意 Game 取一份"干净局面副本"，可供双方自由试走。

    清空的是**上一局的历史与结算痕迹**，保留的是**局面本身**（棋子、轮走方、
    规则配置、开局设置）。这样从终局复盘也能试走，而不会一进来就被
    `Game.move()` 的 `state.finished` 守卫拦住。

    `from_state()` 不会重建 `_snapshots`（它只把 state 换掉），所以末尾必须
    手工补一格起点快照 —— 否则第一次悔棋永远不可用。
    """
    base = game.state.clone()
    base.winner = None
    base.result_reason = None
    base.draw = False
    base.paused = False
    base.paused_by = None
    base.pending_draw_offer = None
    base.pending_undo_offer = None
    base.pending_restart_offer = None
    base.position_counts = {}
    base.history = []
    base.clocks_ms = {Color.RED: SANDBOX_CLOCK_MS, Color.BLACK: SANDBOX_CLOCK_MS}
    base.turn_started_at = time.monotonic()

    sandbox = Game.from_state(
        base,
        asdict(game.options),
        setup=GameSetup.from_dict(game.profile, game.options, game.setup.to_dict()),
    )
    sandbox._snapshots = [base.to_dict()]
    return sandbox


def undo_sandbox_move(game: Game) -> bool:
    """悔一步；起点（只有一格快照）返回 False，让 UI 去禁用按钮。

    显式 `allow_finished=True`：沙盘试走也可能把对方将死，终局默认拒绝悔棋
    （`Game.undo` 的防"复活棋盘"语义）在这里是**反效果** —— 沙盘本来就该能撤回。
    这个开关只在沙盘路径上开，不污染任何权威对局调用点。
    """
    if len(game._snapshots) < 2:
        return False
    game.undo(1, allow_finished=True)
    return True
