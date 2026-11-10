"""CSS 结构守卫：清理死代码时最容易顺手拆掉"看起来没用、其实是必需"的声明。

两件事故各写一条：
1. `.board-shell:before` 原是**两条规则**，首块的径向高光被后块全量覆盖（从未生效），
   但它的 `content/position/inset` 是伪元素存在的必要条件 —— 只删首块会让棋盘底纹直接消失。
2. `.seal` 是死类（HTML/JS 命中 0），已删除；加这条防止有人把它当"样式缺失"补回来。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "web" / "css" / "app.css").read_text(encoding="utf-8")
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")


def _rules(selector: str) -> list[str]:
    return [m.group(1) for m in re.finditer(re.escape(selector) + r"\{([^}]*)\}", CSS)]


def test_board_shell_before_keeps_its_box() -> None:
    """合并后的 `:before` 必须同时具备"存在"与"画图"两半。"""
    bodies = _rules(".board-shell:before")
    assert bodies, "`.board-shell:before` 规则不见了 —— 棋盘底纹会整块消失"
    drawing = [body for body in bodies if "background-image" in body]
    assert drawing, "`:before` 没有 background-image，底纹画不出来"
    body = drawing[0]
    for required in ('content:""', "position:absolute", "inset:0"):
        assert required in body, f"`:before` 缺少 {required} —— 清理死代码时把伪元素本身拆掉了"


def test_seal_does_not_come_back() -> None:
    """`.seal` 已被品牌图标取代（`<img class="brand-icon">`），没有元素再用它。"""
    used = 'class="seal' in HTML or "'seal'" in HTML or 'class=\\"seal' in HTML
    styled = ".seal" in CSS
    assert not (styled and not used), (
        "`.seal` 样式回来了但页面里没有对应元素 —— 这是死代码，删掉它；若确实要用，请先在 index.html 里加元素"
    )
