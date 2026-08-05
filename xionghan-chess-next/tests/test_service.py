from fastapi.testclient import TestClient

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
