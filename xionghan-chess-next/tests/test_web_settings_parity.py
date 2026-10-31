"""网页端设置项与桌面端对齐（P1）：难度六档 / 背景下拉 / 棋子样式 / 再来一局。

网页没有 DOM 测试框架，所以这里做**静态结构断言** + **源码级兼容断言**：
- `index.html` 的下拉项与顺序直接从 HTML 解析（这就是用户看到的东西）；
- 老配置兼容是 JS 逻辑，用源码断言该映射存在（浏览器行为需人工验收，已在提交信息注明）。

为什么不用 TestClient 取页面：`/` 直接返回同一份 `index.html` 静态文件，
解析磁盘文件与解析响应等价，且不引入服务端启动依赖。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
APP_JS = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")


def options_of(select_id: str) -> list[tuple[str, str]]:
    """取某个 `<select>` 的 (value, 文本) 列表。"""
    match = re.search(rf'<select id="{select_id}"[^>]*>(.*?)</select>', HTML, re.S)
    assert match, f"index.html 里找不到 #{select_id}"
    return re.findall(r'<option value="([^"]*)"[^>]*>([^<]*)</option>', match.group(1))


def test_difficulty_has_six_levels_in_desktop_order() -> None:
    values = [value for value, _ in options_of("difficultySelect")]
    assert values == ["beginner", "easy", "medium", "hard", "expert", "master"], values


def test_background_has_no_raw_colour_option_and_defaults_to_1() -> None:
    values = [value for value, _ in options_of("pageBackgroundSelect")]
    assert "none" not in values, "「原色（无图片）」应删除（与桌面同口径）"
    assert values[0] == "1", "默认背景应为 1（山水淡纹）"
    # 默认选中：要么显式 selected，要么是第一个 option
    assert re.search(r'<option value="1" selected', HTML), "背景默认项应显式标记 selected"


def test_piece_style_has_four_options_including_glyph() -> None:
    values = [value for value, _ in options_of("pieceStyleSelect")]
    assert values == ["traditional", "modern", "cartoon", "glyph"], values


def test_legacy_page_background_none_maps_to_1() -> None:
    """老配置 `pageBackground:"none"` 必须读成 `"1"`（与桌面同口径）。"""
    assert "pageBackground==='none')app.preferences.pageBackground='1'" in APP_JS, \
        "app.js 里缺少 none → 1 的兼容映射"


def test_play_again_is_always_clickable_and_confirms_mid_game() -> None:
    """再来一局：局中点击先确认，确认后才重开（桌面语义）。"""
    assert "restartButton" in HTML and "再来一局" in HTML
    assert "confirm(" in APP_JS and "对局尚未结束" in APP_JS, "局中点击应弹确认"
