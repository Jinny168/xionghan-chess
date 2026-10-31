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
