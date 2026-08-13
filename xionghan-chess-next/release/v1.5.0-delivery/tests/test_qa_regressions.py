import asyncio
from pathlib import Path

import pytest

from xionghan_chess.core.game import GameError
from xionghan_chess.core.model import Color
from xionghan_chess.core.protocol import Envelope, MessageType
from xionghan_chess.service.accounts import AccountStore
from xionghan_chess.service.rooms import RoomManager
import xionghan_chess.service.rooms as rooms_module


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.closed = None
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000, reason=""):
        self.closed = (code, reason)

    async def send_json(self, message):
        self.messages.append(message)


def test_replaced_socket_cannot_disconnect_current_connection():
    async def scenario():
        manager = RoomManager()
        room, seat = await manager.create("web", "online", "player")
        first = FakeWebSocket()
        second = FakeWebSocket()
        await manager.connect(room, seat.token, first)
        await manager.connect(room, seat.token, second)
        await manager.disconnect(room, seat.token, first)
        assert first.closed and first.closed[0] == 4001
        assert room.sockets[seat.token] is second
        assert seat.connected is True

    asyncio.run(scenario())


def test_ai_seat_token_is_random_and_rejected_for_clients():
    async def scenario():
        manager = RoomManager()
        room, human = await manager.create("web", "ai", "player")
        ai_seat = next(seat for seat in room.seats.values() if seat.is_ai)
        assert ai_seat.token != "ai"
        assert len(ai_seat.token) >= 32
        with pytest.raises(GameError):
            manager.seat_for(room, ai_seat.token)
        assert manager.seat_for(room, human.token) is human

    asyncio.run(scenario())


def test_ping_does_not_broadcast_state():
    async def scenario():
        manager = RoomManager()
        room, seat = await manager.create("web", "online", "player")
        called = False

        async def broadcast(_room):
            nonlocal called
            called = True

        manager.broadcast = broadcast
        await manager.handle(room, seat, Envelope(type=MessageType.PING, payload={}))
        assert called is False

    asyncio.run(scenario())


def test_ai_result_is_discarded_if_game_is_paused_during_search(monkeypatch):
    async def scenario():
        manager = RoomManager()
        room, _ = await manager.create("traditional", "ai", "player")
        human_move = room.game.rules.legal_moves(room.game.state)[0]
        room.game.move(human_move)
        ai_move = room.game.rules.legal_moves(room.game.state)[0]
        history_length = len(room.game.state.history)

        async def fake_to_thread(_function, *_args):
            room.game.set_paused(True)
            return ai_move

        monkeypatch.setattr(rooms_module.asyncio, "to_thread", fake_to_thread)
        await manager._play_ai(room)
        assert room.game.state.paused is True
        assert len(room.game.state.history) == history_length

    asyncio.run(scenario())


def test_cloud_preferences_are_merged_instead_of_replaced(tmp_path):
    store = AccountStore(tmp_path / "cloud.db")
    account, _ = store.register("merge_user", "password123", "Merge")
    store.save_preferences(account.id, {"boardTheme": "purple", "musicStyle": "qq"})
    merged = store.save_preferences(account.id, {"language": "en"})
    assert merged == {"boardTheme": "purple", "musicStyle": "qq", "language": "en"}


def test_move_invalidates_pending_undo_offer():
    async def scenario():
        manager = RoomManager()
        room, _ = await manager.create("traditional", "local", "player")
        room.game.move(room.game.rules.legal_moves(room.game.state)[0])
        room.game.offer_undo(Color.RED)
        room.game.move(room.game.rules.legal_moves(room.game.state)[0])
        assert room.game.state.pending_undo_offer is None
        with pytest.raises(GameError):
            room.game.respond_undo(Color.BLACK, True)

    asyncio.run(scenario())


def test_timeout_transition_increments_revision_once(monkeypatch):
    async def scenario():
        manager = RoomManager()
        room, _ = await manager.create("traditional", "local", "player")
        room.game.state.clocks_ms[room.game.state.turn] = 1
        monkeypatch.setattr(rooms_module.time, "monotonic", lambda: 10.0)
        room.game.state.turn_started_at = 0.0
        revision = room.revision
        await manager.tick(room)
        assert room.game.state.result_reason == "timeout"
        assert room.revision == revision + 1
        await manager.tick(room)
        assert room.revision == revision + 1

    asyncio.run(scenario())


def test_web_and_android_import_guards_are_present():
    root = Path(__file__).resolve().parents[1]
    web = (root / "web/js/app.js").read_text(encoding="utf-8")
    offline = (root / "android/Resources/assets/offline/offline.js").read_text(encoding="utf-8")
    offline_html = (root / "android/Resources/assets/offline/index.html").read_text(encoding="utf-8")
    assert "file.size>10*1024*1024" in web
    assert "items.every(validPuzzle)" in web
    assert "app.reconnectAttempts>=3" in web
    assert "loadGameDocument" in offline
    assert "legacyFenDocument" in offline
    assert "FEN_PIECES" in offline
    assert "game.recorded=!!game.state.winner||!!game.state.draw" in offline
    assert 'id="gameFileInput"' in offline_html
    assert ".fen" in offline_html


def test_android_offline_lobby_and_game_navigation_are_present():
    root = Path(__file__).resolve().parents[1]
    welcome = (root / "android/Resources/assets/offline/welcome.html").read_text(encoding="utf-8")
    offline = (root / "android/Resources/assets/offline/offline.js").read_text(encoding="utf-8")
    activity = (root / "android/MainActivity.cs").read_text(encoding="utf-8")
    assert "sessionStorage.setItem('xh-offline-start'" in welcome
    assert "location.replace('index.html?page=game')" in welcome
    assert "sessionStorage.getItem('xh-offline-start')" in offline
    assert "OfflineWelcomeUrl" in activity
    assert 'url.Contains("index.html"' in activity


def test_android_selection_sound_and_puzzle_i18n_guards_are_present():
    root = Path(__file__).resolve().parents[1]
    offline = (root / "android/Resources/assets/offline/offline.js").read_text(encoding="utf-8")
    locales = (root / "android/Resources/assets/offline/offline-locales.js").read_text(encoding="utf-8")
    assert "const changed=!selected||selected.id!==piece.id" in offline
    assert "if(changed)playSound('select')" in offline
    assert "toast(tr('puzzleSolved'))" in offline
    assert "puzzleSolved: 'Puzzle solved'" in locales
