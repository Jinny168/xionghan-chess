from __future__ import annotations

from contextlib import asynccontextmanager, suppress
import asyncio
from dataclasses import asdict
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from xionghan_chess.core.ai import Difficulty
from xionghan_chess.core.game import GameError
from xionghan_chess.core.model import Color, Position
from xionghan_chess.core.profiles import PROFILES
from xionghan_chess.core.protocol import Envelope, MessageType
from .rooms import RoomManager
from xionghan_chess.core.rules import archer_star_points
from xionghan_chess.core.storage import game_from_document


manager = RoomManager()
WEB_DIR = Path(__file__).resolve().parents[3] / "web"


async def maintenance() -> None:
    while True:
        await asyncio.sleep(5)
        for room in list(manager.rooms.values()):
            if room.mode in {"ai", "local"} or len(room.seats) == 2:
                room.game.tick()
            await manager.broadcast(room)
        await manager.cleanup()


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(maintenance())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="匈汉象棋 API", version="1.0.0", lifespan=lifespan)


class CreateRoomRequest(BaseModel):
    profile_id: str = Field("web", alias="profileId")
    mode: str = "online"
    player_name: str = Field("玩家", alias="playerName")
    player_color: Color = Field(Color.RED, alias="playerColor")
    difficulty: Difficulty = Difficulty(os.getenv("AI_DEFAULT_DIFFICULTY", "medium"))
    options: dict[str, object] = Field(default_factory=dict)
    initial_minutes: int = Field(20, ge=1, le=180, alias="initialMinutes")
    model_config = {"populate_by_name": True}


class JoinRoomRequest(BaseModel):
    player_name: str = Field("玩家", alias="playerName")
    model_config = {"populate_by_name": True}


class ImportGameRequest(BaseModel):
    document: dict
    mode: str = "local"
    player_name: str = Field("玩家", alias="playerName")
    player_color: Color = Field(Color.RED, alias="playerColor")
    difficulty: Difficulty = Difficulty.MEDIUM
    model_config = {"populate_by_name": True}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "rooms": len(manager.rooms)}


@app.get("/api/profiles")
async def profiles() -> list[dict]:
    return [{"id": p.id, "title": p.title, "rows": p.rows, "cols": p.cols,
             "pieceTypes": sorted(t.value for t in p.enabled_piece_types),
             "archerStarPoints": [{"row": point.row, "col": point.col}
                                  for point in sorted(archer_star_points(p),
                                                      key=lambda item: (item.row, item.col))],
             "options": asdict(p.options)} for p in PROFILES.values()]


@app.post("/api/rooms")
async def create_room(request: CreateRoomRequest) -> dict:
    if request.mode not in {"online", "ai", "local"}:
        raise HTTPException(400, "mode must be online, ai or local")
    try:
        room, seat = await manager.create(request.profile_id, request.mode, request.player_name,
                                          request.player_color, request.difficulty, request.options,
                                          request.initial_minutes)
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
        game = game_from_document(request.document)
        room, seat = await manager.create_from_game(
            game, request.mode, request.player_name, request.player_color,
            request.difficulty,
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


@app.get("/api/rooms/{room_id}/legal")
async def legal_moves(room_id: str, token: str, row: int, col: int) -> dict:
    try:
        room = manager.require(room_id)
        seat = manager.seat_for(room, token)
        source = Position(row, col)
        piece = room.game.state.piece_at(source)
        controlled_color = room.game.state.turn if room.mode == "local" else seat.color
        if not piece or piece.color is not controlled_color or room.game.state.turn is not controlled_color:
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
            envelope = Envelope.model_validate(await websocket.receive_json())
            try:
                await manager.handle(room, seat, envelope)
            except (GameError, KeyError, TypeError, ValueError) as exc:
                await websocket.send_json(Envelope(type=MessageType.ERROR,
                                                   requestId=envelope.request_id,
                                                   revision=room.revision,
                                                   payload={"message": str(exc), "state": room.snapshot(token)}).wire())
    except WebSocketDisconnect:
        if "room" in locals():
            await manager.disconnect(room, token)
    except GameError as exc:
        await websocket.close(code=4403, reason=str(exc))


if WEB_DIR.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")
    app.mount("/css", StaticFiles(directory=WEB_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=WEB_DIR / "js"), name="js")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")


def run() -> None:
    import uvicorn
    uvicorn.run("xionghan_chess.service.app:app", host="0.0.0.0",
                port=int(os.getenv("PORT", "8000")), reload=False)


if __name__ == "__main__":
    run()
