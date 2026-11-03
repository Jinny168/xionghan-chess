"""网页端版本号不得写死：关于框从 `/api/version` 取，缓存戳跟随 `__version__`。

背景：桌面端「关于」曾把版本写死成 1.7.0，网页端「关于」也一直写着 1.8.2。
升版本时漏改就会出现「关于里是旧版本、程序其实是新版」的错位。
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from xionghan_chess import __version__
from xionghan_chess.service.app import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_api_version_returns_the_package_version() -> None:
    data = client.get("/api/version").json()
    assert data["version"] == __version__


def test_about_dialog_is_filled_from_the_api() -> None:
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert 'id="aboutVersion"' in html, "关于框缺少版本占位符"
    assert not re.search(r"版本 \d+\.\d+\.\d+", html), "关于框里还写着固定版本号"

    js = (ROOT / "web/js/app.js").read_text(encoding="utf-8")
    assert "loadAppVersion" in js, "没人去取版本号，占位符会一直显示「版本 —」"
    assert "/api/version" in js


def test_cache_busters_follow_the_version() -> None:
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    busters = set(re.findall(r"\?v=([0-9.]+)", html))
    assert busters == {__version__}, f"index.html 的缓存戳是 {busters}，应为 {__version__}"

    for name in ("app.js", "atlas.js"):
        js = (ROOT / "web/js" / name).read_text(encoding="utf-8")
        for found in set(re.findall(r"i18n\.js\?v=([0-9.]+)", js)):
            assert found == __version__, f"{name} 的 i18n 缓存戳是 {found}，应为 {__version__}"
