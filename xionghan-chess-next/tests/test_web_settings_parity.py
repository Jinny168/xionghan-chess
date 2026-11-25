"""网页端设置项与桌面端对齐（P1）：难度六档 / 背景下拉 / 棋子样式 / 再来一局。

网页没有 DOM 测试框架，所以这里做**静态结构断言** + **源码级兼容断言**：
- `index.html` 的下拉项与顺序直接从 HTML 解析（这就是用户看到的东西）；
- 老存档缺字段的迁移是 JS 逻辑，用源码断言该兜底存在（浏览器行为需人工验收，已在提交信息注明）。

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


def test_difficulty_has_three_levels_in_desktop_order() -> None:
    values = [value for value, _ in options_of("difficultySelect")]
    assert values == ["beginner", "medium", "hard"], values


def test_page_background_exposes_none_and_defaults_to_1() -> None:
    values = [value for value, _ in options_of("pageBackgroundSelect")]
    assert "none" in values, "「无背景」必须作为可选项真正暴露在下拉里"
    assert values[1] == "1", "默认背景项应为 1（山水淡纹）"
    # 默认选中：要么显式 selected，要么是第一个 option
    assert re.search(r'<option value="1" selected', HTML), "背景默认项应显式标记 selected"


def test_piece_style_has_four_options_including_glyph() -> None:
    values = [value for value, _ in options_of("pieceStyleSelect")]
    assert values == ["traditional", "modern", "cartoon", "glyph"], values


def test_explicit_none_page_background_is_preserved_not_rewritten() -> None:
    """显式存的 `pageBackground:"none"` 必须保留，不得被静默归一成 `"1"`；
    只有老存档**缺字段**时才走迁移默认（`!stored.pageBackground`）。"""
    assert "pageBackground==='none')app.preferences.pageBackground='1'" not in APP_JS, \
        "显式 none 不得被静默改写回 1"
    assert "if(!stored.pageBackground)" in APP_JS, "缺字段迁移路径必须保留"


def test_play_again_is_always_clickable_and_confirms_mid_game() -> None:
    """再来一局：局中点击先确认，确认后才重开（桌面语义）。"""
    assert "restartButton" in HTML and "再来一局" in HTML
    assert "confirm(" in APP_JS and "对局尚未结束" in APP_JS, "局中点击应弹确认"


def test_pawn_switches_are_exposed_in_web_rule_options() -> None:
    """P2：兵的两个开关必须在共享分组里（三端同源，Web 读下发的这份）。"""
    from xionghan_chess.core.profiles import piece_option_groups

    keys = piece_option_groups()["pawn"]
    assert "pawn_charge" in keys, f"缺少「过长城后可直冲」开关：{keys}"
    assert "pawn_three_line_capture" in keys, f"缺少「两兵夹一敌子」开关：{keys}"
    assert "pieceOptionGroups" in APP_JS, "Web 没有消费 /api/profiles 下发的棋子分组"


def test_pawn_switches_default_to_off() -> None:
    """两个开关的默认值必须是关（与服务端 `RuleOptions` 一致）。"""
    from xionghan_chess.core.profiles import RuleOptions

    options = RuleOptions()
    assert options.pawn_charge is False
    assert options.pawn_three_line_capture is False


def test_initial_minutes_defaults_to_ten_on_both_ends() -> None:
    """B2：每方时限默认 20 → 10 分钟，桌面与网页必须同一个数。

    三处都要查 —— 它们各自独立、漏一处就会出现「桌面 10 分钟、网页 20 分钟」：
    1. 桌面 `config.DEFAULTS`；
    2. 网页 `index.html` 下拉框的 `selected` 项；
    3. 网页 `app.js` 里读取偏好时的 `|| 20` 兜底与 `preferences` 初始值。
    """
    from xionghan_chess.desktop.config import DEFAULTS

    assert DEFAULTS["initial_minutes"] == 10, "桌面默认时限应为 10 分钟"

    selected = re.findall(r'<option value="(\d+)" selected>', HTML)
    minutes_block = re.search(r'<select id="initialMinutesSelect"[^>]*>(.*?)</select>', HTML, re.S)
    assert minutes_block, "index.html 里找不到 #initialMinutesSelect"
    chosen = re.findall(r'<option value="(\d+)"( selected)?>', minutes_block.group(1))
    assert [value for value, flag in chosen if flag] == ["10"], (
        f"网页时限默认项应为 10 分钟，实际 {[v for v, f in chosen if f]}"
    )
    assert selected, "整份 index.html 里应当存在显式 selected 的选项"

    assert "initialMinutes:10," in APP_JS, "app.js 的偏好初始值应为 10"
    # 用 `??` 而不是 `||`：0 是合法值（虽然下拉框里没有），`||` 会把它当空值兜底，
    # 以后加"不限时=0"或从别处同步进 0 时就会被悄悄改成 10。
    assert "p.initialMinutes??10" in APP_JS, "app.js 读取偏好时应使用 ?? 兜底"
    assert "p.initialMinutes||" not in APP_JS, "app.js 里不该再用 || 兜底（0 会被误判为空值）"


def test_system_theme_change_listener() -> None:
    """**这是文本守卫**：断言 web 旧树注册了系统亮暗 `change` 监听、且只在 `auto` 档重算。

    **运行时正确性以浏览器切系统主题的人工验收为准**——本测试只守"代码还在"，不冒充
    运行时判据。显式 light/dark 偏好不该被系统切换覆盖，故回调用 `app.preferences.systemTheme==='auto'`
    把住；新增后缀兜底 `addListener` 兼容老浏览器。
    """
    assert "function watchSystemTheme()" in APP_JS, "缺少系统主题监听函数 watchSystemTheme"
    assert "matchMedia('(prefers-color-scheme: dark)')" in APP_JS, "未监听 prefers-color-scheme: dark"
    assert "addEventListener('change'" in APP_JS, "缺少 change 事件监听"
    assert "addListener(" in APP_JS, "缺少老浏览器 addListener 兜底"
    assert "app.preferences.systemTheme==='auto'" in APP_JS, "回调缺少 auto 档判断（显式 light/dark 不应被覆盖）"
    assert "watchSystemTheme();" in APP_JS, "启动流程未调用 watchSystemTheme"
