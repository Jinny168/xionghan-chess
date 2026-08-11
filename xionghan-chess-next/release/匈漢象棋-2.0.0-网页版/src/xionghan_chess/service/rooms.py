from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import os
import secrets
import string
import time
from typing import Any

from fastapi import WebSocket

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color, Move, PieceType, Position
from xionghan_chess.core.protocol import Envelope, MessageType
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.i18n import normalize_language, t


RECONNECT_GRACE_SECONDS = int(os.getenv("RECONNECT_GRACE_SECONDS", "90"))


@dataclass(slots=True)
class PlayerSeat:
    token: str
    color: Color
    display_name: str
    connected: bool = False
    disconnected_at: float | None = None


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

    def tr(self, key: str, **params: object) -> str:
        return t(key, self.language, **params)

    def snapshot(self, token: str | None = None) -> dict[str, Any]:
        seat = next((s for s in self.seats.values() if s.token == token), None)
        players = ([
            {"color": Color.RED.value, "name": self.tr("common.local_player_one"), "connected": True},
            {"color": Color.BLACK.value, "name": self.tr("common.local_player_two"), "connected": True},
        ] if self.mode == "local" else [
            {"color": s.color.value, "name": s.display_name, "connected": s.connected}
            for s in self.seats.values()
        ])
        return {
            "roomId": self.id,
            "mode": self.mode,
            "revision": self.revision,
            "youAre": seat.color.value if seat else None,
            "players": players,
            "spectatorCount": sum(item.connected for item in self.spectators.values()),
            "game": self.game.public_state(),
        }


