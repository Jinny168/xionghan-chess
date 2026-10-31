"""5 主题 × 主窗口的渲染基线，用于"零视觉变化"验收。

固定环境（换机器前先看这段）：
- `QT_QPA_PLATFORM=offscreen`；
- 窗口固定 1260×850，初始局面；
- 字体用 `theme.load_bundled_fonts()` 之后的状态（随包字体，不依赖系统字体）。

用法：
    python scripts/theme_pixel_baseline.py --write   # 写基线 PNG
    python scripts/theme_pixel_baseline.py --check   # 与基线逐像素比，非零退出码 1
    python scripts/theme_pixel_baseline.py --noise   # 量噪声底：同主题渲染两次的差异

噪声底：见运行输出（同主题两次渲染的差异像素数）。**若不为 0**，`--check` 的判据应放宽到该值。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "theme_pixels"
SIZE = (1260, 850)
THEMES = ("classic", "green", "blue", "purple", "dark")

# 噪声底（同主题两次渲染的差异像素数）：
#   `--noise` 报 classic 206px、其余 0px —— 但那 206px 是**首次渲染的预热效应**
#   （同一进程里第 1 次与第 2 次 `_render()` 比较）；用写好的基线做 `--check` 时，
#   连跑两次均为 **0 px**。所以判据就用 0，容差留字段以便换机器时按 `--noise` 重测。
NOISE_FLOOR = {"classic": 0, "green": 0, "blue": 0, "purple": 0, "dark": 0}
# 噪声底 **0**：时钟已在 `_freeze_clock()` 里冻结（停 QTimer + 把 `game.tick` 打成空操作 +
# 钉死 `clocks_ms`）。**不要**为了"让测试过"把这里调大 —— 那等于给真实回归开后门；
# 若哪天又出现非 0，先找是哪个随时间变化的元素混进了基线，而不是调容差。
# 噪声底不是 0：侧栏时钟的数字会随秒变化，相邻两次渲染约差 **206 px**（实测在 classic/green/purple
# 之间漂移）。所以容差取 260（206 + 余量）。判据仍是"超过容差才算视觉变了"，
# 但**不能**把容差当"允许回归"——B 阶段的判据是"差异必须落在预期区域"，看的是区域归因而不是这个数。


def _freeze_clock(window) -> None:
    """冻结侧栏时钟 —— 基线截图里不允许出现随时间变化的内容。

    窗口的 `self.timer` 每 250ms 触发 `refresh()`，而 `refresh()` 会调 `game.tick()` 按真实时间扣钟。
    所以只停 QTimer 还不够：先停表，再把 `tick` 打成空操作、并把剩余时间钉死，
    否则"冻结时已扣了多少"仍取决于 processEvents 的调度。
    """
    from PySide6.QtCore import QTimer

    for timer in window.findChildren(QTimer):
        timer.stop()
    game = getattr(window, "game", None)
    if game is None:
        return
    game.tick = lambda *args, **kwargs: None
    from xionghan_chess.core.model import Color

    game.state.clocks_ms = {Color.RED: 20 * 60_000, Color.BLACK: 20 * 60_000}


def _check_game():
    """稳定的最小将军局面：黑王在 (0,4)，红车沿第 0 行打将，轮到黑走。

    为什么需要它：`#b21f1f`（将军态警示色）**只在将军时渲染**，初始局面里根本看不见。
    没有这个夹具，"改完 `--check` 全 0"会被误读成"改对了"或"没生效"。
    """
    from xionghan_chess.core.game import Game
    from xionghan_chess.core.model import Color, GameState, Piece, PieceType

    def pc(kind, color, row, col):
        return Piece.create(kind, color, row, col)

    state = GameState("desktop_complete",
                      [pc(PieceType.KING, Color.RED, 11, 6),
                       pc(PieceType.KING, Color.BLACK, 0, 4),
                       pc(PieceType.ROOK, Color.RED, 0, 10)],
                      turn=Color.BLACK, captured={Color.RED: [], Color.BLACK: []})
    return Game.from_state(state, {}, None)


def _render(app, theme_name: str, state: str = "init"):
    from xionghan_chess.desktop.app import MainWindow
    from xionghan_chess.desktop.config import load_config

    config = load_config()
    config["theme"] = theme_name
    window = MainWindow()
    window.config["theme"] = theme_name
    window.apply_appearance()
    if state == "check":
        window.game = _check_game()
        window.refresh()
    window.resize(*SIZE)
    window.show()
    for _ in range(3):
        app.processEvents()
    if "--no-freeze" not in sys.argv:
        _freeze_clock(window)
        window.refresh()
    for _ in range(2):
        app.processEvents()
    image = window.grab().toImage()
    regions = _regions(window)
    window.close()
    app.processEvents()
    return image, regions


def _rect_of(widget, window) -> tuple[int, int, int, int]:
    """控件在**窗口坐标系**下的矩形（`geometry()` 是相对父控件，直接比会错位）。"""
    from PySide6.QtCore import QPoint

    top_left = widget.mapTo(window, QPoint(0, 0))
    return (top_left.x(), top_left.y(),
            top_left.x() + widget.width(), top_left.y() + widget.height())


def _regions(window) -> dict[str, tuple[int, int, int, int]]:
    """把窗口切成可解释的区域（用于"差异落在哪"）。"""
    board = _rect_of(window.board, window)
    side = _rect_of(window.side, window)
    banner = _rect_of(window.banner, window) if hasattr(window, "banner") else None
    board_rect, side_rect = board, side
    top_limit = min(board_rect[1], side_rect[1])
    regions = {
        "标题栏": (0, 0, window.width(), max(1, top_limit)),
        "棋盘": board_rect,
        "侧栏": side_rect,
    }
    if banner is not None and banner[2] > banner[0]:
        # 横幅是**叠在棋盘上方**的浮层：按几何它会落在"棋盘"矩形里，
        # 所以必须单独取出、且**优先判定**，否则"将军色改到横幅"会被误报成"棋盘变了"。
        regions["横幅"] = banner
    return regions


def _classify(regions: dict, x: int, y: int) -> str:
    for name in ("横幅", "棋盘", "侧栏"):
        x0, y0, x1, y1 = regions[name]
        if x0 <= x < x1 and y0 <= y < y1:
            return name
    x0, y0, x1, y1 = regions["标题栏"]
    if x0 <= x < x1 and y0 <= y < y1:
        return "标题栏"
    return "其它"


def _diff(a, b) -> int:
    if a.size() != b.size():
        return a.width() * a.height()
    count = 0
    for y in range(a.height()):
        for x in range(a.width()):
            if a.pixel(x, y) != b.pixel(x, y):
                count += 1
    return count


def main() -> int:
    state = "check" if "--state=check" in sys.argv else "init"
    app = QApplication.instance() or QApplication([])
    from xionghan_chess.desktop.ui import theme

    theme.load_bundled_fonts()

    if "--noise" in sys.argv:
        for name in THEMES:
            first = _render(app, name)[0]
            second = _render(app, name)[0]
            print(f"{name:8s} 噪声底 {_diff(first, second)} px")
        return 0

    if "--write" in sys.argv:
        OUT.mkdir(parents=True, exist_ok=True)
        for name in THEMES:
            suffix = "_check" if state == "check" else ""
            image = _render(app, name, state)[0]
            path = OUT / f"{name}{suffix}.png"
            image.save(str(path))
            print(f"{name:8s} -> {path.name} {path.stat().st_size} B")
        return 0

    if "--diff-report" in sys.argv:
        from collections import Counter

        from PySide6.QtGui import QImage

        rows = []
        for name in THEMES:
            path = OUT / f"{name}{'_check' if state == 'check' else ''}.png"
            if not path.is_file():
                print(f"{name:8s} 缺基线 {path}")
                return 1
            baseline = QImage(str(path))
            current, regions = _render(app, name, state)
            tally: Counter = Counter()
            if baseline.size() == current.size():
                for y in range(current.height()):
                    for x in range(current.width()):
                        if baseline.pixel(x, y) != current.pixel(x, y):
                            tally[_classify(regions, x, y)] += 1
            total = sum(tally.values())
            detail = "  ".join(f"{k} {v}" for k, v in tally.most_common()) or "无差异"
            rows.append(f"{name:8s} 合计 {total:6d} px | {detail}")
        print("\n".join(rows))
        return 0

    # --check
    failed = []
    for name in THEMES:
        path = OUT / f"{name}{'_check' if state == 'check' else ''}.png"
        if not path.is_file():
            print(f"{name:8s} 缺基线 {path}")
            return 1
        from PySide6.QtGui import QImage

        baseline = QImage(str(path))
        current = _render(app, name, state)[0]
        diff = _diff(baseline, current)
        floor = NOISE_FLOOR.get(name, 0)
        flag = "" if diff <= floor else "  ← 超过噪声底"
        if diff > floor:
            failed.append(name)
        print(f"{name:8s} 差异像素 {diff}（噪声底 {floor}）{flag}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
