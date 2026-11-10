from __future__ import annotations

import asyncio
import os
import secrets
import string
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from xionghan_chess.core.ai import ChessAI, Difficulty, should_accept_draw
from xionghan_chess.core.game import DEFAULT_INITIAL_MINUTES, Game, GameError
from xionghan_chess.core.model import Color, Move, PieceType, Position
from xionghan_chess.core.profiles import RULE_VERSION, get_profile
from xionghan_chess.core.protocol import Envelope, MessageType
from xionghan_chess.core.taunts import TauntScene, select_taunt, swing_scene, taunt_allowed
from xionghan_chess.i18n import normalize_language, t

ZOMBIE_ROOM_SECONDS = 600  # 10 分钟没人连的 online 房视为僵尸
RECONNECT_GRACE_SECONDS = int(os.getenv("RECONNECT_GRACE_SECONDS", "90"))
# 旧客户端（2.0.0 之前的所有构建）没有 `ruleVersion` 字段 —— 它们的走法语义就是 1。
# 所以"没声明"等价于声明 1，而不是"跳过校验"：跳过的话，一台还在跑 1.9.x 的客户端
# 正好可以进 2.0.0 的房间，然后在第 3 手收到「非法走棋」——那才是最难查的一类报告。
CLIENT_RULE_VERSION_ABSENT = 1


class RuleVersionMismatch(GameError):
    """双方走法语义不一致。**专用错误**，别并回通用 GameError。

    联机两端如果各跑一套走法，症状是"同一张盘上前端说能走、后端说非法"，
    而不是"版本不对" —— 所以必须在这里就拦下来，并且让错误信息自己说清楚。
    """


@dataclass(slots=True)
class PlayerSeat:
    token: str
    color: Color
    display_name: str
    connected: bool = False
    disconnected_at: float | None = None
    is_ai: bool = False
    avatar_url: str = ""


@dataclass(slots=True)
class Spectator:
    token: str
    display_name: str
    connected: bool = False


@dataclass(slots=True)
class Room:
    id: str
    game: Game
    mode: str
    initial_minutes: int = 20
    seats: dict[Color, PlayerSeat] = field(default_factory=dict)
    sockets: dict[str, WebSocket] = field(default_factory=dict)
    spectators: dict[str, Spectator] = field(default_factory=dict)
    spectator_sockets: dict[str, WebSocket] = field(default_factory=dict)
    revision: int = 0
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    ai_difficulty: Difficulty = Difficulty.MEDIUM
    language: str = "zh-CN"
    taunts_enabled: bool = True
    taunt_events: set[str] = field(default_factory=set)
    # 台词频率账本（core.taunts.taunt_allowed 消费）：不要用 `chat_history` 反推 ——
    # 它只保留最近 20 条，长局里会误判"还没说过"。
    taunt_sent_total: int = 0
    taunt_sent_by_scene: dict[str, int] = field(default_factory=dict)
    taunt_last_ply: int | None = None
    taunt_last_text: str = ""
    # AI 视角的最近一次评估：每步后与当前值比较，一步变化 ≥2 兵触发 check/defeat。
    # 创建时初始化为开局评估，之后每次 MOVE（以及悔棋/复活/重开）后更新。
    last_ai_eval: float = 0.0
    chat_history: list[dict[str, Any]] = field(default_factory=list)
    # 刚接入/重连的 token：它们的**下一条** STATE 带完整 replay，之后一律不带
    fresh_tokens: set[str] = field(default_factory=set)

    def tr(self, key: str, **params: object) -> str:
        return t(key, self.language, **params)

    def snapshot(self, token: str | None = None, include_replay: bool = True) -> dict[str, Any]:
        seat = next((s for s in self.seats.values() if s.token == token), None)
        players = (
            [
                {
                    "color": Color.RED.value,
                    "name": self.tr("common.local_player_one"),
                    "avatarUrl": "",
                    "connected": True,
                },
                {
                    "color": Color.BLACK.value,
                    "name": self.tr("common.local_player_two"),
                    "avatarUrl": "",
                    "connected": True,
                },
            ]
            if self.mode == "local"
            else [
                {"color": s.color.value, "name": s.display_name, "avatarUrl": s.avatar_url, "connected": s.connected}
                for s in self.seats.values()
            ]
        )
        return {
            "roomId": self.id,
            "mode": self.mode,
            "revision": self.revision,
            "youAre": seat.color.value if seat else None,
            "players": players,
            "chatHistory": list(self.chat_history),
            "spectatorCount": sum(item.connected for item in self.spectators.values()),
            "game": self.game.public_state(include_replay=include_replay),
        }


