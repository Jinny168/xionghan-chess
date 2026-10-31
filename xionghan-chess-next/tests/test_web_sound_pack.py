"""「网页合成」音效包：时长、可复现、与 classic 不同、切包生效、老配置兼容。

参数来自投稿版 WebAudio 合成（见 `scripts/gen_web_sound_pack.py` 顶部表）。
wav 是**生成物**，所以这里既验"参数落地成什么音"，也验"重跑是否逐字节一致"。
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOUNDS = ROOT / "src" / "xionghan_chess" / "desktop" / "resources" / "sounds"
WEB = SOUNDS / "web"

# 目标时长（秒）与 ±5% 容差
EXPECTED = {
    "select": 0.07, "move": 0.11, "capture": 0.13, "check": 0.23,
    "win": 0.54, "lose": 0.56, "click": 0.035, "undo": 0.12,
}


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_eight_files_exist_with_expected_duration() -> None:
    for name, target in EXPECTED.items():
        path = WEB / f"{name}.wav"
        assert path.is_file(), f"缺少 {path.name}"
        actual = duration(path)
        assert abs(actual - target) <= target * 0.05, (
            f"{name}: {actual:.3f}s 与目标 {target}s 差超过 5%")


def test_regenerating_is_byte_identical() -> None:
    """固定种子：重跑必须逐字节一致，否则每次构建都会把仓库改脏。"""
    before = {name: sha(WEB / f"{name}.wav") for name in EXPECTED}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_web_sound_pack.py")],
                   check=True, capture_output=True)
    after = {name: sha(WEB / f"{name}.wav") for name in EXPECTED}
    assert before == after, "重跑后 sha256 变了 —— 随机种子没固定住"


def test_web_pack_differs_from_classic() -> None:
    """两个包的 move 必须是不同波形（同一事件换了音源才说明切包有意义）。"""
    assert sha(WEB / "move.wav") != sha(SOUNDS / "drop.wav")


def test_switching_pack_changes_sources(qt_app) -> None:
    from xionghan_chess.desktop.audio import DesktopAudio

    audio = DesktopAudio()
    assert audio.sound_pack == "classic"
    assert "undo" not in audio.effects, "classic 包不该有 undo（不借 warn 冒充）"
    assert audio.effects["move"].source().toLocalFile().endswith("drop.wav")

    audio.set_sound_pack("web", audition=False)
    assert audio.sound_pack == "web"
    assert audio.effects["move"].source().toLocalFile().replace("\\", "/").endswith("web/move.wav")
    assert "undo" in audio.effects


def test_legacy_config_without_pack_falls_back_to_classic(qt_app) -> None:
    from xionghan_chess.desktop.audio import DesktopAudio

    audio = DesktopAudio()
    audio.set_sound_pack("web", audition=False)
    audio.configure({})                       # 老配置：没有 sound_pack 键
    assert audio.sound_pack == "classic"


@pytest.fixture(scope="module")
def qt_app():
    pytest.importorskip("PySide6", reason="音效需要 Qt")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return app
