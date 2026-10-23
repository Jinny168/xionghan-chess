"""桌面版 offscreen 冒烟测试（阶段0 S0-E；阶段1 S1-9 增补）。

用途：在**无显示环境**（CI / 服务器 / SSH）里验证桌面端「能导入、能装配、能关闭」，
以及阶段 0/1 的关键修复不会回归。

用法：
    QT_QPA_PLATFORM=offscreen python scripts/desktop_smoke.py

为什么是 offscreen：PySide6 在 Linux/无显示环境需要 `QT_QPA_PLATFORM=offscreen`
（或 xvfb）才能创建 QApplication。

判据（全部可观测）：
  1. `xionghan_chess.desktop.app` 可导入        —— PySide6 / QtMultimedia 依赖齐全
  2. `QApplication` 可创建
  3. `MainWindow()` 可构造                     —— 这一步会跑完 _build() /
     load_bundled_fonts() / DesktopAudio() / new_game() 全装配链，是桌面端在
     打包或依赖变更后**最容易静默崩掉**的地方
  4. 关键装配在位（board / game / pool / 异步助手 / 两个 worker）
  5. 认输有二次确认（S0-D 修复的结构性守卫，防回归）
  6. S1-9：UI 重建后对局能接回（不重开、不重复记账）；只改界面类设置保留对局，
     改盘面类设置才重开
  7. 关闭不抛异常

退出码：0 = 通过；1 = 有检查项失败（每条都会打印）。
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import xionghan_chess.desktop.app as app  # noqa: E402


def _play_one_move(window) -> int:
    """在当前对局走一步（取第一个合法着法），返回走后的历史长度。"""
    legal = window.game.rules.legal_moves(window.game.state, window.game.state.turn)
    if legal:
        window.game.move(legal[0])
    return len(window.game.state.history)


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

    # ---- S1-9：设置不应无条件丢对局 ----
    played = _play_one_move(window)
    checks["S1-9 走了一步（前置）"] = played > 0

    window._reattach_game(window.game, (True, True, False))
    checks["S1-9 重建后对局保留"] = len(window.game.state.history) == played
    checks["S1-9 记账/存档哨兵保留"] = (window._stats_recorded, window._autosaved) == (True, True)
    checks["S1-9 规则类设置清单正确"] = set(app.MainWindow._GAME_BREAKING_KEYS) == {
        "profile", "rule_options", "initial_minutes"
    }

    # 真实行为：只改主题 -> 保留对局；改盘面 -> 重开（并在结束后还原用户配置）
    cfg_file = app.config_path()
    cfg_backup = cfg_file.read_bytes() if cfg_file.exists() else None
    try:
        theme_cfg = dict(window.config)
        theme_cfg["theme"] = "dark" if window.config.get("theme") != "dark" else "classic"
        window._apply_settings(theme_cfg)
        checks["S1-9 只改主题保留对局"] = len(window.game.state.history) == played

        profile_cfg = dict(window.config)
        profile_cfg["profile"] = "traditional" if window.config.get("profile") != "traditional" else "desktop_complete"
        window._apply_settings(profile_cfg)
        checks["S1-9 改盘面重开对局"] = len(window.game.state.history) == 0
    finally:
        if cfg_backup is None:
            cfg_file.unlink(missing_ok=True)
        else:
            cfg_file.write_bytes(cfg_backup)

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
