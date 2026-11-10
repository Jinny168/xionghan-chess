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
import queue
import threading
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color, PieceType, Position
from xionghan_chess.core.profiles import RULE_VERSION
from xionghan_chess.core.protocol import Envelope, MessageType
from xionghan_chess.i18n import t
from xionghan_chess.service.app import app
from xionghan_chess.service.rooms import PlayerSeat, Room, RoomManager

PROFILE = "web"

# 死锁护栏：单条消息处理正常在毫秒级，2 秒还没完就说明锁语义被破坏。
HANDLE_TIMEOUT_SECONDS = 2.0

# WS 收帧护栏：正常帧也是毫秒级，2 秒没到只可能是"根本没发出来"。
WS_RECV_TIMEOUT_SECONDS = 2.0


def _recv_json(socket: Any, *, timeout: float = WS_RECV_TIMEOUT_SECONDS) -> dict[str, Any]:
    """带超时的 `socket.receive_json()`：帧不来就**失败**，而不是把 CI 挂到 job timeout。

    为什么需要：Starlette 的 WS 测试会话没有接收超时原语，本仓也没有 pytest-timeout。
    "广播漏发"过去的表现是**阻塞**（实测把 `broadcast` 截成只发第一个 socket 时，
    真 WS 用例挂了 120s+ 才被我 side 掉），CI 侧只会显示 job timeout —— 一条红色的断言
    远好过一个不说话的挂死。

    实现：daemon 线程收帧 + `queue.get(timeout)`。**不用 ThreadPoolExecutor** ——
    它的 `shutdown(wait=True)`（含 `with` 退出）会等那个阻塞的接收线程，等于把挂死还回去；
    daemon 线程不会阻止解释器退出。

    ⚠️ 2 秒是**判据不是兜底**：正常帧毫秒级，所以超时只可能是"帧没发出来"（漏发/只发
    一方/自锁），与"帧到了但内容不对"（后续字段断言负责）在失败消息上明确区分。
    """

    box: queue.Queue[Any] = queue.Queue(maxsize=1)

    def _worker() -> None:
        try:
            box.put(socket.receive_json())
        except BaseException as exc:  # 原样转交给主线程，不在工作线程里吞掉
            box.put(exc)

    threading.Thread(target=_worker, daemon=True).start()
    try:
        item = box.get(timeout=timeout)
    except queue.Empty:
        raise AssertionError(
            f"{timeout:g}s 内没收到 WS 帧 —— 帧根本没发到这条 socket（广播漏发 / 只发了"
            "一方 / 自锁阻塞），不是内容不对：内容问题由后续字段断言负责"
        ) from None
    if isinstance(item, BaseException):
        raise item
    return item


async def _online_pair(
    manager: RoomManager, options: dict[str, object] | None = None
) -> tuple[Room, PlayerSeat, PlayerSeat]:
    """建一个 online 房并坐满两侧（红方先手，所以 `state.turn is Color.RED`）。"""
    room, red = await manager.create(PROFILE, "online", "red", Color.RED, options=options)
    _same_room, black = await manager.join(room.id, "black")
    return room, red, black


async def _send(
    manager: RoomManager,
    room: Room,
    seat: PlayerSeat,
    type_: MessageType,
    payload: dict[str, Any] | None = None,
    *,
    revision: int | None = None,
) -> None:
    """驱动一条协议消息。默认带**当前** revision（除 `revision_independent` 四类外必须匹配）。"""
    envelope = Envelope(type=type_, revision=room.revision if revision is None else revision, payload=payload or {})
    await asyncio.wait_for(manager.handle(room, seat, envelope), timeout=HANDLE_TIMEOUT_SECONDS)


