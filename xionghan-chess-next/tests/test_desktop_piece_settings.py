"""设置页「棋子美术风格」下拉的契约（`piece_render` 的入口与回退项）。

## 挡的是什么

`piece_render` 是「字形 / 位图」的开关，默认 `glyph`。它必须满足三条：

1. **不能是单向门**：下拉第一项「书法字形（默认）」要能把用户从 image 切回 glyph，
   且 **`piece_style` 保留原值**（否则用户切一次就丢掉自己的风格偏好）。
2. **选风格即启用**：选中「传统/现代/卡通」后 `piece_render` 必须变 `image`，
   否则「选了风格但棋盘没变」就是假预览。
3. **整套风格资源缺失时该项不可选**（`web/assets/pieces/<style>` 被改名/未拉 LFS），
   与图谱里「该风格资源缺失」一致；棋盘另有字形回退，所以程序不崩。

第 3 条用打桩 `piece_assets.preload` 模拟「目录缺失」，不需要真的改磁盘。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="SettingsDialog 依赖 PySide6")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from xionghan_chess.desktop.ui import piece_assets, theme  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import GLYPH_STYLE_DATA, SettingsDialog  # noqa: E402


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
    """`SettingsDialog.value()` 会读 `parent().config`，这里给一个最小替身。"""

    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config


def test_dropdown_first_item_is_the_glyph_fallback(qt_app: QApplication) -> None:
    config = _config(piece_render="image", piece_style="cartoon")
    parent = _Parent(config)          # 必须持有引用：父控件被 GC 会连带销毁对话框
    dialog = SettingsDialog(config, parent)
    assert dialog.piece_style.itemData(0) == GLYPH_STYLE_DATA
    assert dialog.piece_style.currentData() == "cartoon", "image 态应落在当前风格上"
    dialog.deleteLater()


def test_glyph_choice_maps_to_the_glyph_style(qt_app: QApplication) -> None:
    parent = _Parent(_config(piece_style="cartoon", piece_render="image"))
    dialog = SettingsDialog(parent.config, parent)
    index = dialog.piece_style.findData(GLYPH_STYLE_DATA)
    dialog.piece_style.setCurrentIndex(index)
    value = dialog.value()
    assert value["piece_render"] == "glyph"
    # 四值互斥：选了「书法字形」就等于 style="glyph"（不再保留旧美术偏好）
    assert value["piece_style"] == "glyph"
    dialog.deleteLater()


def test_choosing_a_style_enables_image(qt_app: QApplication) -> None:
    parent = _Parent(_config(piece_style="traditional", piece_render="glyph"))
    dialog = SettingsDialog(parent.config, parent)
    dialog.piece_style.setCurrentIndex(dialog.piece_style.findData("modern"))
    value = dialog.value()
    assert value["piece_render"] == "image"
    assert value["piece_style"] == "modern"
    dialog.deleteLater()


def test_missing_style_resources_disable_that_option(
        qt_app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    real = piece_assets.preload
    monkeypatch.setattr(piece_assets, "preload",
                        lambda style=None: 0 if style == "cartoon" else real(style))
    config = _config()
    parent = _Parent(config)
    dialog = SettingsDialog(config, parent)
    model = dialog.piece_style.model()
    index = dialog.piece_style.findData("cartoon")
    assert index > 0
    assert not model.item(index).isEnabled(), "缺资源的风格必须灰显"
    assert model.item(dialog.piece_style.findData("traditional")).isEnabled()
    dialog.deleteLater()
