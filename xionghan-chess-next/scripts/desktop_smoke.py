"""桌面版 offscreen 冒烟测试（阶段0 S0-E）。

用途：在**无显示环境**（CI / 服务器 / SSH）里验证桌面端「能导入、能装配、能关闭」。
桌面端此前零自动化护栏（tests/ 对 desktop 符号 grep 0 命中），这个脚本是它的第一道网。

用法：
    QT_QPA_PLATFORM=offscreen python scripts/desktop_smoke.py

为什么是 offscreen：PySide6 在 Linux/无显示环境需要 `QT_QPA_PLATFORM=offscreen`
（或 xvfb）才能创建 QApplication。GitHub Actions 的 windows-latest 有桌面会话，
设 offscreen 更快也更稳。

判据（全部可观测，不靠日志）：
  1. `xionghan_chess.desktop.app` 可导入        —— PySide6 / QtMultimedia 依赖齐全
  2. `QApplication` 可创建
  3. `MainWindow()` 可构造                     —— 这一步会跑完 _build() /
     load_bundled_fonts() / DesktopAudio() / new_game() 全装配链，是桌面端在
     打包或依赖变更后**最容易静默崩掉**的地方
  4. 关键装配在位（board / game / pool / 异步助手 / 两个 worker）
  5. 认输有二次确认（S0-D 修复的结构性守卫，防回归）
  6. 关闭不抛异常

退出码：0 = 通过；1 = 有检查项失败（每条都会打印）。
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import xionghan_chess.desktop.app as app  # noqa: E402


def main() -> int:
    qt = QApplication(sys.argv[:1])
    window = app.MainWindow()

    resign_source = inspect.getsource(app.MainWindow.resign_game)
    draw_source = inspect.getsource(app.MainWindow.draw_game)

    checks: dict[str, bool] = {
        "MainWindow 构造（全装配链）": window is not None,
        "棋盘挂载": getattr(window, "board", None) is not None,
        "对局已开局": window.game is not None and window.game.state is not None,
        "线程池就绪": getattr(window, "pool", None) is not None,
        "异步 HTTP 助手 _request_json_async": hasattr(window, "_request_json_async"),
        "HttpWorker 存在（建连异步化 S0-C）": hasattr(app, "HttpWorker"),
        "AnalysisWorker 存在（分析异步化 S0-C）": hasattr(app, "AnalysisWorker"),
        "认输有二次确认（S0-D 防回归）": "QMessageBox.question" in resign_source,
        "提和仍有确认（S0-D 对照组）": "QMessageBox.question" in draw_source,
    }

    window.close()
    window.deleteLater()
    qt.processEvents()

    failed = [name for name, ok in checks.items() if not ok]
    for name, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FAIL'} {name}")

    if failed:
        print(f"DESKTOP_SMOKE_FAIL: {failed}")
        return 1
    print("DESKTOP_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
