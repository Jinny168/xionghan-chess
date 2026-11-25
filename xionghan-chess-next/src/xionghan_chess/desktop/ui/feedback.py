"""P1-10 桌面四级反馈层：**唯一**的语义反馈出口。

## 为什么要有这一层

原来桌面端所有反馈都往 `statusBar().showMessage()` 里塞：吃掉大子、棋局已保存、
网络断开、房间版本号……20 处调用共用一条 12px 的灰字。结果是**真正要看的**
（保存失败、断线）和**顺带说一句的**（吃掉一个子）视觉权重完全一样，重要的被淹没。

这一层做的事只有两件：
1. 给"需要被看见"的反馈一个**固定位置 + 按语义着色**的条（棋盘上方、横幅下方）；
2. 加**自动消失**，所以它不构成常驻信息（P1-10 的"不加常驻信息"）。

低信息量的通知（房间号、样式切换、吃子播报）**继续留在 statusBar** —— 它们
不该占用一块会变色的区域，否则玩家会重新学会忽略这块区域。

## 四级与配色来源

`success / warn / error / info`。颜色**全部来自 `theme.THEMES`**，模块内零字面量
颜色（`tests/test_no_raw_colors.py` 的扫描面包含本文件）；`error` 复用横幅那一套红，
因为"红"在同一界面里只该有一种含义。

样式**每次 `show_message` 时现取**，而不是构造时定死：主题可切换，一个字面量都
不该被缓存在控件里。切主题时 app 层调 `set_theme()` 刷新当前这条。

## 非法等级不抛异常

UI 层因为一个拼错的字符串崩掉是不可接受的（调用点是业务代码，不是配置解析）。
非法 level 一律回退 `info`，并且**保留原文**——宁可颜色错了，也不要消息丢了。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from . import theme

#: 合法等级。顺序即语义强度（弱 → 强），测试按它遍历。
LEVELS = ("info", "success", "warn", "error")

#: 非法 level 的回退值。
DEFAULT_LEVEL = "info"

#: 默认停留时长（毫秒）。与 statusBar 的 5–8 秒不同：这条**不常驻**，短一点更不打扰。
DEFAULT_TIMEOUT_MS = 4000

#: level → 主题调色键。`error` 指向横幅那一套（不另造第五套红）。
_PALETTE_KEYS = {
    "success": ("success_bg", "success_fg"),
    "warn": ("warn_bg", "warn_fg"),
    "error": ("banner_bg", "banner_fg"),
    "info": ("info_bg", "info_fg"),
}


class FeedbackBar(QWidget):
    """棋盘上方的语义反馈条：一句话 + 按级别着色 + 自动消失。

    用法：`bar.show_message(dlf("棋局已保存：{path}", path=path), "success")`。
    未显示任何消息时**整体隐藏** —— 隐藏的 widget 在 `QVBoxLayout` 里不占高度，
    所以它不会挤压棋盘（`tests/test_desktop_layout_limits.py` 守着这一点）。
    """

    def __init__(self, theme_name: str = "classic", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("feedback_bar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.label = QLabel()
        # objectName 供读屏/自检定位；**不用它做样式选择器** —— 见 `_apply_style` 注释。
        self.label.setObjectName("feedback")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self._theme_name = theme_name
        self._level = DEFAULT_LEVEL
        self._text = ""
        self._timeout_ms = DEFAULT_TIMEOUT_MS
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.hide()

    # ---- 只读状态（测试与自检读它，不要读 label，避免被 QSS 细节纠缠）----

    @property
    def current_level(self) -> str:
        """当前（或最近一次的）语义等级。"""
        return self._level

    @property
    def current_text(self) -> str:
        """当前（或最近一次的）文案原文（未翻译、未加工）。"""
        return self._text

    @property
    def current_timeout_ms(self) -> int:
        """当前这条的自动隐藏时长。"""
        return self._timeout_ms

    @property
    def theme_name(self) -> str:
        return self._theme_name

    # ---- 对外接口 ----

    def set_theme(self, name: str) -> None:
        """切换主题后刷新配色。

        只影响**已显示**的那一条：隐藏时不重建样式，等 `show_message` 现取
        （少一次无意义的 QSS 解析，也少一条"样式到底是什么时候定的"的隐式状态）。
        """
        self._theme_name = name
        if self.isVisible():
            self._apply_style()

    def clear(self) -> None:
        """立刻收起（停表、清文本）。"""
        self._timer.stop()
        self._text = ""
        self.label.clear()
        self.hide()

    def show_message(self, text: str, level: str = DEFAULT_LEVEL, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> None:
        """显示一条反馈。

        参数：
            text: 已翻译好的文案（本模块不碰 i18n）。
            level: `success / warn / error / info`；非法值回退 `info`，不抛异常。
            timeout_ms: 自动隐藏时长；`<= 0` 表示直到下一条消息才消失。
        """
        safe_level = level if level in LEVELS else DEFAULT_LEVEL
        self._level = safe_level
        self._text = text
        self._timeout_ms = timeout_ms
        self.label.setText(text)
        self._apply_style()
        self.show()
        self._timer.stop()
        if timeout_ms > 0:
            self._timer.start(timeout_ms)

    # ---- 内部 ----

    def _palette(self) -> dict:
        """当前主题的调色板；主题名不认识时退回 classic（不 KeyError）。"""
        return theme.THEMES.get(self._theme_name) or theme.THEMES["classic"]

    def _apply_style(self) -> None:
        """按「当前主题 + 当前等级」现取两种颜色，写成 QSS。

        样式**直接设在 label 上**，不用 `#objectName` 选择器：一是少一层选择器解析，
        二是裸色禁令的扫描正则会把 `#` 加对象名的写法误判成颜色字面量（`f/e/e/d`
        都是十六进制字符），留个坑给下一轮。四条属性全写齐 —— 窗口级的
        `QLabel{background/color/border/padding}` 会漏进来，只覆盖一半会更难看。
        """
        palette = self._palette()
        bg_key, fg_key = _PALETTE_KEYS[self._level]
        background = palette.get(bg_key) or _palette_fallback(bg_key)
        foreground = palette.get(fg_key) or _palette_fallback(fg_key)
        self.label.setStyleSheet(
            f"QLabel{{background:{background};color:{foreground};"
            f"border:1px solid {background};border-radius:4px;"
            f"padding:8px 10px;font-weight:600;}}"
        )


def _palette_fallback(key: str) -> str:
    """主题里缺这个键时取 classic 的同一个键。

    不写死兜底色：那等于在 UI 模块里加一个字面量颜色，正好踩裸色禁令。
    """
    return str(theme.THEMES["classic"][key])
