"""桌面端网络层纯函数单测（阶段1 S1-1 新增护栏）。

覆盖 `desktop/net.py` 中**不依赖 Qt、不依赖网络**的部分：
- WebSocket URL 构造（http/https、观战/对局、房间号与 token 拼接）
- 客户端消息编解码（协议字段、中文不转义、往返一致）
- 重连退避与重连判定（三种终止条件 + 三种不可重连 close code）
- `request_json` 的请求构造（通过注入 transport，验证 headers/method/body）

这些逻辑此前全内联在 `MainWindow` 里，桌面端零自动化护栏（严过关 A1–A6 的核心问题）。
"""

from __future__ import annotations

import json

import pytest

from xionghan_chess.desktop import net


# --------------------------------------------------------------------------- #
# ws_url
# --------------------------------------------------------------------------- #


def test_ws_url_http_becomes_ws() -> None:
    assert net.ws_url("http://127.0.0.1:8000", "ABC123", "tok") == "ws://127.0.0.1:8000/ws/ABC123?token=tok"


def test_ws_url_https_becomes_wss() -> None:
    assert net.ws_url("https://example.com", "R1", "t") == "wss://example.com/ws/R1?token=t"


def test_ws_url_spectator_adds_segment() -> None:
    url = net.ws_url("http://h:8000", "R1", "t", spectator=True)
    assert url == "ws://h:8000/ws/R1/spectate?token=t"


def test_ws_url_replaces_only_first_scheme() -> None:
    """`replace(..., 1)` —— 路径里再出现 http:// 不应被二次替换。"""
    url = net.ws_url("http://h/api?next=http://x", "R1", "t")
    assert url.startswith("ws://h/api?next=http://x")


def test_ws_url_does_not_mangle_plain_host() -> None:
    """没有 scheme 的地址保持原样（防御性：配置里写漏 scheme 时不静默变空）。"""
    assert net.ws_url("example.com", "R", "t") == "example.com/ws/R?token=t"


# --------------------------------------------------------------------------- #
# encode / decode
# --------------------------------------------------------------------------- #


def test_encode_message_has_protocol_fields() -> None:
    raw = net.encode_message("move", "ROOM1", 7, {"from": {"row": 1, "col": 2}})
    data = json.loads(raw)
    assert data["type"] == "move"
    assert data["roomId"] == "ROOM1"
    assert data["revision"] == 7
    assert data["payload"] == {"from": {"row": 1, "col": 2}}
    assert data["protocolVersion"] == net.PROTOCOL_VERSION


def test_encode_message_defaults_payload_to_empty_dict() -> None:
    assert json.loads(net.encode_message("resign", "R", 0))["payload"] == {}


def test_encode_message_keeps_chinese_unescaped() -> None:
    """`ensure_ascii=False` —— 否则威特/昵称会变 \\uXXXX，服务端与抓包都难读。"""
    raw = net.encode_message("chat", "R", 1, {"text": "你好，棋友"})
    assert "你好，棋友" in raw
    assert "\\u" not in raw


def test_encode_message_zero_payload_is_not_dropped() -> None:
    """`payload or {}` 的语义：0/False/"" 会被替换成 {}。记录该行为防止误以为能传标量。"""
    assert json.loads(net.encode_message("x", "R", 0, 0))["payload"] == {}


def test_decode_message_roundtrip() -> None:
    original = net.encode_message("state", "R", 3, {"revision": 3, "game": {"history": []}})
    decoded = net.decode_message(original)
    assert decoded["type"] == "state"
    assert decoded["payload"]["game"]["history"] == []


def test_decode_message_propagates_bad_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        net.decode_message("{not json")


# --------------------------------------------------------------------------- #
# reconnect_delay / should_reconnect
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "attempt,expected",
    [(0, 1200), (1, 2400), (2, 4800), (3, 9600), (10, 8000)],
)
def test_reconnect_delay_backoff(attempt: int, expected: int) -> None:
    """前三次按 1200/2400/4800 递增；超过封顶 8000（不是无限翻倍）。"""
    assert net.reconnect_delay(attempt) == min(net.RECONNECT_CAP_MS, expected)


def test_should_reconnect_normal_case() -> None:
    assert net.should_reconnect(1006, closing=False, room_id="ROOM") is True


def test_should_not_reconnect_when_closing_intentionally() -> None:
    assert net.should_reconnect(1000, closing=True, room_id="ROOM") is False


def test_should_not_reconnect_without_room() -> None:
    assert net.should_reconnect(1006, closing=False, room_id=None) is False


@pytest.mark.parametrize("code", sorted(net.NO_RECONNECT_CODES))
def test_should_not_reconnect_on_terminal_codes(code: int) -> None:
    """4001 无效 token / 4403 无权限 / 1008 被踢 —— 重连只会再被踢一次。"""
    assert net.should_reconnect(code, closing=False, room_id="ROOM") is False


# --------------------------------------------------------------------------- #
# request_json（注入 transport，不产生真实网络）
# --------------------------------------------------------------------------- #


def test_request_json_get_has_no_body_and_no_auth() -> None:
    captured: dict[str, object] = {}

    def fake(url: str, body: bytes | None, headers, method: str):
        captured.update(url=url, body=body, headers=dict(headers), method=method)
        return {"ok": True}

    result = net.request_json("http://h/api/me", None, "GET", "", transport=fake)
    assert result == {"ok": True}
    assert captured["method"] == "GET"
    assert captured["body"] is None
    assert captured["headers"] == {"Content-Type": "application/json"}


def test_request_json_posts_utf8_json() -> None:
    captured: dict[str, object] = {}

    def fake(url: str, body: bytes | None, headers, method: str):
        captured.update(body=body, method=method)
        return {}

    net.request_json("http://h/api/rooms", {"playerName": "张三"}, "POST", transport=fake)
    assert captured["method"] == "POST"
    assert json.loads(bytes(captured["body"]).decode("utf-8")) == {"playerName": "张三"}


def test_request_json_sets_bearer_when_token_given() -> None:
    captured: dict[str, object] = {}

    def fake(url: str, body: bytes | None, headers, method: str):
        captured["headers"] = dict(headers)
        return {}

    net.request_json("http://h/api/me", None, "GET", "SECRET", transport=fake)
    assert captured["headers"]["Authorization"] == "Bearer SECRET"


def test_request_json_without_token_omits_authorization() -> None:
    captured: dict[str, object] = {}

    def fake(url: str, body: bytes | None, headers, method: str):
        captured["headers"] = dict(headers)
        return {}

    net.request_json("http://h/x", None, "GET", "", transport=fake)
    assert "Authorization" not in captured["headers"]


def test_net_module_does_not_import_pyside() -> None:
    """net 必须保持纯净，否则无法在无 Qt 环境下单测（也是它存在的理由之一）。

    用 AST 查真实 import 语句 —— 不能直接搜源码文本，因为文档字符串里也会提到 PySide6。
    """
    import ast

    tree = ast.parse(open(net.__file__, encoding="utf-8").read())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not [name for name in imported if name.startswith("PySide6")], imported
