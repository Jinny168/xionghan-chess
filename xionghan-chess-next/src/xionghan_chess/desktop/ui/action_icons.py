"""侧栏操作图标：自绘矢量，统一线宽与端点风格。

为什么不用 `QStyle` 标准图标：
- 语义不对：翻转棋盘的箭头、提和的对勾、认输的叉，都是"系统对话框"的语汇，
  放在棋类操作里读不出含义；
- 风格不统一：`QStyle` 混了实心/空心、粗细不一，七个摆一排像从三个软件里凑的。

这里统一成：24×24 画布、1.8px 描边、圆端点、只用前景色（跟随主题调色板），
按设备像素比渲染成 QIcon，深浅色主题都不会糊。
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

CANVAS = 24.0
STROKE = 1.8
SCALE = 3  # 渲染倍数：24px 的图标按 72px 画再缩，边缘才不毛


def _pen(color: QColor) -> QPen:
    pen = QPen(color)
    pen.setWidthF(STROKE)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _arrow_head(painter: QPainter, tip: QPointF, angle_deg: float, size: float = 4.2) -> None:
    """在 `tip` 处画一个小箭头（`angle_deg` 指向箭头尖端方向）。"""
    import math

    rad = math.radians(angle_deg)
    back = QPointF(tip.x() - math.cos(rad) * size, tip.y() - math.sin(rad) * size)
    left = QPointF(back.x() - math.sin(rad) * size * 0.55, back.y() + math.cos(rad) * size * 0.55)
    right = QPointF(back.x() + math.sin(rad) * size * 0.55, back.y() - math.cos(rad) * size * 0.55)
    painter.drawLine(tip, left)
    painter.drawLine(tip, right)


def _undo(painter: QPainter) -> None:
    """撤回：一条回转箭头。原先还拖了一条横线，28px 下像"↰--"，去掉。"""
    path = QPainterPath(QPointF(9.2, 7.2))
    path.cubicTo(4.2, 8.2, 4.2, 15.8, 9.2, 16.8)
    path.lineTo(QPointF(18.5, 16.8))
    painter.drawPath(path)
    _arrow_head(painter, QPointF(9.2, 7.2), 150)


def _pause(painter: QPainter) -> None:
    for x in (9.0, 15.0):
        painter.drawLine(QPointF(x, 6.5), QPointF(x, 17.5))


def _play(painter: QPainter) -> None:
    path = QPainterPath(QPointF(9.0, 6.5))
    path.lineTo(QPointF(18.0, 12.0))
    path.lineTo(QPointF(9.0, 17.5))
    path.closeSubpath()
    painter.drawPath(path)


def _flag(painter: QPainter) -> None:
    painter.drawLine(QPointF(7.0, 5.0), QPointF(7.0, 19.0))
    path = QPainterPath(QPointF(7.0, 6.0))
    path.lineTo(QPointF(17.5, 8.2))
    path.lineTo(QPointF(7.0, 11.4))
    painter.drawPath(path)


def _balance(painter: QPainter) -> None:
    """和棋：半填充圆（"一半"），国际通用的和局/平手意象。

    试过天平（像桌子）、相对箭头（小尺寸像 ×，和认输撞车）、「½」文字
    （内置字体是**子集**，不含该字形，直接渲染成空白）。纯几何最稳。
    """
    rect = QRectF(4.6, 4.6, 14.8, 14.8)
    painter.drawEllipse(rect)
    half = QPainterPath()
    half.moveTo(QPointF(12.0, 4.6))
    half.arcTo(rect, 90.0, -180.0)
    half.closeSubpath()
    painter.setBrush(QBrush(painter.pen().color()))
    painter.drawPath(half)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _revive(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(5.5, 5.5, 13.0, 13.0))
    painter.drawLine(QPointF(12.0, 9.0), QPointF(12.0, 15.0))
    painter.drawLine(QPointF(9.0, 12.0), QPointF(15.0, 12.0))


def _flip(painter: QPainter) -> None:
    painter.drawLine(QPointF(8.5, 7.0), QPointF(8.5, 16.0))
    _arrow_head(painter, QPointF(8.5, 16.0), 90)
    painter.drawLine(QPointF(15.5, 17.0), QPointF(15.5, 8.0))
    _arrow_head(painter, QPointF(15.5, 8.0), -90)


def _again(painter: QPainter) -> None:
    rect = QRectF(6.0, 6.0, 12.0, 12.0)
    path = QPainterPath()
    path.arcMoveTo(rect, 60)
    path.arcTo(rect, 60, 280)
    painter.drawPath(path)
    _arrow_head(painter, QPointF(15.2, 7.4), -20)


DRAWERS = {
    "undo": _undo,
    "pause": _pause,
    "resume": _play,
    "resign": _flag,
    "draw": _balance,
    "resurrect": _revive,
    "flip": _flip,
    "again": _again,
}


def action_icon(kind: str, color: QColor, size: int = 22) -> QIcon:
    """画一枚动作图标。`kind` 见 `DRAWERS`；未知类型返回空 QIcon。"""
    drawer = DRAWERS.get(kind)
    if drawer is None:
        return QIcon()

    pixmap = QPixmap(int(CANVAS * SCALE), int(CANVAS * SCALE))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(_pen(color))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.scale(SCALE, SCALE)
    drawer(painter)
    painter.end()

    pixmap.setDevicePixelRatio(SCALE)
    return QIcon(pixmap)
