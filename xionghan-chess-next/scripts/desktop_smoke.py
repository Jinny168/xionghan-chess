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

CI 取证（run #121/#122 教训）：冒烟是「先收集 checks 最后统一打印」结构，Qt C++
层一旦崩死（无 Python traceback）日志尾部只剩 Qt 原生警告，无法定位崩点。因此：
  - **增量探针**：每个关键步骤执行前先 `▶ <步骤>` 打到 stdout（flush），CI 下一跑
    尾部最后一个 ▶ 就是崩点，远程即可二分，不必再猜。
  - **回放降级**：runner 无音频设备，QSoundEffect.play() 走到音频后端只会得到
    "playback of this format is not supported"（#122 出现 6 次）且在其后的某个
    C++ 调用里崩死；Windows 同代码零警告完整跑完。装配断言（QSoundEffect /
    QAudioOutput / QMediaPlayer 真实构造）**保留**——那是桌面端最易静默崩的装配链；
    仅把**回放**降级为「不崩即过」：无设备环境下回放效果本就不可断言，理由见
    main() 内注释。
"""

from __future__ import annotations

import inspect
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtGui import QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import xionghan_chess.desktop.app as app  # noqa: E402
from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.profiles import PROFILES  # noqa: E402
from xionghan_chess.core.puzzles import load_puzzles  # noqa: E402
from xionghan_chess.core.storage import game_from_document  # noqa: E402
from xionghan_chess.desktop.config import config_path, load_config  # noqa: E402
from xionghan_chess.desktop.ui import workers as ui_workers  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import (  # noqa: E402
    DocumentDialog,
    GameLibraryDialog,
    HandicapDialog,
    ReplayDialog,
    SettingsDialog,
    TrainingDialog,
)


def _probe(label: str) -> None:
    """增量探针：步骤执行前打点（flush），CI 崩死时日志尾部最后一个 ▶ 即崩点。"""
    print(f"  ▶ {label}", flush=True)


def _play_one_move(window) -> int:
    """在当前对局走一步（取第一个合法着法），返回走后的历史长度。"""
    legal = window.game.rules.legal_moves(window.game.state, window.game.state.turn)
    if legal:
        window.game.move(legal[0])
    return len(window.game.state.history)


def main() -> int:
    # 冒烟必须跑在**隔离的用户目录**里。此前它直接用真实 `%APPDATA%`：测试中途会
    # 改主题/盘型来验证「改设置要不要重开对局」，虽然结尾有备份还原，但只要中途
    # 异常退出，用户真实配置就被留在了测试值上 —— 有人的默认主题变成暗黑就是这么来的。
    # 放到临时目录后，测试怎么折腾都碰不到用户的 settings.json。
    os.environ["APPDATA"] = tempfile.mkdtemp(prefix="xionghan-smoke-")

    # CI 无音频设备下的回放降级（详见模块 docstring「CI 取证」节）：DesktopAudio
    # 的**装配**保持真实（MainWindow 构造仍会 new 出 QSoundEffect ×7 /
    # QAudioOutput / QMediaPlayer 并 setSource——装配崩依旧红），仅把类方法
    # `play` 换成记录型空操作，让走子路径不再真把音频推向无设备的后端。
    # 理由：#122 实测 6 次 "playback of this format is not supported" 后在 C++
    # 层崩死且无 traceback，同代码 Windows 零警告完整跑完——崩面取决于 CI 镜像
    # 的音频后端而非对局逻辑，不应由走子冒烟背；无设备下回放效果本就不可断言。
    def _no_play(self, name: str) -> None:  # noqa: ARG001
        _probe(f"音频回放降级命中（{name}）")

    app.DesktopAudio.play = _no_play  # type: ignore[method-assign]
    _probe("QApplication 创建")
    qt = QApplication(sys.argv[:1])
    _probe("MainWindow() 构造（全装配链，含 DesktopAudio/QSoundEffect）")
    window = app.MainWindow()

    _probe("读取 resign/draw/check_updates 源码")
    resign_source = inspect.getsource(app.MainWindow.resign_game)
    draw_source = inspect.getsource(app.MainWindow.draw_game)
    update_source = inspect.getsource(app.MainWindow.check_updates)
    # 菜单项要真的挂在菜单栏上，不能只在源码里出现过 —— 逐个子菜单收标题。
    _probe("扫描菜单树")
    menu_titles: set[str] = set()
    for top_action in window.menuBar().actions():
        submenu = top_action.menu()
        if submenu is not None:
            menu_titles.update(action.text() for action in submenu.actions())

    checks: dict[str, bool] = {
        "MainWindow 构造（全装配链）": window is not None,
        "棋盘挂载": getattr(window, "board", None) is not None,
        "对局已开局": window.game is not None and window.game.state is not None,
        "线程池就绪": getattr(window, "pool", None) is not None,
        "异步 HTTP 助手 _request_json_async": hasattr(window, "_request_json_async"),
        "HttpWorker 存在（建连异步化 S0-C）": hasattr(app, "HttpWorker"),
        # AnalysisWorker 的归宿是 ui/workers.py（S0-C 搬入）；60d6602 的 ruff
        # 清理删掉了 app.py 里对它的未用再导出（app.py 从未使用它），冒烟从此
        # 改查真实模块，而不是绑在一个随时可被 lint 清理的再导出上。
        "AnalysisWorker 存在（分析异步化 S0-C）": hasattr(ui_workers, "AnalysisWorker"),
        "认输有二次确认（S0-D 防回归）": "QMessageBox.question" in resign_source,
        "提和仍有确认（S0-D 对照组）": "QMessageBox.question" in draw_source,
        # S2-3：更新检查必须**只查不装**。真自更新需要代码签名与回滚（S2-1），
        # 在那之前出现「自动下载/替换 exe」的代码就是越界，这里守一道。
        "更新检查在位（S2-3）": hasattr(window, "check_updates") and "检查更新" in menu_titles,
        "更新只开下载页、不自更新（S2-3）": callable(getattr(window, "check_updates", None))
        and "QDesktopServices.openUrl" in update_source
        and "QProcess" not in update_source,
    }

    # ---- S1-2：棋盘绘制必须真的能跑 ----
    # Qt 会吞掉事件处理器里的异常（只打印不抛），所以 offscreen 下 `show()` 并不能
    # 证明 paintEvent 是好的。这里直接拿一个真 QPainter 调它 —— 异常才会真的冒出来。
    # 这是 BoardWidget 从 app.py 搬到 ui/board_widget.py 后最容易断的地方。
    _probe("S1-2 paintEvent 直调（QPainter on QPixmap）")
    canvas = QPixmap(window.board.size())
    canvas.fill()
    painter = QPainter(canvas)
    try:
        window.board.paintEvent(painter)
        checks["S1-2 棋盘可绘制（paintEvent 直调）"] = True
    except Exception as exc:  # noqa: BLE001
        checks["S1-2 棋盘可绘制（paintEvent 直调）"] = False
        print(f"  paintEvent 异常: {exc!r}")
    finally:
        painter.end()

    # ---- S1-2：6 个对话框必须能构造 ----
    # 它们已搬到 ui/dialogs.py。冒烟只构造 MainWindow 的话，对话框里的漏 import
    # （GameState / BoardWidget / load_game / os 都真的漏过）要等用户点开才炸。
    cfg = load_config()
    sample_game = Game(PROFILES["desktop_complete"])
    dialog_builders = {
        "DocumentDialog": lambda: DocumentDialog("标题", "正文", None),
        "SettingsDialog": lambda: SettingsDialog(cfg, None),
        "HandicapDialog": lambda: HandicapDialog("desktop_complete", {}, None, None),
        "ReplayDialog": lambda: ReplayDialog(sample_game, cfg, None),
        "TrainingDialog": lambda: TrainingDialog(None),
        "GameLibraryDialog": lambda: GameLibraryDialog(Path(tempfile.mkdtemp()), cfg, None),
    }
    for name, build in dialog_builders.items():
        _probe(f"S1-2 构造对话框 {name}")
        try:
            dialog = build()
            dialog.deleteLater()
            checks[f"S1-2 对话框可构造：{name}"] = True
        except Exception as exc:  # noqa: BLE001
            checks[f"S1-2 对话框可构造：{name}"] = False
            print(f"  {name} 构造异常: {exc!r}")

    # ---- S1-9：设置不应无条件丢对局 ----
    _probe("S1-9 走一步（真实 move + 音频 play 降级路径）")
    played = _play_one_move(window)
    checks["S1-9 走了一步（前置）"] = played > 0

    _probe("S1-9 _reattach_game（UI 重建）")
    window._reattach_game(window.game, (True, True, False))
    checks["S1-9 重建后对局保留"] = len(window.game.state.history) == played
    checks["S1-9 记账/存档哨兵保留"] = (window._stats_recorded, window._autosaved) == (True, True)
    checks["S1-9 规则类设置清单正确"] = set(app.MainWindow._GAME_BREAKING_KEYS) == {
        "profile",
        "rule_options",
        "initial_minutes",
    }

    # 真实行为：只改主题 -> 保留对局；改盘面 -> 重开（并在结束后还原用户配置）
    cfg_file = config_path()
    cfg_backup = cfg_file.read_bytes() if cfg_file.exists() else None
    try:
        theme_cfg = dict(window.config)
        theme_cfg["theme"] = "dark" if window.config.get("theme") != "dark" else "classic"
        _probe("S1-9 改主题 _apply_settings（含试听 play 降级）")
        window._apply_settings(theme_cfg)
        checks["S1-9 只改主题保留对局"] = len(window.game.state.history) == played

        profile_cfg = dict(window.config)
        profile_cfg["profile"] = "traditional" if window.config.get("profile") != "traditional" else "desktop_complete"
        _probe("S1-9 改盘面 _apply_settings（重开对局）")
        window._apply_settings(profile_cfg)
        checks["S1-9 改盘面重开对局"] = len(window.game.state.history) == 0
    finally:
        if cfg_backup is None:
            cfg_file.unlink(missing_ok=True)
        else:
            cfg_file.write_bytes(cfg_backup)

    # ---- S2-7 配套：训练模式必须真的判对错 ----
    # 只断言「有 _judge_puzzle 方法」挡不住接线断裂：若 human_move 忘了调它，
    # 玩家走错也照样过。所以这里真进一道题、真走一手错棋，验证三件事：
    # 棋被退回题面、cursor 不动、而且没有把错棋记进历史。
    try:
        puzzle = load_puzzles()[0]
        solution = puzzle.solution[0]

        class _FakeTrainingDialog:  # 只回答「用户选了哪道题」，其余走真实 show_training
            def __init__(self, parent=None) -> None:
                self.selected_game = game_from_document(puzzle.document)
                self.selected_puzzle = puzzle

            def exec(self) -> bool:
                return True

        real_dialog, real_info = app.TrainingDialog, app.QMessageBox.information
        app.TrainingDialog = _FakeTrainingDialog
        app.QMessageBox.information = staticmethod(lambda *a, **k: None)
        try:
            # P1-L：训练题自带 profile，绝不能写进用户的全局配置。
            profile_before = window.config.get("profile")
            _probe("S2-7 show_training（进题）")
            window.show_training()
            checks["P1-L 训练不改全局 profile"] = window.config.get("profile") == profile_before
            prefix = len(window.game.state.history)
            wrong = next(
                move
                for move in window.game.rules.legal_moves(window.game.state)
                if (move.source.row, move.source.col, move.target.row, move.target.col)
                != (solution.source.row, solution.source.col, solution.target.row, solution.target.col)
            )
            _probe("S2-7 答错 human_move")
            window.human_move(wrong)
            checks["S2-7 答错会退回题面"] = len(window.game.state.history) == prefix
            checks["S2-7 答错不计入进度"] = window.puzzle_session is not None and window.puzzle_session.cursor == 0
            _probe("S2-7 答对 human_move")
            window.human_move(solution)
            checks["S2-7 答对即过关"] = window.puzzle_session is None
        finally:
            app.TrainingDialog, app.QMessageBox.information = real_dialog, real_info
    except Exception as exc:  # noqa: BLE001
        checks["S2-7 训练判定端到端"] = False
        print(f"  训练判定异常: {exc!r}")

    _probe("关闭 + deleteLater + processEvents（teardown）")
    window.close()
    window.deleteLater()
    qt.processEvents()

    _probe("汇总打印")
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