def _first_legal_move(room: Room) -> tuple[dict[str, int], dict[str, int]]:
    """取一步合法着法，转成协议里的 `{from, to}`。"""
    move = next(iter(room.game.rules.legal_moves(room.game.state)))
    return ({"row": move.source.row, "col": move.source.col}, {"row": move.target.row, "col": move.target.col})


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
        assert state.finished is True  # finished = winner is not None or draw
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
# 2) DRAW_OFFER —— 只在**自己回合**可提议；只记 pending，不是和棋；已有 pending 则拒绝
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
        assert room.game.state.finished is False  # 只是提议，局面没结束
        assert room.revision == before + 1

        # ★ S3-C 协议行为变更：同一方在 pending 未决时再提和必须**拒绝**。
        #   本用例原先锁的是旧现状（"`Game.offer_draw` 不做去重，只有 turn 校验，所以同一方
        #   重复提议不报错、revision 照常再 +1"，原文自注「不是背书」）。产品判定为缺陷，
        #   本次随 core 守卫（`Game.offer_draw` 的 pending 判断，与 `Game.offer_restart` 对齐）
        #   同步改为新语义：GameError（draw_already_pending）、pending 保持原值、revision 不变。
        #   旧行为的三条副作用（状态值不变却 revision+1、每次整帧重播 STATE、客户端被同一个
        #   pending 连弹两次框）都源于「不拒绝」，所以这一条要连 revision 一起钉死。
        before_duplicate = room.revision
        with pytest.raises(GameError):
            await _send(manager, room, red, MessageType.DRAW_OFFER)
        assert room.revision == before_duplicate, "重复提和被拒时 revision 不许变"
        assert room.game.state.pending_draw_offer is Color.RED, "原提议必须保留，不能被覆盖或清掉"
        assert room.game.state.finished is False

        # 应答清掉 pending 之后，同一方**可以**再提（不是"一局只能提一次"）
        await _send(manager, room, black, MessageType.DRAW_RESPONSE, {"accept": False})
        assert room.game.state.pending_draw_offer is None
        await _send(manager, room, red, MessageType.DRAW_OFFER)
        assert room.game.state.pending_draw_offer is Color.RED

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 2b) DRAW_OFFER —— local 房「提和即终局」这条旁路也要挡住终局后提和
# ─────────────────────────────────────────────────────────────────────────────
def test_draw_offer_rejected_after_game_finished_in_local_room() -> None:
    """local 房不设 pending、直接写 `draw=True`，**绕过** `Game.offer_draw`。

    所以 core 那层的 finished 守卫盖不到它，必须在 `_apply_draw_offer` 里单独补。
    此前这条路径没有守卫：一局已经和棋之后还能再点提和 —— 状态被重设成同一个值、
    revision 照涨、两端各收一帧毫无变化的 STATE。
    """

    async def scenario() -> None:
        manager = RoomManager()
        room, seat = await manager.create(PROFILE, "local", "本机玩家", Color.RED)

        await _send(manager, room, seat, MessageType.DRAW_OFFER)
        assert room.game.state.draw is True
        assert room.game.state.finished is True
        assert room.game.state.result_reason == "draw_agreement"
        assert room.game.state.pending_draw_offer is None  # local 不设 pending

        before = room.revision
        with pytest.raises(GameError):
            await _send(manager, room, seat, MessageType.DRAW_OFFER)
        assert room.revision == before, "终局后提和被拒时 revision 不许变"
        assert room.game.state.draw is True
        assert room.game.state.result_reason == "draw_agreement"

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
        home_squares = [
            Position(spec.row, spec.col)
            for spec in game.profile.pieces
            if spec.type is PieceType.PAWN and spec.color is Color.RED
        ]
        pawn = next(p for p in game.state.pieces if p.type is PieceType.PAWN and p.color is Color.RED)
        game.state.pieces.remove(pawn)
        game.state.captured[Color.RED].append(pawn)
        target = Position(pawn.position.row, pawn.position.col)
        assert game.state.piece_at(target) is None

        before = room.revision
        await _send(manager, room, red, MessageType.RESURRECT, {"row": target.row, "col": target.col})

        revived = game.state.piece_at(target)
        assert revived is not None and revived.type is PieceType.PAWN
        assert revived.color is Color.RED
        assert all(p is not pawn for p in game.state.captured[Color.RED])
        assert game.state.turn is Color.BLACK  # 复活视同一步棋，交出行棋权
        assert room.revision == before + 1

        # 拒绝路径：非本方兵位（红方底线不是兵位）→ GameError，revision 不变。
        bad = Position(0, 0)
        assert bad not in home_squares
        with pytest.raises(GameError):
            await _send(manager, room, red, MessageType.RESURRECT, {"row": bad.row, "col": bad.col})
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
        await _send(manager, local_room, local_seat, MessageType.MOVE, {"from": source, "to": target})
        assert len(local_room.game.state.history) == 1
        old_game = local_room.game
        before = local_room.revision

        await _send(manager, local_room, local_seat, MessageType.RESTART)

        assert local_room.game is not old_game  # 换了新 Game 实例
        assert local_room.game.state.history == []  # 历史清空
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
        created = client.post(
            "/api/rooms",
            json={"profileId": "traditional", "mode": "local", "playerName": "本机玩家", "ruleVersion": RULE_VERSION},
        ).json()
        room_id, token = created["roomId"], created["token"]
        socket_move = next(iter(Game("traditional").rules.legal_moves(Game("traditional").state)))
        frames = []
        with client.websocket_connect(f"/ws/{room_id}") as socket:
            socket.send_json({"type": "auth", "token": token})
            frames.append(_recv_json(socket))  # 1) 首帧 state（带 replay）
            socket.send_json(
                {
                    "type": "move",
                    "roomId": room_id,
                    "revision": frames[0]["revision"],
                    "protocolVersion": 1,
                    "payload": {
                        "from": {"row": socket_move.source.row, "col": socket_move.source.col},
                        "to": {"row": socket_move.target.row, "col": socket_move.target.col},
                    },
                }
            )
            frames.append(_recv_json(socket))  # 2) state（revision+1）
            socket.send_json(
                {
                    "type": "chat",
                    "roomId": room_id,
                    "revision": frames[1]["revision"],
                    "protocolVersion": 1,
                    "payload": {"text": "好棋", "quick": True},
                }
            )
            frames.append(_recv_json(socket))  # 3) chat（revision 不变）
            socket.send_json(
                {
                    "type": "resign",
                    "roomId": room_id,
                    "revision": frames[1]["revision"],
                    "protocolVersion": 1,
                    "payload": {},
                }
            )
            frames.append(_recv_json(socket))  # 4) state（revision+1）

    assert [(frame["type"], frame["revision"]) for frame in frames] == [
        ("state", 0),
        ("state", 1),
        ("chat", 1),
        ("state", 2),
    ]
    assert "replay" in frames[0]["payload"]["game"]  # 首帧 fresh token 带完整 replay
    assert "replay" not in frames[1]["payload"]["game"]  # 之后一律不带（载荷膨胀防线）
    assert frames[2]["payload"]["text"] == "好棋"
    assert frames[3]["payload"]["game"]["winner"] == Color.RED.value


