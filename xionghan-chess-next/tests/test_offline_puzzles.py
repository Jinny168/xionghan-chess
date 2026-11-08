"""Android 离线包与桌面题库的对齐守卫。

背景：Android 是 WebView 壳，跑的是 `android/Resources/assets/offline/` 里的
离线包。那份包原先自带 3 条**手写**的 `OFFLINE_PUZZLES`（每条只是「开局走一步」），
和桌面端 16 条真实残局不是同一套题 —— 用户在一端练的东西，在另一端找不到。

现在题库从 `core/data/puzzles.json` 生成 JS 数据，离线引擎用 `gameFromDocument()`
载入真实题面。本文件保证三件事：
1. 生成物与数据源一致（改题库后忘了重新生成会红）；
2. 每个 document 都能被离线引擎**载入**，且解法首着在该引擎下**合法**；
3. 离线题库的 id 集合与 Python 题库完全一致（不多不少）。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from xionghan_chess.core.puzzles import load_puzzles

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_offline_puzzles.py"
PROBE = ROOT / "scripts" / "offline_puzzle_probe.cjs"
OFFLINE_DIR = ROOT / "android" / "Resources" / "assets" / "offline"
ENGINE = OFFLINE_DIR / "offline.js"
DATA = OFFLINE_DIR / "offline-puzzles.js"


def _probe() -> list[dict]:
    if not shutil.which("node"):
        pytest.skip("Node.js is required to run the offline engine")
    completed = subprocess.run(
        ["node", str(PROBE), str(ENGINE), str(DATA)],
        capture_output=True, text=True, timeout=180,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_generated_data_is_up_to_date() -> None:
    """改了 `puzzles.json` 却没重新生成离线数据 —— 两端就会悄悄不一致。"""
    completed = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                               capture_output=True, text=True, timeout=180)
    assert completed.returncode == 0, (completed.stdout + completed.stderr).strip()


def test_index_html_loads_puzzle_data_before_the_engine() -> None:
    html = (OFFLINE_DIR / "index.html").read_text(encoding="utf-8")
    assert "offline-puzzles.js" in html, "离线页没有加载题库数据"
    assert html.index("offline-puzzles.js") < html.index('src="offline.js"'), \
        "数据必须在引擎之前加载，否则 OFFLINE_PUZZLES 会是空的"


def test_offline_engine_accepts_every_puzzle() -> None:
    """逐条把 document 喂给离线引擎：能载入、棋子数对得上、解法首着合法。"""
    rows = _probe()
    assert rows, "探针没有返回任何题目"
    failures = [row for row in rows if not row["ok"]]
    assert not failures, "以下题目在离线引擎里载入或判定失败：\n  " + "\n  ".join(
        f"{row['id']}: {row['message']}" for row in failures
    )
    mismatched = [row for row in rows if row["pieces"] != row["expected"]]
    assert not mismatched, "棋子数与题面不一致：\n  " + "\n  ".join(
        f"{row['id']}: 载入 {row['pieces']} != 题面 {row['expected']}" for row in mismatched
    )


def test_puzzle_ids_match_the_python_bank() -> None:
    """id 集合必须完全一致 —— 防止只导出了一部分，或残留旧的手写条目。"""
    rows = _probe()
    offline_ids = {row["id"] for row in rows}
    python_ids = {puzzle.id for puzzle in load_puzzles()}
    assert offline_ids == python_ids, (
        f"离线缺：{sorted(python_ids - offline_ids)}；离线多出：{sorted(offline_ids - python_ids)}"
    )


def test_hand_written_drills_are_gone() -> None:
    """旧的手写题库不该再出现在引擎里，否则又是一份会漂移的第二数据源。"""
    source = ENGINE.read_text(encoding="utf-8")
    for legacy in ("puzzle1Title", "puzzle2Title", "puzzle3Title"):
        assert legacy not in source, f"引擎里还留着旧的手写题目键：{legacy}"
