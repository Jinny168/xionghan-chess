"""网页「棋子图谱」首屏静态快照：4 个预设必须各自演示出对应规则。

网页没有本地规则引擎（不加载 `offline.js`），首屏靠 `web/assets/data/atlas_presets.json`。
所以这些断言**只读静态数据**，不依赖服务：数据错了就是演示错了。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "web" / "assets" / "data" / "atlas_presets.json"
PRESETS = {item["id"]: item for item in json.loads(SNAPSHOT.read_text(encoding="utf-8"))["presets"]}


def test_snapshot_matches_generator() -> None:
    """快照必须与生成脚本一致（改了脚本忘了重跑 → 红）。"""
    before = SNAPSHOT.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_atlas_presets.py")],
                   check=True, capture_output=True)
    assert SNAPSHOT.read_text(encoding="utf-8") == before, "快照过期，请重跑 scripts/gen_atlas_presets.py"


def test_clamp_preset_blocks_the_far_diagonal() -> None:
    """夹逼：更远处的敌子（9,9）吃不到，但其它斜线照常可走。"""
    preset = PRESETS["clamp"]
    squares = {(m["row"], m["col"]) for m in preset["moves"]}
    assert (9, 9) not in squares, "被夹逼的斜段不该出现在可走格"
    assert len(squares) >= 5, f"其余斜线应照走，实际 {sorted(squares)}"


def test_three_line_preset_offers_the_sandwiched_enemy() -> None:
    """三连：两兵夹住的敌子（6,4）出现在可吃格。"""
    preset = PRESETS["three"]
    assert preset["options"].get("pawn_three_line_capture") is True
    captures = {(c["row"], c["col"]) for c in preset["captures"]}
    assert (6, 4) in captures, f"夹住的敌子应可吃，实际 {sorted(captures)}"


def test_facing_preset_reports_check() -> None:
    """照面：两王之间无子 → in_check 为真。"""
    assert PRESETS["facing"]["check"] is True


def test_free_preset_has_ordinary_moves() -> None:
    """自由：常规局面有足够可走格，且不处于被将。"""
    preset = PRESETS["free"]
    assert len(preset["moves"]) >= 8
    assert preset["check"] is False


def test_atlas_fetch_path_is_served() -> None:
    """`atlas.js` 请求的 JSON 必须①文件真存在 ②前缀属于 `app.py` 已挂载的静态目录。

    防的是"路径看起来对、但没有任何东西服务它"——上一版 fetch 的是 `/data/...`，
    服务端只挂了 `/assets` `/css` `/js` `/locales`，打开图谱就是空的。
    """
    atlas_js = (ROOT / "web" / "js" / "atlas.js").read_text(encoding="utf-8")
    match = re.search(r"fetch\('(/[^']+\.json)'\)", atlas_js)
    assert match, "atlas.js 里找不到 fetch 的 JSON 路径"
    url = match.group(1)
    assert (ROOT / "web" / url.lstrip("/")).is_file(), f"{url} 在 web/ 下没有对应文件"

    app_py = (ROOT / "src" / "xionghan_chess" / "service" / "app.py").read_text(encoding="utf-8")
    mounts = set(re.findall(r'app\.mount\("(/[a-z]+)"', app_py))
    prefix = "/" + url.lstrip("/").split("/")[0]
    assert prefix in mounts, f"{prefix} 不在已挂载目录 {sorted(mounts)} 里，运行时会 404"
