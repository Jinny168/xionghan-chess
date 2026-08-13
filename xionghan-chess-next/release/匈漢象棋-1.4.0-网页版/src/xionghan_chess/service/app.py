from __future__ import annotations

from contextlib import asynccontextmanager, suppress
import asyncio
from dataclasses import asdict
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from xionghan_chess.core.ai import Difficulty
from xionghan_chess.core.analysis import analyze_game
from xionghan_chess.core.game import GameError
from xionghan_chess.core.model import Color, Position
from xionghan_chess.core.profiles import PROFILES
from xionghan_chess.core.protocol import Envelope, MessageType
from .rooms import RoomManager
from xionghan_chess.core.rules import archer_star_points
from xionghan_chess.core.storage import game_from_document
from xionghan_chess.core.storage import game_document
from xionghan_chess.core.puzzles import load_puzzles, puzzle_by_id
from xionghan_chess.core.setup import FirstMove, profile_slots
from xionghan_chess.i18n import normalize_language, t
from .accounts import Account, AccountError, AccountStore


manager = RoomManager()
accounts = AccountStore()
WEB_DIR = Path(__file__).resolve().parents[3] / "web"
LOCALES_DIR = Path(__file__).resolve().parents[3] / "locales"


async def maintenance() -> None:
    while True:
        await asyncio.sleep(5)
        for room in list(manager.rooms.values()):
            await manager.tick(room)
            await manager.broadcast(room)
        await manager.cleanup()


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(maintenance())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="匈汉象棋 API", version="1.4.0", lifespan=lifespan)


class CreateRoomRequest(BaseModel):
    profile_id: str = Field("web", alias="profileId")
    mode: str = "online"
    player_name: str = Field("玩家", alias="playerName")
    player_color: Color = Field(Color.RED, alias="playerColor")
    difficulty: Difficulty = Difficulty(os.getenv("AI_DEFAULT_DIFFICULTY", "medium"))
    options: dict[str, object] = Field(default_factory=dict)
    initial_minutes: int = Field(20, ge=1, le=180, alias="initialMinutes")
    language: str = "zh-CN"
    first_move: FirstMove = Field(FirstMove.RED, alias="firstMove")
    red_slots: list[str] | None = Field(None, alias="redSlots")
    black_slots: list[str] | None = Field(None, alias="blackSlots")
    model_config = {"populate_by_name": True}


class JoinRoomRequest(BaseModel):
    player_name: str = Field("玩家", alias="playerName")
    language: str = "zh-CN"
    model_config = {"populate_by_name": True}


class ImportGameRequest(BaseModel):
    document: dict
    mode: str = "local"
    player_name: str = Field("玩家", alias="playerName")
    player_color: Color = Field(Color.RED, alias="playerColor")
    difficulty: Difficulty = Difficulty.MEDIUM
    language: str = "zh-CN"
    model_config = {"populate_by_name": True}


class CredentialsRequest(BaseModel):
    username: str
    password: str
    display_name: str = Field("", alias="displayName")
    model_config = {"populate_by_name": True}


class PreferencesRequest(BaseModel):
    preferences: dict[str, object] = Field(default_factory=dict)


class CloudGameRequest(BaseModel):
    document: dict
    title: str = ""
    game_id: int | None = Field(None, alias="gameId")
    model_config = {"populate_by_name": True}


class FavoriteRequest(BaseModel):
    favorite: bool = True


class SpectateRequest(BaseModel):
    display_name: str = Field("观众", alias="displayName")
    model_config = {"populate_by_name": True}


class AnalyzeRequest(BaseModel):
    document: dict
    difficulty: Difficulty = Difficulty.BEGINNER


def bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "请先登录")
    return authorization[7:].strip()


def current_account(authorization: str | None) -> tuple[Account, str]:
    token = bearer_token(authorization)
    try:
        return accounts.authenticate(token), token
    except AccountError as exc:
        raise HTTPException(401, str(exc)) from exc


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "rooms": len(manager.rooms), "version": app.version}


@app.get("/api/profiles")
async def profiles() -> list[dict]:
    return [{"id": p.id, "title": p.title, "rows": p.rows, "cols": p.cols,
             "pieceTypes": sorted(t.value for t in p.enabled_piece_types),
             "pieceSlots": profile_slots(p, p.options),
             "archerStarPoints": [{"row": point.row, "col": point.col}
                                  for point in sorted(archer_star_points(p),
                                                      key=lambda item: (item.row, item.col))],
             "options": asdict(p.options)} for p in PROFILES.values()]


