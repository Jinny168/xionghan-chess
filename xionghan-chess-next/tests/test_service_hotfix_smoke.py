"""服务端 hotfix 冒烟：端点不再 500 / 僵尸房回收 / options 类型校验。

这一组存在的原因：S1 那个 `NameError`（`game_from_document` 没导入）让两个端点必 500，
而**单测全绿**——core 覆盖得很全，端点一次都没打过。所以这里从 HTTP 层打。
"""

from __future__ import annotations

import asyncio
import time

import pytest

pytest.importorskip("fastapi", reason="端点冒烟需要 fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from xionghan_chess.service.app import app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def _minimal_document() -> dict:
    """最小可解析存档：双王 + 空池。"""
    return {
        "profileId": "desktop_complete",
        "state": {
            "pieces": [
                {"id": "k1", "type": "king", "color": "red", "row": 12, "col": 12},
                {"id": "k2", "type": "king", "color": "black", "row": 0, "col": 10},
            ],
            "turn": "red", "captured": {"red": [], "black": []}, "history": [],
        },
    }


def test_analysis_endpoint_is_not_500(client: TestClient) -> None:
    """S1：`/api/analysis` 必须能进到业务层（200 或 400 都行，**不能 500**）。"""
    response = client.post("/api/analysis", json={"document": _minimal_document()})
    assert response.status_code != 500, response.text
    assert response.status_code in (200, 400, 422), response.status_code


def test_cloud_save_endpoint_is_not_500(client: TestClient) -> None:
    """S1：`/api/me/games` 同理（未登录应 401/400，不能 500）。"""
    response = client.post("/api/me/games", json={"document": _minimal_document(), "title": "t"})
    assert response.status_code != 500, response.text


def test_room_rejects_non_bool_option(client: TestClient) -> None:
    """S3：字符串冒充布尔必须 400。"""
    response = client.post("/api/rooms", json={"options": {"pawn_promotion": "yes"}})
    assert response.status_code == 400, response.text
    assert "pawn_promotion" in response.text


def test_room_rejects_unknown_option_key(client: TestClient) -> None:
    """S3：未知键必须 400 并点出键名。"""
    response = client.post("/api/rooms", json={"options": {"unknown_key": 1}})
    assert response.status_code == 400, response.text
    assert "unknown_key" in response.text


def test_online_room_without_socket_is_reclaimed() -> None:
    """S2：建 online 房、从不连 socket，创建时间推到 20 分钟前 → `cleanup()` 后应被移除。"""
    from xionghan_chess.service.rooms import ZOMBIE_ROOM_SECONDS, RoomManager

    manager = RoomManager()

    async def scenario() -> bool:
        created = await manager.create("desktop_complete", "online", "P1")
        room = created[0] if isinstance(created, tuple) else created
        room.created_at = time.time() - (ZOMBIE_ROOM_SECONDS + 300)
        await manager.cleanup()
        return room.id in manager.rooms

    still_there = asyncio.run(scenario())
    assert not still_there, "从未连 socket 的 online 房没有被回收"


def test_invalid_json_goes_through_the_normal_disconnect_path() -> None:
    """B-02：发非法 JSON 后，连接关闭、**座位离线**、房间 socket 清空。

    以前 `json.JSONDecodeError` 会穿透 `receive_envelope`：既不回错误帧，
    也不进 `except WebSocketDisconnect` 的清理，结果"连接断了但座位仍在线"。
    """
    from xionghan_chess.service.app import manager
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(app)
    created = client.post("/api/rooms", json={
        "profileId": "desktop_complete", "mode": "local", "playerName": "P1"}).json()
    room_id, token = created["roomId"], created["token"]

    received: list[dict] = []
    with client.websocket_connect(f"/ws/{room_id}?token={token}") as socket:
        received.append(socket.receive_json())        # 首帧 STATE
        socket.send_text("这不是 JSON")
        try:
            received.append(socket.receive_json())    # 协议错误帧
        except WebSocketDisconnect:
            pass

    assert any(item.get("type") == "error" for item in received), f"没收到协议错误帧：{received}"
    room = manager.rooms.get(room_id)
    assert room is not None
    assert token not in room.sockets, "socket 没被清理"
    seat = next(s for s in room.seats.values() if s.token == token)
    assert seat.connected is False, "座位仍标记在线"


def test_player_name_length_is_capped(client: TestClient) -> None:
    """S4：玩家名按**码点**限 24；超长回 400 并点名字段，不静默截断。

    1MB 的名字曾让一次快照从 13 KB 涨到 1.01 MB，而快照是每 5 秒广播的。
    """
    for name in ("A" * 1024, "A" * 1_000_000):
        response = client.post("/api/rooms", json={
            "profileId": "traditional", "mode": "local", "playerName": name})
        assert response.status_code == 400, response.status_code
        assert "playerName" in response.json()["detail"]

    ok = client.post("/api/rooms", json={
        "profileId": "traditional", "mode": "local", "playerName": "名" * 24})
    assert ok.status_code == 200, ok.text


def test_player_name_length_is_capped(client: TestClient) -> None:
    """S4：玩家名按**码点**限 24；超长回 400 并点名字段，不静默截断。

    1MB 的名字曾让一次快照从 13 KB 涨到 1.01 MB，而快照是每 5 秒广播的。
    """
    for name in ("A" * 1024, "A" * 1_000_000):
        response = client.post("/api/rooms", json={
            "profileId": "traditional", "mode": "local", "playerName": name})
        assert response.status_code == 400, response.status_code
        assert "playerName" in response.json()["detail"]

    ok = client.post("/api/rooms", json={
        "profileId": "traditional", "mode": "local", "playerName": "名" * 24})
    assert ok.status_code == 200, ok.text


def test_oversized_frame_is_rejected() -> None:
    """B-05：单帧超过 64 KB → 回 ERROR 帧 + 抛 WebSocketDisconnect（走正常断开路径）。

    用桩对象直测 `receive_envelope`：走真实 WS 时"发 65 KB 文本"在不同 TestClient 版本上
    会阻塞（实测本机超时），而这里要验的是**判据**，不是传输层。
    """
    import asyncio

    from starlette.websockets import WebSocketDisconnect

    from xionghan_chess.service.app import MAX_FRAME_BYTES, receive_envelope

    class Stub:
        def __init__(self, text: str) -> None:
            self.text = text
            self.sent: list[dict] = []
            self.closed: int | None = None

        async def receive_text(self) -> str:
            return self.text

        async def send_json(self, payload: dict) -> None:
            self.sent.append(payload)

        async def close(self, code: int = 1000, reason: str | None = None) -> None:
            self.closed = code

    # ① 超大帧：先回 ERROR，再断开
    big = Stub("x" * (MAX_FRAME_BYTES + 1024))
    try:
        asyncio.run(receive_envelope(big))
    except WebSocketDisconnect as exc:
        assert exc.code == 1002
    else:
        raise AssertionError("超大帧没有断开连接")
    assert big.sent and big.sent[0]["type"] == "error", big.sent
    assert big.closed == 1002

    # ② 正常帧：照常返回信封（防止把上限做成 0 也能过）
    ok = Stub('{"type": "ping", "roomId": "A", "revision": 0, "protocolVersion": 1, "payload": {}}')
    envelope = asyncio.run(receive_envelope(ok))
    assert envelope.type.value == "ping"
    assert ok.closed is None
