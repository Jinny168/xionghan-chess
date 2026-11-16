"""webapp 首跑引导静态守卫（P1-9）：三步定稿文案、可跳过、零规则术语、零采集。

只检查呈现层接线，不触碰棋盘规则。防止：
① 引导实现被误删；② 文案退化成 JS 硬编码（绕过 i18n）；③ 首访标记改键导致老用户重看；
④ 把"点棋子"当跳过信号（第②步正是鼓励点棋子，点一下就消失会教不完整）。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "webapp" / "js" / "ui" / "app.js"
I18N_JS = ROOT / "webapp" / "js" / "i18n.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def test_onboarding_function_exists_and_wired() -> None:
    source = _read(APP_JS)
    assert "function maybeShowOnboarding()" in source, "首跑引导函数被删"
    # 必须由启动流程调用（不是死代码）
    assert "maybeShowOnboarding();" in source, "首跑引导未在启动时调用"


def test_onboarding_steps_come_from_i18n_keys_not_hardcoded() -> None:
    """三步文案必须走 i18n 键，不在 JS 里硬编码中英文。"""
    body = _function_body(_read(APP_JS), "maybeShowOnboarding")
    for key in ("onboard.step1", "onboard.step2", "onboard.step3"):
        assert f"'{key}'" in body, f"引导未使用 i18n 键: {key}"
    # 三步通过数组统一走 t() 翻译（不逐字硬编码）
    assert "t(steps[idx])" in body, "引导文案未经 t() 翻译"
    # 不得出现旧的硬编码文案
    assert "Tap a piece, then tap a square to move" not in body
    assert "点选棋子，再点落点即可落子" not in body


def test_onboarding_i18n_keys_present_in_both_languages() -> None:
    i18n = _read(I18N_JS)
    for key in ("onboard.step1", "onboard.step2", "onboard.step3"):
        assert i18n.count(f"'{key}'") == 2, f"{key} 应在 zh/en 各出现一次"


def test_onboarding_uses_existing_visited_marker_and_is_skippable() -> None:
    body = _function_body(_read(APP_JS), "maybeShowOnboarding")
    # 沿用既有首访标记，不改键（老用户不重看）
    assert "xh-web-visited" in body, "未沿用既有首访标记 xh-web-visited"
    # 可跳过：有 stop 收起逻辑 + 落子检测（历史变长）
    assert "stop()" in body and "clearTimeout" in body, "引导缺收起/跳过逻辑"
    assert "history" in body, "引导缺落子检测（落子后应收起）"
    # 不把点棋子当跳过信号（那会让第②步自我否定）
    assert "pointerdown" not in body, "不得把点棋子当跳过信号"


def test_onboarding_has_no_telemetry() -> None:
    body = _function_body(_read(APP_JS), "maybeShowOnboarding")
    for token in ("fetch(", "XMLHttpRequest", "analytics", "track(", "sendBeacon"):
        assert token not in body, f"引导不得引入网络/采集: {token}"
