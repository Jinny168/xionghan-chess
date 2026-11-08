"""生成「网页合成」音效包：`src/xionghan_chess/desktop/resources/sounds/web/*.wav`。

参数来自 WorkBuddy 投稿版的 **WebAudio 现场合成**实现（页面里没有 wav/mp3），
按原样复刻，不做"调音"：

| 事件 | 参数 |
|---|---|
| select  | sine 760Hz, 0.07s, gain .10 |
| move    | sine 190Hz, 0.11s, gain .24, slide −70 + 噪声(0.06s, .10, lowpass 900，与音同时起) |
| capture | triangle 320Hz, 0.09s, gain .20, slide −180 + 噪声(0.12s, .16, lowpass 1600, delay .01) |
| check   | triangle 620Hz 0.16s .18 + triangle 930Hz 0.14s .12, delay .09 |
| win     | 523/659/784/1046Hz sine, 0.24s, gain .16, 逐音延迟 0.1s |
| lose    | 392/330/262Hz sine, 0.30s, gain .16, 逐音延迟 0/0.13/0.26s（总长 0.56s） |
| click   | square 520Hz, 0.035s, gain .06 |
| undo    | sine 300Hz, 0.12s, gain .14, slide +120 |

包络：8ms 指数升到目标 gain，再指数降到 1e-4（在 duration 处）。
噪声：白噪声 × (1-i/n)² 包络，再经 RBJ biquad lowpass（Q=0.707）。
随机源固定种子 —— **重跑必须逐字节一致**，否则每次构建都会把二进制改脏。

只用标准库：`wave` / `math` / `struct` / `random`。

## 时长以**原实现的时序**为准，不以验收表为准
| 事件 | 时长 | 推导 |
|---|---|---|
| select | 0.070 | tone 0.07 |
| move | **0.110** | tone 0.11 与 noise 0.06 重叠（noise 无 delay） |
| capture | 0.130 | tone 0.09；noise delay 0.01 + 0.12 |
| check | 0.230 | 0.09 + 0.14 |
| win | 0.540 | 0.30 + 0.24 |
| lose | **0.560** | 0.26 + 0.30 |
| click | 0.035 | tone 0.035 |
| undo | 0.120 | tone 0.12 |

**验收表若与代码不符，先质疑表。** 这一轮的教训不是"表算错了"，而是为了对上表去改声音 ——
参数复刻的本义是"听起来一样"，不是"数字看着一样"。
"""
from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

RATE = 44100
SEED = 20261031
OUT = Path(__file__).resolve().parents[1] / "src/xionghan_chess/desktop/resources/sounds/web"

ATTACK = 0.008          # 指数升包络时长
FLOOR = 1e-4            # 衰减终点


def envelope(n: int, gain: float, duration: float) -> list[float]:
    """8ms 指数升到 gain，再指数降到 FLOOR（duration 处）。"""
    out = []
    attack_n = max(1, int(ATTACK * RATE))
    release_n = max(1, n - attack_n)
    for i in range(n):
        t = i / RATE
        if i < attack_n:
            value = gain * (t / ATTACK)
        else:
            ratio = (i - attack_n) / release_n
            value = gain * (FLOOR / gain) ** ratio
        out.append(value)
    return out


def tone(freq: float, duration: float, gain: float, wave_type: str = "sine",
         slide: float = 0.0) -> list[float]:
    n = int(duration * RATE)
    env = envelope(n, gain, duration)
    samples = []
    phase = 0.0
    for i in range(n):
        f = freq + (slide * (i / n) if slide else 0.0)
        phase += 2 * math.pi * f / RATE
        if wave_type == "sine":
            value = math.sin(phase)
        elif wave_type == "triangle":
            value = 2 / math.pi * math.asin(math.sin(phase))
        else:  # square
            value = 1.0 if math.sin(phase) >= 0 else -1.0
        samples.append(value * env[i])
    return samples


def lowpass(samples: list[float], fc: float) -> list[float]:
    """RBJ biquad lowpass，Q=0.707。"""
    w0 = 2 * math.pi * fc / RATE
    cos_w0, alpha = math.cos(w0), math.sin(w0) / (2 * 0.707)
    b0 = (1 - cos_w0) / 2
    b1 = 1 - cos_w0
    b2 = (1 - cos_w0) / 2
    a0 = 1 + alpha
    a1 = -2 * cos_w0
    a2 = 1 - alpha
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    out, x1, x2, y1, y2 = [], 0.0, 0.0, 0.0, 0.0
    for x in samples:
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out.append(y)
        x2, x1 = x1, x
        y2, y1 = y1, y
    return out


def noise(duration: float, gain: float, fc: float, rng: random.Random) -> list[float]:
    n = max(1, int(duration * RATE))
    raw = [rng.uniform(-1, 1) * gain * (1 - i / n) ** 2 for i in range(n)]
    return lowpass(raw, fc)


def mix(*layers: tuple[float, list[float]]) -> list[float]:
    """按 (起始秒, 波形) 叠加成一条轨。"""
    total = max(int(delay * RATE) + len(data) for delay, data in layers)
    out = [0.0] * total
    for delay, data in layers:
        start = int(delay * RATE)
        for i, value in enumerate(data):
            out[start + i] += value
    return out


def write_wav(name: str, samples: list[float]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        frames = bytearray()
        for value in samples:
            clipped = max(-1.0, min(1.0, value))
            frames += struct.pack("<h", int(clipped * 32767))
        handle.writeframes(bytes(frames))
    print(f"{name:8s} {len(samples) / RATE:.3f}s  -> {path.name}")


def main() -> None:
    rng = random.Random(SEED)          # 固定种子：重跑逐字节一致
    write_wav("select", tone(760, 0.07, 0.10))
    write_wav("move", mix(
        (0.0, tone(190, 0.11, 0.24, slide=-70)),
        (0.0, noise(0.06, 0.10, 900, rng)),     # 与音同时起 → 重叠，总长 0.11s
    ))
    write_wav("capture", mix(
        (0.0, tone(320, 0.09, 0.20, wave_type="triangle", slide=-180)),
        (0.01, noise(0.12, 0.16, 1600, rng)),
    ))
    write_wav("check", mix(
        (0.0, tone(620, 0.16, 0.18, wave_type="triangle")),
        (0.09, tone(930, 0.14, 0.12, wave_type="triangle")),
    ))
    write_wav("win", mix(*[(0.1 * i, tone(f, 0.24, 0.16)) for i, f in
                           enumerate((523, 659, 784, 1046))]))
    write_wav("lose", mix(*[(0.13 * i, tone(f, 0.30, 0.16)) for i, f in
                            enumerate((392, 330, 262))]))
    write_wav("click", tone(520, 0.035, 0.06, wave_type="square"))
    write_wav("undo", tone(300, 0.12, 0.14, slide=120))


if __name__ == "__main__":
    main()
