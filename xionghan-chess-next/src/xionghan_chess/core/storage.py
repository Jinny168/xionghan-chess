from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
import time
from typing import Any

from .game import Game
from .legacy import migrate_legacy_game
from .model import GameState, UnsupportedSaveError
from .profiles import get_profile
from .rules import POSITION_KEY_VERSION


FORMAT_VERSION = 1


def game_document(game: Game) -> dict[str, Any]:
    return {
        "formatVersion": FORMAT_VERSION,
        # Which `position_key` format the `state.positionCounts` ledger is in, so
        # a load can re-derive it instead of trusting keys it can no longer
        # reproduce (see `_rebuild_position_counts`).
        "positionKeyVersion": POSITION_KEY_VERSION,
        "profileId": game.profile.id,
        "options": asdict(game.options),
        "setup": game.setup.to_dict(),
        "state": game.state.to_dict(),
        "snapshots": list(game._snapshots),
        "savedAt": datetime.now().isoformat(timespec="seconds"),
    }


def _rebuild_position_counts(game: Game) -> dict[str, int]:
    """Re-derive the repetition ledger in the *current* key format.

    A document saved before `POSITION_KEY_VERSION` 2 carries a ledger keyed by
    the old pool-blind `position_key`. Those keys can never be produced again, so
    keeping them would silently drop every pre-load occurrence: a position seen
    twice before the load and once after would sit at 2 and the threefold draw
    would never fire (漏判). Replaying the document's own snapshots through
    today's `position_key` rebuilds the exact ledger, so the count carries across
    the version change instead of either side of it mis-judging (误判).

    The snapshot list is the pre-move state of every ply and the live state is
    the last one, which is exactly the set `Game._record_position` counted.
    """
    counts: dict[str, int] = {}
    for snapshot in game._snapshots:
        key = game.rules.position_key(GameState.from_dict(snapshot))
        counts[key] = counts.get(key, 0) + 1
    key = game.rules.position_key(game.state)
    counts[key] = counts.get(key, 0) + 1
    return counts


def _assert_in_bounds(profile, state, where: str) -> None:
    """按 `profile.rows/cols` 校验坐标上界。

    `Position` 只管非负；上界依赖棋盘尺寸，所以在这里查。
    越界会让 `piece_at` 静默取不到，最后变成"无王可吃"的僵尸局。
    """
    for piece in state.pieces:
        row, col = piece.position.row, piece.position.col
        # 上下界都查：`Position` 本身允许负值（引擎用它探测越界格），
        # 所以"存档里出现负坐标"只能在这里拦。
        if row < 0 or col < 0 or row >= profile.rows or col >= profile.cols:
            raise UnsupportedSaveError(
                f"{where}坐标越界：row={row}, col={col}（棋盘 {profile.rows}×{profile.cols}）")

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
    _profile = get_profile(profile_id)
    _assert_in_bounds(_profile, state, "当前局面")
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
        _assert_in_bounds(_profile, snapshot, f"复盘第 {len(snapshots) + 1} 步")
        snapshots.append(snapshot.to_dict())
    if snapshots and len(snapshots) != len(state.history):
        raise ValueError("棋谱步数与复盘数据不一致")
    game = Game.from_state(state, data.get("options", {}), data.get("setup"))
    game._snapshots = snapshots
    # A document written before the pool entered the key cannot be trusted as-is;
    # anything carrying today's marker is loaded verbatim.
    if int(data.get("positionKeyVersion", 1)) < POSITION_KEY_VERSION:
        game.state.position_counts = _rebuild_position_counts(game)
    game.state.turn_started_at = time.monotonic()
    return game


def game_from_content(value: str | dict[str, Any]) -> Game:
    """Load a current document or migrate legacy .fen content."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None
        data = parsed if isinstance(parsed, dict) else migrate_legacy_game(value)
    else:
        data = value
    if int(data.get("formatVersion", 0)) != FORMAT_VERSION:
        data = migrate_legacy_game(data)
    return game_from_document(data)
