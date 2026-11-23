"""webapp：截断提示必须取「原始 history」，而非恒假的 results.length。

缺陷背景：`runAnalysis` 先把总数截到 CAP（`Math.min(history.length, CAP)`），worker
一状态一结果，故 `results.length <= CAP` 恒成立 —— 旧判据 `results.length > CAP`
永远为假，200 手棋也拿不到「仅分析前 N 手」提示，与 2.2.1 更新日志不实承诺。

本文件从 `webapp/js/ui/app.js` **抽取真实源码**注入假 DOM / 假 CAP 真执行：
1. 三态（200 / 120 / 80）断言提示只在 200 出现，恰好 120 不误报；
2. 换局后标志随 `resetAnalysis()` 作废，不把上一局的 true 贴到新局；
3. 静态断言标志取自 Math.min 之前的原始 history，且 finishAnalysis 不再用
   `results.length > CAP`（反向验证：改回旧判据，真执行用例必须红）。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from _node_guard import module_skip_mark, require_node

if (mark := module_skip_mark()) is not None:
    pytestmark = mark

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "webapp" / "js" / "ui" / "app.js"


# 探针：抽取 app.js 里三个真实函数，用假 DOM / 假 t / 假 worker 真执行。
# 结果条数严格取 postMessage 的 states 长度（worker 一状态一结果，恒 <= CAP），
# 不另造一个「> CAP」的假结果来迎合旧判据。
PROBE = r"""
import { readFileSync } from 'node:fs';

const [root] = process.argv.slice(2);
const src = readFileSync(`${root}/webapp/js/ui/app.js`, 'utf8');