# 不校验客户端 revision 的四类。它们本身就是「对别人请求的应答/旁路消息」，对方那条请求
# 可能已经把 revision 抬高过，再校验就会误杀。
# ⚠️ **「不校验」≠「不产生」**：除 CHAT 外，这四类在成功时同样 `room.revision += 1`。
# 这两件事常被混为一谈（旧代码把它写成一个叫 `revision_independent` 的局部 set，名字只
# 说了前半句），所以这里提成模块级常量并起一个说明两面的名字。
_REVISION_INDEPENDENT: frozenset[MessageType] = frozenset(
    {
        MessageType.CHAT,
        MessageType.DRAW_RESPONSE,
        MessageType.UNDO_RESPONSE,
        MessageType.RESTART_RESPONSE,
    }
)

# 这些消息会**改变局面但不推进一手的评估序列**（悔棋/复活/重开）：处理完后要把
# `last_ai_eval` 重同步到当前局面，否则下一次 MOVE 的 delta 会把"局面回退"误读成
# "AI 一步间突然变差"，凭空触发一条 defeat 台词。
_AI_EVAL_RESYNC: frozenset[MessageType] = frozenset(
    {
        MessageType.UNDO_REQUEST,
        MessageType.UNDO_RESPONSE,
        MessageType.RESURRECT,
        MessageType.RESTART,
        MessageType.RESTART_REQUEST,
        MessageType.RESTART_RESPONSE,
    }
)

# 分派表里处理函数的类型。**刻意是同步签名**（返回 Awaitable 就不匹配）：
# `Room.lock` 是 `asyncio.Lock`（非重入），锁内出现任何 await 都可能自锁，而 mypy 会替
# 我们在"有人把处理函数改成 async / 往里加 await"时直接报错，不等线上偶发卡死。
_Apply = Callable[[Room, PlayerSeat, Envelope], dict[str, Any] | None]


