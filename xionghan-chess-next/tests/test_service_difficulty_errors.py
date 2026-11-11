"""D-2 / D-3：服务层档位只对外三档，存储归一旧档名。

背景（两个缺陷同时修，必须同一个提交）：

- **D-2 报错文案**：`Difficulty` 保留 6 个成员是桌面兼容层（老 `settings.json` 可能
  存 `expert`/`master`），但对外接口只该暴露 beginner / medium / hard。此前三个请求
  模型直接吃 `Difficulty`，传 `"nope"` 时 pydantic 的报错会把 6 个成员全列出来。
- **D-3 存储归一**：`Room.ai_difficulty` 此前原样收下调用方给的档位，旧客户端传
  `expert` 就会存进 `expert`，再广播给前端 —— 库里/线上出现旧名。

`Room.__post_init__` 是**单一入口**：`create` 与 `create_from_game`（以及将来新增的
构造点）都自动覆盖。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from xionghan_chess.core.ai import PUBLIC_DIFFICULTIES, Difficulty
from xionghan_chess.core.game import Game
from xionghan_chess.core.storage import game_document
from xionghan_chess.service.app import app, manager
from xionghan_chess.service.rooms import Room


def test_create_room_rejects_unknown_difficulty_with_three_options_only() -> None:
    """未知档位 → 400，且正文只列对外三档，不泄漏 easy/expert/master。"""
    with TestClient(app) as client:
        response = client.post(
            "/api/rooms",
            json={"profileId": "web", "mode": "ai", "playerName": "red", "difficulty": "nope"},
        )

    assert response.status_code == 400, response.text
    body = response.text.lower()
    for legacy in ("easy", "expert", "master"):
        assert legacy not in body, f"报错正文泄漏了内部旧档名 {legacy!r}：{response.text}"
    # 去掉 pydantic 的 "Value error, " 前缀后，中文提示应当是可读的
    assert "未知档位" in response.text
    assert "beginner / medium / hard" in response.text


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [("easy", Difficulty.BEGINNER), ("expert", Difficulty.HARD), ("master", Difficulty.HARD)],
)
def test_room_post_init_normalizes_legacy_names(legacy: str, expected: Difficulty) -> None:
    """直接构造 Room 也要归一 —— 这是 create / create_from_game 的共同入口。"""
    room = Room(id="r1", game=Game("web"), mode="ai", ai_difficulty=legacy)

    assert room.ai_difficulty is expected
    assert room.ai_difficulty in PUBLIC_DIFFICULTIES


def test_import_room_normalizes_expert_to_hard() -> None:
    """导入路径不走 `create`，靠 `__post_init__` 覆盖 —— 显式证明这一点。"""
    with TestClient(app) as client:
        response = client.post(
            "/api/rooms/import",
            json={
                "document": game_document(Game("web")),
                "mode": "local",
                "playerName": "本机玩家",
                "difficulty": "expert",
            },
        )

    assert response.status_code == 200, response.text
    room = manager.rooms[response.json()["roomId"]]
    assert room.ai_difficulty is Difficulty.HARD
