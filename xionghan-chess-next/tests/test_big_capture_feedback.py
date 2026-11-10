"""D3 吃大子反馈：阈值与"哪些子算大子"两端必须一致。

两端各有一份实现（Python 判状态栏、JS 判抖动+提示），一旦清单分叉，
同一步棋会出现"桌面喊了、网页没反应"。这条测试就是拦这个的。
"""

from __future__ import annotations

import re
from pathlib import Path

from xionghan_chess.core.model import BIG_CAPTURE_VALUE, PIECE_VALUES, is_big_capture

ROOT = Path(__file__).resolve().parents[1]


def test_threshold_is_the_agreed_value() -> None:
    assert BIG_CAPTURE_VALUE == 420, "阈值改了要同步桌面与网页两端"


def test_threshold_splits_the_piece_table_as_expected() -> None:
    # 王不在比较范围内：吃到王意味着对局结束，走的是 finished 分支，轮不到"大子反馈"。
    big = {kind for kind, value in PIECE_VALUES.items() if value >= BIG_CAPTURE_VALUE and kind != "king"}
    assert big == {"rook", "cannon", "horse", "archer", "thunder", "guard", "patrol"}


def test_big_and_small_captures() -> None:
    assert is_big_capture(["rook"])
    assert is_big_capture(["pawn", "horse"]), "吃到多子时任意一个大子就算"
    assert not is_big_capture(["pawn"])
    assert not is_big_capture(["advisor", "elephant"])  # 士/相被吃太常见，不喊
    assert not is_big_capture([])


def test_web_list_matches_python() -> None:
    js = (ROOT / "web/js/app.js").read_text(encoding="utf-8")
    match = re.search(r"BIG_CAPTURE_TYPES=\[([^\]]*)\]", js)
    assert match, "网页端找不到 BIG_CAPTURE_TYPES"
    web = {item.strip().strip("'\"") for item in match.group(1).split(",") if item.strip()}
    py = {kind for kind, value in PIECE_VALUES.items() if value >= BIG_CAPTURE_VALUE and kind != "king"}
    assert web == py, f"两端的大子清单不一致：网页 {web} / Python {py}"


def test_web_shakes_the_board_once_per_big_capture() -> None:
    js = (ROOT / "web/js/app.js").read_text(encoding="utf-8")
    assert "function shakeBoard()" in js
    assert "if(isBigCapture(last.captured)){shakeBoard();" in js, "吃大子没触发视觉反馈"
    css = (ROOT / "web/css/app.css").read_text(encoding="utf-8")
    assert "@keyframes board-shake" in css, "缺少抖动动画定义"
