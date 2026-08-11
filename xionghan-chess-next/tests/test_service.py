from fastapi.testclient import TestClient

from xionghan_chess.core.game import Game
from xionghan_chess.core.storage import game_document
from xionghan_chess.service.app import app


def test_legal_move_endpoint_uses_authoritative_engine():
    with TestClient(app) as client:
        created = client.post("/api/rooms", json={
            "profileId": "web", "mode": "online", "playerName": "red", "playerColor": "red"
        }).json()
        room_id, token = created["roomId"], created["token"]
        response = client.get(f"/api/rooms/{room_id}/legal", params={"token": token, "row": 8, "col": 0})
        assert response.status_code == 200
        assert {"row": 7, "col": 0} in response.json()["moves"]
        assert "captures" in response.json()


def test_ai_moves_first_when_human_selects_black():
    with TestClient(app) as client:
        created = client.post("/api/rooms", json={
            "profileId": "web", "mode": "ai", "playerName": "black",
            "playerColor": "black", "difficulty": "beginner"
        }).json()
        assert len(created["snapshot"]["game"]["history"]) == 1
        assert created["snapshot"]["game"]["turn"] == "black"


def test_chat_broadcast_does_not_advance_revision():
    with TestClient(app) as client:
        created = client.post("/api/rooms", json={
            "profileId": "web", "mode": "online", "playerName": "red", "playerColor": "red"
        }).json()
        room_id, token = created["roomId"], created["token"]
        revision = created["snapshot"]["revision"]
        with client.websocket_connect(f"/ws/{room_id}?token={token}") as socket:
            state = socket.receive_json()
            assert state["type"] == "state"
            socket.send_json({"type": "chat", "roomId": room_id, "revision": revision,
                              "protocolVersion": 1,
                              "payload": {"text": "好棋！", "quick": True}})
            chat = socket.receive_json()
            assert chat["type"] == "chat"
            assert chat["revision"] == revision
            assert chat["payload"]["text"] == "好棋！"
            assert chat["payload"]["quick"] is True


def test_local_mode_controls_both_colors_and_undoes_one_ply():
    with TestClient(app) as client:
        created = client.post("/api/rooms", json={
            "profileId": "traditional", "mode": "local", "playerName": "本机玩家"
        }).json()
        room_id, token = created["roomId"], created["token"]
        with client.websocket_connect(f"/ws/{room_id}?token={token}") as socket:
            snapshot = socket.receive_json()["payload"]
            first = snapshot["game"]["replay"][0]
            move = next(iter(Game("traditional").rules.legal_moves(Game("traditional").state)))
            socket.send_json({"type": "move", "roomId": room_id,
                              "revision": snapshot["revision"], "protocolVersion": 1,
                              "payload": {"from": {"row": move.source.row, "col": move.source.col},
                                          "to": {"row": move.target.row, "col": move.target.col}}})
            after_move = socket.receive_json()["payload"]
            assert after_move["game"]["turn"] == "black"
            legal_moves = []
            for black_piece in (p for p in after_move["game"]["pieces"] if p["color"] == "black"):
                legal = client.get(f"/api/rooms/{room_id}/legal", params={
                    "token": token, "row": black_piece["row"], "col": black_piece["col"]
                })
                legal_moves.extend(legal.json()["moves"])
            assert legal_moves
            socket.send_json({"type": "undo_request", "roomId": room_id,
                              "revision": after_move["revision"], "protocolVersion": 1,
                              "payload": {}})
            after_undo = socket.receive_json()["payload"]
            assert after_undo["game"]["pieces"] == first["pieces"]


def test_imported_game_can_resume_in_local_mode():
    game = Game("traditional")
    game.move(game.rules.legal_moves(game.state)[0])
    with TestClient(app) as client:
        response = client.post("/api/rooms/import", json={
            "document": game_document(game), "mode": "local", "playerName": "本机玩家"
        })
        assert response.status_code == 200
        payload = response.json()
        assert payload["snapshot"]["mode"] == "local"
        assert payload["snapshot"]["game"]["history"] == game.state.to_dict()["history"]


def test_imported_ai_game_continues_when_it_is_ai_turn():
    game = Game("traditional")
    game.move(game.rules.legal_moves(game.state)[0])
    with TestClient(app) as client:
        response = client.post("/api/rooms/import", json={
            "document": game_document(game), "mode": "ai", "playerName": "红方",
            "playerColor": "red", "difficulty": "beginner",
        })
        assert response.status_code == 200
        snapshot = response.json()["snapshot"]["game"]
        assert len(snapshot["history"]) == 2
        assert snapshot["turn"] == "red"


def test_pause_is_synchronized_and_blocks_legal_moves():
    with TestClient(app) as client:
        created = client.post("/api/rooms", json={
            "profileId": "traditional", "mode": "local", "playerName": "本机玩家"
        }).json()
        room_id, token = created["roomId"], created["token"]
        with client.websocket_connect(f"/ws/{room_id}?token={token}") as socket:
            snapshot = socket.receive_json()["payload"]
            socket.send_json({"type": "pause", "roomId": room_id,
                              "revision": snapshot["revision"], "protocolVersion": 1,
                              "payload": {"paused": True}})
            paused = socket.receive_json()["payload"]
            assert paused["game"]["paused"] is True
            legal = client.get(f"/api/rooms/{room_id}/legal", params={
                "token": token, "row": 6, "col": 0
            })
            assert legal.json()["moves"] == []

            socket.send_json({"type": "pause", "roomId": room_id,
                              "revision": paused["revision"], "protocolVersion": 1,
                              "payload": {"paused": False}})
            resumed = socket.receive_json()["payload"]
            assert resumed["game"]["paused"] is False
