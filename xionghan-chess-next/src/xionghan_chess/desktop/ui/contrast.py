"""高对比棋子组：既有令牌的**程序化派生**（WCAG 相对亮度）。

## 零新增色值

本模块产出的每个颜色，都由既有令牌 hex 经线性混色计算得出；源码里不出现任何
新的 hex 字面量（混色目标黑/白由整数通道 `0` / `255` 给出，不是色板条目）。
白名单 `benchmarks/color_allowlist.txt` 不因此增加条目。

## 派生方向

对比比不足时，按盘底明暗选混色方向：

- 浅底（盘底相对亮度 > 0.179）：把令牌向**黑**混，压深到与盘底拉开对比；
- 深底：把令牌向**白**混，提亮到与盘底拉开对比。

混色比例 `mix ∈ [0, 1]`：`0` = 原令牌，`1` = 混到极值（黑或白）。

## 判据

- 文本/字形（棋子描边、棋子文字）目标 **4.5:1**（`TEXT_TARGET`）；
- 非文本图形（可走点圆盘、可吃点环）目标 **3:1**（`GRAPHIC_TARGET`）。

迭代到首个达标比例；若混到极值仍不达标，`met=False`，返回极值色并把实测
比值写进 `Derived.ratio` —— 不偷加色值去硬凑达标。

## 三端一致

`web/js/app.js` 与 `webapp/js/ui/board.js` 各自镜像**同一套**公式（相对亮度、
混色方向、目标比值、步长），与本模块逐行对应；改公式必须三端同步。
"""

from __future__ import annotations

from dataclasses import dataclass

# WCAG 2.x：正文文本 4.5:1，非文本图形 3:1。
TEXT_TARGET = 4.5
GRAPHIC_TARGET = 3.0

# 相对亮度分界：高于此值视为浅底（向黑混），低于视为深底（向白混）。
_LIGHT_THRESHOLD = 0.179
# 混色步进：0.05，首个达标比例即停，避免过度派生。
_MIX_STEP = 0.05
_MIX_MAX = 1.0


def _channel_to_linear(channel: int) -> float:
    """sRGB 单通道 → 线性亮度（WCAG 公式）。"""
    s = channel / 255.0
    if s <= 0.03928:
        return float(s / 12.92)
    return float(((s + 0.055) / 1.055) ** 2.4)


def _parse_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        raise ValueError(f"invalid hex color: {hex_color!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def relative_luminance(hex_color: str) -> float:
    """WCAG 相对亮度（0 = 黑，1 = 白）。"""
    r, g, b = _parse_rgb(hex_color)
    return (
        0.2126 * _channel_to_linear(r)
        + 0.7152 * _channel_to_linear(g)
        + 0.0722 * _channel_to_linear(b)
    )


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 对比比 `(L1+0.05)/(L2+0.05)`，L1 ≥ L2。"""
    l1, l2 = relative_luminance(foreground), relative_luminance(background)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def _mix(token: tuple[int, int, int], target: tuple[int, int, int], mix: float) -> str:
    r = round(token[0] + (target[0] - token[0]) * mix)
    g = round(token[1] + (target[1] - token[1]) * mix)
    b = round(token[2] + (target[2] - token[2]) * mix)
    return f"#{r:02x}{g:02x}{b:02x}"


@dataclass(frozen=True)
class Derived:
    """派生结果：`color` 为可渲染 hex；`met` 标明是否达到目标比值。"""

    color: str
    ratio: float
    target: float
    met: bool
    mix: float


def derive_rgb(token_rgb: tuple[int, int, int], background: str, target: float = TEXT_TARGET) -> Derived:
    """把既有令牌的 RGB 三元组派生到与盘底对比达标；不达标保留极值并写明实测比值。

    与 `derive_for_background` 同一条公式；区别在入口吃 RGB 三元组（既有 rgba 提示点
    令牌），UI 层不必为派生另写一个 hex 字面量。
    """
    token_hex = _rgb_hex(token_rgb)
    base_ratio = contrast_ratio(token_hex, background)
    if base_ratio >= target:
        return Derived(color=token_hex, ratio=base_ratio, target=target, met=True, mix=0.0)

    dark_background = relative_luminance(background) <= _LIGHT_THRESHOLD
    # 浅底压黑，深底提亮到白；白/黑由通道极值给出，不是新色板条目。
    target_rgb: tuple[int, int, int] = (255, 255, 255) if dark_background else (0, 0, 0)

    best = Derived(color=token_hex, ratio=base_ratio, target=target, met=False, mix=0.0)
    mix = _MIX_STEP
    while mix <= _MIX_MAX + 1e-9:
        candidate = _mix(token_rgb, target_rgb, mix)
        ratio = contrast_ratio(candidate, background)
        if ratio >= base_ratio:
            best = Derived(color=candidate, ratio=ratio, target=target, met=ratio >= target, mix=mix)
        if ratio >= target:
            return best
        mix += _MIX_STEP
    return best


def derive_for_background(token: str, background: str, target: float = TEXT_TARGET) -> Derived:
    """把既有令牌派生到与盘底对比达标；不达标时保留极值并写明实测比值。

    参数：
        token: 既有令牌 hex（红/黑墨、accent、提示红等）。
        background: 盘底 hex（主题 `board` / `paper[0]`）。
        target: 目标对比比，文本 `TEXT_TARGET`，图形 `GRAPHIC_TARGET`。
    """
    return derive_rgb(_parse_rgb(token), background, target)


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
