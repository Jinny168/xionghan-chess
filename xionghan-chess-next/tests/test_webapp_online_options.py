"""M5 联机规则取源静态守卫：房间权威 options，本机 prefs 不得混入。

回归背景：webapp 联机走 Node HTTP 长轮询（online/server.mjs），snapshot() 不下发
options，房间由 createRoom() 用档案默认 options 创建；原 applyRemote() 却用
mergeOptions(profile.options, app.prefs.options) 混入本机偏好，导致轻量档房间的
 invading_victory / pawn_resurrection 等开关呈现与房间规则不一致。

守卫三个载体：JS 唯一源 + 两份重建后的内嵌 bundle（dist 与 online/public）。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CARRIERS = (
    ROOT / "webapp" / "js" / "ui" / "app.js",
    ROOT / "webapp" / "dist" / "index.html",
    ROOT / "online" / "public" / "index.html",
)
OLD_MERGE = "mergeOptions(profile.options, app.prefs.options)"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    """沿用 tests/test_webapp_onboarding.py 的函数体切片范式。"""
    marker = f"function {name}("
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def test_apply_remote_uses_room_options_not_local_prefs() -> None:
    """applyRemote 函数体：不碰 prefs.options、调用纯函数、保留 profileId 回退。"""
    for path in CARRIERS:
        body = _function_body(_read(path), "applyRemote")
        assert "app.prefs.options" not in body, f"{path.name}: applyRemote 仍混入本机偏好"
        assert "resolveRemoteOptions(data, profile)" in body, f"{path.name}: 未走房间 options 纯函数"
        assert "getProfile(data.state.profileId || app.prefs.profileId)" in body, (
            f"{path.name}: profileId 回退被误删"
        )


def test_single_player_prefs_merge_paths_untouched() -> None:
    """单机 / 人机 / 残局 / 读档路径仍用本机 prefs，旧的 3 处应只剩 2 处。"""
    for path in CARRIERS:
        count = _read(path).count(OLD_MERGE)
        assert count == 2, f"{path.name}: {OLD_MERGE} 出现 {count} 次（应为 2，单机路径勿误改）"
