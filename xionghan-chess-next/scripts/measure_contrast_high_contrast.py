"""E1 高对比棋子组：三端 × 三类元素 WCAG 对比度实测。

## 口径

- 相对亮度 / 对比比 / 派生公式与桌面 `contrast.py` 同一份（本脚本直接复用它）。
- 取色：令牌来自三端源码既有条目（见每条 `source` 指向的文件与令牌名）；
  脚本启动时自检表内 hex 确实出现在对应源码文件中，防止手写数字漂移。
- 半透明元素（可走点圆盘、可吃点环/半透明盘）先按 alpha 与盘底合成等效 RGB，
  再对盘底算对比比。
- 判据：棋子描边/文字属文本，目标 `TEXT_TARGET = 4.5:1`；可走点 / 可吃点属
  非文本图形，目标 `GRAPHIC_TARGET = 3:1`（WCAG 1.4.11）。
- 高对比开启：棋子墨色经 `derive_for_background` 派生；提示点不派生（既有令牌）。

输出：一行 JSON（stdout 最后一行），含三端每类元素的实测比值、目标、是否达标、
派生 mix。禁止把数字手写进报告——以本脚本输出为准。

用法：
    python scripts/measure_contrast_high_contrast.py
    python scripts/measure_contrast_high_contrast.py --json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.desktop.ui.contrast import (  # noqa: E402
    GRAPHIC_TARGET,
    TEXT_TARGET,
    contrast_ratio,
    derive_for_background,
)

# ---------------------------------------------------------------------------
# 令牌表：每条 hex / rgb 都能在 `source` 指向的源码里找到对应既有条目。
# 不在这里新增任何色板条目；提示点 rgb 取自既有 rgba() 字面量。
# ---------------------------------------------------------------------------

# 桌面：board_widget.py —— 墨 #9a2424/#24211e；可走点 accent @LEGAL_DOT_ALPHA_LIGHT(.55)；
#       可吃点环 rgb(205,32,32,220)、半透明盘 rgb(148,30,30,90)。
# webapp：board.js —— 墨 #a3271f/#2b2622；可走点 rgba(58,104,72,.78)；可吃点环 rgba(176,58,46,.85)。
# web：app.js —— 墨 #a12424/#292522；可走点 rgba(49,92,72,.72)；可吃点叉 rgba(205,32,32,.9)。

SOURCES: dict[str, dict[str, object]] = {
    "desktop": {
        "source": "src/xionghan_chess/desktop/ui/board_widget.py",
        "themes": {
            "classic": {
                "background": "#e7c88d",  # theme.py THEMES.classic.board
                "ink_red": "#9a2424",
                "ink_black": "#24211e",
                "legal": {"rgb": [0x31, 0x5C, 0x48], "alpha": 0.55},
                "capture_ring": {"rgb": [205, 32, 32], "alpha": 220 / 255},
                "capture_fill": {"rgb": [148, 30, 30], "alpha": 90 / 255},
            },
            "dark": {
                "background": "#34302b",
                "ink_red": "#9a2424",
                "ink_black": "#24211e",
                "legal": {"rgb": [0x9F, 0xBF, 0xA8], "alpha": 0.60},
                "capture_ring": {"rgb": [205, 32, 32], "alpha": 220 / 255},
                "capture_fill": {"rgb": [148, 30, 30], "alpha": 90 / 255},
            },
        },
    },
    "webapp": {
        "source": "webapp/js/ui/board.js",
        "themes": {
            "classic": {
                "background": "#f3e3c3",  # THEMES.classic.paper[0]
                "ink_red": "#a3271f",
                "ink_black": "#2b2622",
                "legal": {"rgb": [58, 104, 72], "alpha": 0.78},
                "capture_ring": {"rgb": [176, 58, 46], "alpha": 0.85},
            },
            "ink": {
                "background": "#3a3a3c",
                "ink_red": "#a3271f",
                "ink_black": "#2b2622",
                "legal": {"rgb": [58, 104, 72], "alpha": 0.78},
                "capture_ring": {"rgb": [176, 58, 46], "alpha": 0.85},
            },
        },
    },
    "web": {
        "source": "web/js/app.js",
        "themes": {
            "classic": {
                "background": "#f9e8c4",  # app.css :root --board-bg
                "ink_red": "#a12424",
                "ink_black": "#292522",
                "legal": {"rgb": [49, 92, 72], "alpha": 0.72},
                "capture_ring": {"rgb": [205, 32, 32], "alpha": 0.90},
            },
            "dark": {
                "background": "#2c2c2c",
                "ink_red": "#a12424",
                "ink_black": "#292522",
                "legal": {"rgb": [49, 92, 72], "alpha": 0.72},
                "capture_ring": {"rgb": [205, 32, 32], "alpha": 0.90},
            },
        },
    },
}


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{v:02x}" for v in rgb)


def _composite(fg_rgb: list[int], alpha: float, bg: str) -> str:
    """半透明前景压在盘底上的等效不透明色。"""
    br, bg_, bb = _hex_rgb(bg)
    r = round(fg_rgb[0] * alpha + br * (1 - alpha))
    g = round(fg_rgb[1] * alpha + bg_ * (1 - alpha))
    b = round(fg_rgb[2] * alpha + bb * (1 - alpha))
    return _rgb_hex((r, g, b))


def _check_source_traceable(endpoint: str, source: str, theme: dict[str, object]) -> None:
    """表内盘底 / 墨色 hex 必须能在源码里检索到（既有条目，非新增）。"""
    text = (ROOT / source).read_text(encoding="utf-8")
    # 盘底令牌可能落在 CSS 变量里（桌面 theme.py / web app.css），单独放行。
    background_sources = {
        "desktop": "src/xionghan_chess/desktop/ui/theme.py",
        "web": "web/css/app.css",
    }
    for key in ("background", "ink_red", "ink_black"):
        token = str(theme[key])
        if key == "background" and endpoint in background_sources:
            bg_text = (ROOT / background_sources[endpoint]).read_text(encoding="utf-8")
            assert token in bg_text, f"{endpoint} 盘底 {token} 未在 {background_sources[endpoint]} 出现"
            continue
        if token not in text:
            raise AssertionError(f"{endpoint} 令牌 {token} 未在 {source} 出现")


def measure() -> dict[str, object]:
    report: dict[str, object] = {"targets": {"text": TEXT_TARGET, "graphic": GRAPHIC_TARGET}, "endpoints": {}}

    for endpoint, spec in SOURCES.items():
        endpoint_out: dict[str, object] = {"source": spec["source"], "themes": {}}
        for theme_name, theme in spec["themes"].items():
            theme = dict(theme)
            _check_source_traceable(endpoint, str(spec["source"]), theme)
            background = str(theme["background"])
            theme_out: dict[str, object] = {"background": background}

            # 棋子：文本判据 4.5:1；高对比开启经派生。
            for side, token_key in (("red", "ink_red"), ("black", "ink_black")):
                token = str(theme[token_key])
                derived = derive_for_background(token, background, TEXT_TARGET)
                base_ratio = contrast_ratio(token, background)
                theme_out[f"piece_{side}"] = {
                    "token": token,
                    "derived": derived.color,
                    "ratio": round(base_ratio, 2),
                    "derived_ratio": round(derived.ratio, 2),
                    "target": TEXT_TARGET,
                    "met": derived.met,
                    "mix": round(derived.mix, 2),
                    "criterion": "text",
                }

            # 可走点（空点圆盘）：非文本图形 3:1。
            legal = theme["legal"]
            legal_hex = _composite(legal["rgb"], legal["alpha"], background)
            theme_out["legal_dot"] = {
                "composite": legal_hex,
                "ratio": round(contrast_ratio(legal_hex, background), 2),
                "target": GRAPHIC_TARGET,
                "met": contrast_ratio(legal_hex, background) >= GRAPHIC_TARGET,
                "criterion": "graphic",
            }

            # 可吃点：红描边环（受害盘若存在同测）。
            ring = theme["capture_ring"]
            ring_hex = _composite(ring["rgb"], ring["alpha"], background)
            entry: dict[str, object] = {
                "composite": ring_hex,
                "ratio": round(contrast_ratio(ring_hex, background), 2),
                "target": GRAPHIC_TARGET,
                "met": contrast_ratio(ring_hex, background) >= GRAPHIC_TARGET,
                "criterion": "graphic",
            }
            if "capture_fill" in theme:
                fill = theme["capture_fill"]
                fill_hex = _composite(fill["rgb"], fill["alpha"], background)
                entry["fill_composite"] = fill_hex
                entry["fill_ratio"] = round(contrast_ratio(fill_hex, background), 2)
                entry["fill_met"] = contrast_ratio(fill_hex, background) >= GRAPHIC_TARGET
            theme_out["capture_hint"] = entry

            endpoint_out["themes"][theme_name] = theme_out
        report["endpoints"][endpoint] = endpoint_out

    return report


def _print_table(report: dict[str, object]) -> None:
    for endpoint, spec in report["endpoints"].items():
        for theme_name, theme in spec["themes"].items():
            print(f"\n[{endpoint} / {theme_name}] 盘底 {theme['background']}")
            for key, item in theme.items():
                if not isinstance(item, dict):
                    continue
                ratio = item.get("derived_ratio") or item.get("ratio")
                flag = "OK " if item["met"] else "GAP"
                print(f"  {flag} {key:14s} ratio={ratio:<5} target={item['target']} ({item['criterion']})")


def main() -> int:
    report = measure()
    as_json = "--json" in sys.argv
    if as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        _print_table(report)
        print("\n" + json.dumps(report, ensure_ascii=False, sort_keys=True))

    # 文本判据：派生后必须达标；图形判据不达标的元素在报告里单独标注。
    gaps: list[str] = []
    for endpoint, spec in report["endpoints"].items():
        for theme_name, theme in spec["themes"].items():
            for key, item in theme.items():
                if not isinstance(item, dict):
                    continue
                if item["criterion"] == "text" and not item["met"]:
                    gaps.append(f"{endpoint}/{theme_name}/{key}")
    if gaps:
        print(f"\n警告：以下文本元素派生后仍未达 {TEXT_TARGET}:1 -> {', '.join(gaps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
