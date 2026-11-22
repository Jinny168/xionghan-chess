"""终局副作用的失败路径：**报错不能变成静默，也不能变成定时器里的死循环**。

`_settle_finished()` 跑在 `refresh()` 里，而 `refresh()` 是 250ms 定时器槽。
这里的两个副作用（战绩落盘、自动存档）都会写盘，磁盘满 / 只读 / 杀软锁文件
都会抛异常。异常一旦穿出 `refresh()`：

- 哨兵不置位 → 下一 tick 继续重试 → **每 250ms 抛一次**；
- 同一函数后面的「结果弹窗」永远走不到 → 用户看到的是「终局什么都不发生」。

所以本文件钉住两条契约：

1. 战绩落盘失败 → 有 error 提示、**终局弹窗照常出现**、哨兵置位（不再重试）；
2. 自动存档失败 → 有 error 提示（只提示一次，不刷屏）、哨兵**不**置位（允许重试），
   成功后立即停止重试。
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="MainWindow 依赖 PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from xionghan_chess.core.model import Color  # noqa: E402
from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def silent_dialogs(monkeypatch: pytest.MonkeyPatch) -> None:
    """不让任何模态框把 offscreen 测试挂住。"""
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    monkeypatch.setattr(appmod, "show_result_dialog", staticmethod(lambda *a, **k: False))


@pytest.fixture()
def window(monkeypatch: pytest.MonkeyPatch, tmp_path, qt_app: QApplication):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    theme.load_bundled_fonts()
    win = appmod.MainWindow()
    win.config["language"] = "zh-CN"
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


# --------------------------------------------------------------------------- #
# 项 1：record_result 失败
# --------------------------------------------------------------------------- #


def test_record_result_failure_does_not_block_result_dialog(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """战绩落盘抛 OSError 时：弹窗照常出现、哨兵置位、只记一次、有 error 提示。"""
    window.config["autosave"] = False
    dialogs: list[int] = []
    monkeypatch.setattr(appmod, "show_result_dialog", staticmethod(lambda *a, **k: dialogs.append(1) or False))
    attempts: list[int] = []

    def boom(*args, **kwargs):
        attempts.append(1)
        raise OSError("disk full")

    monkeypatch.setattr(appmod, "record_result", boom)
    notes: list[tuple[str, str]] = []
    monkeypatch.setattr(window, "notify", lambda text, level="info", timeout_ms=0: notes.append((text, level)))

    window.game.resign(Color.RED)
    for _ in range(5):
        window.refresh()

    assert len(dialogs) == 1, "战绩落盘失败吞掉了终局弹窗 —— 用户看不到任何结果"
    assert window._stats_recorded is True, "失败也必须置位，否则 250ms 定时器会无限重试"
    assert len(attempts) == 1, f"失败后仍在重试：{len(attempts)} 次"
    assert any(level == "error" for _, level in notes), f"失败没有 error 级提示：{notes}"


def test_record_result_real_write_failure_does_not_escape_refresh(
    window, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """真实 `record_result` 的写盘失败路径（目录建不出来）也不能穿出 refresh()。"""
    from xionghan_chess.desktop import storage

    window.config["autosave"] = False
    # 用一个**普通文件**当父目录：mkdir(parents=True) 会抛 NotADirectoryError(OSError)。
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(storage, "statistics_path", lambda: blocker / "statistics.json")

    window.game.resign(Color.RED)
    # 不抛异常即为通过：refresh() 是定时器槽，异常穿出就是每 250ms 报错一次。
    for _ in range(3):
        window.refresh()
    assert window._stats_recorded is True


# --------------------------------------------------------------------------- #
# 项 2：自动存档失败
# --------------------------------------------------------------------------- #


def test_autosave_failure_is_reported_and_retried(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """首次 TypeError（序列化层，不是 OSError）也要捕获，并允许下一轮重试。"""
    window.config["autosave"] = True
    monkeypatch.setattr(appmod, "record_result", lambda *a, **k: None)
    attempts: list[int] = []

    def flaky(game):
        attempts.append(1)
        if len(attempts) == 1:
            raise TypeError("not JSON serializable")
        return Path("memory://autosave")

    monkeypatch.setattr(appmod, "autosave_game", flaky)
    notes: list[tuple[str, str]] = []
    monkeypatch.setattr(window, "notify", lambda text, level="info", timeout_ms=0: notes.append((text, level)))

    window.game.resign(Color.RED)
    window.refresh()
    assert len(attempts) == 1
    assert window._autosaved is False, "失败不能置位，否则永远不会重试"
    assert len([1 for _, level in notes if level == "error"]) == 1

    window.refresh()
    assert len(attempts) == 2, "失败后应当重试"
    assert window._autosaved is True, "成功后应停止重试"

    window.refresh()
    assert len(attempts) == 2, "成功后不该再写盘"


def test_repeated_autosave_failures_do_not_spam_feedback(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """每 250ms 重试但不能每 250ms 弹一次 error（否则反馈条等于刷屏噪声）。"""
    window.config["autosave"] = True
    monkeypatch.setattr(appmod, "record_result", lambda *a, **k: None)
    attempts: list[int] = []

    def always_fail(game):
        attempts.append(1)
        raise OSError("read-only volume")

    monkeypatch.setattr(appmod, "autosave_game", always_fail)
    notes: list[tuple[str, str]] = []
    monkeypatch.setattr(window, "notify", lambda text, level="info", timeout_ms=0: notes.append((text, level)))

    window.game.resign(Color.RED)
    for _ in range(10):
        window.refresh()

    assert len(attempts) == 10, "应当每一轮都重试"
    error_notes = [text for text, level in notes if level == "error"]
    assert len(error_notes) == 1, f"失败提示刷屏了：{error_notes}"


def test_config_can_disable_autosave(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """`autosave=False` 时不该尝试写盘（既有行为，防这次改动回退）。"""
    window.config["autosave"] = False
    monkeypatch.setattr(appmod, "record_result", lambda *a, **k: None)
    attempts: list[int] = []
    monkeypatch.setattr(appmod, "autosave_game", lambda game: attempts.append(1))
    window.game.resign(Color.RED)
    window.refresh()
    assert attempts == []