class RoomManager:
    def __init__(self, max_rooms: int | None = None):
        self.max_rooms = max_rooms or int(os.getenv("MAX_ONLINE_GAMES", "200"))
        self.rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _check_rule_version(rule_version: int | None, language: str) -> None:
        """走法语义不一致就拒绝建房/加入。

        为什么拦在建房这一层而不是"落子报非法时再说"：两端各跑一套走法时，
        症状是"我看到能走、服务器说非法"，普通玩家只会以为程序坏了；
        而这时候棋局已经开始了，代价是一整局。

        `rule_version is None` 表示**同进程调用方**（单测、内部脚本、AI 房自建），
        它跟服务器是同一份代码、同一个 `RULE_VERSION`，不可能不一致，故跳过检查。
        **远端客户端的"没声明"不等于 None**：HTTP 层把缺省值定成 1（2.0.0 之前
        所有构建的走法语义），所以旧缓存客户端照样会被拦下 —— 这才是这道门的意义。
        """
        if rule_version is None:
            return
        declared = int(rule_version)
        if declared == RULE_VERSION:
            return
        raise RuleVersionMismatch(t("error.rule_version_mismatch", language, client=declared, server=RULE_VERSION))

    async def create(
        self,
        profile_id: str,
        mode: str,
        player_name: str,
        player_color: Color = Color.RED,
        difficulty: Difficulty = Difficulty.MEDIUM,
        options: dict[str, object] | None = None,
        initial_minutes: int = DEFAULT_INITIAL_MINUTES,
        language: str = "zh-CN",
        setup: dict[str, Any] | None = None,
        avatar_url: str = "",
        taunts_enabled: bool = True,
        rule_version: int | None = None,
    ) -> tuple[Room, PlayerSeat]:
        get_profile(profile_id)
        language = normalize_language(language)
        self._check_rule_version(rule_version, language)
        async with self._lock:
            if len(self.rooms) >= self.max_rooms:
                raise GameError(t("error.room_limit", language))
            room_id = self._room_id()
            room = Room(
                room_id,
                Game(profile_id, options, initial_minutes, language, setup),
                mode,
                initial_minutes=initial_minutes,
                ai_difficulty=difficulty,
                language=language,
                taunts_enabled=taunts_enabled,
            )
            seat = PlayerSeat(
                secrets.token_urlsafe(24),
                player_color,
                player_name or t("common.player", language),
                avatar_url=avatar_url.strip(),
            )
            room.seats[player_color] = seat
            if mode == "ai":
                room.seats[player_color.opponent] = PlayerSeat(
                    secrets.token_urlsafe(32),
                    player_color.opponent,
                    "Xionghan AI" if language == "en" else "匈汉棋灵",
                    True,
                    None,
                    True,
                )
                room.last_ai_eval = self._ai_eval(room.game, room)
            self.rooms[room_id] = room
            return room, seat

    async def create_from_game(
        self,
        game: Game,
        mode: str,
        player_name: str,
        player_color: Color = Color.RED,
        difficulty: Difficulty = Difficulty.MEDIUM,
        language: str = "zh-CN",
    ) -> tuple[Room, PlayerSeat]:
        language = normalize_language(language)
        game.language = language
        async with self._lock:
            if len(self.rooms) >= self.max_rooms:
                raise GameError(t("error.room_limit", language))
            room_id = self._room_id()
            remaining = max(game.state.clocks_ms.values(), default=20 * 60_000)
            initial_minutes = max(1, (remaining + 59_999) // 60_000)
            room = Room(
                room_id, game, mode, initial_minutes=initial_minutes, ai_difficulty=difficulty, language=language
            )
            seat = PlayerSeat(secrets.token_urlsafe(24), player_color, player_name or t("common.player", language))
            room.seats[player_color] = seat
            if mode == "ai":
                room.seats[player_color.opponent] = PlayerSeat(
                    secrets.token_urlsafe(32),
                    player_color.opponent,
                    "Xionghan AI" if language == "en" else "匈汉棋灵",
                    True,
                    None,
                    True,
                )
                room.last_ai_eval = self._ai_eval(room.game, room)
            room.game.state.turn_started_at = time.monotonic()
            self.rooms[room_id] = room
            return room, seat

    async def join(
        self, room_id: str, player_name: str, avatar_url: str = "", rule_version: int | None = None
    ) -> tuple[Room, PlayerSeat]:
        room = self.require(room_id)
        self._check_rule_version(rule_version, room.language)
        async with room.lock:
            if room.mode != "online":
                raise GameError(room.tr("error.room_reject_online"))
            colors = [c for c in Color if c not in room.seats]
            if not colors:
                raise GameError(room.tr("error.room_full"))
            seat = PlayerSeat(
                secrets.token_urlsafe(24),
                colors[0],
                player_name or room.tr("common.player"),
                avatar_url=avatar_url.strip(),
            )
            room.seats[seat.color] = seat
            room.game.state.turn_started_at = time.monotonic()
            room.revision += 1
            return room, seat

    def require(self, room_id: str) -> Room:
        room = self.rooms.get(room_id.upper())
        if not room:
            raise GameError(t("error.room_not_found"))
        return room

    def seat_for(self, room: Room, token: str) -> PlayerSeat:
        seat = next((s for s in room.seats.values() if secrets.compare_digest(s.token, token)), None)
        if not seat or seat.is_ai:
            raise GameError(room.tr("error.invalid_token"))
        return seat

    async def add_spectator(self, room_id: str, display_name: str) -> tuple[Room, Spectator]:
        room = self.require(room_id)
        async with room.lock:
            token = secrets.token_urlsafe(24)
            spectator = Spectator(token, display_name.strip() or room.tr("common.player"))
            room.spectators[token] = spectator
            return room, spectator

    async def connect_spectator(
        self, room: Room, token: str, websocket: WebSocket, accepted: bool = False
    ) -> Spectator:
        spectator = room.spectators.get(token)
        if spectator is None:
            raise GameError(room.tr("error.invalid_token"))
        if not accepted:
            await websocket.accept()
        async with room.lock:
            previous = room.spectator_sockets.get(token)
            room.spectator_sockets[token] = websocket
            spectator.connected = True
        if previous:
            await previous.close(code=4001, reason=room.tr("error.account_connected"))
        await self.broadcast(room)
        return spectator

    async def disconnect_spectator(self, room: Room, token: str, websocket: WebSocket | None = None) -> None:
        async with room.lock:
            current = room.spectator_sockets.get(token)
            if websocket is not None and current is not websocket:
                return
            room.spectator_sockets.pop(token, None)
            spectator = room.spectators.get(token)
            if spectator:
                spectator.connected = False
        await self.broadcast(room)

    async def spectator_chat(self, room: Room, spectator: Spectator, text: str) -> None:
        text = text.strip()
        if not text or len(text) > 80:
            raise GameError(room.tr("error.chat_too_long" if text else "error.chat_empty"))
        await self.broadcast_envelope(
            room,
            MessageType.CHAT,
            {
                "color": "spectator",
                "sender": spectator.display_name,
                "text": text,
                "quick": False,
                "timestamp": int(time.time() * 1000),
            },
        )

    async def connect(self, room: Room, token: str, websocket: WebSocket, accepted: bool = False) -> PlayerSeat:
        seat = self.seat_for(room, token)
        # WS 现在**先握手再认证**（token 在首帧），握手已经做过了，这里不能再 accept 一次。
        if not accepted:
            await websocket.accept()
        async with room.lock:
            previous = room.sockets.get(token)
            room.sockets[token] = websocket
            fresh = getattr(room, "fresh_tokens", None)
            if fresh is None:
                fresh = room.fresh_tokens = set()
            fresh.add(token)  # 这一条 STATE 带完整 replay
            seat.connected = True
            seat.disconnected_at = None
            room.last_activity = time.time()
        if previous:
            await previous.close(code=4001, reason=room.tr("error.account_connected"))
        return seat

    async def disconnect(self, room: Room, token: str, websocket: WebSocket | None = None) -> None:
        async with room.lock:
            current = room.sockets.get(token)
            if websocket is not None and current is not websocket:
                return
            room.sockets.pop(token, None)
            try:
                seat = self.seat_for(room, token)
            except GameError:
                return
            seat.connected = False
            seat.disconnected_at = time.time()
            room.revision += 1
        await self.broadcast(room)

    async def handle(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        """单条协议消息：**锁内**只做同步状态修改，**锁外**统一广播（见 `_after_apply`）。

        锁内只剩三件事：PING 早退、revision 校验、查表调用一个**同步**处理函数。
        处理函数的类型是 `_Apply`（同步签名），这是刻意的类型约束 —— 见模块级 `_Apply`
        注释：谁把它改成 async 或往里加 await，mypy 会直接报错。
        """
        # 锁内只做状态修改；`apply_result` 是唯一需要跨出锁的一段数据
        # （CHAT 的广播载荷 / DRAW_OFFER 的 `drawDeclined`）。
        apply_result: dict[str, Any] | None = None
        async with room.lock:
            if envelope.type is MessageType.PING:
                return
            self._check_revision(room, envelope)
            handler = self._apply_handlers().get(envelope.type)
            if handler is None:
                raise GameError(room.tr("error.unsupported_message"))
            apply_result = handler(room, seat, envelope)
        await self._after_apply(room, seat, envelope, apply_result)

    @staticmethod
    def _check_revision(room: Room, envelope: Envelope) -> None:
        """客户端 revision 校验（`_REVISION_INDEPENDENT` 里的四类跳过校验）。"""
        if envelope.type in _REVISION_INDEPENDENT:
            return
        # local 房**必须**带 revision：它没有 online 房那条 turn 兜底，
        # 而原来的 `revision is not None and ...` 写法会让"不填 revision"整段跳过校验，
        # 于是乱序/重复的落子消息会被直接采纳。
        if room.mode == "local" and envelope.revision is None:
            raise GameError("local 房需要 revision")
        if envelope.revision is not None and envelope.revision != room.revision:
            raise GameError(room.tr("error.client_stale"))

    def _apply_handlers(self) -> dict[MessageType, _Apply]:
        """`MessageType` → **同步**处理函数（12 项）。

        每次 handle 重建一次（12 个 bound method，量级 1µs；对比一次 JSON 序列化 ~100µs）。
        用表而不是 if/elif 链的两个理由：
        ① 锁内从 90 行压到 5 行，两相位边界一眼可辨；
        ② "12 个类型齐不齐"可数 —— 漏一项时 `.get()` 返回 None 会走
           `error.unsupported_message`（与原 `else` 分支行为一致），不会静默落进别的分支。
        不用 `getattr(self, "名字")`：那在 strict 下退化成 Any，等于把 `_Apply` 的类型
        约束换掉 —— 而类型约束正是这条重构的主要产出，不能为省一次字典构造丢掉。
        """
        return {
            MessageType.CHAT: self._apply_chat,
            MessageType.MOVE: self._apply_move,
            MessageType.RESIGN: self._apply_resign,
            MessageType.DRAW_OFFER: self._apply_draw_offer,
            MessageType.DRAW_RESPONSE: self._apply_draw_response,
            MessageType.UNDO_REQUEST: self._apply_undo_request,
            MessageType.UNDO_RESPONSE: self._apply_undo_response,
            MessageType.RESURRECT: self._apply_resurrect,
            MessageType.RESTART: self._apply_restart,
            MessageType.RESTART_REQUEST: self._apply_restart_request,
            MessageType.RESTART_RESPONSE: self._apply_restart_response,
            MessageType.PAUSE: self._apply_pause,
        }

    # ── 锁内处理函数：全部 `def`（同步）。约定：成功时各自 `room.revision += 1`；
    #    **唯一例外是 CHAT**（不改局面、也不涨 revision），它返回要广播的载荷。 ──

    def _apply_chat(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> dict[str, Any]:
        text = str(envelope.payload.get("text", "")).strip()
        if not text:
            raise GameError(room.tr("error.chat_empty"))
        if len(text) > 80:
            raise GameError(room.tr("error.chat_too_long"))
        payload = {
            "color": seat.color.value,
            "sender": seat.display_name,
            "text": text,
            "quick": bool(envelope.payload.get("quick")),
            "timestamp": int(time.time() * 1000),
        }
        room.last_activity = time.time()
        return payload

    def _apply_move(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        if room.mode != "local" and room.game.state.turn is not seat.color:
            raise GameError(room.tr("error.not_your_turn"))
        source = envelope.payload.get("from", {})
        target = envelope.payload.get("to", {})
        promotion = envelope.payload.get("promotion")
        move = Move(
            Position(int(source["row"]), int(source["col"])),
            Position(int(target["row"]), int(target["col"])),
            PieceType(promotion) if promotion else None,
        )
        room.game.move(move)
        room.revision += 1
        room.last_activity = time.time()

    def _apply_resign(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        resigning = room.game.state.turn if room.mode == "local" else seat.color
        room.game.resign(resigning)
        room.revision += 1

    def _apply_draw_offer(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> dict[str, Any] | None:
        if room.mode == "local":
            # S3-C：local 房没有协商对象，提和即终局 —— 这条路径**绕过** Game.offer_draw
            # （不设 pending、直接写 draw），所以 finished 守卫必须在这里单独补，
            # 不能指望 core 那层。此前一局已经和棋/分胜负之后还能再点提和：状态被重设
            # 成同一个值、revision 照涨、两端各收一帧毫无变化的 STATE。
            if room.game.state.finished:
                raise GameError(room.tr("error.game_finished"))
            room.game.state.draw = True
            room.game.state.result_reason = "draw_agreement"
            room.revision += 1
            return None
        room.game.offer_draw(seat.color)
        room.revision += 1
        if room.mode != "ai":
            return None
        # AI 房：玩家提和 → AI 立刻应答（同步，锁内零 await）。判定用 core 的唯一实现，
        # 两端不许各写一个阈值。拒绝时把结果带出锁外，由 `_after_apply` 广播台词。
        ai_seat = next((item for item in room.seats.values() if item.is_ai), None)
        if ai_seat is None:
            return None
        accept = should_accept_draw(room.game, ai_seat.color)
        room.game.respond_draw(ai_seat.color, accept)
        return {"drawDeclined": not accept}

    def _apply_draw_response(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        room.game.respond_draw(seat.color, bool(envelope.payload.get("accept")))
        room.revision += 1

    def _apply_undo_request(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        if room.mode == "local":
            room.game.undo(1)
        else:
            room.game.offer_undo(seat.color)
        room.revision += 1

    def _apply_undo_response(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        room.game.respond_undo(seat.color, bool(envelope.payload.get("accept")))
        room.revision += 1

    def _apply_resurrect(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        color = room.game.state.turn if room.mode == "local" else seat.color
        room.game.resurrect_pawn(color, Position(int(envelope.payload["row"]), int(envelope.payload["col"])))
        room.revision += 1

    def _apply_restart(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        if room.mode == "online":
            room.game.offer_restart(seat.color)
        else:
            profile_id = room.game.profile.id
            room.game = Game(
                profile_id, envelope.payload.get("options"), room.initial_minutes, room.language, room.game.setup
            )
        room.revision += 1

    def _apply_restart_request(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        if room.mode != "online":
            raise GameError(room.tr("error.unsupported_message"))
        room.game.offer_restart(seat.color)
        room.revision += 1

    def _apply_restart_response(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        accepted = room.game.respond_restart(seat.color, bool(envelope.payload.get("accept")))
        if accepted:
            profile_id = room.game.profile.id
            room.game = Game(
                profile_id, envelope.payload.get("options"), room.initial_minutes, room.language, room.game.setup
            )
        room.revision += 1

    def _apply_pause(self, room: Room, seat: PlayerSeat, envelope: Envelope) -> None:
        paused = bool(envelope.payload.get("paused", not room.game.state.paused))
        room.game.set_paused(paused, seat.color)
        room.revision += 1

    @staticmethod
    def _ai_color(room: Room) -> Color | None:
        seat = next((item for item in room.seats.values() if item.is_ai), None)
        return seat.color if seat is not None else None

    @classmethod
    def _ai_eval(cls, game: Game, room: Room) -> float:
        """AI 视角评估（与难度无关；约 1ms，不跑搜索、不用 RNG）。"""
        color = cls._ai_color(room)
        if color is None:
            return 0.0
        return ChessAI(Difficulty.BEGINNER)._evaluate(game, color)

    @staticmethod
    def _ai_snapshot(room: Room) -> Game:
        """在锁内克隆一步后的局面，锁外再求值 —— 避免评估读到一个正在被改的 state。"""
        return Game.from_state(room.game.state.clone(), room.game.options, room.game.setup)

    @classmethod
    def _swing_scene(cls, room: Room, game: Game) -> TauntScene | None:
        """更新 `last_ai_eval` 并返回本步的波动场景（不足 2 兵返回 None）。"""
        current = cls._ai_eval(game, room)
        scene = swing_scene(room.last_ai_eval, current)
        room.last_ai_eval = current
        return scene

    async def _after_apply(
        self, room: Room, seat: PlayerSeat, envelope: Envelope, apply_result: dict[str, Any] | None
    ) -> None:
        """锁**外**的统一收尾：广播 + AI 跟进。

        ⚠️ **必须**在 `async with room.lock` 之外调用：`Room.lock` 是 `asyncio.Lock`
        （非重入），而 `broadcast` / `broadcast_envelope` 自己会再取同一把锁 —— 在锁内
        调用会立刻自锁，表现为整房间卡死且无异常。锁内保持零 `await` 是这条不变量的
        另一半（谁往锁内加 await，都有可能触发同类死锁）。

        `apply_result` 只对两类消息有值：CHAT（广播载荷，且**不**涨 revision）与
        DRAW_OFFER（AI 房的 `drawDeclined`，用于决定要不要播拒绝台词）。
        """
        if envelope.type is MessageType.CHAT:
            await self.broadcast_envelope(room, MessageType.CHAT, apply_result if apply_result is not None else {})
            return
        await self.broadcast(room)
        if (
            envelope.type is MessageType.DRAW_OFFER
            and apply_result is not None
            and apply_result.get("drawDeclined")
            and room.mode == "ai"
        ):
            await self._broadcast_ai_taunt(room, "draw_declined")
        if room.mode == "ai":
            if envelope.type is MessageType.MOVE and not room.game.state.finished:
                # 每步只判一次：与上一步后的评估比较，|Δ| ≥2 兵才触发。
                async with room.lock:
                    snapshot = self._ai_snapshot(room)
                scene = self._swing_scene(room, snapshot)
                if scene is not None:
                    await self._broadcast_ai_taunt(room, scene)
            elif envelope.type in _AI_EVAL_RESYNC:
                # 局面被回退/换成另一局：只重同步基线，**不**触发台词。
                async with room.lock:
                    snapshot = self._ai_snapshot(room)
                room.last_ai_eval = self._ai_eval(snapshot, room)
        if room.mode == "ai" and room.game.state.finished:
            scene = self._finished_ai_scene(room)
            if scene:
                await self._broadcast_ai_taunt(room, scene)
        if (
            room.mode == "ai"
            and not room.game.state.finished
            and not room.game.state.paused
            and room.game.state.turn is seat.color.opponent
        ):
            await self._play_ai(room)

    async def _play_ai(self, room: Room) -> None:
        # scene 的取值域就是 core/taunts.py 的 TauntScene（opening/check/victory/defeat）。
        # 标注成 str 会让 `choose_taunt(scene)` 在 strict 下报 arg-type；这里不是加
        # cast 糊过去，而是把真实取值域写出来 —— 以后谁多加一个 scene 值，mypy 会立刻红。
        scene: TauntScene | None = None
        async with room.lock:
            if room.game.state.finished or room.game.state.paused:
                return
            state = room.game.state.clone()
            options = room.game.options
            difficulty = room.ai_difficulty
        ai = ChessAI(difficulty)
        move = await asyncio.to_thread(ai.choose_move, Game.from_state(state, options))
        # 锁外求值要用的快照与两个布尔量都在锁内取好，避免锁外读到半更新的局面。
        snapshot: Game | None = None
        gives_check = near_opening = False
        async with room.lock:
            if (
                move
                and not room.game.state.paused
                and not room.game.state.finished
                and room.game.state.turn is state.turn
                and room.game.state.history == state.history
            ):
                try:
                    room.game.move(move)
                    room.revision += 1
                    if room.game.state.finished:
                        scene = self._finished_ai_scene(room)
                    else:
                        snapshot = self._ai_snapshot(room)
                        gives_check = room.game.rules.in_check(room.game.state, room.game.state.turn)
                        near_opening = len(room.game.state.history) <= 2
                except GameError:
                    pass
        if snapshot is not None:
            # 优先级：终局（victory/defeat）> 局势波动 > 将军 > 开局寒暄。
            scene = self._swing_scene(room, snapshot) or (
                "check" if gives_check else ("opening" if near_opening else None)
            )
        await self.broadcast(room)
        if scene:
            await self._broadcast_ai_taunt(room, scene)

    @staticmethod
    def _finished_ai_scene(room: Room) -> TauntScene | None:
        ai_seat = next((seat for seat in room.seats.values() if seat.is_ai), None)
        if ai_seat is None or room.game.state.winner is None:
            return None
        return "victory" if room.game.state.winner is ai_seat.color else "defeat"

    async def _broadcast_ai_taunt(self, room: Room, scene: TauntScene) -> None:
        """AI 台词：设置 → 去重 → 频率 → 确定性选词 → 广播。账本只在这里更新。"""
        if not room.taunts_enabled:
            return
        ai_seat = next((seat for seat in room.seats.values() if seat.is_ai), None)
        if ai_seat is None:
            return
        plies = len(room.game.state.history)
        # 事件键带 `sent_total`：`draw_declined` 在同一手上可能连续发生多次
        # （提和→被拒→再提和），只按 `scene:plies` 去重会把第二次起全部吞掉。
        event_key = f"{scene}:{plies}:{room.taunt_sent_total}"
        if event_key in room.taunt_events:
            return
        text = select_taunt(
            scene, room.language, f"{room.id}:{event_key}", [room.taunt_last_text] if room.taunt_last_text else []
        )
        allowed, _reason = taunt_allowed(
            scene,
            plies,
            room.taunt_sent_total,
            room.taunt_sent_by_scene,
            room.taunt_last_ply,
            room.taunt_last_text,
            text,
        )
        if not allowed or text is None:
            return
        room.taunt_events.add(event_key)
        room.taunt_sent_total += 1
        room.taunt_sent_by_scene[scene] = room.taunt_sent_by_scene.get(scene, 0) + 1
        room.taunt_last_ply = plies
        room.taunt_last_text = text
        payload = {
            "color": ai_seat.color.value,
            "sender": ai_seat.display_name,
            "text": text,
            "quick": True,
            "automated": True,
            "scene": scene,
            "timestamp": int(time.time() * 1000),
        }
        room.chat_history = [*room.chat_history[-19:], payload]
        await self.broadcast_envelope(room, MessageType.CHAT, payload)

    async def broadcast(self, room: Room) -> None:
        async with room.lock:
            revision = room.revision
            player_sockets = list(room.sockets.items())
            spectator_sockets = list(room.spectator_sockets.items())
            # 刚接入/重连的 socket 第一条 STATE 带完整 replay，之后一律不带。
            # 为什么不在 connect 里额外发一帧：那会让"一问一答"的时序整体后移一帧，
            # 客户端按 revision 对齐的用例会读到上一条。
            # `Room.fresh_tokens` 是 dataclass 已声明的字段，getattr 的默认值只是
            # 对老调用面的防御。显式标注是因为 `getattr(..., set())` 推不出元素类型。
            fresh: set[str] = getattr(room, "fresh_tokens", set())
            player_messages = {
                token: Envelope(
                    type=MessageType.STATE,
                    roomId=room.id,
                    revision=revision,
                    payload=room.snapshot(token, include_replay=token in fresh),
                ).wire()
                for token in room.sockets
            }
            if fresh:
                room.fresh_tokens = set()
            spectator_message = Envelope(
                type=MessageType.STATE,
                roomId=room.id,
                revision=revision,
                payload=room.snapshot(None, include_replay=False),
            ).wire()
        dead: list[tuple[str, WebSocket]] = []
        for token, socket in player_sockets:
            try:
                await socket.send_json(player_messages[token])
            except Exception:
                dead.append((token, socket))
        for token, socket in dead:
            if room.sockets.get(token) is socket:
                room.sockets.pop(token, None)
        dead_spectators: list[tuple[str, WebSocket]] = []
        for token, socket in spectator_sockets:
            try:
                await socket.send_json(spectator_message)
            except Exception:
                dead_spectators.append((token, socket))
        for token, socket in dead_spectators:
            if room.spectator_sockets.get(token) is socket:
                room.spectator_sockets.pop(token, None)

    async def broadcast_envelope(self, room: Room, type_: MessageType, payload: dict[str, Any]) -> None:
        revision = room.revision
        player_sockets = list(room.sockets.items())
        spectator_sockets = list(room.spectator_sockets.items())
        dead: list[tuple[str, WebSocket]] = []
        for token, socket in player_sockets:
            try:
                await socket.send_json(Envelope(type=type_, roomId=room.id, revision=revision, payload=payload).wire())
            except Exception:
                dead.append((token, socket))
        for token, socket in dead:
            if room.sockets.get(token) is socket:
                room.sockets.pop(token, None)
        dead_spectators: list[tuple[str, WebSocket]] = []
        for token, socket in spectator_sockets:
            try:
                await socket.send_json(Envelope(type=type_, roomId=room.id, revision=revision, payload=payload).wire())
            except Exception:
                dead_spectators.append((token, socket))
        for token, socket in dead_spectators:
            if room.spectator_sockets.get(token) is socket:
                room.spectator_sockets.pop(token, None)

    async def tick(self, room: Room) -> None:
        async with room.lock:
            if room.mode not in {"ai", "local"} and len(room.seats) != 2:
                return
            was_finished = room.game.state.finished
            room.game.tick()
            if not was_finished and room.game.state.finished:
                room.revision += 1

    async def cleanup(self) -> None:
        now = time.time()
        stale: list[str] = []
        changed: list[Room] = []
        for room_id, room in list(self.rooms.items()):
            async with room.lock:
                disconnected = [s for s in room.seats.values() if not s.is_ai and not s.connected]
                expired = [
                    s for s in disconnected if s.disconnected_at and now - s.disconnected_at > RECONNECT_GRACE_SECONDS
                ]
                if expired and not room.game.state.finished and room.mode == "online":
                    room.game.state.winner = expired[0].color.opponent
                    room.game.state.result_reason = "disconnect_timeout"
                    room.revision += 1
                    changed.append(room)
                abandoned = room.mode in {"ai", "local"} and not room.sockets and now - room.last_activity > 1800
                # S2：online 房如果**从未建立 socket**（匿名建房把配额占满的那条路），
                # `disconnected_at` 恒为空、`abandoned` 又不覆盖 online → 永不回收。
                # 用"创建时间"兜底，10 分钟没人连就清掉。
                zombie = (
                    room.mode == "online"
                    and not room.sockets
                    and now - getattr(room, "created_at", now) > ZOMBIE_ROOM_SECONDS
                )
                if abandoned or zombie or (room.game.state.finished and now - room.last_activity > 3600):
                    stale.append(room_id)
        for room in changed:
            await self.broadcast(room)
        async with self._lock:
            for room_id in stale:
                self.rooms.pop(room_id, None)

    def _room_id(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            room_id = "".join(secrets.choice(alphabet) for _ in range(6))
            if room_id not in self.rooms:
                return room_id
