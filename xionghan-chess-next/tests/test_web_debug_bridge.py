"""离屏证据调试桥门禁（批次 G）。

`web/js/app.js` 末尾挂了一个**仅离屏证据脚本使用**的调试桥：只有页面在模块加载
之前已置 `window.__XH_DEBUG__ === 'offscreen'`，才把少量成员挂到 `window.__xh`；
生产路径不启用、零副作用、不进入公开导出。

本测试对源码做静态断言（不在 Python 里执行该浏览器模块），并复用 `scripts/
verify_debug_bridge.mjs` 跑一遍 node 侧双保险。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from tests._node_guard import require_node

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "js" / "app.js"
VERIFY_MJS = ROOT / "scripts" / "verify_debug_bridge.mjs"

SOURCE = APP_JS.read_text(encoding="utf-8")

_BRIDGE_IF = re.compile(r"if\s*\(\s*window\.__XH_DEBUG__\s*===\s*'offscreen'\s*\)")


def _extract_if_block(text: str) -> str | None:
    """从桥条件 `if (...) {` 起按大括号配平取出块体；取不到返回 None。"""
    match = _BRIDGE_IF.search(text)
    if match is None:
        return None
    open_brace = text.find("{", match.end())
    if open_brace < 0:
        return None
    depth = 0
    for index in range(open_brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace + 1 : index]
    return None


def test_bridge_gated_behind_offscreen_flag() -> None:
    """桥必须被 `window.__XH_DEBUG__ === 'offscreen'` 条件包裹，成员挂载在块体内。"""
    block = _extract_if_block(SOURCE)
    assert block is not None, "缺少 `if (window.__XH_DEBUG__ === 'offscreen')` 条件块"
    assert re.search(
        r"window\.__xh\s*=\s*\{\s*app,\s*draw,\s*resizeBoard,\s*geometry\s*\}",
        block,
    ), "条件块内未按约定挂载 `window.__xh = { app, draw, resizeBoard, geometry }`"


def test_no_second_xh_assignment() -> None:
    """`window.__xh` 赋值只应有桥块内一处；无标记时不得挂全局。"""
    assignments = re.findall(r"window\.__xh\s*=", SOURCE)
    assert len(assignments) == 1, f"window.__xh 赋值 {len(assignments)} 处，应为 1 处"


def test_bridge_not_exported() -> None:
    """桥不得进入任何 export / 公开 API 清单。"""
    assert not re.search(r"export\s*(default|const|function|let|var|\{)", SOURCE), "app.js 出现 export 泄漏"
    for line in SOURCE.splitlines():
        assert not ("export" in line and "__xh" in line), f"`__xh` 与 export 同行：{line}"


def test_bridge_block_has_no_production_side_effects() -> None:
    """条件块体零副作用：不写 storage、不改 DOM。"""
    block = _extract_if_block(SOURCE)
    assert block is not None
    for forbidden in ("localStorage", "setItem", "sessionStorage", "document."):
        assert forbidden not in block, f"桥块体内出现生产副作用项 `{forbidden}`"


def test_node_verify_script_passes() -> None:
    """node 侧静态门禁双保险：verify_debug_bridge.mjs 退出 0。"""
    require_node()
    completed = subprocess.run(
        ["node", str(VERIFY_MJS)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=60,
    )
    assert completed.returncode == 0, (
        f"verify_debug_bridge.mjs 退出 {completed.returncode}\n{completed.stdout}\n{completed.stderr}"
    )
