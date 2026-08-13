import uuid

import pytest
from fastapi.testclient import TestClient

from xionghan_chess.core.analysis import analyze_game, quality_for_loss
from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color
from xionghan_chess.core.puzzles import load_puzzles
from xionghan_chess.core.profiles import get_profile
from xionghan_chess.core.setup import GameSetup, profile_slots
from xionghan_chess.core.storage import game_from_document
from xionghan_chess.service.accounts import AccountStore
from xionghan_chess.service import app as service_app


def test_custom_setup_requires_equal_counts_and_supports_black_first():
    profile = get_profile("web")
    slots = profile_slots(profile, profile.options)
    red = [item["id"] for item in slots if item["color"] == "red"]
    black = [item["id"] for item in slots if item["color"] == "black"]
    red.remove(next(item for item in red if ":pawn:" in item))
    black.remove(next(item for item in black if ":pawn:" in item))

    setup = GameSetup.build(profile, profile.options, "black", red, black)
    game = Game(profile, setup=setup)
    assert game.state.turn is Color.BLACK
    assert len([piece for piece in game.state.pieces if piece.color is Color.RED]) == len(red)
    assert len([piece for piece in game.state.pieces if piece.color is Color.BLACK]) == len(black)

    with pytest.raises(ValueError, match="same number"):
        GameSetup.build(profile, profile.options, "red", red[:-1], black)


def test_account_store_round_trip(tmp_path):
    store = AccountStore(tmp_path / "cloud.db")
    account, token = store.register("player_one", "password123", "棋手一")
    assert store.authenticate(token).id == account.id
    assert store.save_preferences(account.id, {"theme": "dark"}) == {"theme": "dark"}
    saved = store.save_game(account.id, {"formatVersion": 1}, "测试棋局")
    assert store.favorite_game(account.id, saved["id"], True)["favorite"] is True
    updated = store.update_profile(account.id, "新棋手", "https://example.com/avatar.png")
    assert updated.public()["avatarUrl"] == "https://example.com/avatar.png"
    assert store.authenticate(token).public()["displayName"] == "新棋手"


def test_auth_api_and_preferences_use_bearer_token(tmp_path, monkeypatch):
    monkeypatch.setattr(service_app, "accounts", AccountStore(tmp_path / "api.db"))
    username = f"user_{uuid.uuid4().hex[:8]}"
    with TestClient(service_app.app) as client:
        registered = client.post("/api/auth/register", json={
            "username": username, "password": "password123", "displayName": "云棋手",
        })
        assert registered.status_code == 200
        token = registered.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        saved = client.put("/api/me/preferences", headers=headers,
                           json={"preferences": {"pieceStyle": "modern"}})
        assert saved.json()["preferences"]["pieceStyle"] == "modern"
        assert client.get("/api/me", headers=headers).json()["account"]["username"] == username
        profile = client.put("/api/me/profile", headers=headers,
                             json={"displayName": "云端棋手", "avatarUrl": "https://example.com/a.png"})
        assert profile.status_code == 200
        assert profile.json()["account"]["avatarUrl"].endswith("a.png")


def test_room_snapshot_carries_avatar_and_taunt_setting():
    with TestClient(service_app.app) as client:
        created = client.post("/api/rooms", json={
            "profileId": "web", "mode": "ai", "playerName": "头像棋手",
            "avatarUrl": "https://example.com/player.png", "tauntsEnabled": False,
        })
        assert created.status_code == 200
        player = next(item for item in created.json()["snapshot"]["players"] if item["color"] == "red")
        assert player["avatarUrl"].endswith("player.png")
        assert created.json()["snapshot"]["chatHistory"] == []


def test_spectator_channel_is_read_only():
    with TestClient(service_app.app) as client:
        room = client.post("/api/rooms", json={
            "profileId": "web", "mode": "online", "playerName": "red",
        }).json()
        spectator = client.post(f"/api/rooms/{room['roomId']}/spectate",
                                json={"displayName": "viewer"}).json()
        with client.websocket_connect(
                f"/ws/{room['roomId']}/spectate?token={spectator['token']}") as socket:
            state = socket.receive_json()
            assert state["type"] == "state"
            assert state["payload"]["youAre"] is None
            socket.send_json({"type": "move", "protocolVersion": 1, "payload": {}})
            assert socket.receive_json()["type"] == "error"


def test_built_in_puzzle_solutions_are_legal():
    puzzles = load_puzzles()
    assert {item.difficulty for item in puzzles} == {"beginner", "advanced", "master"}
    for puzzle in puzzles:
        game = game_from_document(puzzle.document)
        for move in puzzle.solution:
            assert game.rules.is_legal(game.state, move), puzzle.id
            game.move(move)


def test_analysis_scores_played_move(monkeypatch):
    monkeypatch.setenv("AI_TIME_SCALE", "0.05")
    game = Game("traditional")
    game.move(game.rules.legal_moves(game.state)[0])
    result = analyze_game(game, "beginner")
    assert result["analyzedPlies"] == 1
    assert result["moves"][0]["quality"] in {
        "best", "good", "inaccuracy", "mistake", "blunder",
    }
    assert quality_for_loss(500) == "blunder"
