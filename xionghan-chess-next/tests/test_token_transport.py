"""S5：座位 token 不再走 query string。

query 里的 token 会被写进访问日志、浏览器历史、Referer —— 那是持续泄露。
现在：REST 走 `X-Room-Token` 头，WS 走**连接后的首帧** `{"type":"auth","token":...}`。
**不做兼容期**：旧的 `?token=` 直接拒绝（留一条兼容路径＝留着泄露渠道）。
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from xionghan_chess.core.profiles import RULE_VERSION
from xionghan_chess.service.app import app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def _room(client: TestClient) -> tuple[str, str]:
    created = client.post(
        "/api/rooms",
        json={"ruleVersion": RULE_VERSION, "profileId": "traditional", "mode": "local", "playerName": "P1"},
    ).json()
    return created["roomId"], created["token"]


def test_query_token_is_rejected_on_rest(client: TestClient) -> None:
    room_id, token = _room(client)
    response = client.get(f"/api/rooms/{room_id}?token={token}")
    assert response.status_code == 400, response.status_code
    assert "X-Room-Token" in response.json()["detail"]


def test_header_token_is_accepted_on_rest(client: TestClient) -> None:
    room_id, token = _room(client)
    response = client.get(f"/api/rooms/{room_id}", headers={"X-Room-Token": token})
    assert response.status_code == 200, response.text
    assert response.json()["roomId"] == room_id


def test_query_token_is_rejected_on_websocket(client: TestClient) -> None:
    room_id, token = _room(client)
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(f"/ws/{room_id}?token={token}") as socket:
            socket.receive_json()
    assert closed.value.code == 4401


def test_auth_first_frame_connects(client: TestClient) -> None:
    room_id, token = _room(client)
    with client.websocket_connect(f"/ws/{room_id}") as socket:
        socket.send_json({"type": "auth", "token": token})
        state = socket.receive_json()
    assert state["type"] == "state"
    assert state["payload"]["roomId"] == room_id


def test_invalid_auth_frame_closes_with_4401(client: TestClient) -> None:
    """首帧不是 JSON → 直接 close(4401)，不留半连接。"""
    room_id, _token = _room(client)
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(f"/ws/{room_id}") as socket:
            socket.send_text("这不是 JSON")
            socket.receive_json()
    assert closed.value.code == 4401


def test_auth_timeout_closes_with_4401(client: TestClient, monkeypatch) -> None:
    """5 秒内没收到 auth → close(4401)（测试里把超时压到 50ms）。"""
    from xionghan_chess.service import app as app_module

    monkeypatch.setattr(app_module, "AUTH_TIMEOUT_SECONDS", 0.05, raising=False)
    room_id, _token = _room(client)
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(f"/ws/{room_id}") as socket:
            socket.receive_json()
    assert closed.value.code == 4401
