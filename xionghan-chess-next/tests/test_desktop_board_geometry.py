"""棋盘几何换算单测（阶段1 S1-2，验收策略 A4）。

这些是**纯函数**（不 import PySide6），所以能在 CI 的 pytest job 里跑 ——
这是桌面端第一批不需要 PySide6 的自动化覆盖。
"""
from __future__ import annotations

import pytest

from xionghan_chess.core.model import Position
from xionghan_chess.desktop.ui.board_geometry import (
    cell_layout,
    point_to_position,
    position_to_point,
    view_position,
)

SIZES = [(13, 13), (10, 9), (13, 9)]


@pytest.mark.parametrize("rows,cols", SIZES)
def test_cell_layout_is_square_and_centred(rows, cols):
    w, h = 900.0, 700.0
    ix, iy, gl, gt, cw, ch, pad = cell_layout(w, h, rows, cols)
    assert cw == ch, "格子必须是正方形"
    assert pad > 0 and pad < cw
    # 第一条线 = 缩进 + 边距
    assert gl == pytest.approx(ix + pad)
    assert gt == pytest.approx(iy + pad)
    # 外框在可用区域内居中
    board_w = cw * (cols - 1) + pad * 2
    board_h = ch * (rows - 1) + pad * 2
    assert ix == pytest.approx((w - board_w) / 2)
    assert iy == pytest.approx((h - board_h) / 2)
    assert ix >= 0 and iy >= 0, "可用区域必须放得下棋盘"


@pytest.mark.parametrize("rows,cols", SIZES)
def test_cell_layout_scales_with_area(rows, cols):
    """可用区域越大格子越大；且极宽/极高区域分别由高/宽项主导。

    注意**不是**简单的「较短边主导」：cell = min(w/(cols-1+1.35), h/(rows-1+1.35))，
    分母含 cols/rows，非正方盘面（如 10×9）时两侧系数不同，故分别精确断言。
    """
    small = cell_layout(600.0, 500.0, rows, cols)[4]
    large = cell_layout(1200.0, 1000.0, rows, cols)[4]
    assert large > small
    # 极宽区域：宽度项被撑得极大，最小值落到高度项
    wide = cell_layout(4000.0, 600.0, rows, cols)[4]
    assert wide == pytest.approx(600.0 / (rows - 1 + 1.35))
    # 极高区域：最小值落到宽度项
    tall = cell_layout(600.0, 4000.0, rows, cols)[4]
    assert tall == pytest.approx(600.0 / (cols - 1 + 1.35))


@pytest.mark.parametrize("rows,cols", SIZES)
@pytest.mark.parametrize("flipped", [False, True])
def test_point_and_position_round_trip(rows, cols, flipped):
    """像素 → 棋盘 → 像素 必须还原（绘制与输入共用一套换算的关键保证）。"""
    _, _, gl, gt, cw, ch, _pad = cell_layout(900.0, 700.0, rows, cols)
    for row in range(rows):
        for col in range(cols):
            x, y = position_to_point(row, col, gl, gt, cw, ch, rows, cols, flipped)
            back = point_to_position(x, y, gl, gt, cw, ch, rows, cols, flipped)
            assert back == Position(row, col), f"round-trip 失败: ({row},{col}) flipped={flipped}"


@pytest.mark.parametrize("rows,cols", SIZES)
@pytest.mark.parametrize("flipped", [False, True])
def test_point_out_of_bounds_returns_none(rows, cols, flipped):
    """远离棋盘的点必须返回 None。

    注意：不能用「最后一格 + 0.9 格」这种近界点 —— flipped=True 时棋盘最后一格
    映射到视图左上角，那个偏移仍在盘内。用远离盘面数格的点，对翻转/不翻转都成立。
    """
    _, _, gl, gt, cw, ch, _pad = cell_layout(900.0, 700.0, rows, cols)
    far = 5.0
    for x, y in (
        (gl - cw * far, gt - ch * far),                       # 左上外侧
        (gl + (cols + far) * cw, gt + (rows + far) * ch),     # 右下外侧
        (gl - cw * far, gt + (rows + far) * ch),              # 左下外侧
        (gl + (cols + far) * cw, gt - ch * far),              # 右上外侧
    ):
        assert point_to_position(x, y, gl, gt, cw, ch, rows, cols, flipped) is None


@pytest.mark.parametrize("rows,cols", SIZES)
def test_view_position_flip_is_involution(rows, cols):
    """翻转两次必须还原。"""
    for row in range(rows):
        for col in range(cols):
            once = view_position(row, col, rows, cols, True)
            twice = view_position(once.row, once.col, rows, cols, True)
            assert twice == Position(row, col)
            assert view_position(row, col, rows, cols, False) == Position(row, col)


@pytest.mark.parametrize("rows,cols", SIZES)
def test_view_position_maps_corners(rows, cols):
    """翻转必须把四角对调。"""
    assert view_position(0, 0, rows, cols, True) == Position(rows - 1, cols - 1)
    assert view_position(rows - 1, cols - 1, rows, cols, True) == Position(0, 0)
    assert view_position(0, cols - 1, rows, cols, True) == Position(rows - 1, 0)
    assert view_position(rows - 1, 0, rows, cols, True) == Position(0, cols - 1)
