"""棋盘几何换算（纯函数，无 Qt 依赖）—— 阶段1 S1-2 抽出。

原在 `app.py::BoardWidget._geometry` / `_position` / `_view_position` 里，与
QPainter 绘制、鼠标事件绑死，无法单测。抽成纯函数后：
- 可单测（坐标映射点错格子是最刺眼的用户可见缺陷，见验收策略 A4）；
- 绘制与输入共用同一套换算，不会两侧漂移。

所有坐标均为「可用区域」的局部坐标（可用区域左上角为 0,0），
调用方需自行加上可用区域在窗口里的偏移（app.py 里是 rect().adjusted(13,13,-13,-13)）。
"""
from __future__ import annotations

from xionghan_chess.core.model import Position

# 与原实现一致的布局系数。改动即视觉回归，不要随意调。
_OUTER_RATIO = 1.35   # 棋盘外框总宽 ≈ cell * (cols - 1 + 1.35)
_PAD_RATIO = 0.675    # 外框到第一条棋盘线的边距 = cell * 0.675


def cell_layout(width: float, height: float, rows: int, cols: int) -> tuple[float, float, float, float, float, float, float]:
    """由可用区域尺寸与棋盘规模算布局。

    返回 ``(inset_x, inset_y, grid_left, grid_top, cell_w, cell_h, pad)``：
      - ``inset_x/y``：棋盘外框相对可用区域的缩进（外框在可用区域内居中）
      - ``grid_left/top``：第一条棋盘线的坐标（= inset + pad）
      - ``cell_w/cell_h``：格子尺寸（正方形，二者相等）
      - ``pad``：外框到第一条线的边距
    """
    cell = min(width / max(1, cols - 1 + _OUTER_RATIO),
               height / max(1, rows - 1 + _OUTER_RATIO))
    pad = cell * _PAD_RATIO
    board_w = cell * (cols - 1) + pad * 2
    board_h = cell * (rows - 1) + pad * 2
    inset_x = (width - board_w) / 2
    inset_y = (height - board_h) / 2
    return inset_x, inset_y, inset_x + pad, inset_y + pad, cell, cell, pad


def view_position(row: int, col: int, rows: int, cols: int, flipped: bool) -> Position:
    """棋盘坐标 → 展示坐标（处理 flipped 翻转；不翻转时原样返回）。"""
    if not flipped:
        return Position(row, col)
    return Position(rows - 1 - row, cols - 1 - col)


def point_to_position(x: float, y: float, left: float, top: float,
                      cw: float, ch: float, rows: int, cols: int,
                      flipped: bool) -> Position | None:
    """像素坐标 → 棋盘坐标。越界返回 ``None``（与鼠标命中测试一致）。"""
    col = round((x - left) / cw)
    row = round((y - top) / ch)
    if flipped:
        row, col = rows - 1 - row, cols - 1 - col
    return Position(row, col) if 0 <= row < rows and 0 <= col < cols else None


def position_to_point(row: int, col: int, left: float, top: float,
                      cw: float, ch: float, rows: int, cols: int,
                      flipped: bool) -> tuple[float, float]:
    """棋盘坐标 → 像素坐标（point_to_position 的逆运算，供绘制与动画用）。"""
    view_row, view_col = (rows - 1 - row, cols - 1 - col) if flipped else (row, col)
    return left + view_col * cw, top + view_row * ch
