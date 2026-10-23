from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect

from .ui import theme
from .texts import dl


class DesktopAudio:
    def __init__(self) -> None:
        # S1-1：资源路径统一走 theme.resource()，本模块不再自己拼 __file__ 相对路径
        # （audio.py 若被搬位置，旧写法会静默指到不存在的目录，音效全部静音而不报错）。
        root = theme.resource("sounds")
        files = {
            "select": "choose.wav", "move": "drop.wav", "capture": "eat.wav",
            "check": "warn.wav", "win": "fc_victory_sound.wav",
            "lose": "fc_defeat_sound.wav", "button": "button.wav",
        }
        # P1-S：失败要能说出来。此前没有订阅任何状态信号 —— 文件缺失或格式不支持时
        # 只是「没有声音」，玩家和开发者都无从判断。现在把失败收集到 `failures`，
        # 并可通过 `on_failure` 回调让界面提示一次。
        self.failures: dict[str, str] = {}
        self.on_failure: Callable[[str], None] | None = None
        self.effects: dict[str, QSoundEffect] = {}
        for name, filename in files.items():
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(root / filename)))
            effect.statusChanged.connect(lambda name=name: self._on_effect_status(name))
            self.effects[name] = effect
        # 阶段1 S1-5：BGM 由无压缩 WAV 换成 OGG/Vorbis（74.88 MB -> 5.98 MB，省 68.90 MB）。
        # 依据 Qt 官方文档：QMediaPlayer 支持压缩格式；而短音效走 QSoundEffect，
        # 官方要求"低延迟播放未压缩音频（通常 WAV）"，故 sounds/ 下其余 wav 不动。
        self.music_files = {"fc": root / "fc_background_sound.ogg", "qq": root / "qq_background_sound.ogg"}
        self.output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.output)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.player.errorOccurred.connect(self._on_player_error)
        self.enabled = True
        self.music_enabled = False
        self.music_style = "fc"
        self.sound_volume = 70
        self.music_volume = 40

    # ---- P1-S：失败收集与上报 ----
    def _record_failure(self, key: str, reason: str) -> None:
        """同一个音源只报一次，避免每次播放都刷屏。"""
        if key in self.failures:
            return
        self.failures[key] = reason
        if self.on_failure is not None:
            self.on_failure(f"{key}: {reason}")

    def _on_effect_status(self, name: str) -> None:
        effect = self.effects.get(name)
        if effect is not None and effect.status() is QSoundEffect.Status.Error:
            self._record_failure(name, dl("音效加载/播放失败（文件缺失或格式不支持）"))

    def _on_player_error(self, error: QMediaPlayer.Error, message: str) -> None:
        if error != QMediaPlayer.Error.NoError:
            self._record_failure("music", message or dl("背景音乐加载失败"))

    def failure_summary(self) -> str:
        """给界面用的一句话；没有失败返回空串。"""
        if not self.failures:
            return ""
        return dl("部分音效无法播放：") + "、".join(sorted(self.failures))

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
