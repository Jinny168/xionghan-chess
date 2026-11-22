"""webapp：换棋谱必须作废逐手分析（否则旧档位贴到新棋谱上）。

`app.analysis` 是**按 ply 下标寻址**的分析结果，`drawReplay` 靠
`app.analysis[index].quality` 给棋谱条目挂 `q-<quality>` 底色。原先只有
`startGame` / `enterOnline` / `useEntry` 三处清空，`startPuzzle`（残局/每日题
会整个换掉 `app.game`）和 `restoreSession`（读档换 `app.game`）没清 —— 分析完
一局再开一道题、点复盘，题目列表的第 N 手会挂上**上一局**的档位底色。显示错
信息且不报错，正是最该守的一类静默故障。

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
