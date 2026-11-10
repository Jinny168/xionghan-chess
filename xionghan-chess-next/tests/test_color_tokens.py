"""颜色令牌的可读性守卫：拆开"前景红"与"填充红"之后，两边的约束都要守住。

背景：`--red` 长期一个令牌担两个相反的角色 —— 前景文字要**浅**（暗底上才看得见），
背景填充要**深**（白字才压得住）。暗色下把 `--red` 调浅，白字压红底立刻从 4.57 崩到 1.56。
所以拆出 `--red-ink`（前景）并**冻结 `--red`**（填充 + 控件状态）。

本文件守三件事：
1. 前景红对所在底色 ≥ 4.5（正文级）；
2. 填充红上的白字 ≥ 4.5（`.result-mark` 是 42px 大字，按 3.0 算，这里用更严的 4.5）；
3. 控件状态用的 `--red` 对底色 ≥ 3.0（WCAG 1.4.11 非文本对比）。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = ROOT / "scripts" / "css_snapshot.py"


def _tables() -> dict:
    spec = importlib.util.spec_from_file_location("css_snapshot_for_colors", SNAPSHOT_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = module.strip_comments(module.CSS.read_text(encoding="utf-8"))
    tables = module.variable_tables(module.split_rules(text))
    tables["_expand"] = module.expand
    return tables


def _channel(value: float) -> float:
    value /= 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    text = hex_color.lstrip("#")
    r, g, b = (int(text[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _ratio(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    high, low = max(la, lb), min(la, lb)
    return (high + 0.05) / (low + 0.05)


def test_red_ink_is_readable_on_surface() -> None:
    tables = _tables()
    expand = tables["_expand"]
    for scope in ("light", "dark"):
        ink = expand("var(--red-ink)", tables[scope])
        surface = expand("var(--surface)", tables[scope])
        ratio = _ratio(ink, surface)
        assert ratio >= 4.5, f"{scope} 前景红 {ink} 在 {surface} 上只有 {ratio:.2f}:1"


def test_white_on_red_fill_is_readable() -> None:
    """填充红只给"白字压红底"用 —— 暗色那份不能再被调浅。"""
    tables = _tables()
    expand = tables["_expand"]
    for scope in ("light", "dark"):
        fill = expand("var(--red)", tables[scope])
        ratio = _ratio(fill, "#ffffff")
        assert ratio >= 4.5, f"{scope} 白字压在 {fill} 上只有 {ratio:.2f}:1"


def test_red_state_contrast_passes_non_text_threshold() -> None:
    """`--red` 还兼着控件状态（accent-color / 激活下划线），按 1.4.11 需 ≥3:1。"""
    tables = _tables()
    expand = tables["_expand"]
    for scope in ("light", "dark"):
        state = expand("var(--red)", tables[scope])
        surface = expand("var(--surface)", tables[scope])
        ratio = _ratio(state, surface)
        assert ratio >= 3.0, f"{scope} 状态红 {state} 对 {surface} 只有 {ratio:.2f}:1"


def test_red_ink_differs_from_red_in_dark_scope() -> None:
    """暗色下两者**必须不同**：相同就说明又退回"一个令牌两个角色"。"""
    tables = _tables()
    expand = tables["_expand"]
    assert expand("var(--red-ink)", tables["dark"]) != expand("var(--red)", tables["dark"])