# ─────────────────────────────────────────────────────────────────────────────
# 8) 双端广播可见性 —— offer 是"给对方看的"，只有两个 socket 都收到才算生效
# ─────────────────────────────────────────────────────────────────────────────
def test_pending_offers_reach_both_sockets() -> None:
    """`DRAW_OFFER` / `UNDO_REQUEST` 之后，**两个** socket 的 STATE 里都要看到对应 pending 字段。

    为什么必须走 WS 而不是直连 `handle`：上面 1-6 条只证明"状态被改了"，证明不了"广播到了
    对手那条 socket"；第 7 条是单 socket 的 local 房，根本没有第二个收件人。
    拆分时若把第二个 socket 的帧丢了、或者只给发起方发，只有这条会红。

    ⚠️ 已知代价：如果帧真的丢了，本用例会**阻塞**而不是快速失败（Starlette 的 WS 测试会话
    没有接收超时原语，本仓也没有 pytest-timeout），CI 侧表现为 job timeout。我实测过这个
    场景（把 `broadcast` 的发送循环截成 1 个 socket）：它挂住、不报错。正确代码上本用例是
    毫秒级，所以这只在"有人真的改坏广播"时付出代价 —— 可接受，但别误以为它会给出漂亮的
    失败信息。要给 WS 接收加超时，需要单独引入机制，不在本轮范围。
    """
    with TestClient(app) as client:
        created = client.post(
            "/api/rooms",
            json={
                "profileId": "traditional",
                "mode": "online",
                "playerName": "red",
                "playerColor": "red",
                "ruleVersion": RULE_VERSION,
            },
        ).json()
        room_id, red_token = created["roomId"], created["token"]
        joined = client.post(
            f"/api/rooms/{room_id}/join", json={"playerName": "black", "ruleVersion": RULE_VERSION}
        ).json()
        black_token = joined["token"]

        with client.websocket_connect(f"/ws/{room_id}") as red_ws:
            red_ws.send_json({"type": "auth", "token": red_token})
            _recv_json(red_ws)  # 红方自己的首帧
            with client.websocket_connect(f"/ws/{room_id}") as black_ws:
                black_ws.send_json({"type": "auth", "token": black_token})
                black_first = _recv_json(black_ws)  # 黑方首帧
                red_second = _recv_json(red_ws)  # 黑方接入触发的广播（红方也要收）
                revision = red_second["revision"]
                assert black_first["revision"] == revision

                # 红方求和 → 两边的 STATE 都要带 pendingDrawOffer=red
                red_ws.send_json(
                    {"type": "draw_offer", "roomId": room_id, "revision": revision, "protocolVersion": 1, "payload": {}}
                )
                red_frame = _recv_json(red_ws)
                black_frame = _recv_json(black_ws)
                assert red_frame["type"] == black_frame["type"] == "state"
                assert red_frame["revision"] == black_frame["revision"] == revision + 1
                assert red_frame["payload"]["game"]["pendingDrawOffer"] == Color.RED.value
                assert black_frame["payload"]["game"]["pendingDrawOffer"] == Color.RED.value

                # 红方走一步，然后黑方请求悔棋 → 两边的 STATE 都要带 pendingUndoOffer=black
                move = next(iter(Game("traditional").rules.legal_moves(Game("traditional").state)))
                red_ws.send_json(
                    {
                        "type": "move",
                        "roomId": room_id,
                        "revision": red_frame["revision"],
                        "protocolVersion": 1,
                        "payload": {
                            "from": {"row": move.source.row, "col": move.source.col},
                            "to": {"row": move.target.row, "col": move.target.col},
                        },
                    }
                )
                _recv_json(red_ws)
                _recv_json(black_ws)
                black_ws.send_json(
                    {
                        "type": "undo_request",
                        "roomId": room_id,
                        "revision": red_frame["revision"] + 1,
                        "protocolVersion": 1,
                        "payload": {},
                    }
                )
                red_undo = _recv_json(red_ws)
                black_undo = _recv_json(black_ws)

    assert red_undo["type"] == black_undo["type"] == "state"
    assert red_undo["payload"]["game"]["pendingUndoOffer"] == Color.BLACK.value
    assert black_undo["payload"]["game"]["pendingUndoOffer"] == Color.BLACK.value
    assert red_undo["revision"] == black_undo["revision"]


