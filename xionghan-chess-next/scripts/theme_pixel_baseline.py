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


def _render(app, theme_name: str):
    from xionghan_chess.desktop.app import MainWindow
    from xionghan_chess.desktop.config import load_config

    config = load_config()
    config["theme"] = theme_name
    window = MainWindow()
    window.config["theme"] = theme_name
    window.apply_appearance()
    window.resize(*SIZE)
    window.show()
    for _ in range(3):
        app.processEvents()
    image = window.grab().toImage()
    window.close()
    app.processEvents()
    return image


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
    app = QApplication.instance() or QApplication([])
    from xionghan_chess.desktop.ui import theme

    theme.load_bundled_fonts()

    if "--noise" in sys.argv:
        for name in THEMES:
            first, second = _render(app, name), _render(app, name)
            print(f"{name:8s} 噪声底 {_diff(first, second)} px")
        return 0

    if "--write" in sys.argv:
        OUT.mkdir(parents=True, exist_ok=True)
        for name in THEMES:
            image = _render(app, name)
            path = OUT / f"{name}.png"
            image.save(str(path))
            print(f"{name:8s} -> {path.name} {path.stat().st_size} B")
        return 0

    # --check
    failed = []
    for name in THEMES:
        path = OUT / f"{name}.png"
        if not path.is_file():
            print(f"{name:8s} 缺基线 {path}")
            return 1
        from PySide6.QtGui import QImage

        baseline = QImage(str(path))
        current = _render(app, name)
        diff = _diff(baseline, current)
        floor = NOISE_FLOOR.get(name, 0)
        flag = "" if diff <= floor else "  ← 超过噪声底"
        if diff > floor:
            failed.append(name)
        print(f"{name:8s} 差异像素 {diff}（噪声底 {floor}）{flag}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
