"""B：AI 提和判定 + 两端接线。

## 为什么单独一个文件

提和的语义有两个容易写反/写漏的点，各钉一组：

1. **符号**：AI 只在**自评落后**时接受。架构侧给的片段写成 `>= -阈值`，方向反了；
   这里用"AI 少一个车"的构造局面把方向钉死，而不是靠读代码判断。
2. **接线**：桌面与服务端必须调**同一个** `should_accept_draw`（阈值只有一处定义），
   而桌面此前是"点一下立刻和棋"、服务端是"静默无响应"——两端行为相反。这里用
   源码 grep 守住"只有一个实现、两端都调用"。

服务端用例直连 `RoomManager.handle`（不走 WS），revision 语义可以精确到 +1。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from xionghan_chess.core.ai import DRAW_ACCEPT_THRESHOLD, ChessAI, Difficulty, should_accept_draw
from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color, PieceType
from xionghan_chess.core.protocol import Envelope, MessageType
from xionghan_chess.core.taunts import TAUNT_TOTAL_LIMIT
from xionghan_chess.service.rooms import RoomManager

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "xionghan_chess"


def _without(game: Game, color: Color, kind: PieceType) -> Game:
    """复制局面并移除某一方的一枚棋子（构造"落后/领先"用）。"""
    state = game.state.clone()
    state.pieces = [piece for piece in state.pieces
                    if not (piece.color is color and piece.type is kind)]
    return Game.from_state(state, game.options, game.setup)


def _ai_score(game: Game, color: Color) -> float:
    return ChessAI(Difficulty.BEGINNER)._evaluate(game, color)


# ── 1. 符号与边界 ───────────────────────────────────────────────────────────

def test_ai_accepts_only_when_it_is_behind() -> None:
    """落后一车（-1804 左右）→ 接受；均势（初始 0）→ 拒绝；领先 → 拒绝。"""
    base = Game("traditional")
    behind = _without(base, Color.BLACK, PieceType.ROOK)   # AI 执黑、少一车
    ahead = _without(base, Color.RED, PieceType.ROOK)      # AI 执黑、红少一车

    assert _ai_score(behind, Color.BLACK) < DRAW_ACCEPT_THRESHOLD
    assert should_accept_draw(behind, Color.BLACK) is True

    assert should_accept_draw(base, Color.BLACK) is False
    assert _ai_score(base, Color.BLACK) > DRAW_ACCEPT_THRESHOLD

    assert _ai_score(ahead, Color.BLACK) > 0
    assert should_accept_draw(ahead, Color.BLACK) is False


def test_same_position_gives_the_same_verdict() -> None:
    game = _without(Game("traditional"), Color.BLACK, PieceType.ROOK)
    assert should_accept_draw(game, Color.BLACK) is True
    assert should_accept_draw(game, Color.BLACK) is True


def test_threshold_is_a_closed_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    """边界值：`-150.0` 接受、`-149.9` 拒绝（`<=` 而非 `<`）。"""
    def fake_evaluate(self: ChessAI, game: Game, color: Color) -> float:
        return DRAW_ACCEPT_THRESHOLD

    monkeypatch.setattr(ChessAI, "_evaluate", fake_evaluate)
    assert should_accept_draw(Game("traditional"), Color.RED) is True

    def fake_above(self: ChessAI, game: Game, color: Color) -> float:
        return DRAW_ACCEPT_THRESHOLD + 0.1

    monkeypatch.setattr(ChessAI, "_evaluate", fake_above)
    assert should_accept_draw(Game("traditional"), Color.RED) is False


# ── 2. 服务端接线（AI 房）────────────────────────────────────────────────────

def _ai_room_setup(*, taunts_enabled: bool = True):
    async def scenario():
        manager = RoomManager()
        room, human = await manager.create("traditional", "ai", "player", Color.RED,
                                           taunts_enabled=taunts_enabled)
        return manager, room, human
    return asyncio.run(scenario())


def _send_offer(manager: RoomManager, room, seat) -> None:
    async def scenario() -> None:
        await asyncio.wait_for(
            manager.handle(room, seat, Envelope(type=MessageType.DRAW_OFFER,
                                                revision=room.revision)),
            timeout=2)
    asyncio.run(scenario())


def test_ai_accepts_draw_when_behind_without_taunt() -> None:
    manager, room, human = _ai_room_setup()
    room.game = _without(room.game, Color.BLACK, PieceType.ROOK)   # AI 落后
    revision = room.revision

    _send_offer(manager, room, human)

    assert room.game.state.draw is True
    assert room.game.state.result_reason == "draw_agreement"
    assert room.game.state.pending_draw_offer is None
    assert room.revision == revision + 1
    assert room.chat_history == [], "接受提和不该再补一句拒绝台词"


def test_ai_declines_draw_and_says_so() -> None:
    manager, room, human = _ai_room_setup()
    revision = room.revision

    _send_offer(manager, room, human)

    assert room.game.state.draw is False
    assert room.game.state.pending_draw_offer is None
    assert room.revision == revision + 1
    assert len(room.chat_history) == 1
    message = room.chat_history[0]
    assert message["scene"] == "draw_declined"
    assert message["automated"] is True
    assert message["text"]


def test_declined_taunt_respects_disabled_setting() -> None:
    manager, room, human = _ai_room_setup(taunts_enabled=False)

    _send_offer(manager, room, human)

    assert room.game.state.draw is False
    assert room.chat_history == []


def test_online_room_still_pends_the_offer() -> None:
    """非 AI 房不能走"AI 立刻应答"，否则线上对手之间会被自动判和。"""
    async def scenario() -> None:
        manager = RoomManager()
        room, red = await manager.create("traditional", "online", "red", Color.RED)
        revision = room.revision
        await manager.handle(room, red, Envelope(type=MessageType.DRAW_OFFER, revision=revision))
        assert room.game.state.pending_draw_offer is Color.RED
        assert room.game.state.draw is False
        assert room.revision == revision + 1

    asyncio.run(scenario())


def _first_legal(room) -> tuple[dict[str, int], dict[str, int]]:
    move = next(iter(room.game.rules.legal_moves(room.game.state)))
    return ({"row": move.source.row, "col": move.source.col},
            {"row": move.target.row, "col": move.target.col})


# ── 2b. 局势波动触发（每步一次，|Δ| ≥ 240）────────────────────────────────

def test_swing_check_after_a_positive_jump(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")

    async def scenario() -> None:
        manager = RoomManager()
        room, human = await manager.create("traditional", "ai", "player", Color.RED,
                                           difficulty=Difficulty.BEGINNER)
        current = manager._ai_eval(room.game, room)
        room.last_ai_eval = current - 600        # 人为制造"AI 一步间大幅变好"
        source, target = _first_legal(room)
        await asyncio.wait_for(manager.handle(
            room, human, Envelope(type=MessageType.MOVE, revision=room.revision,
                                  payload={"from": source, "to": target})), timeout=5)
        assert room.chat_history, "正向波动应广播一条台词"
        assert room.chat_history[0]["scene"] == "check"
        assert room.last_ai_eval != current - 600, "基线必须更新到当前局面"

    asyncio.run(scenario())


def test_swing_defeat_after_a_negative_jump(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_TIME_SCALE", "0.1")

    async def scenario() -> None:
        manager = RoomManager()
        room, human = await manager.create("traditional", "ai", "player", Color.RED,
                                           difficulty=Difficulty.BEGINNER)
        current = manager._ai_eval(room.game, room)
        room.last_ai_eval = current + 600        # 人为制造"AI 一步间大幅变差"
        source, target = _first_legal(room)
        await asyncio.wait_for(manager.handle(
            room, human, Envelope(type=MessageType.MOVE, revision=room.revision,
                                  payload={"from": source, "to": target})), timeout=5)
        assert room.chat_history, "负向波动应广播一条台词"
        assert room.chat_history[0]["scene"] == "defeat"

    asyncio.run(scenario())


def test_ai_eval_is_deterministic() -> None:
    """`last_ai_eval` 的来源必须可复现：同局面两次求值逐位相同。"""
    game = Game("traditional")
    assert ChessAI(Difficulty.BEGINNER)._evaluate(game, Color.BLACK) == \
        ChessAI(Difficulty.BEGINNER)._evaluate(game, Color.BLACK)


def test_draw_declined_bypasses_cooldown_but_stops_at_the_four_per_game_limit() -> None:
    """「被拒必发」优先于 4 手冷却；但每局最多 4 条，第 5 次被拒不再发。

    连续 5 次提和都在**同一手**（不推进棋局）：若 `draw_declined` 不绕过冷却，
    第 2 次起就会因 too_soon 被压掉——这正是要锁住的优先级。
    """
    async def scenario() -> None:
        manager = RoomManager()
        room, human = await manager.create("traditional", "ai", "player", Color.RED,
                                           difficulty=Difficulty.BEGINNER)

        async def offer() -> None:
            await manager.handle(room, human, Envelope(type=MessageType.DRAW_OFFER,
                                                       revision=room.revision))

        for index in range(1, TAUNT_TOTAL_LIMIT + 1):
            await offer()
            assert room.game.state.draw is False, "均势时 AI 应拒绝"
            assert len(room.chat_history) == index, f"第 {index} 次被拒应发一条"
            assert room.chat_history[-1]["scene"] == "draw_declined"

        assert room.taunt_sent_total == TAUNT_TOTAL_LIMIT
        await offer()
        assert len(room.chat_history) == TAUNT_TOTAL_LIMIT, "第 5 次被拒不得再发（总数 4）"

    asyncio.run(scenario())


# ── 3. 桌面走同一条纯函数路径 ───────────────────────────────────────────────

def test_offer_draw_outside_your_turn_is_rejected_without_state_change() -> None:
    """桌面 `draw_game` 现在先调 `offer_draw`；非本方回合由 core 拒绝且状态不动。"""
    game = Game("traditional")          # 轮到红方
    before = (game.state.pending_draw_offer, game.state.draw, len(game.state.history))
    with pytest.raises(GameError):
        game.offer_draw(Color.BLACK)     # 黑方不在自己回合提和
    assert (game.state.pending_draw_offer, game.state.draw, len(game.state.history)) == before


def test_offer_then_ai_verdict_then_response_matches_desktop_flow() -> None:
    """桌面的三步：offer(human) → should_accept_draw(ai) → respond_draw(ai)。"""
    game = _without(Game("traditional"), Color.BLACK, PieceType.ROOK)  # AI 落后
    human, ai = Color.RED, Color.BLACK

    game.offer_draw(human)
    accept = should_accept_draw(game, ai)
    game.respond_draw(ai, accept)

    assert accept is True
    assert game.state.draw is True
    assert game.state.pending_draw_offer is None


# ── 4. 唯一实现 / 两端都调用 ───────────────────────────────────────────────

def test_should_accept_draw_has_a_single_implementation() -> None:
    implementations = [path for path in PACKAGE.rglob("*.py")
                       if "def should_accept_draw" in path.read_text(encoding="utf-8")]
    assert [path.name for path in implementations] == ["ai.py"], (
        f"阈值实现必须只有一处，实际：{[str(p) for p in implementations]}")
    assert "should_accept_draw" in (PACKAGE / "service" / "rooms.py").read_text(encoding="utf-8")
    assert "should_accept_draw" in (PACKAGE / "desktop" / "app.py").read_text(encoding="utf-8")


def test_web_client_filters_automated_taunts_when_disabled() -> None:
    """Web 端无需新组件，但"关掉台词"必须由客户端也过滤一层（服务端已在源头不发）。"""
    source = (PACKAGE.parents[1] / "web" / "js" / "app.js").read_text(encoding="utf-8")
    line = next(item for item in source.splitlines() if item.startswith("function appendChat"))
    assert "payload.automated" in line
    assert "taunts===false" in line
