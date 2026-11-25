"""webapp：换棋谱必须作废逐手分析（否则旧档位贴到新棋谱上）。

`app.analysis` 是**按 ply 下标寻址**的分析结果，`drawReplay` 靠
`app.analysis[index].quality` 给棋谱条目挂 `q-<quality>` 底色。原先只有
`startGame` / `enterOnline` / `useEntry` 三处清空，`startPuzzle`（残局/每日题
会整个换掉 `app.game`）、`restoreSession`（读档换 `app.game`）与**导入棋谱**
（`#fileInput.onchange`）都没清 —— 分析完一局再开一道题或导入另一份棋谱、点复盘，
棋谱列表的第 N 手会挂上**上一局**的档位底色。显示错信息且不报错，正是最该守的
一类静默故障。

两条口径：
1. 凡是**替换 `app.game`** 的入口都要调 `resetAnalysis()`；
2. `openReplay` **不能**清 —— 复盘正是分析结果的唯一显示面，清了就等于把功能删了。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "webapp" / "js" / "ui" / "app.js"

# 所有会替换 app.game 的入口（换局 / 重开 / 开题 / 联机 / 读档；重开与退出题目
# 都经由 startGame，退出联机经由 startGame，故不单列）。
GAME_REPLACING_ENTRIES = (
    "startGame",
    "startPuzzle",
    "enterOnline",
    "useEntry",
    "restoreSession",
)


def _source() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def test_reset_analysis_clears_result_and_invalidates_inflight_worker() -> None:
    body = _function_body(_source(), "resetAnalysis")
    assert "app.analysis = null" in body, "resetAnalysis 必须清空 app.analysis"
    assert "app.analysisId += 1" in body, (
        "resetAnalysis 必须递增 analysisId，否则换局在途的旧分析结果回来时仍会补写"
    )


def test_every_game_replacing_entry_resets_analysis() -> None:
    source = _source()
    missing = [name for name in GAME_REPLACING_ENTRIES if "resetAnalysis()" not in _function_body(source, name)]
    assert not missing, "这些入口换了 app.game 却没作废旧分析：" + ", ".join(missing)


def test_import_document_handler_resets_analysis() -> None:
    """导入棋谱（`#fileInput.onchange`）也是换棋谱，且是最贴近用户报障的一条。"""
    source = _source()
    start = source.index("$('#fileInput').onchange")
    handler = source[start:source.index("\n  };\n", start)]
    assert "app.game = gameFromDocument(" in handler
    assert "resetAnalysis()" in handler, "导入棋谱后旧分析仍会贴到新棋谱上"


def test_no_game_assignment_escapes_the_invariant() -> None:
    """所有 `app.game = ...` 赋值点必须在邻近处作废旧分析。

    `applyRemote` 是唯一例外：联机续走只**追加**历史，第 k 手之前的局面没变，
    已有分析的 ply 下标依然对得上，清了反而白丢结果。
    """
    lines = _source().splitlines()
    uncovered: list[str] = []
    for index, line in enumerate(lines):
        if "app.game = " not in line:
            continue
        window = "\n".join(lines[index : index + 15])
        if "resetAnalysis()" in window:
            continue
        enclosing = next((f for f in reversed(lines[: index + 1]) if f.startswith("function ")), "")
        if enclosing.startswith("function applyRemote("):
            continue
        uncovered.append(f"app.js:{index + 1}（{enclosing.strip() or '模块顶层'}）")
    assert not uncovered, "这些 app.game 赋值点没作废旧分析：" + "；".join(uncovered)


def test_open_replay_keeps_analysis() -> None:
    body = _function_body(_source(), "openReplay")
    assert "resetAnalysis()" not in body, (
        "openReplay 不得清空分析：复盘正是档位底色的唯一显示面，清了功能就没了"
    )


def test_replay_list_only_paints_quality_when_analysis_exists() -> None:
    body = _function_body(_source(), "drawReplay")
    assert "app.analysis && app.analysis[index]" in body, (
        "drawReplay 必须在 app.analysis 为空时不挂 q-<quality> 类"
    )