# ─────────────────────────────────────────────────────────────────────────────
# 9) 拒绝键随模式不同 —— local / online 走两个不同前置检查，键不一样
# ─────────────────────────────────────────────────────────────────────────────
def test_undo_request_without_history_uses_mode_specific_error_key() -> None:
    """无历史时悔棋的**拒绝键不同**：

    · local  —— `handle` 直接 `Game.undo(1)` → `Game.undo` 的前置检查 → `error.no_undo`
    · online —— `handle` 调 `Game.offer_undo` → 另一处前置检查 → `error.no_undo_move`

    两个键来自**两个不同函数的前置检查**，而它们在 `handle` 里只隔着一个 `if room.mode`
    分叉。拆分成一个门时最容易把两条合并、只留一个键 —— 那会让客户端的中文提示退化，
    而且没有任何现有用例会红（两类各只被"有历史"的成功路径覆盖过）。
    """

    async def scenario() -> None:
        manager = RoomManager()

        local_room, local_seat = await manager.create(PROFILE, "local", "本机玩家", Color.RED)
        local_before = local_room.revision
        with pytest.raises(GameError) as local_exc:
            await _send(manager, local_room, local_seat, MessageType.UNDO_REQUEST)
        assert local_room.revision == local_before

        online_room, red, _black = await _online_pair(manager)
        online_before = online_room.revision
        with pytest.raises(GameError) as online_exc:
            await _send(manager, online_room, red, MessageType.UNDO_REQUEST)
        assert online_room.revision == online_before

        assert str(local_exc.value) == t("error.no_undo")
        assert str(online_exc.value) == t("error.no_undo_move")
        assert str(local_exc.value) != str(online_exc.value)

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 10) 招魂被配置关闭时的拒绝 —— web 默认关，desktop 默认开
# ─────────────────────────────────────────────────────────────────────────────
def test_resurrect_rejects_when_rule_is_disabled_by_profile() -> None:
    """`web` profile 默认关闭招魂（profiles.py:224 `RuleOptions(pawn_resurrection=False)`），
    RESURRECT 必须在 `Game.resurrect_pawn` 的第一道**配置检查**上拒绝（`error.resurrect_not_allowed`），
    而不是掉进位置/归属那些后面的检查。

    这条同时说明 RESURRECT 的**可达性**：默认开启招魂的只有 `desktop_complete` /
    `desktop_classic`，`web` 用户走不到这条分支。所以上面第 5 条才显式传
    `options={"pawn_resurrection": True}`；两条合起来，才把"能不能开"与"开了怎么走"都钉住。
    它也是**真实用户路径**：客户端并不判档案，直接发 resurrect 就会撞在这里被拒。
    """

    async def scenario() -> None:
        manager = RoomManager()
        room, red, _black = await _online_pair(
            manager, options={"pawn_resurrection": False}
        )  # 显式关（2.0 的 web 默认是开）
        game = room.game
        assert game.options.pawn_resurrection is False
        home = next(
            Position(spec.row, spec.col)
            for spec in game.profile.pieces
            if spec.type is PieceType.PAWN and spec.color is Color.RED
        )
        before = room.revision

        with pytest.raises(GameError) as exc:
            await _send(manager, room, red, MessageType.RESURRECT, {"row": home.row, "col": home.col})

        assert str(exc.value) == t("error.resurrect_not_allowed")
        assert room.revision == before  # 拒绝路径不涨 revision

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 11) 双端扇出的**快速失败**版本：假 socket 替掉真 WS
# ─────────────────────────────────────────────────────────────────────────────
class _RecordingSocket:
    """假 socket：只把 `broadcast` 发来的帧记下来。

    `broadcast()` 对**每个 token** 单独序列化一条 STATE（rooms.py `for token, socket in
    player_sockets`），所以两个 stub 各收自己那一份 —— 直驱 `handle` 时没有真 socket，
    这是观察"扇出"的最小手段。
    """

    def __init__(self) -> None:
        self.frames: list[dict[str, Any]] = []

    async def send_json(self, data: dict[str, Any]) -> None:
        self.frames.append(data)


