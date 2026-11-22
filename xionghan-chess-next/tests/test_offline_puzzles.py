"""Android 离线包与桌面题库的对齐守卫。

背景：Android 是 WebView 壳，跑的是 `android/Resources/assets/offline/` 里的
离线包。那份包原先自带 3 条**手写**的 `OFFLINE_PUZZLES`（每条只是「开局走一步」），
和桌面端 16 条真实残局不是同一套题 —— 用户在一端练的东西，在另一端找不到。

现在题库从 `core/data/puzzles.json` 生成 JS 数据，离线引擎用 `gameFromDocument()`
载入真实题面。本文件保证三件事：
1. 生成物与数据源一致（改题库后忘了重新生成会红）；
2. 每个 document 都能被离线引擎**载入**，且解法首着在该引擎下**合法**；
3. 离线题库的 id 集合与 Python 题库完全一致（不多不少）。

三条基线纪律（踩过坑，别再重复）：
1. 唯一基线是 tracked 的 `android/Resources/assets/offline/offline-puzzles.js`；
2. `android/obj/**` 下的同名文件是 APK 构建残留（实测 13 条题、11 月 9 日），
   **不作基线**，也不能据此判断正式产物落后；
3. `--check` 的判据是「重算文本 == 现文件文本」逐字节相等，所以它只证明
   「产物与生成器一致」，**不证明「产物是对的」** —— `_stable_ids` 曾把同一枚
   棋子编成两个 id（`endgame-elephant-eye-01` / `endgame-advisor-palace-01`），
   当时 `--check` 全绿。一致性归 `--check`，正确性归本文件的逐项断言。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _node_guard import module_skip_mark, require_node

from xionghan_chess.core.puzzles import load_puzzles

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_offline_puzzles.py"
PROBE = ROOT / "scripts" / "offline_puzzle_probe.cjs"
OFFLINE_DIR = ROOT / "android" / "Resources" / "assets" / "offline"
ENGINE = OFFLINE_DIR / "offline.js"

# 缺 node 时整模块显式失败（不许静默 skip），守卫与逃生阀见 tests/_node_guard.py。
if (mark := module_skip_mark()) is not None:
    pytestmark = mark
DATA = OFFLINE_DIR / "offline-puzzles.js"

# 与 `scripts/build_offline_puzzles.py::_stable_ids` 的识别口径一致：只有同时带
# 这五个键的对象才算「棋子」，才会被重编号。
PIECE_FIELDS = {"id", "type", "color", "row", "col"}


def _offline_payload() -> dict[str, dict]:
    """读生成物里的题库，按题目 id 建索引。"""
    text = DATA.read_text(encoding="utf-8")
    marker = "window.XH_OFFLINE_PUZZLES = "
    start = text.index(marker) + len(marker)
    end = text.rindex(";")
    return {item["id"]: item for item in json.loads(text[start:end])}


def _piece_paths(value: object, path: str = "") -> dict[str, dict]:
    """按结构路径收集棋子对象。

    同一枚棋子可能在 `state.captured` 与 `history[].captured` 各出现一次；
    用路径做键才能在不依赖编号的前提下把两侧对齐。
    """
    out: dict[str, dict] = {}
    if isinstance(value, dict):
        if PIECE_FIELDS <= set(value):
            out[path] = value
        for key, item in value.items():
            if key == "id" and PIECE_FIELDS <= set(value):
                continue
            out.update(_piece_paths(item, f"{path}/{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            out.update(_piece_paths(item, f"{path}[{index}]"))
    return out



def _probe() -> list[dict]:
    require_node()
    completed = subprocess.run(
        ["node", str(PROBE), str(ENGINE), str(DATA)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_generated_data_is_up_to_date() -> None:
    """改了 `puzzles.json` 却没重新生成离线数据 —— 两端就会悄悄不一致。"""
    completed = subprocess.run([sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True, timeout=180)
    assert completed.returncode == 0, (completed.stdout + completed.stderr).strip()


def test_index_html_loads_puzzle_data_before_the_engine() -> None:
    html = (OFFLINE_DIR / "index.html").read_text(encoding="utf-8")
    assert "offline-puzzles.js" in html, "离线页没有加载题库数据"
    assert html.index("offline-puzzles.js") < html.index('src="offline.js"'), (
        "数据必须在引擎之前加载，否则 OFFLINE_PUZZLES 会是空的"
    )


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


def test_piece_ids_keep_identity_across_duplicate_occurrences() -> None:
    """同一枚棋子在 document 内出现多次时，重编号后必须仍是同一个新 id。

    被吃的子会同时出现在 `state.captured`（阵亡池，升变/复活按 id 删）与
    `history[].captured`（着法记录）。这两处描述的是**同一实体**，原 id 相同；
    若生成器逐次重编号，它就会被拆成两个身份 —— 这正是 2026-11 那两道题
    （`endgame-elephant-eye-01` / `endgame-advisor-palace-01`）的历史差异。
    """
    payload = _offline_payload()
    problems: list[str] = []
    for puzzle in load_puzzles():
        original = _piece_paths(puzzle.document)
        generated = _piece_paths(payload[puzzle.id]["document"])
        assert set(original) == set(generated), (
            f"{puzzle.id}: 内外结构路径不一致，缺 {sorted(set(original) - set(generated))}，"
            f"多 {sorted(set(generated) - set(original))}"
        )
        forward: dict[str, set[str]] = {}
        backward: dict[str, set[str]] = {}
        for path, piece in original.items():
            forward.setdefault(piece["id"], set()).add(generated[path]["id"])
            backward.setdefault(generated[path]["id"], set()).add(piece["id"])
        split = {old: new for old, new in forward.items() if len(new) > 1}
        merged = {new: old for new, old in backward.items() if len(old) > 1}
        if split:
            problems.append(f"{puzzle.id}: 同一原 id 被拆成多个新 id -> {split}")
        if merged:
            problems.append(f"{puzzle.id}: 不同原 id 被合并成同一新 id -> {merged}")
    assert not problems, "棋子 id 身份不一致：\n  " + "\n  ".join(problems)


def test_piece_ids_are_dense_and_unique_per_puzzle() -> None:
    """每题的新 id 号段必须是 `p0001…pN` 连续、且 N == 该题实体数。

    实体数按**去重后的原 id** 计：同一实体多处出现只算一个编号。
    这条与上一条互补 —— 上一条盯「身份」，这条盯「号段不重不漏」。
    """
    payload = _offline_payload()
    problems: list[str] = []
    for puzzle in load_puzzles():
        original = _piece_paths(puzzle.document)
        generated = _piece_paths(payload[puzzle.id]["document"])
        entities = len({piece["id"] for piece in original.values()})
        new_ids = {piece["id"] for piece in generated.values()}
        expected = {f"p{index:04d}" for index in range(1, entities + 1)}
        if len(new_ids) != entities:
            problems.append(f"{puzzle.id}: 新 id 数量 {len(new_ids)} != 实体数 {entities}")
        elif new_ids != expected:
            problems.append(
                f"{puzzle.id}: 号段不连续，缺 {sorted(expected - new_ids)}，多 {sorted(new_ids - expected)}"
            )
    assert not problems, "棋子 id 号段不健康：\n  " + "\n  ".join(problems)