@app.post("/api/rooms")
async def create_room(request: CreateRoomRequest) -> dict:
    if request.mode not in {"online", "ai", "local"}:
        raise HTTPException(400, "mode must be online, ai or local")
    try:
        language = normalize_language(request.language)
        room, seat = await manager.create(request.profile_id, request.mode, request.player_name,
                                          request.player_color, request.difficulty, request.options,
                                          request.initial_minutes, language, {
                                              "firstMove": request.first_move.value,
                                              "redSlots": request.red_slots,
                                              "blackSlots": request.black_slots,
                                          })
        if request.mode == "ai" and room.game.state.turn is not seat.color:
            await manager._play_ai(room)
        return {"roomId": room.id, "token": seat.token, "color": seat.color.value,
                "snapshot": room.snapshot(seat.token)}
    except (GameError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/rooms/import")
async def import_room(request: ImportGameRequest) -> dict:
    if request.mode not in {"ai", "local"}:
        raise HTTPException(400, "imported games support ai or local mode")
    try:
        language = normalize_language(request.language)
        game = game_from_document(request.document)
        room, seat = await manager.create_from_game(
            game, request.mode, request.player_name, request.player_color,
            request.difficulty, language,
        )
        if request.mode == "ai" and not room.game.state.finished and room.game.state.turn is not seat.color:
            await manager._play_ai(room)
        return {"roomId": room.id, "token": seat.token, "color": seat.color.value,
                "snapshot": room.snapshot(seat.token)}
    except (GameError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/rooms/{room_id}/join")
async def join_room(room_id: str, request: JoinRoomRequest) -> dict:
    try:
        room, seat = await manager.join(room_id.upper(), request.player_name)
        async with room.lock:
            room.language = normalize_language(request.language)
            room.game.language = room.language
        await manager.broadcast(room)
        return {"roomId": room.id, "token": seat.token, "color": seat.color.value,
                "snapshot": room.snapshot(seat.token)}
    except GameError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/rooms/{room_id}")
async def room_state(room_id: str, token: str | None = None) -> dict:
    try:
        return manager.require(room_id).snapshot(token)
    except GameError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/rooms/{room_id}/spectate")
async def spectate_room(room_id: str, request: SpectateRequest) -> dict:
    try:
        room, spectator = await manager.add_spectator(room_id.upper(), request.display_name)
        return {"roomId": room.id, "token": spectator.token,
                "snapshot": room.snapshot(spectator.token)}
    except GameError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/rooms/{room_id}/legal")
async def legal_moves(room_id: str, token: str, row: int, col: int) -> dict:
    try:
        room = manager.require(room_id)
        seat = manager.seat_for(room, token)
        source = Position(row, col)
        piece = room.game.state.piece_at(source)
        controlled_color = room.game.state.turn if room.mode == "local" else seat.color
        if (room.game.state.paused or not piece or piece.color is not controlled_color
                or room.game.state.turn is not controlled_color):
            return {"revision": room.revision, "moves": []}
        moves = [m for m in room.game.rules.legal_moves(room.game.state) if m.source == source]
        captures = {
            captured.position
            for move in moves
            for captured in room.game.rules.captured_by_move(room.game.state, move)
        }
        return {"revision": room.revision,
                "moves": [{"row": m.target.row, "col": m.target.col} for m in moves],
                "captures": [{"row": pos.row, "col": pos.col}
                             for pos in sorted(captures)]}
    except GameError as exc:
        raise HTTPException(403, str(exc)) from exc


@app.websocket("/ws/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str, token: str) -> None:
    try:
        room = manager.require(room_id)
        seat = await manager.connect(room, token, websocket)
        await manager.broadcast(room)
        while True:
            envelope = await receive_envelope(websocket)
            try:
                await manager.handle(room, seat, envelope)
            except (GameError, KeyError, TypeError, ValueError) as exc:
                await websocket.send_json(Envelope(type=MessageType.ERROR,
                                                   requestId=envelope.request_id,
                                                   revision=room.revision,
                                                   payload={"message": str(exc), "state": room.snapshot(token)}).wire())
    except WebSocketDisconnect:
        if "room" in locals():
            await manager.disconnect(room, token, websocket)
    except GameError as exc:
        await websocket.close(code=4403, reason=str(exc))


@app.websocket("/ws/{room_id}/spectate")
async def websocket_spectator(websocket: WebSocket, room_id: str, token: str) -> None:
    try:
        room = manager.require(room_id)
        spectator = await manager.connect_spectator(room, token, websocket)
        while True:
            envelope = await receive_envelope(websocket)
            if envelope.type is not MessageType.CHAT:
                await websocket.send_json(Envelope(type=MessageType.ERROR,
                                                   requestId=envelope.request_id,
                                                   revision=room.revision,
                                                   payload={"message": "观战通道仅允许聊天"}).wire())
                continue
            try:
                await manager.spectator_chat(room, spectator,
                                             str(envelope.payload.get("text", "")))
            except GameError as exc:
                await websocket.send_json(Envelope(type=MessageType.ERROR,
                                                   revision=room.revision,
                                                   payload={"message": str(exc)}).wire())
    except WebSocketDisconnect:
        if "room" in locals():
            await manager.disconnect_spectator(room, token, websocket)
    except GameError as exc:
        await websocket.close(code=4403, reason=str(exc))


async def receive_envelope(websocket: WebSocket) -> Envelope:
    try:
        return Envelope.model_validate(await websocket.receive_json())
    except ValidationError as exc:
        await websocket.close(code=1002, reason="Unsupported or invalid protocol message")
        raise WebSocketDisconnect(code=1002) from exc


@app.post("/api/auth/register")
async def register(request: CredentialsRequest) -> dict:
    try:
        account, token = await asyncio.to_thread(
            accounts.register, request.username, request.password, request.display_name)
        return {"account": account.public(), "token": token,
                "preferences": accounts.preferences(account.id)}
    except AccountError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/auth/login")
async def login(request: CredentialsRequest) -> dict:
    try:
        account, token = await asyncio.to_thread(accounts.login, request.username, request.password)
        return {"account": account.public(), "token": token,
                "preferences": accounts.preferences(account.id)}
    except AccountError as exc:
        raise HTTPException(401, str(exc)) from exc


@app.post("/api/auth/logout")
async def logout(authorization: str | None = Header(None)) -> dict:
    _, token = current_account(authorization)
    await asyncio.to_thread(accounts.logout, token)
    return {"ok": True}


@app.get("/api/me")
async def me(authorization: str | None = Header(None)) -> dict:
    account, _ = current_account(authorization)
    return {"account": account.public(), "preferences": accounts.preferences(account.id)}


@app.put("/api/me/preferences")
async def save_cloud_preferences(request: PreferencesRequest,
                                 authorization: str | None = Header(None)) -> dict:
    account, _ = current_account(authorization)
    return {"preferences": await asyncio.to_thread(
        accounts.save_preferences, account.id, request.preferences)}


@app.get("/api/me/games")
async def cloud_games(favorite: bool | None = None,
                      authorization: str | None = Header(None)) -> list[dict]:
    account, _ = current_account(authorization)
    return await asyncio.to_thread(accounts.list_games, account.id, favorite)


@app.post("/api/me/games")
async def save_cloud_game(request: CloudGameRequest,
                          authorization: str | None = Header(None)) -> dict:
    account, _ = current_account(authorization)
    try:
        game_from_document(request.document)
        return await asyncio.to_thread(accounts.save_game, account.id, request.document,
                                       request.title, request.game_id)
    except (AccountError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/me/games/{game_id}")
async def cloud_game(game_id: int, authorization: str | None = Header(None)) -> dict:
    account, _ = current_account(authorization)
    try:
        return await asyncio.to_thread(accounts.get_game, account.id, game_id)
    except AccountError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.put("/api/me/games/{game_id}/favorite")
async def favorite_cloud_game(game_id: int, request: FavoriteRequest,
                              authorization: str | None = Header(None)) -> dict:
    account, _ = current_account(authorization)
    try:
        return await asyncio.to_thread(accounts.favorite_game, account.id, game_id, request.favorite)
    except AccountError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.delete("/api/me/games/{game_id}")
async def delete_cloud_game(game_id: int, authorization: str | None = Header(None)) -> dict:
    account, _ = current_account(authorization)
    await asyncio.to_thread(accounts.delete_game, account.id, game_id)
    return {"ok": True}


@app.post("/api/analysis")
async def analysis(request: AnalyzeRequest) -> dict:
    try:
        game = game_from_document(request.document)
        return await asyncio.to_thread(analyze_game, game, request.difficulty)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/puzzles")
async def puzzles(difficulty: str | None = None) -> list[dict]:
    items = load_puzzles()
    if difficulty:
        items = [item for item in items if item.difficulty == difficulty]
    return [item.summary() for item in items]


@app.get("/api/puzzles/{puzzle_id}")
async def puzzle(puzzle_id: str, reveal: bool = False) -> dict:
    try:
        return puzzle_by_id(puzzle_id).payload(reveal)
    except KeyError as exc:
        raise HTTPException(404, "习题不存在") from exc


if WEB_DIR.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")
    app.mount("/css", StaticFiles(directory=WEB_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=WEB_DIR / "js"), name="js")
    if LOCALES_DIR.exists():
        app.mount("/locales", StaticFiles(directory=LOCALES_DIR), name="locales")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")


def run() -> None:
    import uvicorn
    uvicorn.run("xionghan_chess.service.app:app", host="0.0.0.0",
                port=int(os.getenv("PORT", "8000")), reload=False)


if __name__ == "__main__":
    run()