def test_broadcast_fans_out_to_every_socket() -> None:
    """双端广播的**快速失败**版本（与第 8 条并存，不是重复）。

    为什么两条都要：
    · 第 8 条走真 TestClient WS —— 证明帧真的过了传输层到达对端，但 Starlette 的 WS 会话
      没有接收超时，广播一旦漏发，那条用例会**阻塞**到 job timeout（我在 docstring 里
      记过这个代价）；
    · 本用例把 `room.sockets` 换成只记帧的 stub —— 同一类回归**立即断言失败**，并且能
      直接指出是哪个 seat 没收到。一快一真，成本都极低。
    """

    async def scenario() -> None:
        manager = RoomManager()
        room, red, black = await _online_pair(manager)
        red_sock, black_sock = _RecordingSocket(), _RecordingSocket()
        room.sockets = {red.token: red_sock, black.token: black_sock}

        await _send(manager, room, red, MessageType.DRAW_OFFER)
        assert red_sock.frames, "提和后红方 socket 一帧都没收到"
        assert black_sock.frames, "提和后黑方 socket 一帧都没收到"
        for seat, socket in (("red", red_sock), ("black", black_sock)):
            frame = socket.frames[-1]
            assert frame["type"] == MessageType.STATE.value, seat
            assert frame["payload"]["game"]["pendingDrawOffer"] == Color.RED.value, seat
            assert frame["revision"] == room.revision, seat
        assert red_sock.frames[-1]["revision"] == black_sock.frames[-1]["revision"]

        # 悔棋请求同样要扇出到两边（先走一手让 history 非空）
        source, target = _first_legal_move(room)
        await _send(manager, room, red, MessageType.MOVE, {"from": source, "to": target})
        await _send(manager, room, black, MessageType.UNDO_REQUEST)
        for seat, socket in (("red", red_sock), ("black", black_sock)):
            frame = socket.frames[-1]
            assert frame["type"] == MessageType.STATE.value, seat
            assert frame["payload"]["game"]["pendingUndoOffer"] == Color.BLACK.value, seat
            assert frame["revision"] == room.revision, seat

    _run(scenario)


