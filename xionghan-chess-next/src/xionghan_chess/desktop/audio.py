from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect


class DesktopAudio:
    def __init__(self) -> None:
        root = Path(__file__).resolve().parent / "resources" / "sounds"
        files = {
            "select": "choose.wav", "move": "drop.wav", "capture": "eat.wav",
            "check": "warn.wav", "win": "fc_victory_sound.wav",
            "lose": "fc_defeat_sound.wav", "button": "button.wav",
        }
        self.effects: dict[str, QSoundEffect] = {}
        for name, filename in files.items():
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(root / filename)))
            self.effects[name] = effect
        # 阶段1 S1-5：BGM 由无压缩 WAV 换成 OGG/Vorbis（74.88 MB -> 5.98 MB，省 68.90 MB）。
        # 依据 Qt 官方文档：QMediaPlayer 支持压缩格式；而短音效走 QSoundEffect，
        # 官方要求"低延迟播放未压缩音频（通常 WAV）"，故 sounds/ 下其余 wav 不动。
        self.music_files = {"fc": root / "fc_background_sound.ogg", "qq": root / "qq_background_sound.ogg"}
        self.output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.output)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.enabled = True
        self.music_enabled = False
        self.music_style = "fc"
        self.sound_volume = 70
        self.music_volume = 40

    def configure(self, config: dict) -> None:
        self.enabled = bool(config.get("sound", True))
        self.music_enabled = bool(config.get("music", False))
        self.music_style = str(config.get("music_style", "fc"))
        self.sound_volume = int(config.get("sound_volume", 70))
        self.music_volume = int(config.get("music_volume", 40))
        for effect in self.effects.values():
            effect.setVolume(self.sound_volume / 100)
        self.output.setVolume(self.music_volume / 100)
        if self.music_enabled:
            self.play_music()
        else:
            self.player.stop()

    def play(self, name: str) -> None:
        if self.enabled and name in self.effects:
            self.effects[name].play()

    def play_music(self) -> None:
        source = QUrl.fromLocalFile(str(self.music_files.get(self.music_style, self.music_files["fc"])))
        if self.player.source() != source:
            self.player.setSource(source)
        self.player.play()

    def stop(self) -> None:
        self.player.stop()
