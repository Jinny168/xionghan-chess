from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import time
from typing import Any

from .game import Game
from .model import GameState


FORMAT_VERSION = 1


def game_document(game: Game) -> dict[str, Any]:
    return {
        "formatVersion": FORMAT_VERSION,
        "profileId": game.profile.id,
        "options": asdict(game.options),
        "setup": game.setup.to_dict(),
        "state": game.state.to_dict(),
        "snapshots": list(game._snapshots),
        "savedAt": datetime.now().isoformat(timespec="seconds"),
    }


def game_from_document(data: dict[str, Any]) -> Game:
    if not isinstance(data, dict):
        raise ValueError("棋谱文件内容无效")
    if int(data.get("formatVersion", 0)) != FORMAT_VERSION:
        raise ValueError("不支持的棋谱文件版本")
    raw_state = data.get("state")
    if not isinstance(raw_state, dict):
        raise ValueError("棋谱缺少有效的当前局面")
    state = GameState.from_dict(raw_state)
    profile_id = str(data.get("profileId", state.profile_id))
    if profile_id != state.profile_id:
        raise ValueError("棋谱规则档案与局面不一致")
    raw_snapshots = data.get("snapshots", [])
    if not isinstance(raw_snapshots, list):
        raise ValueError("棋谱复盘数据无效")
    snapshots: list[dict[str, Any]] = []
    for item in raw_snapshots:
        if not isinstance(item, dict):
            raise ValueError("棋谱复盘数据无效")
        snapshot = GameState.from_dict(item)
        if snapshot.profile_id != profile_id:
            raise ValueError("棋谱包含不同规则档案的局面")
        snapshots.append(snapshot.to_dict())
    if snapshots and len(snapshots) != len(state.history):
        raise ValueError("棋谱步数与复盘数据不一致")
    game = Game.from_state(state, data.get("options", {}), data.get("setup"))
    game._snapshots = snapshots
    game.state.turn_started_at = time.monotonic()
    return game
