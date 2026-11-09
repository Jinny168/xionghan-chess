"""网页端音频资产守卫（S3-A3：两首 BGM 由 WAV 转 mp3 128k）。

## 为什么需要这个文件

`web/assets/sounds` 长期存着两首 BGM 的 WAV 副本（76.32 MiB），而桌面端早在 S1-5
就换成了 OGG。A2 测绘确认：三端音频共 83.89 MiB，其中 74.88 MiB 就是这两个副本。
A3 把 web 侧换成 mp3 128k（`76.32 → 7.92 MiB`）。

换格式的失败模式**全部是静默的**，所以必须有静态守卫：

1. **体积**：立项目标是「≤8MB」。没有断言，下一次有人往这里丢 wav 没人拦。
2. **魔数/参数**：只改扩展名不改文件（或反过来）时，`<audio>` 只会静默失败。
3. **引用一致性**：`web/js/app.js` 里写死的文件名必须真的存在于磁盘。
   网页端 `play().catch()` 会吞掉 404 —— 漏放文件等于没声音，且控制台什么都没有。
   这条是四者中最重要的一条（2026-11-09 实测：改文件名而忘记放文件时，页面完全无提示）。
4. **与桌面同名音效逐字节一致**：两套副本是历史遗留。A2 结论是**不做去重**
   （1.44 MiB / 1.7%，不值得引入构建期复制），但要求「漂移必须显形」。

## 刻意不做的事

- **不对 mp3 做「重跑编码逐字节一致」断言**。libmp3lame 的产物里带编码器版本串
  （实测 ID3 的 TSSE 帧写着 `Lavf63.1.102`），跨 ffmpeg 版本必然变字节，
  硬钉只会让每次升级工具链都红。`test_web_sound_pack.py` 那条断言只适用于
  纯标准库合成器（自己写 wave 头，逐字节可控），不适用于第三方编码器。
- 改为把**产物 sha256 + 时长 + 采样率钉成锚点**：要换文件，就得连锚点一起改，
  改的人必然读到这段注释。
- **不检查 mp3 是否「听起来对」**。听感是人工项（见 A2 报告 §六），
  能自动化的只有「文件没被换错」。

## 关于时长断言的口径

本文件自带一个最小 MPEG-1/2 Layer III 帧头解析器（只用标准库），靠**数帧**算时长。
它会多算 Xing/Info 帧与 LAME 尾部填充，实测比 `ffprobe` 长约 0.07s
（190.067 vs 190.000；234.456 vs 234.389）—— 所以容差取 0.5%，不是 0.1%。
0.5% 对「文件被替换/截断」依然拦得住（换个文件时长差异远大于此）。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_SOUNDS = ROOT / "web" / "assets" / "sounds"
DESKTOP_SOUNDS = ROOT / "src" / "xionghan_chess" / "desktop" / "resources" / "sounds"
APP_JS = ROOT / "web" / "js" / "app.js"

# 8.5 MiB：现状 8,299,808 B（7.92 MiB），留 ~0.6 MB 余量给将来加音效。
MAX_TOTAL_BYTES = 8_912_896

# 锚点：换文件必须连这里一起改。sha256 为 2026-11-09 实测产物。
BGM_ANCHORS = {
    "fc_background_sound.mp3": {
        "sha256": "7696d93f90b6a9923e2af7527a99bb091ca9d01fe01a2c9cdf0a92f77cd687d0",
        "sample_rate": 44100,
        "channels": 2,
        "bitrate": 128000,
        "duration": 190.000,
    },
    "qq_background_sound.mp3": {
        "sha256": "8a6dd5a79a7c2feb4f4366f23622ca9ec2736a6d474d5a87270b5f42fe902819",
        "sample_rate": 48000,
        "channels": 2,
        "bitrate": 128000,
        "duration": 234.389,
    },
}

# 与桌面同名、逐字节相同的音效（原 8 个，check.wav 作为 0 引用的死文件已删 → 7 个）。
CLASSIC_SHARED = (
    "button.wav", "choose.wav", "drop.wav", "eat.wav",
    "fc_defeat_sound.wav", "fc_victory_sound.wav", "warn.wav",
)

_AUDIO_NAME = re.compile(r"[A-Za-z0-9_-]+\.(?:wav|mp3|ogg)")

# ── 最小 MPEG Layer III 帧头解析（只用标准库）───────────────────────────────
# 表索引 = bitrate_index / sample_rate_index，见 ISO/IEC 11172-3 & 13818-3。
_BITRATES_V1_L3 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
_BITRATES_V2_L3 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)
_SAMPLE_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}


def _id3v2_size(data: bytes) -> int:
    """ID3v2 头长度（含 10 字节头，含 footer 时再 +10）。ffmpeg 产物有 44 字节 TSSE 标签。"""
    if data[:3] != b"ID3":
        return 0
    size = 0
    for byte in data[6:10]:
        size = (size << 7) | (byte & 0x7F)
    return 10 + size + (10 if data[5] & 0x10 else 0)


def mp3_stream_info(path: Path) -> dict[str, int | float]:
    """数帧求时长。返回 sample_rate / channels / bitrate / duration（均取第一帧）。"""
    data = path.read_bytes()
    pos = _id3v2_size(data)
    frames = 0
    sample_rate = 0
    channels = 0
    bitrate_value = 0
    samples_per_frame = 0
    while pos + 4 <= len(data):
        b0, b1, b2, b3 = data[pos:pos + 4]
        if b0 != 0xFF or (b1 & 0xE0) != 0xE0:
            break                      # 帧序列结束（尾部 ID3v1 / 填充）
        version = (b1 >> 3) & 0x03      # 3=MPEG1 2=MPEG2 0=MPEG2.5 1=保留
        layer = (b1 >> 1) & 0x03        # 1=Layer III
        bitrate_index = (b2 >> 4) & 0x0F
        rate_index = (b2 >> 2) & 0x03
        padding = (b2 >> 1) & 0x01
        mode = (b3 >> 6) & 0x03
        if version == 1 or layer != 1 or bitrate_index in (0, 15) or rate_index == 3:
            break                      # 非法/自由码率/保留采样率
        mpeg1 = version == 3
        bitrate = (_BITRATES_V1_L3 if mpeg1 else _BITRATES_V2_L3)[bitrate_index] * 1000
        rate = _SAMPLE_RATES[version][rate_index]
        samples_per_frame = 1152 if mpeg1 else 576
        if not frames:                 # 以第一帧为准（CBR 全程一致）
            sample_rate = rate
            channels = 1 if mode == 3 else 2
            bitrate_value = bitrate
        frames += 1
        pos += (144 if mpeg1 else 72) * bitrate // rate + padding
    if not frames:
        raise AssertionError(f"{path.name} 里找不到合法的 MPEG Layer III 帧")
    return {
        "frames": frames,
        "sample_rate": sample_rate,
        "channels": channels,
        "bitrate": bitrate_value,
        "duration": frames * samples_per_frame / sample_rate,
    }


def sha256sum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── 1. 体积门禁 ───────────────────────────────────────────────────────────
def test_sound_pack_stays_under_budget() -> None:
    files = [p for p in WEB_SOUNDS.iterdir() if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    detail = "、".join(f"{p.name}={p.stat().st_size}" for p in sorted(files))
    assert total <= MAX_TOTAL_BYTES, (
        f"web/assets/sounds 共 {total} B = {total / 1024 / 1024:.2f} MiB，"
        f"超过门禁 {MAX_TOTAL_BYTES} B（8.5 MiB）—— 是不是又塞进 wav 了？明细：{detail}")


# ── 2. BGM 是真正的 mp3，且参数/时长/内容均为锚点值 ─────────────────────────
def test_bgm_files_are_real_mp3_with_pinned_params() -> None:
    for name, anchor in BGM_ANCHORS.items():
        path = WEB_SOUNDS / name
        assert path.is_file(), f"缺少 BGM：{path}"
        head = path.read_bytes()[:3]
        # ffmpeg+libmp3lame 会先写 ID3v2（实测 44 B，含 TSSE "Lavf…"），
        # 所以不能只认 0xFF 同步字；两种都接受，其余一律判失败。
        assert head == b"ID3" or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0), (
            f"{name} 开头是 {head!r}，既不是 ID3v2 也不是 MPEG 同步字 —— "
            "扩展名是 mp3 但内容不是（改名没改文件？还是误放了 wav/ogg？）")

        info = mp3_stream_info(path)
        assert info["sample_rate"] == anchor["sample_rate"], (
            f"{name} 采样率 {info['sample_rate']} ≠ 锚点 {anchor['sample_rate']}")
        assert info["channels"] == anchor["channels"], (
            f"{name} 声道 {info['channels']} ≠ 锚点 {anchor['channels']}")
        # 用户定案：BGM 保持 mp3 128k。体积门禁只能拦"变大"，这条拦"降码率换时长"。
        assert info["bitrate"] == anchor["bitrate"] == 128000, (
            f"{name} 码率 {info['bitrate']} ≠ 128000")
        expected = float(anchor["duration"])
        # 0.5%：见模块注释「关于时长断言的口径」（解析器多算 Xing/Info 帧，实测偏长 0.07s）
        assert abs(float(info["duration"]) - expected) <= expected * 0.005, (
            f"{name} 时长 {info['duration']:.3f}s 与锚点 {expected}s 差超过 0.5%")
        assert sha256sum(path) == anchor["sha256"], (
            f"{name} 的 sha256 与锚点不符 —— 文件被换过。"
            "确认是新编码结果后，请连同本文件的 BGM_ANCHORS 一起更新并注明重编原因/命令。")


# ── 3. app.js ↔ 磁盘：双向一一对应（最重要的一条）──────────────────────────
def test_app_js_audio_references_resolve_to_real_files() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    referenced = set(_AUDIO_NAME.findall(source))
    on_disk = {p.name for p in WEB_SOUNDS.iterdir() if p.is_file()}

    missing = sorted(referenced - on_disk)
    assert not missing, (
        f"web/js/app.js 引用了磁盘上不存在的音频：{missing} —— "
        "网页端 play().catch() 会吞掉 404，玩家只会觉得「没声音」，控制台无任何提示。")

    unreferenced = sorted(on_disk - referenced)
    assert not unreferenced, (
        f"web/assets/sounds 里有文件在整个 app.js 中 0 引用：{unreferenced} —— "
        "死文件，会白白计入包体（`check.wav` 就是这样躺了半年）。")


# ── 4. classic 音效与桌面逐字节一致（防两套副本漂移）────────────────────────
def test_classic_effects_are_byte_identical_to_desktop() -> None:
    for name in CLASSIC_SHARED:
        web = WEB_SOUNDS / name
        desktop = DESKTOP_SOUNDS / name
        assert web.is_file(), f"web 侧缺少 {name}"
        assert desktop.is_file(), f"desktop 侧缺少 {name}"
        assert sha256sum(web) == sha256sum(desktop), (
            f"{name} 两侧内容不一致 —— 只改了一边？"
            "两份副本是历史遗留（A2 决定不去重），但漂移必须显形。")
