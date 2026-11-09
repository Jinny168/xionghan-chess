"""服务端快照接受规则（桌面端）。

与 `web/js/state.js::applySnapshot` 同口径：
- 同一房间内，revision 只许前进或相等（相等表示重复帧，可接受但不算新版本）；
- 换房间时无障碍接受，调用方负责把基线重置为新房间的 revision。

单独成模块是为了能脱离 Qt 单测；`app.py` 只负责把结果应用到界面。
"""

from __future__ import annotations


def should_accept_snapshot(
    current_room: str | None,
    current_revision: int,
    incoming_room: str | None,
    incoming_revision: int,
) -> bool:
    """同房间 revision 不得倒退；跨房间一律接受。"""
    if incoming_room != current_room:
        return True
    return incoming_revision >= current_revision