# ─────────────────────────────────────────────────────────────────────────────
# 12) 路由表覆盖自检 —— 新增 MessageType 必须登记，或显式归入 PING 早退
# ─────────────────────────────────────────────────────────────────────────────
def test_apply_table_covers_every_message_type() -> None:
    """路由表必须覆盖**全部"客户端→服务端"类型**，且三类例外都要显式点名。

    为什么需要这条：漏登记**不会报错**。查表拿到 None 会走 `error.unsupported_message`，
    于是"服务端忘了接这个类型"表现得和"协议不支持"一模一样 —— 不崩溃、现有测试全绿，
    只是功能静默消失。新增消息类型时这就是典型的静默降级。

    ⚠️ 断言**不能**写成 `set(handlers) | {PING} == set(MessageType)`：那会要求给
    `HELLO` / `JOIN` / `STATE` / `ERROR` 也登记处理函数，而它们是**服务端→客户端**类型，
    客户端发来即非法，必须继续走 `unsupported_message`。为了"让断言通过"去给它们登记
    handler，等于把非法消息变成合法处理 —— 那是行为变更，不是补覆盖。
    所以例外分两桶、都在测试里写死：进表反而错。
    """
    handlers = set(RoomManager()._apply_handlers())
    # 桶 1：锁内早退，不进表
    short_circuit = {MessageType.PING}
    # 桶 2：服务端→客户端类型，客户端发来一律 unsupported（故意不登记）
    server_to_client = {MessageType.HELLO, MessageType.JOIN, MessageType.STATE, MessageType.ERROR}

    missing = set(MessageType) - handlers - short_circuit - server_to_client
    assert not missing, (
        "新增 MessageType 必须显式决定归属：登记处理函数 / 归入 PING 早退 / "
        f"归入 server_to_client（故意不支持）。当前未归属：{sorted(m.name for m in missing)}"
    )
    assert not (handlers & short_circuit), "PING 在 handle 锁内早退，不该进路由表（进了也是永远调用不到的死配置）"
    assert not (handlers & server_to_client), (
        "服务端→客户端类型不该有处理函数：登记它们等于接受非法客户端消息，"
        f"属行为变更。多登记了：{sorted(m.name for m in handlers & server_to_client)}"
    )
    assert handlers <= set(MessageType), (
        f"路由表里有已不存在的 MessageType：{sorted(m.name for m in handlers - set(MessageType))}"
    )

    # 结构对了还要行为对：服务端→客户端类型发给 handle 必须被拒成 unsupported_message。
    async def scenario() -> None:
        manager = RoomManager()
        room, red, _black = await _online_pair(manager)
        for message_type in sorted(server_to_client, key=lambda m: m.name):
            with pytest.raises(GameError) as exc:
                await _send(manager, room, red, message_type)
            assert str(exc.value) == t("error.unsupported_message"), message_type.name

    _run(scenario)
