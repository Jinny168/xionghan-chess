"""P1-11 web 旧树侧栏分层的结构守卫（文本级；视觉留给浏览器人工验收）。

高频（玩家状态/时钟、棋谱）常驻；低频（双方损失、房间）折进 details。硬约束：
`.workspace` 的 grid 列宽与 `.board-shell` 宽度公式不许改，棋盘不缩。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "css" / "app.css").read_text(encoding="utf-8")
APP = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")


def test_low_frequency_blocks_are_details_with_ids_intact() -> None:
    """两个低频块是 details，且 redCaptured / blackCaptured / roomCode 的 id 原样在内。"""
    captured = HTML.split('<details class="side-details" id="capturedDetails">', 1)[1].split("</details>", 1)[0]
    assert 'id="redCaptured"' in captured
    assert 'id="blackCaptured"' in captured
    room = HTML.split('<details class="side-details" id="roomDetails">', 1)[1].split("</details>", 1)[0]
    assert 'id="roomCode"' in room and 'id="copyRoomButton"' in room
    # 左侧 player-column 不再常驻黑方损失。
    left = HTML.split('<aside class="player-column">', 1)[1].split("</aside>", 1)[0]
    assert 'id="blackCaptured"' not in left
    # 高频棋谱仍是常驻 record-panel，聊天 tab 不动。
    assert '<section class="record-panel">' in HTML and 'id="moveList"' in HTML


def test_room_details_hidden_outside_online() -> None:
    assert "$('#roomDetails').hidden=mode!=='online'" in APP


def test_toggle_restores_move_list_scroll() -> None:
    """details 开合后补一次 scrollTop=scrollHeight（唯一实打实的回归点）。"""
    assert "'capturedDetails','roomDetails'" in APP
    assert "addEventListener('toggle'" in APP
    assert "list.scrollTop=list.scrollHeight" in APP


def test_board_width_and_grid_untouched() -> None:
    assert (
        "grid-template-columns:minmax(220px,280px) minmax(520px,1fr) minmax(230px,300px)"
        in CSS
    )
    assert "width:min(100%,calc(100vh - 190px))" in CSS
    assert ".side-details summary::before{content:'▸'" in CSS
    assert ".side-details[open] summary::before{content:'▾'" in CSS


def test_no_visibility_dependencies_on_sidebar() -> None:
    """折叠不删 DOM；确认没有依赖 :visible / offsetParent 的旧逻辑。"""
    assert ":visible" not in APP
    assert "offsetParent" not in APP
