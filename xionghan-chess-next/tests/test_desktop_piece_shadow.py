"""P1-1 桌面棋子投影：必须在 `_draw_piece` 这个**分发入口**上一视同仁，且必须真的看得见。

## 这一层的四个硬约束，都是"看不见的代码"型契约

1. **不许三个渲染分支各画一遍。** 字形 / 位图 / 回退（`draw_piece_glyph`、
   `_draw_piece_image`、`draw_fallback_piece`）的坐标系与半径算法各不相同，
   各画一遍早晚漏一条 —— 回退分支在本项目历史上就被漏过一次。
   所以投影只写在 `_draw_piece` 里，让任何棋子都必然有。
   本条用"三种模式都有像素变化"来证伪：若哪天有人把投影搬进某一个分支，
   另外两个模式立刻少掉这些像素。

2. **必须真的看得见。** 这条是踩过坑换来的：第一版用纯色椭圆
   （半径 0.98r / 偏移 0.07r），可见面积几何上为 0 —— 字形棋子可见外沿 1.05r，
   而 0.98r + 0.07r 正好也是 1.05r，**两者恰好重合**，
   实测开/关投影只差 0.40% 像素（且全是抗锯齿溢出，可感知差异为 **0**）。
   "参数写进去了"不等于"用户看得见"，所以这里直接断言可感知强度与方向。

3. **强度必须是单旋钮、且旋钮真的有效。** 渐变方案下**圆心 alpha 完全被棋子盖住**
   （0.72 × 1.30r = 0.936r < 1.05r），所以"圆心一个常量、中段一个常量"是接口陷阱：
   改圆心是空转。现在只有 `PIECE_SHADOW_STRENGTH` 一个旋钮，所有色标按比例派生；
   本条用"4 档单调递增"把"改了没反应"变成红。

4. **按盘底色标定。** 同一组 alpha 在浅盘和深盘上的观感差一个量级
   （硬区像素 classic 13,327 vs dark 242）。所以主题提供 `shadow_gain`，
   对用户仍是一个强度条。本条用硬区像素预算卡住"浅盘脏、深盘看不见"两头。

## 测量口径

不看具体色值（投影强度属于设计参数，会调），只比"开投影 / 关投影"两张图。
**关投影的方式与参数解耦**：把 `_piece_shadow_brush` 换成一个空刷子，
不依赖任何一个数值常量 —— 否则改参数会把测试连同断言一起改瞎。
"可感知"取每通道 Δ≥6（Δ=1~5 肉眼基本分辨不出，正是抗锯齿溢出的量级）；
"硬区"取 Δ≥30（真正的深色带，用来判断会不会看起来"脏了一圈"）。
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="棋盘渲染依赖 PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, Piece, PieceType  # noqa: E402
from xionghan_chess.desktop.ui import board_widget, piece_assets, theme  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WIDGET_PY = ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "board_widget.py"

GLYPH_MODE = board_widget.GLYPH_MODE
IMAGE_MODE = board_widget.IMAGE_MODE

PERCEPTIBLE_DELTA = 6
HARD_DELTA = 30
MIN_VISIBLE_RATIO = 0.02        # 设计口径：开/关差异 ≥ 2.0% 棋盘面积
MIN_DOWNWARD_LEAN = 1.5         # 底部厚度 ≥ 顶部 1.5 倍（等宽就是描边，不是影子）
# 每套主题的硬区（Δ≥30）上下界 —— **五套全覆盖**，缺一套就等于那套超重无人拦
# （曾经只写 classic/dark 两套，把 green 的 gain 调到 1.0 也全套绿）。
# 下界防空画、上界防"脏了一圈"。括号内是本次定标时的实测值。
HARD_ZONE_BUDGET = {
    "classic": (2000, 7000),    # 实测 4,211
    "green": (2000, 7000),      # 实测 4,008
    "blue": (2000, 7000),       # 实测 4,031
    "purple": (2000, 7000),     # 实测 4,058
    "dark": (150, 300),         # 实测 242（深底几乎不显，必须给足满系数）
}

# 可感知（Δ≥6）面积下界：**浅色四套 4.0%**；dark 取 3.0%。
#
# 这里有一处**验收线本身互斥**，如实记下来而不是偷偷改数：
# 设计要求"五套 ≥4.0% 且 dark 硬区 ≤300"，但在 dark 上这两条不可同时成立 ——
#   gain 1.00 → 可感知 3.67% / 硬区 242   （面积不达 4.0%，硬区达标）
#   gain 1.10 → 可感知 4.03% / 硬区 324   （面积刚过线，硬区超 300 约 8%）
# 深底上要把黑影推到 4% 面积，必然加浓到 324 个硬区像素。
# 取 gain 1.00：保住"深盘不加重"（设计说暗盘只需"看得见"，不需要追平浅盘），
# 且 3.67% 远高于 2.0% 的可见线。若哪天真要 4.0%，必须同时放宽 hard 上界。
SOFT_AREA_FLOOR = {
    "classic": 0.040,
    "green": 0.040,
    "blue": 0.040,
    "purple": 0.040,
    "dark": 0.030,      # 见上：3.67% 实测，4.0% 与硬区 ≤300 互斥
}

SMALL = 480
MEASURE = 700
BOARD = MEASURE * MEASURE


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def render(*, mode: str = GLYPH_MODE, size: int = SMALL, theme_name: str = "classic",
           pieces: int = 1) -> QImage:
    """`pieces=1` 放一枚子在中心（比形状）；`pieces=0` 用整盘 61 枚（比强度）。"""
    game = Game("web")
    if pieces:
        game.state.pieces = [Piece.create(PieceType.ROOK, Color.RED, 5, 5)]
    board = board_widget.BoardWidget()
    board.resize(size, size)
    board.set_game(game, Color.RED, True)
    board.set_appearance(theme_name, "none", "traditional", mode)
    board.interactive = False
    canvas = QPixmap(size, size)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage()


def render_without_shadow(**kwargs) -> QImage:
    """关投影：把刷子换成 NoBrush，不碰任何数值常量。

    只在**这一次**渲染内生效（`MonkeyPatch.context`），否则连"开投影"那张图
    也会被一起关掉，比出来的差异恒为 0。
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(board_widget, "_piece_shadow_brush",
                      lambda gain=1.0: QBrush(Qt.BrushStyle.NoBrush))
        return render(**kwargs)