function extract(name) {
  const marker = `function ${name}(`;
  const start = src.indexOf(marker);
  if (start < 0) throw new Error(`missing function ${name}`);
  const brace = src.indexOf('{', start);
  let depth = 0;
  for (let i = brace; i < src.length; i++) {
    if (src[i] === '{') depth += 1;
    else if (src[i] === '}') {
      depth -= 1;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error(`unbalanced braces: ${name}`);
}

const capMatch = /^const CAP = (\d+);$/m.exec(src);
if (!capMatch) throw new Error('missing module-level const CAP');
const CAP = Number(capMatch[1]);
const srcs = ['resetAnalysis', 'runAnalysis', 'finishAnalysis'].map(extract).join('\n');

const nodes = {
  '#analysisProgress': { hidden: true },
  '#analysisProgressText': { textContent: '' },
  '#analysisSummary': { hidden: true, textContent: '' },
};
const $ = (sel) => nodes[sel] ?? null;
const t = (key, params = {}) => {
  const table = {
    'analysis.running': () => `RUNNING(${params.done}/${params.total})`,
    'analysis.done': () => `DONE(${params.n})`,
    'analysis.capped': () => `CAPPED(${params.n})`,
    'analysis.failed': () => 'FAILED',
    'analysis.empty': () => 'EMPTY',
  };
  return (table[key] || (() => key))();
};
const toast = () => {};
const analysisFailed = () => {};
const updateAnalysisProgress = ({ total }) => { progressTotal = total; };
const drawReplay = () => {};

let progressTotal = null;
let posted = null;

function makeApp(historyLen) {
  const history = Array.from({ length: historyLen }, (_, i) => ({
    move: { source: `s${i}`, target: `t${i}` },
    color: i % 2 ? 'black' : 'red',
    notation: `n${i}`,
  }));
  return {
    game: {
      state: { history },
      publicState: () => ({ replay: Array.from({ length: historyLen }, (_, i) => ({ ply: i })) }),
      profile: { id: 'probe' },
      options: {},
    },
    worker: { postMessage: (msg) => { posted = msg; } },
    analysis: null,
    analysisId: 0,
    analysisTruncated: false,
  };
}

function build(app) {
  const factory = new Function(
    'app', '$', 't', 'CAP', 'toast', 'analysisFailed', 'updateAnalysisProgress', 'drawReplay',
    `${srcs}\nreturn { resetAnalysis, runAnalysis, finishAnalysis };`,
  );
  return factory(app, $, t, CAP, toast, analysisFailed, updateAnalysisProgress, drawReplay);
}

function finishWithPostedResults(fns) {
  const results = Array.from({ length: posted.states.length }, () => ({ quality: 'best' }));
  fns.finishAnalysis(results);
  return results.length;
}

for (const historyLen of [200, 120, 80]) {
  const app = makeApp(historyLen);
  const fns = build(app);
  progressTotal = null;
  posted = null;
  fns.runAnalysis();
  const flag = app.analysisTruncated;
  const resultsLen = finishWithPostedResults(fns);
  const summary = nodes['#analysisSummary'].textContent;
  console.log(`WEBAPP|history=${historyLen}|total=${progressTotal}|results=${resultsLen}|flag=${flag}|capped=${summary.includes('CAPPED')}|summary=${summary}`);
}

// 换局：上一局 200 手留下 true，换局入口调 resetAnalysis 后必须清掉，
// 且随后的 80 手新局不得沿用旧标志误报。
{
  const app = makeApp(200);
  const fns = build(app);
  posted = null;
  fns.runAnalysis();
  const before = app.analysisTruncated;
  app.game = makeApp(80).game;
  fns.resetAnalysis();
  const afterReset = app.analysisTruncated;
  posted = null;
  fns.runAnalysis();
  const resultsLen = finishWithPostedResults(fns);
  const summary = nodes['#analysisSummary'].textContent;
  console.log(`SWITCH|before=${before}|afterReset=${afterReset}|newFlag=${app.analysisTruncated}|results=${resultsLen}|capped=${summary.includes('CAPPED')}|summary=${summary}`);
}
"""


def _source() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def _rows(output: str, prefix: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in output.splitlines():
        parts = line.split("|")
        if parts and parts[0] == prefix:
            fields = dict(field.split("=", 1) for field in parts[1:])
            key = fields.get("history") or prefix
            rows[key] = fields
    return rows


def _run_probe(tmp_path: Path) -> str:
    require_node()
    probe = tmp_path / "webapp_capped_probe.mjs"
    probe.write_text(PROBE, encoding="utf-8")
    completed = subprocess.run(
        ["node", str(probe), str(ROOT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert completed.returncode == 0, (
        f"node 探针失败 rc={completed.returncode}\n"
        f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
    )
    return completed.stdout


def test_flag_comes_from_original_history_and_reset_clears_it() -> None:
    source = _source()
    run = _function_body(source, "runAnalysis")
    finish = _function_body(source, "finishAnalysis")
    reset = _function_body(source, "resetAnalysis")

    assert "const truncated = history.length > CAP;" in run, (
        "必须用原始 history.length（在 Math.min 之前）记录截断标志"
    )
    assert run.index("const truncated = history.length > CAP;") < run.index(
        "const total = Math.min(history.length, CAP);"
    ), "截断标志必须在 Math.min 之前判定"
    assert run.index("resetAnalysis();") < run.index("app.analysisTruncated = truncated;"), (
        "置位必须在 resetAnalysis 之后，否则会被换局作废逻辑清掉"
    )
    assert "app.analysisTruncated = false;" in reset, "resetAnalysis 必须一并清截断标志"
    assert "app.analysisTruncated ?" in finish, "finishAnalysis 必须改用标志决定提示"
    assert not re.search(r"results\.length\s*>=?\s*CAP", finish), (
        "不得再用恒假的 results.length > CAP 判据"
    )
    assert "t('analysis.capped', { n: CAP })" in finish, "文案手数仍须取 CAP"


def test_three_states_real_execution(tmp_path: Path) -> None:
    rows = _rows(_run_probe(tmp_path), "WEBAPP")
    assert set(rows) == {"200", "120", "80"}, f"探针没输出完整三态：\n{rows}"

    assert rows["200"]["total"] == "120" and rows["200"]["results"] == "120"
    assert rows["200"]["flag"] == "true" and rows["200"]["capped"] == "true"
    assert "CAPPED(120)" in rows["200"]["summary"], "截断时 n 必须取 CAP（120）"

    assert rows["120"]["total"] == "120" and rows["120"]["results"] == "120"
    assert rows["120"]["flag"] == "false" and rows["120"]["capped"] == "false", (
        "恰好 120 手是全覆盖，不得误报截断"
    )

    assert rows["80"]["total"] == "80" and rows["80"]["results"] == "80"
    assert rows["80"]["flag"] == "false" and rows["80"]["capped"] == "false"


def test_switch_game_clears_truncated_flag(tmp_path: Path) -> None:
    rows = _rows(_run_probe(tmp_path), "SWITCH")
    assert list(rows) == ["SWITCH"], f"探针没输出换局证据：\n{rows}"
    data = rows["SWITCH"]
    assert data["before"] == "true", "200 手局必须置位"
    assert data["afterReset"] == "false", "换局必须随 analysisId 一并清标志"
    assert data["newFlag"] == "false", "换局后的 80 手新局不得沿用上一局的 true"
    assert data["capped"] == "false", "换局后新局不得误报截断"
