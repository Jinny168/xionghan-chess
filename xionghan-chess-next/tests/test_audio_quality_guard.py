"""音频档位守卫：一律 44.1kHz，且不存在"22k 低档"的残留。

## 为什么需要它

用户已定案（2026-11-09）：**不设双档，一律 44.1k，适用范围含 BGM，留高保真的**。
这条决定有三类静默失败方式，都必须变成可执行断言：

1. **有人重新生成 `fc_*` 音效时用了 22.05k**（体积小一半，听感在笔电喇叭上几乎无差）——
   听感是人工项，能自动化的只有"采样率必须是 44100"；
2. **有人把"双档"方案做了一半**：留下 `*_22k.wav` 或 `sound_quality` 开关，但没接上 UI/
   配置——下次重构时会被当成"死文件"清理掉，或反过来复活一个用户已经否掉的方案；
3. **BGM 被换成低码率**：体积门禁（`test_web_audio_assets.py` 的 8.5 MiB）只能拦住
   "变大"，拦不住"从 128k 降到 64k 换更多时长"。

本文件只看磁盘事实，不启动音频设备，CI 上必跑。
"""

from __future__ import annotations

import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOUNDS = ROOT / "src" / "xionghan_chess" / "desktop" / "resources" / "sounds"

# 用户定案：fc 音效固定 44.1kHz（BGM 的 mp3 128k 由 test_web_audio_assets.py 钉）。
FC_EFFECTS = ("fc_victory_sound.wav", "fc_defeat_sound.wav")


def test_fc_effects_are_44100_hz() -> None:
    for name in FC_EFFECTS:
        path = SOUNDS / name
        assert path.is_file(), f"缺少音效：{path}"
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
        assert rate == 44100, (
            f"{name} 采样率 {rate} ≠ 44100 —— 用户已定案「一律 44.1k」，"
            "不要重新生成 22.05k 版本（听感差异在自动测试里抓不到，只能钉采样率）"
        )


def test_no_22k_assets_or_quality_switch_remains() -> None:
    """中止的"双档"方案不得留下任何可执行痕迹。"""
    leftovers = [path for path in ROOT.rglob("*_22k.wav") if ".git" not in path.parts and ".venv" not in path.parts]
    assert not leftovers, f"发现 22k 音效残留：{[str(p) for p in leftovers]}"

    for base in (ROOT / "src" / "xionghan_chess" / "desktop", ROOT / "web" / "js"):
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".js"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert "sound_quality" not in text, f"{path} 里还有 sound_quality 开关"
            assert "_22k" not in text, f"{path} 里还有 22k 分支"
