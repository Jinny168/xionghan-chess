"""S3-B1 Step 0：`RoomManager.handle` 六条零覆盖分支的直测安全网 + 一条帧序列快照。

## 为什么需要这个文件

`handle`（rooms.py L260-365，106 行）分派 12 个消息类型，其中**六类在既有测试里一次
都没被驱动过**：`resign` / `draw_offer` / `draw_response` / `undo_response` /
`resurrect` / `restart`。复测（2026-11-10，HEAD d02a8ab）：

    for t in resign draw_offer draw_response undo_response resurrect restart; do
        printf "%-16s %s\n" "$t" "$(grep -rho "\"type\": \"$t\"" tests/ | wc -l)"
    done        # 全部 0（另 undo_request / restart_request / restart_response 各 ≥1）

它们是真实用户会走到的协议路径。做 `handle` 结构拆分之前必须先钉住 —— 否则拆分没有
任何东西守护，而「广播帧不变」这条护栏现有 `test_broadcast_payload.py` 兜不住
（那 61 行只查 replay 有无与载荷体积，不查逐帧 type/revision）。

## 两条刻意的取舍

1. **不构造真实吃子/将军局面**去测规则：本文件测的是分派的**接线**（state 变更、
   revision 单调性、拒绝路径、帧顺序），规则本身归 core 自己的用例。需要「已被吃一兵」
   这类前置状态时直接改 `state.captured`，用例内有注释说明。
2. **除帧序列快照外不走 HTTP/WS**，而是每个用例新建一个 `RoomManager()` 直连 `handle`：
   revision 语义要精确到 +1，走 HTTP/WS 会混进 join/broadcast 的副作用；直连也不碰
   `service/app.py` 里的模块级单例，用例之间零共享。

## 一个必须记住的语义（拆分的首要约束）

`Room.lock` 是 **`asyncio.Lock`（非重入）**。`handle` 现在是「锁内纯同步状态修改 /
锁外统一广播」两相位：锁内 0 个 `await`，4 个 `await` 全在锁外。任何把 `broadcast*`
挪进 `async with room.lock` 的改动都会**立刻死锁**（同任务二次 acquire），且表现为
「偶发卡死、无异常」。本文件所有用例都用 `asyncio.wait_for(..., timeout=2)` 包一层，
把这种退化变成「超时失败」而不是挂住 CI。
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color, PieceType, Position
from xionghan_chess.core.protocol import Envelope, MessageType
from xionghan_chess.service.app import app
from xionghan_chess.service.rooms import PlayerSeat, Room, RoomManager

PROFILE = "web"

# 死锁护栏：单条消息处理正常在毫秒级，2 秒还没完就说明锁语义被破坏。
HANDLE_TIMEOUT_SECONDS = 2.0


async def _online_pair(manager: RoomManager,
                       options: dict[str, object] | None = None) -> tuple[Room, PlayerSeat, PlayerSeat]:
    """建一个 online 房并坐满两侧（红方先手，所以 `state.turn is Color.RED`）。"""
    room, red = await manager.create(PROFILE, "online", "red", Color.RED, options=options)
    _same_room, black = await manager.join(room.id, "black")
    return room, red, black


async def _send(manager: RoomManager, room: Room, seat: PlayerSeat, type_: MessageType,
                payload: dict[str, Any] | None = None, *,
                revision: int | None = None) -> None:
    """驱动一条协议消息。默认带**当前** revision（除 `revision_independent` 四类外必须匹配）。"""
    envelope = Envelope(type=type_,
                        revision=room.revision if revision is None else revision,
                        payload=payload or {})
    await asyncio.wait_for(manager.handle(room, seat, envelope), timeout=HANDLE_TIMEOUT_SECONDS)


def _first_legal_move(room: Room) -> tuple[dict[str, int], dict[str, int]]:
    """取一步合法着法，转成协议里的 `{from, to}`。"""
    move = next(iter(room.game.rules.legal_moves(room.game.state)))
    return ({"row": move.source.row, "col": move.source.col},
            {"row": move.target.row, "col": move.target.col})


def _run(scenario: Callable[[], Awaitable[None]]) -> None:
    """同步用例壳：`asyncio.run` 起一个干净 loop（本仓未装 pytest-asyncio，不为这几条引入新依赖）。"""
    asyncio.run(scenario())


# ─────────────────────────────────────────────────────────────────────────────
# 1) RESIGN —— 终局 + revision +1；终局后再认输必须拒绝（L-01 的反转 bug 防线）
# ─────────────────────────────────────────────────────────────────────────────
def test_resign_ends_game_and_bumps_revision() -> None:
    async def scenario() -> None:
        manager = RoomManager()
        room, red, _black = await _online_pair(manager)
        before = room.revision

        await _send(manager, room, red, MessageType.RESIGN)

        state = room.game.state
        assert state.finished is True                      # finished = winner is not None or draw
        assert state.winner is Color.BLACK
        assert state.result_reason == "resignation"
        assert room.revision == before + 1

        # 拒绝路径：终局后再认输 → GameError，且 revision **不涨**。
        # L-01 就是这么来的：允许它就会把 winner 从「对手胜」翻成「自己胜」。
        with pytest.raises(GameError):
            await _send(manager, room, red, MessageType.RESIGN)
        assert room.revision == before + 1
        assert room.game.state.winner is Color.BLACK

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 2) DRAW_OFFER —— 只在**自己回合**可提议；只记 pending，不是和棋
# ─────────────────────────────────────────────────────────────────────────────
def test_draw_offer_requires_own_turn_and_records_pending_offer() -> None:
    async def scenario() -> None:
        manager = RoomManager()
        room, red, black = await _online_pair(manager)
        before = room.revision

        # 拒绝路径：不是自己回合 → GameError（draw_own_turn），状态与 revision 都不动。
        with pytest.raises(GameError):
            await _send(manager, room, black, MessageType.DRAW_OFFER)
        assert room.revision == before
        assert room.game.state.pending_draw_offer is None

        # 成功路径（红方先手）
        await _send(manager, room, red, MessageType.DRAW_OFFER)
        assert room.game.state.pending_draw_offer is Color.RED
        assert room.game.state.finished is False           # 只是提议，局面没结束
        assert room.revision == before + 1

        # 锁住现状（**不是**背书）：`Game.offer_draw` 不做去重，只有 turn 校验，所以同一方
        # 重复提议不报错、revision 照常再 +1。是否「重复提议应拒绝」是产品判断，
        # 不在本安全网里改语义 —— 若将来判定为缺陷，改这条用例并同步改 core。
        await _send(manager, room, red, MessageType.DRAW_OFFER)
        assert room.revision == before + 2
        assert room.game.state.pending_draw_offer is Color.RED

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 3) DRAW_RESPONSE —— 属 revision_independent（**不校验**客户端 revision），但仍 +1
# ─────────────────────────────────────────────────────────────────────────────
def test_draw_response_ignores_stale_revision_and_needs_pending_offer() -> None:
    async def scenario() -> None:
        manager = RoomManager()
        room, red, black = await _online_pair(manager)

        # 拒绝路径（先做）：没有 pending 时应答 → GameError（no_pending_draw），revision 不变。
        before = room.revision
        with pytest.raises(GameError):
            await _send(manager, room, black, MessageType.DRAW_RESPONSE, {"accept": True})
        assert room.revision == before
        assert room.game.state.draw is False

        await _send(manager, room, red, MessageType.DRAW_OFFER)
        before = room.revision
        # ★ 传过期 revision（0）必须**照样生效**：DRAW_RESPONSE 在 revision_independent 集合里。
        #   集合名字只说了「不校验 revision」，没说「不产生 revision」——两件事常被混谈，
        #   这里用一次过期 revision + 一次 delta 断言把它钉死。
        await _send(manager, room, black, MessageType.DRAW_RESPONSE, {"accept": True}, revision=0)

        state = room.game.state
        assert state.draw is True
        assert state.finished is True
        assert state.result_reason == "draw_agreement"
        assert state.pending_draw_offer is None
        assert room.revision == before + 1

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 4) UNDO_RESPONSE —— accept 后真回退（redo 语义：`undo(2 if 快照>=2 else 1)`）
# ─────────────────────────────────────────────────────────────────────────────
def test_undo_response_rewinds_history_after_request() -> None:
    async def scenario() -> None:
        manager = RoomManager()
        room, red, black = await _online_pair(manager)
        source, target = _first_legal_move(room)
        await _send(manager, room, red, MessageType.MOVE, {"from": source, "to": target})
        assert len(room.game.state.history) == 1

        # 悔棋请求：不要求是请求方的回合，只要求历史非空。
        await _send(manager, room, red, MessageType.UNDO_REQUEST)
        assert room.game.state.pending_undo_offer is Color.RED

        before = room.revision
        await _send(manager, room, black, MessageType.UNDO_RESPONSE, {"accept": True})

        # 一手时 `len(_snapshots) < 2` → undo(1) → 回到开局：历史清空、轮次回到红方。
        assert room.game.state.history == []
        assert room.game.state.turn is Color.RED
        assert room.game.state.pending_undo_offer is None
        assert room.revision == before + 1

        # 拒绝路径：pending 已被消费，再应答 → GameError（no_pending_undo），revision 不变。
        with pytest.raises(GameError):
            await _send(manager, room, black, MessageType.UNDO_RESPONSE, {"accept": True})
        assert room.revision == before + 1

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 5) RESURRECT —— 复活已吃之兵；位置/归属校验必须拒绝越权
# ─────────────────────────────────────────────────────────────────────────────
def test_resurrect_restores_captured_pawn_and_rejects_bad_square() -> None:
    async def scenario() -> None:
        manager = RoomManager()
        # `web` profile 的默认选项**关掉了复活**（profiles.py:224 的
        # `RuleOptions(pawn_resurrection=False, ...)`），所以这里显式开启该规则。
        # 本用例测的是 `handle` 的 RESURRECT 分派与状态变更，与「哪个 profile 默认开」
        # 无关；不这么做会红在 `resurrect_not_allowed`（离分派很远的地方）。
        room, red, _black = await _online_pair(manager, options={"pawn_resurrection": True})
        game = room.game
        assert game.state.turn is Color.RED

        # 前置状态：把红方一个兵从盘面移到 `captured`，等价于「这个兵已被吃」。
        # 刻意不构造真实吃子棋谱 —— 本用例测的是 handle 的分派与状态变更，不是吃子规则。
        home_squares = [Position(spec.row, spec.col) for spec in game.profile.pieces
                        if spec.type is PieceType.PAWN and spec.color is Color.RED]
        pawn = next(p for p in game.state.pieces
                    if p.type is PieceType.PAWN and p.color is Color.RED)
        game.state.pieces.remove(pawn)
        game.state.captured[Color.RED].append(pawn)
        target = Position(pawn.position.row, pawn.position.col)
        assert game.state.piece_at(target) is None

        before = room.revision
        await _send(manager, room, red, MessageType.RESURRECT,
                    {"row": target.row, "col": target.col})

        revived = game.state.piece_at(target)
        assert revived is not None and revived.type is PieceType.PAWN
        assert revived.color is Color.RED
        assert all(p is not pawn for p in game.state.captured[Color.RED])
        assert game.state.turn is Color.BLACK           # 复活视同一步棋，交出行棋权
        assert room.revision == before + 1

        # 拒绝路径：非本方兵位（红方底线不是兵位）→ GameError，revision 不变。
        bad = Position(0, 0)
        assert bad not in home_squares
        with pytest.raises(GameError):
            await _send(manager, room, red, MessageType.RESURRECT,
                        {"row": bad.row, "col": bad.col})
        assert room.revision == before + 1

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 6) RESTART —— local 立即重开（换 Game 实例），online 只记 offer
# ─────────────────────────────────────────────────────────────────────────────
def test_restart_rebuilds_in_local_but_only_offers_in_online() -> None:
    async def scenario() -> None:
        manager = RoomManager()

        # local：立即重开
        local_room, local_seat = await manager.create(PROFILE, "local", "本机玩家", Color.RED)
        source, target = _first_legal_move(local_room)
        await _send(manager, local_room, local_seat, MessageType.MOVE,
                    {"from": source, "to": target})
        assert len(local_room.game.state.history) == 1
        old_game = local_room.game
        before = local_room.revision

        await _send(manager, local_room, local_seat, MessageType.RESTART)

        assert local_room.game is not old_game                   # 换了新 Game 实例
        assert local_room.game.state.history == []               # 历史清空
        assert local_room.game.profile.id == old_game.profile.id  # 同一 profile
        assert local_room.revision == before + 1

        # online：只记 offer，**不**重开 —— 这是 RESTART 与 RESTART_REQUEST 的唯一区别
        # 只在入口（前者 local 走重开、online 走 offer；后者非 online 直接拒绝）。
        online_room, red, _black = await _online_pair(manager)
        old_online_game = online_room.game
        before = online_room.revision

        await _send(manager, online_room, red, MessageType.RESTART)

        assert online_room.game is old_online_game
        assert online_room.game.state.pending_restart_offer is Color.RED
        assert online_room.revision == before + 1

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 7) 帧序列快照 —— 拆分 `handle` 时唯一能守住「广播不变」的门禁
# ─────────────────────────────────────────────────────────────────────────────
def test_broadcast_frame_sequence_is_stable() -> None:
    """建房（local）→ auth → move → chat → resign，逐帧锁住 `(type, revision)` 与关键字段。

    为什么用 local 房：单 socket、无需 join，帧数与顺序完全确定。
    为什么必须有这一条：`handle` 的收尾是「CHAT 走 broadcast_envelope，其余走 broadcast」，
    拆分时最容易把顺序或分支搞错，而这类错误在 HTTP 码与快照字段上都看不出来，只体现在帧上。
    `revision` 的期望值同时锁住了「CHAT 不涨 revision」这条现状（0,1,1,2）。
    """
    with TestClient(app) as client:
        created = client.post("/api/rooms", json={
            "profileId": "traditional", "mode": "local", "playerName": "本机玩家"}).json()
        room_id, token = created["roomId"], created["token"]
        socket_move = next(iter(Game("traditional").rules.legal_moves(Game("traditional").state)))
        frames = []
        with client.websocket_connect(f"/ws/{room_id}") as socket:
            socket.send_json({"type": "auth", "token": token})
            frames.append(socket.receive_json())                       # 1) 首帧 state（带 replay）
            socket.send_json({"type": "move", "roomId": room_id,
                              "revision": frames[0]["revision"], "protocolVersion": 1,
                              "payload": {"from": {"row": socket_move.source.row,
                                                   "col": socket_move.source.col},
                                          "to": {"row": socket_move.target.row,
                                                 "col": socket_move.target.col}}})
            frames.append(socket.receive_json())                       # 2) state（revision+1）
            socket.send_json({"type": "chat", "roomId": room_id,
                              "revision": frames[1]["revision"], "protocolVersion": 1,
                              "payload": {"text": "好棋", "quick": True}})
            frames.append(socket.receive_json())                       # 3) chat（revision 不变）
            socket.send_json({"type": "resign", "roomId": room_id,
                              "revision": frames[1]["revision"], "protocolVersion": 1,
                              "payload": {}})
            frames.append(socket.receive_json())                       # 4) state（revision+1）

    assert [(frame["type"], frame["revision"]) for frame in frames] == [
        ("state", 0), ("state", 1), ("chat", 1), ("state", 2)]
    assert "replay" in frames[0]["payload"]["game"]        # 首帧 fresh token 带完整 replay
    assert "replay" not in frames[1]["payload"]["game"]    # 之后一律不带（载荷膨胀防线）
    assert frames[2]["payload"]["text"] == "好棋"
    assert frames[3]["payload"]["game"]["winner"] == Color.RED.value