def _raw(image: QImage) -> bytes:
    return bytes(image.constBits())


def _deltas(a: QImage, b: QImage) -> bytes:
    """逐像素返回 max(|ΔR|,|ΔG|,|ΔB|)。RGB32 每像素 4 字节（B,G,R,A）。"""
    pa, pb = _raw(a), _raw(b)
    out = bytearray(len(pa) // 4)
    for index in range(len(out)):
        i = index * 4
        out[index] = max(abs(pa[i] - pb[i]), abs(pa[i + 1] - pb[i + 1]),
                         abs(pa[i + 2] - pb[i + 2]))
    return bytes(out)


def differing_pixels(a: QImage, b: QImage) -> int:
    return sum(1 for d in _deltas(a, b) if d)


def count_at_least(a: QImage, b: QImage, delta: int) -> int:
    return sum(1 for d in _deltas(a, b) if d >= delta)


def energy(a: QImage, b: QImage) -> int:
    """差异能量（Δ 之和）。

    用它做单调性判据而非面积：阈值类指标天生有"平台区"（低档全在阈值以下时面积恒 0），
    而能量是连续量，旋钮每一步都必须真的加上去。
    """
    return sum(_deltas(a, b))


# --- 三个分支都要有 -------------------------------------------------------

@pytest.mark.parametrize("mode", [GLYPH_MODE, IMAGE_MODE])
def test_shadow_is_drawn_in_every_render_branch(qt_app: QApplication, mode: str) -> None:
    """字形与位图两条分支都必须有投影像素。"""
    on = render(mode=mode)
    off = render_without_shadow(mode=mode)
    assert differing_pixels(on, off) > 0, f"{mode} 模式下没有画投影（开/关投影渲染结果完全相同）"


def test_shadow_is_drawn_in_the_fallback_branch(qt_app: QApplication,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    """回退分支（无美术棋子）同样有投影 —— 因为它画在分发入口，不在分支里。"""
    monkeypatch.setattr(piece_assets, "pixmap", lambda *args, **kwargs: None)
    on = render(mode=IMAGE_MODE)
    off = render_without_shadow(mode=IMAGE_MODE)
    assert differing_pixels(on, off) > 0, "回退分支没有投影 —— 投影被搬进分支了"


# --- 必须真的看得见（这条抓的是"参数写了但不可见"） ----------------------

@pytest.mark.parametrize("theme_name", ["classic", "dark"])
def test_shadow_is_actually_visible(qt_app: QApplication, theme_name: str) -> None:
    """开/关投影的**可感知**差异必须 ≥ 2.0% 棋盘面积（浅色 / 深色各一次）。

    第一版纯色椭圆实测只有 0.40% 且**可感知面积 0.00%**，
    靠这条会被直接拦下 —— 而不是等到人肉截图才发现"加了等于没加"。
    """
    on = render(size=MEASURE, theme_name=theme_name, pieces=0)
    off = render_without_shadow(size=MEASURE, theme_name=theme_name, pieces=0)
    ratio = count_at_least(on, off, PERCEPTIBLE_DELTA) / BOARD
    assert ratio >= MIN_VISIBLE_RATIO, (
        f"[{theme_name}] 投影可感知面积只有 {ratio:.2%}，低于验收线 {MIN_VISIBLE_RATIO:.0%}"
        "（参数写进去了但用户看不见 —— 先确认 PIECE_SHADOW_STRENGTH 与 shadow_gain 是否被改回硬边椭圆）")


def test_shadow_leans_downward_instead_of_being_a_uniform_ring(qt_app: QApplication) -> None:
    """底部可见厚度必须 ≥ 顶部的 1.5 倍：影子重心向下，等宽就不是影子而是描边。"""
    on = render(size=MEASURE)
    off = render_without_shadow(size=MEASURE)
    deltas = _deltas(on, off)
    width = MEASURE

    def changed_at(x: int, y: int) -> bool:
        return deltas[y * width + x] >= PERCEPTIBLE_DELTA

    board = board_widget.BoardWidget()
    board.resize(MEASURE, MEASURE)
    _, left, top, cw, ch = board._geometry()
    cx, cy = int(left + 5 * cw), int(top + 5 * ch)
    band = range(cx - 2, cx + 3)

    up = sum(1 for dy in range(-60, 0) if any(changed_at(x, cy + dy) for x in band))
    down = sum(1 for dy in range(0, 60) if any(changed_at(x, cy + dy) for x in band))
    assert up > 0 and down > 0, f"投影没有同时出现在上下两侧（上 {up}px / 下 {down}px）"
    assert down >= up * MIN_DOWNWARD_LEAN, (
        f"投影上下等宽（上 {up}px / 下 {down}px），看起来会是描边而不是落影")


# --- 单旋钮必须真的有效 ---------------------------------------------------

def test_strength_knob_changes_the_rendering_monotonically(
        qt_app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """`PIECE_SHADOW_STRENGTH` 四档（0 / ⅓ / ⅔ / 1）必须让强度**严格递增**。

    这里守的是"旋钮是不是接对了量"：如果旋钮去驱动**圆心 alpha**
    （而圆心被棋子完全盖住），四档会画出一模一样的图，这条立刻红 ——
    那正是把 `ALPHA` 常量改成旋钮时最容易埋的雷。
    面积与能量**两个指标都要单调**：面积防"看不出来"，能量防"面积到顶后偷偷加浓"。
    """
    off = render_without_shadow(size=MEASURE, pieces=0)
    areas: list[float] = []
    energies: list[int] = []
    for step in (0.0, 1 / 3, 2 / 3, 1.0):
        monkeypatch.setattr(board_widget, "PIECE_SHADOW_STRENGTH", step)
        board_widget._SHADOW_BRUSH_CACHE.clear()
        on = render(size=MEASURE, pieces=0)
        areas.append(count_at_least(on, off, PERCEPTIBLE_DELTA) / BOARD)
        energies.append(energy(on, off))

    assert all(b > a for a, b in zip(areas, areas[1:])), f"可感知面积不是严格递增：{areas}"
    assert all(b > a for a, b in zip(energies, energies[1:])), f"差异能量不是严格递增：{energies}"


def test_strength_zero_renders_exactly_like_no_shadow(
        qt_app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    """旋钮拧到 0 必须**逐像素相同**（不是"看起来差不多"）。

    判据写成 `== 0` 而不是 `> 0`：这是"关掉"的明确失败路径 ——
    只要漏了任何一个色标没跟着派生，这里就会红。
    """
    monkeypatch.setattr(board_widget, "PIECE_SHADOW_STRENGTH", 0.0)
    board_widget._SHADOW_BRUSH_CACHE.clear()
    on = render(size=MEASURE, pieces=0)
    off = render_without_shadow(size=MEASURE, pieces=0)
    assert differing_pixels(on, off) == 0, "强度为 0 仍有可见投影（有色标没跟着旋钮派生）"


def test_every_theme_stays_within_its_budget(qt_app: QApplication) -> None:
    """**五套主题全查**：可感知面积不低于下界、硬区落在区间内。

    缺一套就等于那套"调坏了也没人知道"——曾经只覆盖 classic/dark，
    green/blue/purple 超重 70% 而全套仍是绿的。
    两头都要查的原因：只查上界会放过"画了但太淡"，只查下界会放过"脏了一圈"。
    """
    problems = []
    for theme_name in theme.THEMES:
        assert theme_name in HARD_ZONE_BUDGET, f"{theme_name} 没有硬区预算"
        assert theme_name in SOFT_AREA_FLOOR, f"{theme_name} 没有可感知下界"
        on = render(size=MEASURE, theme_name=theme_name, pieces=0)
        off = render_without_shadow(size=MEASURE, theme_name=theme_name, pieces=0)
        low, high = HARD_ZONE_BUDGET[theme_name]
        hard = count_at_least(on, off, HARD_DELTA)
        soft = count_at_least(on, off, PERCEPTIBLE_DELTA) / BOARD
        if not low <= hard <= high:
            problems.append(f"{theme_name}: 硬区 {hard} px 不在 [{low}, {high}]")
        if soft < SOFT_AREA_FLOOR[theme_name]:
            problems.append(
                f"{theme_name}: 可感知面积 {soft:.2%} 低于下界 {SOFT_AREA_FLOOR[theme_name]:.1%}")
    assert not problems, "；".join(problems)


def test_theme_calibration_covers_every_theme() -> None:
    """每套主题都必须有 `shadow_gain`，且浅盘系数不得高于深盘（否则标定逻辑反了）。"""
    missing = [name for name, palette in theme.THEMES.items() if "shadow_gain" not in palette]
    assert not missing, f"这些主题缺少 shadow_gain（投影会掉回默认系数）：{missing}"
    dark = theme.THEMES["dark"]["shadow_gain"]
    for name, palette in theme.THEMES.items():
        if name == "dark":
            continue
        assert palette["shadow_gain"] <= dark, (
            f"{name} 的 shadow_gain {palette['shadow_gain']} 高于 dark {dark} —— "
            "浅底上黑影更显眼，系数应当更低")


# --- 硬约束 ---------------------------------------------------------------

def test_no_graphics_effect_is_used_for_the_shadow() -> None:
    """禁止 `QGraphicsDropShadowEffect`：与自带 QPainter 的绘制流程冲突。

    判据是"**代码里真的用了**"，不是"文件里出现过这个词" —— `_draw_piece` 的注释
    正是在解释为什么不用它，所以先剥掉注释再查（否则注释会把这条断言说成假话）。
    """
    offenders: list[str] = []
    for path in sorted(WIDGET_PY.parent.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        kept: list[str] = []
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type in (tokenize.COMMENT, tokenize.STRING):
                continue            # 文档字符串里提到它不算使用
            kept.append(token.string)
        if "QGraphicsDropShadowEffect" in " ".join(kept):
            offenders.append(path.name)
    assert not offenders, (
        "棋盘棋子投影不得用 QGraphicsDropShadowEffect（会接管 paint 流程、"
        f"与 paintEvent 的坐标系和绘制顺序冲突，并拖慢走子动画）：{offenders}")


def test_shadow_has_a_single_external_knob() -> None:
    """投影只对外暴露**一个**强度旋钮，且那个"改了没反应"的圆心常量已经移除。

    P2-2 要把"投影强度"暴露成用户可调项；如果同时留着
    `PIECE_SHADOW_ALPHA`（圆心）和 `PIECE_SHADOW_CORE_ALPHA`（中段）两个常量，
    用户拧到 0 会毫无反应 —— 那是接口陷阱，不是参数问题。
    """
    for name in ("PIECE_SHADOW_STRENGTH", "PIECE_SHADOW_CORE_ALPHA",
                 "PIECE_SHADOW_CENTER_FACTOR", "PIECE_SHADOW_CORE_STOP",
                 "PIECE_SHADOW_OFFSET", "PIECE_SHADOW_RATIO"):
        assert hasattr(board_widget, name), f"缺少投影参数常量 {name}"
    assert not hasattr(board_widget, "PIECE_SHADOW_ALPHA"), (
        "`PIECE_SHADOW_ALPHA`（圆心）已被 `PIECE_SHADOW_STRENGTH` 取代："
        "它在渐变里被棋子完全盖住，单独改它没有任何可见效果")


def test_shadow_brush_is_reused_instead_of_rebuilt_per_piece(qt_app: QApplication) -> None:
    """刷子必须复用：61 枚子 × 60fps = 每秒最多 3660 次构造，不能每枚子重建。

    判据是"渲染一整盘之后，缓存里只多了一个条目" —— 与实现方式无关。

    `qt_app` 参数是**必需的**：本文件其它渲染用例都会先建 QApplication，
    这条若省掉就会"单独跑崩、跟文件跑过"—— 那是执行顺序在偷偷兜底，
    正是本项目最不想要的那种假绿（QA 在验收时点过这条风险）。
    """
    board_widget._SHADOW_BRUSH_CACHE.clear()
    render(size=MEASURE, pieces=0)
    assert len(board_widget._SHADOW_BRUSH_CACHE) == 1, (
        f"整盘渲染后应只缓存 1 个投影刷子，实际 {len(board_widget._SHADOW_BRUSH_CACHE)} 个"
        "（说明每枚子都在重建渐变）")
