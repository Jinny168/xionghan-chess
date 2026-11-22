"""P1-11 侧栏信息分层：自建可折叠分组 `CollapsibleBox`。

## 为什么不用现成控件（技术选型已定，别再改）

- **QGroupBox + setCheckable**：勾选框的语义是"启用/禁用整组子控件"（子控件会变灰
  且不可交互），不是"收起/展开"。拿它做折叠，玩家点一下发现组里的按钮全灰了。
- **QToolBox**：一次只能展开一页，切到另一页时前一组自动收起。侧栏的「阵亡子力」
  与将来的规则区需要**同时可见**，这条互斥语义直接不成立。
- 因此自建：`QToolButton`（checkable + 箭头）+ 内容容器，切换只改 `setVisible`。

## 一条硬约束

本控件**只改可见性，不改任何尺寸**：收起时内容容器 `hide()`，但不 `setFixedHeight(0)`、
不动 `minimumWidth`。侧栏宽度是 `QSplitter` 里写死的 330（`app.py`），棋盘尺寸由
`_SquareHost` 按剩余空间算 —— 谁在这里动尺寸，谁就会把棋盘挤小。
`tests/test_desktop_collapsible.py` 用"折叠前后棋盘宽度不变"钉死这条。

## 不持久化

折叠状态**不写配置**（新一轮存储通道 = 新一轮迁移与一致性债）。每次启动都是构造时
传入的 `expanded`，默认收起。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLayout, QSizePolicy, QToolButton, QVBoxLayout, QWidget


class CollapsibleBox(QWidget):
    """一个标题按钮 + 一块可收起的内容容器。

    参数：
        title: 标题（已翻译文案；调用方负责 i18n，本控件不查词表）。
        expanded: 初始是否展开。默认**收起**（P1-11 的目标是把低频信息先藏起来）。
    """

    def __init__(self, title: str, expanded: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = bool(expanded)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._outer = outer

        self.header = QToolButton(self)
        self.header.setObjectName("collapsible_header")
        self.header.setText(title)
        self.header.setToolTip(title)
        self.header.setAccessibleName(title)
        self.header.setCheckable(True)
        self.header.setChecked(self._expanded)
        self.header.setAutoRaise(True)
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header.setArrowType(Qt.ArrowType.DownArrow if self._expanded else Qt.ArrowType.RightArrow)
        self.header.clicked.connect(self._toggle)
        outer.addWidget(self.header)

        content = QWidget(self)
        self._content_layout: QLayout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        outer.addWidget(content)
        self._content = content
        content.setVisible(self._expanded)

    # ---- 只读状态 ----

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    @property
    def title(self) -> str:
        return self.header.text()

    @property
    def content(self) -> QWidget:
        """当前内容容器（`set_content_layout` 会换掉它，所以别缓存）。"""
        return self._content

    # ---- 内容装配 ----

    def add_widget(self, widget: QWidget) -> None:
        """往内容容器里追加一个控件。"""
        self._content_layout.addWidget(widget)

    def set_content_layout(self, layout: QLayout) -> None:
        """用一整个布局替换内容容器里的东西。

        实现是**换容器**而不是 `QWidget.setLayout()` 换布局：Qt 里一个 widget 已经
        有布局之后再 setLayout 第二个只会打印警告且不生效，换容器是唯一不踩坑的写法。
        旧容器连子控件一起 `deleteLater()`，所以调用后原来 add 进去的控件不再受本框管理。
        """
        holder = QWidget(self)
        holder.setLayout(layout)
        old = self._content
        self._outer.removeWidget(old)
        old.hide()
        old.setParent(None)
        old.deleteLater()
        self._outer.addWidget(holder)
        self._content = holder
        self._content_layout = layout
        holder.setVisible(self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        """以代码方式展开/收起（与点击 header 走同一条路径）。"""
        expanded = bool(expanded)
        if expanded == self._expanded:
            return
        self._toggle(expanded)

    # ---- 内部 ----

    def _toggle(self, checked: bool) -> None:
        """点击 header：只改可见性与箭头方向，**不碰任何尺寸**。"""
        self._expanded = bool(checked)
        self.header.setChecked(self._expanded)
        self.header.setArrowType(Qt.ArrowType.DownArrow if self._expanded else Qt.ArrowType.RightArrow)
        self._content.setVisible(self._expanded)
