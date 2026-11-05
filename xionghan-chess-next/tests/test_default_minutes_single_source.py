"""默认时长必须只有一个来源。

B2 把 UI 的默认时长从 20 改成 10 时，`Game`、服务端请求模型、房间创建三处
仍各自写着 20 —— 桌面/网页都显式传参所以当时没暴露，但任何**漏传**的调用点
（第三方客户端、脚本、老测试）都会拿到 20，与界面显示不一致。

这条测试锁的就是"五处指向同一个常量"。以后谁再手写一个数字，立刻红。
"""

from __future__ import annotations

import inspect

from xionghan_chess.core.game import DEFAULT_INITIAL_MINUTES, Game
from xionghan_chess.desktop.config import DEFAULTS
from xionghan_chess.service.app import CreateRoomRequest
from xionghan_chess.service.rooms import RoomManager


def test_constant_is_the_agreed_value() -> None:
    assert DEFAULT_INITIAL_MINUTES == 10


def test_every_default_reads_the_same_constant() -> None:
    sources = {
        "Game.__init__": inspect.signature(Game.__init__).parameters["initial_minutes"].default,
        "桌面 DEFAULTS": DEFAULTS["initial_minutes"],
        "API CreateRoomRequest": CreateRoomRequest.model_fields["initial_minutes"].default,
        "RoomManager.create": inspect.signature(RoomManager.create)
        .parameters["initial_minutes"].default,
    }
    for name, value in sources.items():
        assert value == DEFAULT_INITIAL_MINUTES, (
            f"{name} 的默认时长是 {value}，与常量 {DEFAULT_INITIAL_MINUTES} 不一致 —— "
            "漏传时长的调用点会拿到另一个数")
