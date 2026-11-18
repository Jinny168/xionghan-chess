"""webapp 每日一题接线守卫：题库同源 + UI 接线 + 零采集。

算法等价由 test_daily_parity.py 的 365 天逐日对拍钉死；本文件守：
1. webapp/js/data/puzzles.js 由 core 生成（--check 绿），不手改；
2. UI 接线闭合（按钮 → openDaily → startPuzzle → 完成记录 → 刷新）；
3. 零采集（daily.js 无网络、只写 localStorage 单键 xh-daily）。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "webapp" / "js" / "ui" / "app.js"
DAILY_JS = ROOT / "webapp" / "js" / "ui" / "daily.js"
INDEX_HTML = ROOT / "webapp" / "index.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_web_puzzles_generated_from_core_source() -> None:
    """题库必须与 core/data/puzzles.json 同源（build_web_puzzles --check 绿）。"""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_web_puzzles.py"), "--check"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"webapp 题库与 core 分叉：{proc.stdout}{proc.stderr}"


def test_all_web_puzzles_load_and_first_move_is_legal_in_js_engine() -> None:
    """35 条题在 JS 引擎里必须都能开局、首着合法（题库格式转换成立的前提）。

    用 node 原生脚本跑，不引入新依赖；脚本内联在临时文件，跑完即删。
    """
    script = """
import { PUZZLES } from '../js/data/puzzles.js';
import { Game } from '../js/core/game.js';
import { getProfile } from '../js/core/profiles.js';
import { makePiece, createState } from '../js/core/model.js';
let ok = 0, bad = [];
for (const p of PUZZLES) {
  try {
    const profile = getProfile(p.profileId);
    const pieces = (p.pieces||[]).map(x=>makePiece(x.type,x.color,x.row,x.col));
    const state = createState(profile.id, pieces, p.turn||'red');
    const g = new Game(profile, profile.options, {state});
    const legal = g.rules.legalMoves(g.state, g.state.turn);
    const first = p.solution[0];
    const key = m => `${m.source.row},${m.source.col}-${m.target.row},${m.target.col}`;
    const hit = legal.find(m=>key(m)===`${first.from.row},${first.from.col}-${first.to.row},${first.to.col}`);
    if (!hit) bad.push(p.id + ':first-illegal'); else ok++;
  } catch (e) { bad.push(p.id + ':' + String(e.message).slice(0,40)); }
}
console.log(JSON.stringify({ok, total: PUZZLES.length, bad}));
"""
    probe = ROOT / "webapp" / "tests" / "_tmp_verify_puzzles.mjs"
    probe.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            ["node", str(probe)], cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
        result = json.loads(proc.stdout)
    finally:
        probe.unlink(missing_ok=True)
    assert result["ok"] == result["total"], f"题目无法开局/首着非法：{result['bad']}"


def test_daily_ui_wiring_is_closed() -> None:
    app = _read(APP_JS)
    daily = _read(DAILY_JS)
    html = _read(INDEX_HTML)
    # 按钮在 HTML 中存在并绑定
    assert 'id="dailyPuzzleButton"' in html
    assert "dailyButton.onclick = openDaily" in app
    # openDaily 走 pickDaily + startPuzzle（复用现成做题流程）
    assert "pickDaily(PUZZLES, today)" in app
    assert "startPuzzle(puzzle)" in app
    # 完成分支记录连续天数
    assert "recordDailySolved(data)" in app
    assert "solveToday(record" in daily
    # 题库列表打开时刷新按钮状态
    assert "refreshDailyButton();" in app


def test_daily_has_no_telemetry_and_uses_single_local_key() -> None:
    daily = _read(DAILY_JS)
    for token in ("fetch(", "XMLHttpRequest", "sendBeacon", "analytics", "track("):
        assert token not in daily, f"每日题不得引入网络/采集: {token}"
    assert "localStorage.setItem(DAILY_KEY" in daily
    assert "export const DAILY_KEY = 'xh-daily'" in daily  # 与 core/旧树同字段名
    # 只写这一个键，不按天堆键
    assert daily.count("localStorage.setItem(") == 1


def test_daily_i18n_keys_present_in_both_languages() -> None:
    i18n = _read(ROOT / "webapp" / "js" / "i18n.js")
    for key in ("puzzle.daily", "puzzle.daily_done", "puzzle.daily_streak", "puzzle.daily_solved", "puzzle.daily_empty"):
        assert i18n.count(f"'{key}'") == 2, f"{key} 应在 zh/en 各出现一次"
