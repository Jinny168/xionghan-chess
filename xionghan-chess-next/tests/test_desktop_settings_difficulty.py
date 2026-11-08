"""设置页「难度」下拉遇到未知档位时的行为（并档前的预埋守卫）。

## 为什么单开一条

`SettingsDialog` 原来是 `setCurrentIndex(max(0, findData(config["difficulty"])))`：
配置里出现**不在列表里的档位**（旧版本写下的值、用户手改 `settings.json`、
将来把「高级/大师」并成一档）时，`findData` 返回 -1、`max(0, -1)` 变成 0 ——
下拉静默停在「入门」，用户点「确定」就把难度**无声降级**成最弱的一档，且界面上
看不出任何异样。

现在的行为：显式回落到默认档（中级），并把原值作为**不可选的提示条目**插在下拉顶部，
用户一眼能看到「你原来的档位不在这份列表里」。这条文件钉住的就是这个差异。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="SettingsDialog 依赖 PySide6")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import SettingsDialog  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def fonts(qt_app: QApplication) -> None:
    theme.load_bundled_fonts()


def _config(**overrides: object) -> dict:
    base = {
        "profile": "desktop_complete", "language": "zh-CN", "difficulty": "medium",
        "human_color": "red", "initial_minutes": 20, "sound": True, "sound_volume": 70,
        "theme": "classic", "font": "system", "background": "none",
        "piece_style": "traditional", "piece_render": "glyph",
    }
    base.update(overrides)
    return base


class _Parent(QWidget):
    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config


def test_known_difficulty_selects_that_entry(qt_app: QApplication) -> None:
    config = _config(difficulty="hard")
    parent = _Parent(config)
    dialog = SettingsDialog(config, parent)
    assert dialog._unknown_difficulty is False
    assert dialog.difficulty.currentData() == "hard"
    assert dialog.value()["difficulty"] == "hard"
    dialog.deleteLater()


def test_unknown_difficulty_falls_back_to_default_and_shows_the_raw_value(
        qt_app: QApplication) -> None:
    """未知档位 → 选默认（medium），并在下拉里显示原值且**不可选**。"""
    config = _config(difficulty="legendary")
    parent = _Parent(config)
    dialog = SettingsDialog(config, parent)
    assert dialog._unknown_difficulty is True
    assert dialog.difficulty.currentData() == "medium", "未知档位必须显式回落到默认"
    placeholder = dialog.difficulty.model().item(0)
    assert placeholder is not None and not placeholder.isEnabled(), "原值条目应当灰显"
    assert "legendary" in placeholder.text(), "提示里要带上原来的值，否则用户不知道发生了什么"
    assert dialog.value()["difficulty"] == "medium"
    dialog.deleteLater()


def test_unknown_difficulty_never_silently_becomes_beginner(qt_app: QApplication) -> None:
    """回归守卫：绝不能因为 `findData` 返回 -1 就落到第 0 项「入门」。"""
    config = _config(difficulty="__nope__")
    parent = _Parent(config)
    dialog = SettingsDialog(config, parent)
    assert dialog.difficulty.currentData() != "beginner"
    dialog.deleteLater()
