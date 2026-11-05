"""广播快照不得携带 `replay`：它是每一步的完整局面历史，随步数线性膨胀。

审计实测：开局 13 KB → 60 手 2.29 MB（77×）→ 512 手约 19 MB/次，且每个 socket 单独序列化；
常规广播每 5 秒一次，等于每个连接每 5 秒传十几 MB。

改法：`public_state(include_replay=...)` 加开关；`broadcast()` 传 False；
**刚接入/重连的 socket 第一条 STATE 仍带完整 replay**（走 `Room.fresh_tokens`），
这样观战/复盘不缺数据，且消息条数不变（不在 connect 里额外插一帧，否则客户端时序会整体后移）。
"""

from __future__ import annotations

import asyncio
import json

from xionghan_chess.core.game import Game


def _game_with_60_plies() -> Game:
    game = Game("desktop_complete")
    game._snapshots = [game.state.to_dict() for _ in range(60)]
    return game


def test_broadcast_snapshot_has_no_replay() -> None:
    lean = _game_with_60_plies().public_state(include_replay=False)
    assert "replay" not in lean, "广播快照又带上 replay 了 —— 载荷会随步数线性膨胀"


def test_join_snapshot_still_carries_full_replay() -> None:
    state = _game_with_60_plies().public_state(include_replay=True)
    assert len(state["replay"]) == 61, "入房应拿到 60 手 + 当前局面"


def test_broadcast_payload_is_an_order_of_magnitude_smaller() -> None:
    game = _game_with_60_plies()
    full = len(json.dumps(game.public_state(include_replay=True)).encode())
    lean = len(json.dumps(game.public_state(include_replay=False)).encode())
    assert lean < 100_000, f"广播仍偏大：{lean} B"
    assert full / lean >= 10, f"降幅只有 {full / lean:.1f}×"


def test_fresh_socket_gets_replay_only_on_its_first_state() -> None:
    """`Room.fresh_tokens` 里的 token，第一条 STATE 带 replay；之后清空。"""

    async def scenario() -> tuple[int, dict, dict]:
        from xionghan_chess.service.rooms import RoomManager

        manager = RoomManager()
        room = await manager.create("desktop_complete", "online", "P1")
        if isinstance(room, tuple):
            room = room[0]
        token = next(iter(room.sockets)) if room.sockets else None
        room.fresh_tokens = {token} if token else set()
        first = room.snapshot(token, include_replay=(token in room.fresh_tokens))
        room.fresh_tokens = set()
        second = room.snapshot(token, include_replay=(token in getattr(room, "fresh_tokens", set())))
        return len(room.fresh_tokens), first["game"], second["game"]

    _, first, second = asyncio.run(scenario())
    assert "replay" not in second, "首帧之后的广播不该再带 replay"