class RoomManager:
    def __init__(self, max_rooms: int | None = None):
        self.max_rooms = max_rooms or int(os.getenv("MAX_ONLINE_GAMES", "200"))
        self.rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()

    async def create(self, profile_id: str, mode: str, player_name: str,
                     player_color: Color = Color.RED,
                     difficulty: Difficulty = Difficulty.MEDIUM,
                     options: dict[str, object] | None = None,
                     initial_minutes: int = 20,
                     language: str = "zh-CN",
                     setup: dict[str, Any] | None = None) -> tuple[Room, PlayerSeat]:
        get_profile(profile_id)
        language = normalize_language(language)
        async with self._lock:
            if len(self.rooms) >= self.max_rooms:
                raise GameError(t("error.room_limit", language))
            room_id = self._room_id()
            room = Room(room_id, Game(profile_id, options, initial_minutes, language, setup), mode,
                        initial_minutes=initial_minutes, ai_difficulty=difficulty,
                        language=language)
            seat = PlayerSeat(secrets.token_urlsafe(24), player_color, player_name or t("common.player", language))
            room.seats[player_color] = seat
            if mode == "ai":
                room.seats[player_color.opponent] = PlayerSeat("ai", player_color.opponent, "Xionghan AI" if language == "en" else "匈汉棋灵", True)
            self.rooms[room_id] = room
            return room, seat

    async def create_from_game(self, game: Game, mode: str, player_name: str,
                               player_color: Color = Color.RED,
                               difficulty: Difficulty = Difficulty.MEDIUM,
                               language: str = "zh-CN") -> tuple[Room, PlayerSeat]:
        language = normalize_language(language)
        game.language = language
        async with self._lock:
            if len(self.rooms) >= self.max_rooms:
                raise GameError(t("error.room_limit", language))
            room_id = self._room_id()
            remaining = max(game.state.clocks_ms.values(), default=20 * 60_000)
            initial_minutes = max(1, (remaining + 59_999) // 60_000)
            room = Room(room_id, game, mode, initial_minutes=initial_minutes,
                        ai_difficulty=difficulty, language=language)
            seat = PlayerSeat(secrets.token_urlsafe(24), player_color, player_name or t("common.player", language))
            room.seats[player_color] = seat
            if mode == "ai":
                room.seats[player_color.opponent] = PlayerSeat(
                    "ai", player_color.opponent, "Xionghan AI" if language == "en" else "匈汉棋灵", True
                )
            room.game.state.turn_started_at = time.monotonic()
            self.rooms[room_id] = room
            return room, seat

    async def join(self, room_id: str, player_name: str) -> tuple[Room, PlayerSeat]:
        room = self.require(room_id)
        async with room.lock:
            if room.mode != "online":
                raise GameError(room.tr("error.room_reject_online"))
            colors = [c for c in Color if c not in room.seats]
            if not colors:
                raise GameError(room.tr("error.room_full"))
            seat = PlayerSeat(secrets.token_urlsafe(24), colors[0], player_name or room.tr("common.player"))
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
        seat = next((s for s in room.seats.values() if secrets.compare_digest(s.token, token)) , None)
        if not seat:
            raise GameError(room.tr("error.invalid_token"))
        return seat

    async def add_spectator(self, room_id: str, display_name: str) -> tuple[Room, Spectator]:
        room = self.require(room_id)
        async with room.lock:
            token = secrets.token_urlsafe(24)
            spectator = Spectator(token, display_name.strip() or room.tr("common.player"))
            room.spectators[token] = spectator
            return room, spectator

    async def connect_spectator(self, room: Room, token: str,
                                websocket: WebSocket) -> Spectator:
        spectator = room.spectators.get(token)
        if spectator is None:
            raise GameError(room.tr("error.invalid_token"))
        await websocket.accept()
        previous = room.spectator_sockets.get(token)
        if previous:
            await previous.close(code=4001, reason=room.tr("error.account_connected"))
        room.spectator_sockets[token] = websocket
        spectator.connected = True
        await self.broadcast(room)
        return spectator

    async def disconnect_spectator(self, room: Room, token: str) -> None:
        room.spectator_sockets.pop(token, None)
        spectator = room.spectators.get(token)
        if spectator:
            spectator.connected = False
        await self.broadcast(room)

    async def spectator_chat(self, room: Room, spectator: Spectator, text: str) -> None:
        text = text.strip()
        if not text or len(text) > 80:
            raise GameError(room.tr("error.chat_too_long" if text else "error.chat_empty"))
        await self.broadcast_envelope(room, MessageType.CHAT, {
            "color": "spectator", "sender": spectator.display_name, "text": text,
            "quick": False, "timestamp": int(time.time() * 1000),
        })

    async def connect(self, room: Room, token: str, websocket: WebSocket) -> PlayerSeat:
        seat = self.seat_for(room, token)
        await websocket.accept()
        previous = room.sockets.get(token)
        if previous:
            await previous.close(code=4001, reason=room.tr("error.account_connected"))
        room.sockets[token] = websocket
        seat.connected = True
        seat.disconnected_at = None
        room.last_activity = time.time()
        return seat

    async def disconnect(self, room: Room, token: str) -> None:
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
        async with room.lock:
            if envelope.type is not MessageType.CHAT and envelope.revision is not None and envelope.revision != room.revision:
                raise GameError(room.tr("error.client_stale"))
            if envelope.type is MessageType.CHAT:
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
            elif envelope.type is MessageType.MOVE:
                if room.mode != "local" and room.game.state.turn is not seat.color:
                    raise GameError(room.tr("error.not_your_turn"))
                source = envelope.payload.get("from", {})
                target = envelope.payload.get("to", {})
                promotion = envelope.payload.get("promotion")
                move = Move(Position(int(source["row"]), int(source["col"])),
                            Position(int(target["row"]), int(target["col"])),
                            PieceType(promotion) if promotion else None)
                room.game.move(move)
                room.revision += 1
                room.last_activity = time.time()
            elif envelope.type is MessageType.RESIGN:
                resigning = room.game.state.turn if room.mode == "local" else seat.color
                room.game.resign(resigning)
                room.revision += 1
            elif envelope.type is MessageType.DRAW_OFFER:
                if room.mode == "local":
                    room.game.state.draw = True
                    room.game.state.result_reason = "draw_agreement"
                else:
                    room.game.offer_draw(seat.color)
                room.revision += 1
            elif envelope.type is MessageType.DRAW_RESPONSE:
                room.game.respond_draw(seat.color, bool(envelope.payload.get("accept")))
                room.revision += 1
            elif envelope.type is MessageType.UNDO_REQUEST:
                if room.mode == "local":
                    room.game.undo(1)
                else:
                    room.game.offer_undo(seat.color)
                room.revision += 1
            elif envelope.type is MessageType.UNDO_RESPONSE:
                room.game.respond_undo(seat.color, bool(envelope.payload.get("accept")))
                room.revision += 1
            elif envelope.type is MessageType.RESURRECT:
                color = room.game.state.turn if room.mode == "local" else seat.color
                room.game.resurrect_pawn(color, Position(int(envelope.payload["row"]),
                                                         int(envelope.payload["col"])))
                room.revision += 1
            elif envelope.type is MessageType.RESTART:
                profile_id = room.game.profile.id
                room.game = Game(profile_id, envelope.payload.get("options"), room.initial_minutes,
                                 room.language, room.game.setup)
                room.revision += 1
            elif envelope.type is MessageType.PAUSE:
                paused = bool(envelope.payload.get("paused", not room.game.state.paused))
                room.game.set_paused(paused, seat.color)
                room.revision += 1
            elif envelope.type is not MessageType.PING:
                raise GameError(room.tr("error.unsupported_message"))
        if envelope.type is MessageType.CHAT:
            await self.broadcast_envelope(room, MessageType.CHAT, payload)
            return
        await self.broadcast(room)
        if (room.mode == "ai" and not room.game.state.finished and not room.game.state.paused
                and room.game.state.turn is seat.color.opponent):
            await self._play_ai(room)

    async def _play_ai(self, room: Room) -> None:
        state = room.game.state.clone()
        options = room.game.options
        ai = ChessAI(room.ai_difficulty)
        move = await asyncio.to_thread(ai.choose_move, Game.from_state(state, options))
        async with room.lock:
            if move and room.game.state.turn is state.turn and room.game.state.history == state.history:
                room.game.move(move)
                room.revision += 1
        await self.broadcast(room)

    async def broadcast(self, room: Room) -> None:
        dead: list[str] = []
        for token, socket in list(room.sockets.items()):
            try:
                await socket.send_json(Envelope(type=MessageType.STATE, roomId=room.id,
                                                revision=room.revision,
                                                payload=room.snapshot(token)).wire())
            except Exception:
                dead.append(token)
        for token in dead:
            room.sockets.pop(token, None)
        dead_spectators: list[str] = []
        for token, socket in list(room.spectator_sockets.items()):
            try:
                await socket.send_json(Envelope(type=MessageType.STATE, roomId=room.id,
                                                revision=room.revision,
                                                payload=room.snapshot(token)).wire())
            except Exception:
                dead_spectators.append(token)
        for token in dead_spectators:
            room.spectator_sockets.pop(token, None)

    async def broadcast_envelope(self, room: Room, type_: MessageType,
                                 payload: dict[str, Any]) -> None:
        dead: list[str] = []
        for token, socket in list(room.sockets.items()):
            try:
                await socket.send_json(Envelope(type=type_, roomId=room.id,
                                                revision=room.revision,
                                                payload=payload).wire())
            except Exception:
                dead.append(token)
        for token in dead:
            room.sockets.pop(token, None)
        dead_spectators: list[str] = []
        for token, socket in list(room.spectator_sockets.items()):
            try:
                await socket.send_json(Envelope(type=type_, roomId=room.id,
                                                revision=room.revision,
                                                payload=payload).wire())
            except Exception:
                dead_spectators.append(token)
        for token in dead_spectators:
            room.spectator_sockets.pop(token, None)

    async def cleanup(self) -> None:
        now = time.time()
        stale: list[str] = []
        for room_id, room in self.rooms.items():
            disconnected = [s for s in room.seats.values() if s.token != "ai" and not s.connected]
            expired_player = any(s.disconnected_at and now - s.disconnected_at > RECONNECT_GRACE_SECONDS
                                 for s in disconnected)
            if expired_player and not room.game.state.finished and room.mode == "online":
                for seat in disconnected:
                    if seat.disconnected_at and now - seat.disconnected_at > RECONNECT_GRACE_SECONDS:
                        room.game.state.winner = seat.color.opponent
                        room.game.state.result_reason = "disconnect_timeout"
                        room.revision += 1
            if room.game.state.finished and now - room.last_activity > 3600:
                stale.append(room_id)
        for room_id in stale:
            self.rooms.pop(room_id, None)

    def _room_id(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            room_id = "".join(secrets.choice(alphabet) for _ in range(6))
            if room_id not in self.rooms:
                return room_id
