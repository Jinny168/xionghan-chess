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


def test_onboarding_try_scope_wraps_only_storage_access() -> None:
    """`try { ... }` 只许包两行存储访问，不许把整个函数体吞进去。

    为什么这条重要：当前实现是对的 —— 隐私模式下 `localStorage` 连读都会抛，
    只包「读 + 写」两行，存储不可用时当"已访问过"，而 DOM 创建、定时器、落子
    检测都留在 try 外，逻辑 bug 仍会照常暴露。但这个"只包存储，不包逻辑"的
    边界没有任何守卫：将来有人图省事把整个函数体包进 try，全部引导逻辑的异常
    都会被静默吞掉，既有测试仍会全绿（它们只查键名与调用点）。所以这里直接对
    源码结构断言 try 块的内容，把边界钉死。
    """
    body = _function_body(_read(APP_JS), "maybeShowOnboarding")
    start = body.index("try {")
    brace = body.index("{", start)
    depth = 0
    for index in range(brace, len(body)):
        if body[index] == "{":
            depth += 1
        elif body[index] == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    else:  # pragma: no cover - 源码不配平时才会走到
        raise AssertionError("maybeShowOnboarding 的 try 块花括号未配平")

    block = body[start:end]
    code_lines = [
        line.strip()
        for line in block.splitlines()
        if line.strip() and not line.strip().startswith("//")
    ]
    # 去掉 `try {` 与收尾 `}`，块内只应剩两行真实语句。
    statements = [line for line in code_lines if line not in ("try {", "}")]
    assert len(statements) == 2, (
        "try 块内只应有两行存储访问（读 + 写），实际为：\n  " + "\n  ".join(statements)
    )
    assert statements[0] == "visited = localStorage.getItem('xh-web-visited');"
    assert statements[1] == "localStorage.setItem('xh-web-visited', '1');"
    # 逻辑符号一律不得出现在 try 块内（出现即说明整段逻辑被包进去了）。
    for token in ("const steps", "setTimeout", "startPlies", "$(`#toast`)", "if ("):
        assert token not in block, f"引导逻辑 `{token}` 被包进了 try 块，异常会被静默吞掉"


def test_first_run_picks_light_profile_without_changing_default() -> None:
    """新用户首次落点=轻量档；系统默认不动（老用户回家路径不变）。"""
    source = _read(APP_JS)
    assert "function maybePickFirstRunProfile()" in source, "首访落档函数被删"
    body = _function_body(source, "maybePickFirstRunProfile")
    # 只首访：读 xh-web-visited 才判首访；设置轻量档并落盘
    assert "xh-web-visited" in body, "首访落档未读首访标记"
    assert "app.prefs.profileId = 'desktop_light'" in body, "首访未落到轻量档"
    assert "savePrefs()" in body, "首访落档未持久化"
    # 不改系统默认：DEFAULT_PREFS 里的 profileId 必须仍是 desktop_complete
    assert "profileId: 'desktop_complete'" in source, "系统默认 profile 被改（老用户回家路径不能动）"
    # 有安全降级：生成产物缺轻量档时不崩
    assert "PROFILES.desktop_light" in body, "缺轻量档时无安全降级"


def test_first_run_profile_runs_before_onboarding_marker_is_written() -> None:
    """boot 中首访落档必须在引导写标记之前，否则首访判定失效。

    注意：不能用 _function_body 切 boot —— boot 体内有缩进的箭头函数与注释，
    "\nfunction " 会命中它们而提前截断（曾据此误报一例假红）。顶层函数定义
    行首无缩进，用正则按行定位 boot 的真实边界。
    """
    import re

    source = _read(APP_JS)
    # 先剥行注释：boot 开头的注释里就写着 "maybeShowOnboarding()"，
    # 不剥会让 find 命中注释而误报假红（文本取证铁律：别把注释当代码）。
    code = "\n".join(line.split("//", 1)[0] for line in source.splitlines())
    m = re.search(r"^function boot\(\) \{", code, re.M)
    assert m, "boot 函数缺失"
    nxt = re.search(r"^function \w+\(", code[m.end():], re.M)
    boot = code[m.start(): m.end() + (nxt.start() if nxt else len(code) - m.end())]
    pick_at = boot.find("maybePickFirstRunProfile()")
    guide_at = boot.find("maybeShowOnboarding()")
    assert pick_at != -1 and guide_at != -1, "boot 缺首访落档或引导调用"
    assert pick_at < guide_at, "首访落档必须在引导写 xh-web-visited 标记之前调用"


def test_first_run_profile_has_no_telemetry() -> None:
    body = _function_body(_read(APP_JS), "maybePickFirstRunProfile")
    for token in ("fetch(", "XMLHttpRequest", "analytics", "track(", "sendBeacon"):
        assert token not in body, f"首访落档不得引入网络/采集: {token}"
