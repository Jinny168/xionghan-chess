"""桌面端网络层：HTTP 阻塞实现 + 局域网 WebSocket 协议编解码。

设计要点（阶段1 S1-1）：

1. **协议编解码是纯函数** —— `encode_message()` / `decode_message()` / `ws_url()` /
   `reconnect_delay()` 都不碰 Qt，也不碰 self，可在无 GUI 环境下直接单测。
   此前这些逻辑内联在 `MainWindow` 里，桌面端零自动化护栏。
2. **传输可注入** —— `post_json()` 接受 `transport` 参数，默认是 urllib 实现。
   测试可注入假 transport 验证请求构造（headers/method/body），不必起服务器。
3. **阻塞实现集中一处** —— `request_json()` 是全仓唯一的同步 HTTP 实现，
   仅供 `account_sync()` 这条「对话框与请求交错」的链式流程使用。
   新代码请用 `MainWindow._request_json_async()`（走 QThreadPool）。

⚠️ 本模块**不得** import 任何 PySide6.Widgets —— 保持可在 offscreen/无显示环境导入。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping

# 协议版本**单一来源**：这里曾经是第二份 `PROTOCOL_VERSION = 1`。
# 两份同名常量分居两个模块，改一处另一处就悄悄留在旧版本 —— 症状是"桌面连上服务端后
# 首帧就被判协议不符"，而两边看代码都"写着 1"。现在只认 `core/protocol.py` 那一份，
# 这里保留名字只是因为 `desktop/net.py` 是它对外的唯一出口（`net.PROTOCOL_VERSION`）。
from xionghan_chess.core.protocol import PROTOCOL_VERSION  # noqa: F401  (re-export)

# 传输函数签名：(url, body, headers, method) -> 解析后的 JSON。
# 抽成类型别名，方便测试注入。
Transport = Callable[[str, "bytes | None", Mapping[str, str], str], Any]

# 服务端主动关闭且**不值得重连**的 close code：
# 4001 = 无效 token，4403 = 无权限，1008 = 策略拒绝（被踢）。
NO_RECONNECT_CODES = frozenset({4001, 4403, 1008})

MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_BASE_MS = 1200
RECONNECT_CAP_MS = 8000


def _error_detail(exc: "urllib.error.HTTPError") -> str:
    """从 4xx 响应的 body 里取 `detail`（字符串，或 `{code,message}` 形式的专用错误）。"""
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:  # noqa: BLE001  —— body 不是 JSON / 读不出来都退回 str(exc)
        return ""
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        return str(detail.get("message") or detail.get("code") or "")
    return ""


def _urllib_transport(url: str, body: bytes | None, headers: Mapping[str, str], method: str) -> Any:
    """默认传输实现：urllib，15s 超时（与原 `request_json` 一致）。"""
    request = urllib.request.Request(url, body, dict(headers), method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 服务端 4xx 的可读信息在 JSON 的 `detail` 里。不读 body 的话，用户只看到
        # 「HTTP Error 409: Conflict」—— 而 409 的全部意义就是告诉他「版本不一致，
        # 请刷新」，所以这里把 detail 抬成异常文本（`str(exc)` 只是最后的兜底）。
        raise ValueError(_error_detail(exc) or str(exc)) from exc


def request_json(
    url: str,
    payload: Any = None,
    method: str = "GET",
    token: str = "",
    *,
    transport: Transport | None = None,
) -> Any:
    """同步 HTTP JSON 请求（阻塞）。

    调用方须自行保证不在 GUI 事件的**长链路**上使用（`account_sync` 是既有例外，
    因为它是对话框与请求交错的流程，异步化需整链改回调）。
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    return (transport or _urllib_transport)(url, body, headers, method)


def ws_url(base: str, room_id: str, spectator: bool = False) -> str:
    """把 HTTP(S) 服务地址转成 WebSocket 地址。

    http://host:8000 → ws://host:8000/ws/<room>
    https://...      → wss://...
    观战额外加 `/spectate` 段。

    **token 不再放 URL**：连接后由客户端发首帧 `auth`（见 `encode_auth`）。
    URL 会进访问日志、浏览器历史、Referer —— 那是泄露渠道。
    """
    scheme_swapped = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    suffix = "/spectate" if spectator else ""
    return f"{scheme_swapped}/ws/{room_id}{suffix}"


def encode_auth(token: str) -> str:
    """WS 首帧：`{"type": "auth", "token": ...}`。服务端 5 秒内收不到就 close(4401)。"""
    return json.dumps({"type": "auth", "token": token}, ensure_ascii=False)


def encode_message(type_: str, room_id: str | None, revision: int, payload: Any = None) -> str:
    """编客户端→服务端消息。`ensure_ascii=False` 保留中文（聊天/昵称）。"""
    return json.dumps(
        {
            "type": type_,
            "roomId": room_id,
            "revision": revision,
            "payload": payload or {},
            "protocolVersion": PROTOCOL_VERSION,
        },
        ensure_ascii=False,
    )


def decode_message(text: str) -> dict[str, Any]:
    """解服务端→客户端消息。畸形 JSON 交由调用方捕获（保持原行为：向上抛）。"""
    return json.loads(text)


def reconnect_delay(attempt: int) -> int:
    """第 `attempt` 次重连的等待毫秒数：1200 → 2400 → 4800，封顶 8000。"""
    return min(RECONNECT_CAP_MS, RECONNECT_BASE_MS * (2**attempt))


def should_reconnect(close_code: int, closing: bool, room_id: str | None) -> bool:
    """断线后是否值得重连（纯判定，便于单测覆盖三种终止条件）。"""
    if closing or not room_id:
        return False
    return int(close_code) not in NO_RECONNECT_CODES
