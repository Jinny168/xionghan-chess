"""音效失败上报单测（问题 P1-S）。

原来 `DesktopAudio` 不订阅任何状态信号：文件缺失或格式不支持时只是「没有声音」，
玩家以为游戏本来就没音效，开发者也没有任何线索。现在失败会进 `failures`
并通过 `on_failure` 通知界面。

音频设备在 CI/offscreen 下不一定可用，所以这里不测「真的响不响」，只测
**失败被记录、被去重、被翻译成一句人话**——这才是 P1-S 要的。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="audio 依赖 QtMultimedia")

from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.desktop import audio as audio_module  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def player(qt_app: QApplication) -> audio_module.DesktopAudio:
    instance = audio_module.DesktopAudio()
    instance.failures.clear()          # 不关心构造期是否有设备相关噪声
    instance.on_failure = None
    return instance


def test_failures_container_exists(player: audio_module.DesktopAudio) -> None:
    assert isinstance(player.failures, dict)
    assert player.failure_summary() == ""


def test_record_failure_reports_once(player: audio_module.DesktopAudio) -> None:
    seen: list[str] = []
    player.on_failure = seen.append
    player._record_failure("move", "文件缺失")
    player._record_failure("move", "文件缺失")
    player._record_failure("capture", "格式不支持")
    assert player.failures == {"move": "文件缺失", "capture": "格式不支持"}
    assert len(seen) == 2, "同一个音源只该报一次，否则每次播放都刷屏"


def test_player_error_is_recorded(player: audio_module.DesktopAudio) -> None:
    player._on_player_error(QMediaPlayer.Error.ResourceError, "找不到 OGG")
    assert player.failures["music"] == "找不到 OGG"


def test_player_no_error_is_ignored(player: audio_module.DesktopAudio) -> None:
    player._on_player_error(QMediaPlayer.Error.NoError, "")
    assert "music" not in player.failures


def test_player_error_without_message_still_reported(player: audio_module.DesktopAudio) -> None:
    player._on_player_error(QMediaPlayer.Error.FormatError, "")
    assert "music" in player.failures and player.failures["music"]


def test_summary_lists_every_failure(player: audio_module.DesktopAudio) -> None:
    player._record_failure("move", "文件缺失")
    player._record_failure("check", "格式不支持")
    summary = player.failure_summary()
    assert "部分音效无法播放" in summary
    assert "check" in summary and "move" in summary


def test_signals_are_actually_connected() -> None:
    """结构守卫：状态信号必须真的被订阅，否则上面的记录逻辑永远不会被触发。"""
    source = Path(audio_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    connected = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "connect":
            target = node.func.value
            if isinstance(target, ast.Attribute):
                connected.add(target.attr)
    assert "statusChanged" in connected, connected
    assert "errorOccurred" in connected, connected
