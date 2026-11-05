"""Y1：local 房必须带 `revision`（否则乱序/重复消息会被采纳）。

原写法 `revision is not None and ...` 会让"客户端不填 revision"整段跳过校验；
online 房还有 turn 兜底，local 房没有。
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from xionghan_chess.core.profiles import RULE_VERSION
from xionghan_chess.service.app import app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def _open_local(client: TestClient):
    created = client.post("/api/rooms", json={
        "ruleVersion": RULE_VERSION,
        "profileId": "traditional", "mode": "local", "playerName": "P1"}).json()
    return created["roomId"], created["token"]


def _first_move():
    from xionghan_chess.core.game import Game

    game = Game("traditional")
    move = next(iter(game.rules.legal_moves(game.state)))
    return move


def test_local_move_without_revision_is_rejected(client: TestClient) -> None:
    room_id, token = _open_local(client)
    move = _first_move()
    with client.websocket_connect(f"/ws/{room_id}") as socket:
        socket.send_json({"type": "auth", "token": token})
        snapshot = socket.receive_json()["payload"]
        socket.send_json({"type": "move", "roomId": room_id, "protocolVersion": 1,
                          "payload": {"from": {"row": move.source.row, "col": move.source.col},
                                      "to": {"row": move.target.row, "col": move.target.col}}})
        reply = socket.receive_json()
    assert reply["type"] == "error", reply
    assert "revision" in reply["payload"]["message"]
    assert snapshot["revision"] >= 0


def test_local_move_with_stale_revision_is_rejected(client: TestClient) -> None:
    room_id, token = _open_local(client)
    move = _first_move()
    with client.websocket_connect(f"/ws/{room_id}") as socket:
        socket.send_json({"type": "auth", "token": token})
        snapshot = socket.receive_json()["payload"]
        socket.send_json({"type": "move", "roomId": room_id,
                          "revision": snapshot["revision"] - 1, "protocolVersion": 1,
                          "payload": {"from": {"row": move.source.row, "col": move.source.col},
                                      "to": {"row": move.target.row, "col": move.target.col}}})
        reply = socket.receive_json()
    assert reply["type"] == "error", reply


def test_local_move_with_correct_revision_is_accepted(client: TestClient) -> None:
    room_id, token = _open_local(client)
    move = _first_move()
    with client.websocket_connect(f"/ws/{room_id}") as socket:
        socket.send_json({"type": "auth", "token": token})
        snapshot = socket.receive_json()["payload"]
        socket.send_json({"type": "move", "roomId": room_id,
                          "revision": snapshot["revision"], "protocolVersion": 1,
                          "payload": {"from": {"row": move.source.row, "col": move.source.col},
                                      "to": {"row": move.target.row, "col": move.target.col}}})
        reply = socket.receive_json()
    assert reply["type"] == "state", reply
    assert len(reply["payload"]["game"]["history"]) == 1
