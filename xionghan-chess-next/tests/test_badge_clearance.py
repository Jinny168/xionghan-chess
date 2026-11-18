"""射徽记环顶与正上邻格棋子盘缘下沿的间隙回归断言（D1）。

## 几何口径（纯计算，参数全部从三端源码常量读出，不在测试里另抄一份数字）

- 徽记中心在盘缘上方 `orbit × r`；射徽记细环半径 `ring × size × r`；
  环路径顶到子心的距离 = `(orbit + ring × size) × r`（记为 `top_path`）。
- 环线宽 `stroke × r`，含线宽半宽的外缘顶 = `top_path + stroke / 2`（记为 `top_outer`，更严）。
- 正上邻格棋子中心距 1 个 cell，其盘缘下沿在 `1 cell − r`；因此

  - 路径顶间隙：`gap_path = 1 − ρ × (1 + top_path)`
  - 外缘顶间隙：`gap_outer = 1 − ρ × (1 + top_outer)`

  其中 `ρ` 是棋子盘半径占格比例（桌面 / web 旧树 0.39，webapp 0.42）。

## 阈值口径

断言阈值钉在**环路径顶** `top_path` 那个量上（`gap_path ≥ 0.06 cell`）；
更严的外缘顶 `gap_outer` 一并算出，写进失败信息。参考现状：

- 桌面 / web（ρ=0.39）：`top_path=1.211`，`gap_path≈0.1377 cell`，`gap_outer≈0.1270 cell`；
- webapp（ρ=0.42）：`gap_path≈0.0714 cell`（过线），`gap_outer≈0.0598 cell`（刚低于 0.06，
  这也是后续把 webapp 盘径收到 0.39 的理由之一）。

任一参数（盘径比例 ρ、轨道 orbit、半尺寸 size、环倍数 ring、线宽 stroke）改动后，
本用例从源码重新提取并复算；间隙跌破 0.06 即红，失败信息点名是哪一端、哪个参数、新间隙是多少。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CLEARANCE = 0.06

_NUM = r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)"

# 每端的参数提取正则：(pattern, 命中第几处)。索引口径与视觉清单 VA-02/VA-14 一致。
_SPECS: dict[str, dict[str, object]] = {
    "desktop": {
        "file": "src/xionghan_chess/desktop/ui/board_widget.py",
        "rho": (rf"radius = min\(cw, ch\) \* ({_NUM})", 0),
        "orbit": (rf"BADGE_ORBIT = ({_NUM})", 0),
        "size": (rf"BADGE_SIZE = ({_NUM})", 0),
        "stroke": (rf"BADGE_STROKE = ({_NUM})", 0),
        "ring": (rf"QPointF\(bx, by\), r \* ({_NUM})", 0),
    },
    "web": {
        "file": "web/js/app.js",
        "rho": (rf"r=Math\.min\(g\.cw,g\.ch\)\*({_NUM})", 3),
        "orbit": (rf"BADGE_ORBIT=({_NUM})", 0),
        "size": (rf"BADGE_SIZE=({_NUM})", 0),
        "stroke": (rf"BADGE_STROKE=({_NUM})", 0),
        "ring": (rf"ctx\.arc\(bx,by,R\*({_NUM}),", 0),
    },
    "webapp": {
        "file": "webapp/js/ui/board.js",
        "rho": (rf"const r = cell \* ({_NUM})", 0),
        "orbit": (rf"const BADGE_ORBIT = ({_NUM});", 0),
        "size": (rf"const BADGE_SIZE = ({_NUM});", 0),
        "stroke": (rf"const BADGE_STROKE = ({_NUM});", 0),
        "ring": (rf"ctx\.arc\(bx, by, R \* ({_NUM}),", 0),
    },
}

_PARAM_LABEL = {
    "rho": "棋子盘半径比例 ρ",
    "orbit": "徽记轨道 orbit",
    "size": "徽记半尺寸 size",
    "stroke": "徽记线宽 stroke",
    "ring": "射环倍数 ring",
}


def _extract(end: str, param: str, text: str, pattern: str, index: int) -> float:
    hits = re.findall(pattern, text)
    assert len(hits) > index, (
        f"{end}：{_PARAM_LABEL[param]} 在源码里只命中 {len(hits)} 处，"
        f"提取口径要取第 {index + 1} 处。渲染器结构或常量被改了 —— 先核对源码与本用例口径。"
    )
    return float(hits[index])


@pytest.mark.parametrize("end", sorted(_SPECS))
def test_archer_badge_clearance_above_threshold(end: str) -> None:
    spec = _SPECS[end]
    text = (ROOT / str(spec["file"])).read_text(encoding="utf-8")

    params: dict[str, float] = {}
    for param, rule in spec.items():
        if param == "file":
            continue
        pattern, index = rule  # type: ignore[misc]
        params[param] = _extract(end, param, text, pattern, index)

    rho, orbit, size, stroke, ring = (
        params["rho"],
        params["orbit"],
        params["size"],
        params["stroke"],
        params["ring"],
    )

    top_path = orbit + ring * size
    top_outer = top_path + stroke / 2
    gap_path = 1.0 - rho * (1.0 + top_path)
    gap_outer = 1.0 - rho * (1.0 + top_outer)

    assert gap_path >= CLEARANCE, (
        f"{end} 射徽记环顶与正上邻格盘缘下沿间隙不足 {CLEARANCE} 格。\n"
        f"参数：ρ={rho:g}，orbit={orbit:g}，size={size:g}，ring={ring:g}，stroke={stroke:g}；\n"
        f"环路径顶 top_path={top_path:.4f}r，外缘顶 top_outer={top_outer:.4f}r；\n"
        f"路径顶间隙 gap_path={gap_path:.4f} cell，外缘顶间隙 gap_outer={gap_outer:.4f} cell。\n"
        "请优先核对盘径比例 ρ 或徽记轨道 / 半尺寸 / 环倍数；改动后同步更新视觉清单与三端。"
    )
