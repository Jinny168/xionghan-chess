"""版本检查单测（阶段2 S2-3）。

覆盖三件容易出错、又不容易在界面上被发现的事：
1. **版本比较**：`1.7` vs `1.7.0`、`v` 前缀、预发布后缀。比错了会「永远提示有新版本」
   或「永远提示已是最新」，两种都不会崩，只会静默错到底。
2. **清单解析**：GitHub Releases 的 `url` 字段是 api.github.com（点开是一坨 JSON），
   必须回落到下载页而不是把 API 地址给用户点。
3. **失败折叠**：离线不是异常路径，是常态，必须折成 error 状态而不是抛给界面。

本文件不依赖 PySide6 —— `update.py` 特意与 UI 解耦，这样这些逻辑在纯命令行
环境也能验。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from xionghan_chess.desktop import update


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1.7.0", (1, 7, 0)),
        ("v1.7.1", (1, 7, 1)),
        ("V2.0", (2, 0)),
        ("1.7.0-rc1", (1, 7, 0)),
        ("1.7.0+build5", (1, 7, 0)),
        ("  v1.6.12  ", (1, 6, 12)),
        ("", ()),
        ("abc", ()),
    ],
)
def test_parse_version(text: str, expected: tuple[int, ...]) -> None:
    assert update.parse_version(text) == expected


@pytest.mark.parametrize(
    "remote,local,expected",
    [
        ("1.7.1", "1.7.0", True),
        ("1.7.0", "1.7.0", False),
        ("1.7", "1.7.0", False),          # 补零后相等
        ("1.7.0", "1.7", False),          # 同上，对称
        ("1.10.0", "1.9.9", True),        # 数字比较而非字典序
        ("2.0.0", "1.99.99", True),
        ("1.6.9", "1.7.0", False),
        ("v1.7.1", "1.7.0", True),
        ("abc", "1.7.0", False),          # 无法解析时不声称有新版
        ("1.7.1", "abc", False),
    ],
)
def test_is_newer(remote: str, local: str, expected: bool) -> None:
    assert update.is_newer(remote, local) is expected


def test_parse_release_github_shape() -> None:
    payload = {
        "tag_name": "v1.7.1",
        "html_url": "https://github.com/Jinny168/xionghan-chess/releases/tag/v1.7.1",
        "body": "修了什么",
        "published_at": "2026-11-01T00:00:00Z",
    }
    info = update.parse_release(payload)
    assert info is not None
    assert info.version == "v1.7.1"
    assert info.url.endswith("/releases/tag/v1.7.1")
    assert info.notes == "修了什么"
    assert info.published_at.startswith("2026-11-01")


def test_parse_release_manifest_shape() -> None:
    info = update.parse_release({"version": "1.8.0", "url": "https://example.com/dl", "notes": "n"})
    assert info is not None
    assert info.version == "1.8.0"
    assert info.url == "https://example.com/dl"


def test_update_info_label_strips_tag_prefix() -> None:
    """界面显示用 label：GitHub tag 带 v 前缀，直接显示会变成「最新版本 v9.9.9」。"""
    info = update.parse_release({"tag_name": "v9.9.9"})
    assert info is not None
    assert info.version == "v9.9.9"
    assert info.label == "9.9.9"
    plain = update.parse_release({"version": "1.8.0"})
    assert plain is not None and plain.label == "1.8.0"


def test_parse_release_skips_draft_and_prerelease() -> None:
    """草稿与预发布不该出现在普通用户的「有新版本」提示里。"""
    assert update.parse_release({"tag_name": "v1.8.0", "draft": True}) is None
    assert update.parse_release({"tag_name": "v1.8.0-rc1", "prerelease": True}) is None


def test_parse_release_rejects_api_url() -> None:
    """GitHub API 的 `url` 指向 api.github.com —— 给用户点开是 JSON，必须回落下载页。"""
    info = update.parse_release({
        "tag_name": "v1.7.1",
        "url": "https://api.github.com/repos/Jinny168/xionghan-chess/releases/1",
    })
    assert info is not None
    assert info.url == update.DOWNLOAD_PAGE


@pytest.mark.parametrize("payload", [None, [], "text", {}, {"tag_name": ""}, {"version": "abc"}])
def test_parse_release_invalid_payloads(payload: object) -> None:
    assert update.parse_release(payload) is None


def _transport(payload: object, calls: list[tuple[str, object, str]] | None = None):
    def inner(url: str, body: object, headers: object, method: str) -> object:
        if calls is not None:
            calls.append((url, body, method))
        return payload
    return inner


def test_check_for_update_reports_update() -> None:
    result = update.check_for_update("1.7.0", transport=_transport({"tag_name": "v1.7.1"}))
    assert result.status == update.STATUS_UPDATE
    assert result.info is not None and result.info.version == "v1.7.1"


def test_check_for_update_reports_latest() -> None:
    result = update.check_for_update("1.7.0", transport=_transport({"tag_name": "v1.7.0"}))
    assert result.status == update.STATUS_LATEST


def test_check_for_update_swallows_network_error() -> None:
    """离线是常态：必须折成 error，不能把异常抛进 GUI 事件链。"""
    def boom(url: str, body: object, headers: object, method: str) -> object:
        raise OSError("network unreachable")

    result = update.check_for_update("1.7.0", transport=boom)
    assert result.status == update.STATUS_ERROR
    assert "network unreachable" in result.error
    assert result.info is None


def test_check_for_update_uses_configured_url() -> None:
    calls: list[tuple[str, object, str]] = []
    update.check_for_update("1.7.0", transport=_transport({"tag_name": "v1.7.1"}, calls),
                            url="https://example.com/manifest.json")
    assert calls and calls[0][0] == "https://example.com/manifest.json"
    assert calls[0][2] == "GET"


def test_update_module_has_no_qt_dependency() -> None:
    """版本比较不该依赖桌面环境 —— 否则这些逻辑只能靠手工点菜单来验。"""
    tree = ast.parse(Path(update.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "PySide6" not in imported, imported


def test_local_version_matches_package_metadata() -> None:
    """界面显示的「当前版本」必须与 `xionghan_chess.__version__` 同源，不能各写一份。"""
    import xionghan_chess

    assert update.parse_version(xionghan_chess.__version__)
