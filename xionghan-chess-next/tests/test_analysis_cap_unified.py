"""三端复盘分析上限统一到 120 + Web 旧树「真被截断才出现」的覆盖提示。

三端一致不靠 codegen，而靠本文件的三道断言（漂移即红）：
1. `core/analysis.py::ANALYSIS_PLY_CAP == 120`，且 `analyze_game` 的默认值取自它；
   服务端显式传参、`AnalyzeRequest` 两字段不变、桌面 import 同一常量、Webapp
   `const CAP` 与它相等（Webapp 文件不动，只读断言）。
2. **真取词**：把 `web/js/i18n.js` 复制成 `.mjs` 真 import，stub `fetch` 读磁盘上
   真实的 `locales/*.json`，跑 `setLanguage()`，确认 `t('analysis.capped', {n: 120})`
   在中英两侧都返回文案而不是裸键（与 `fix-naked-key` 同类守卫）。
3. **真渲染**：从 `web/js/app.js` 抽出**真实的** `renderAnalysis` 源码，注入真实 `t()`
   与假 DOM，构造「截断 / 恰好等于上限 / 未截断」三种结果，确认提示只在第一种出现，
   且 `{n}` 被替换成数字而非字面量。判据用 `analyzedPlies < history.length`，
   不硬编码 120；`n` 取服务端实际分析手数。
"""

from __future__ import annotations

import inspect
import re
import subprocess
from pathlib import Path

from _node_guard import module_skip_mark, require_node

if (mark := module_skip_mark()) is not None:
    pytestmark = mark

ROOT = Path(__file__).resolve().parents[1]

# i18n.js 用 ESM `export`；仓库没有 `"type": "module"`，Node 会把 `.js` 当 CJS。
# 复制到临时目录的 `.mjs` 再真 import，不改原文件。
PROBE = r"""
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const [root, i18nPath, mode] = process.argv.slice(2);

// setLanguage() → applyStaticI18n() 会碰这些浏览器 API，给最小可用桩。
globalThis.Node = { TEXT_NODE: 3 };
globalThis.document = {
  title: '',
  documentElement: { lang: '' },
  querySelectorAll: () => [],
  querySelector: () => null,
  getElementById: () => null,
};
const store = new Map();
globalThis.localStorage = {
  getItem: (key) => store.get(key) ?? null,
  setItem: (key, value) => store.set(key, String(value)),
  removeItem: (key) => store.delete(key),
};

// 真取词的关键：fetch 读的是磁盘上真实的 locales/*.json，不是测试里重写的假词表。
globalThis.fetch = async (url) => {
  const match = /\/locales\/([^/]+)\.json/.exec(String(url));
  if (!match) throw new Error(`unexpected fetch: ${url}`);
  const text = readFileSync(`${root}/locales/${match[1]}.json`, 'utf8');
  return { ok: true, json: async () => JSON.parse(text) };
};

const { t, setLanguage } = await import(pathToFileURL(i18nPath).href);

if (mode === 'i18n') {
  await setLanguage('zh-CN');
  console.log(`zh|${t('analysis.capped', { n: 120 })}`);
  await setLanguage('en');
  console.log(`en|${t('analysis.capped', { n: 120 })}`);
} else if (mode === 'render') {
  const src = readFileSync(`${root}/web/js/app.js`, 'utf8');
  const start = src.indexOf('function renderAnalysis(');
  if (start < 0) throw new Error('renderAnalysis not found');
  const brace = src.indexOf('{', start);
  let depth = 0;
  let end = -1;
  for (let i = brace; i < src.length; i++) {
    if (src[i] === '{') depth += 1;
    else if (src[i] === '}') {
      depth -= 1;
      if (depth === 0) { end = i + 1; break; }
    }
  }
  if (end < 0) throw new Error('renderAnalysis braces unbalanced');
  const fnSrc = src.slice(start, end);

  const nodes = {
    '#analysisLoading': { hidden: false },
    '#analysisContent': { hidden: true },
    '#analysisMoveList': { innerHTML: '' },
    '#analysisCapped': { hidden: true, textContent: '' },
  };
  const $ = (selector) => nodes[selector] ?? null;
  const app = { state: { history: [] }, lastAnalysisResult: null };

  await setLanguage('zh-CN');  // 用真词表跑真渲染
  const render = new Function('$', 't', 'app', `${fnSrc}\nreturn renderAnalysis;`)($, t, app);

  const cases = [
    ['truncated', 200, 120],       // 被截断：analyzedPlies < history.length
    ['at-cap', 120, 120],          // 恰好等于上限：不误报
    ['not-truncated', 80, 80],     // 未截断：不显示
  ];
  for (const [label, historyLen, analyzedPlies] of cases) {
    nodes['#analysisCapped'].hidden = true;
    nodes['#analysisCapped'].textContent = '';
    app.state.history = new Array(historyLen);
    render({ analyzedPlies, moves: [] });
    const node = nodes['#analysisCapped'];
    console.log(`${label}|hidden=${node.hidden}|text=${node.textContent}`);
  }

  // 语言切换后对已打开弹窗重跑渲染，提示也应跟着换成英文
  await setLanguage('en');
  app.state.history = new Array(200);
  nodes['#analysisCapped'].hidden = true;
  nodes['#analysisCapped'].textContent = '';
  render({ analyzedPlies: 120, moves: [] });
  console.log(`en-truncated|hidden=${nodes['#analysisCapped'].hidden}|text=${nodes['#analysisCapped'].textContent}`);
} else {
  throw new Error(`unknown mode: ${mode}`);
}
"""


def _run_probe(tmp_path: Path, mode: str) -> str:
    require_node()
    i18n_copy = tmp_path / "i18n_probe.mjs"
    i18n_copy.write_text((ROOT / "web/js/i18n.js").read_text(encoding="utf-8"), encoding="utf-8")
    probe = tmp_path / "probe.mjs"
    probe.write_text(PROBE, encoding="utf-8")
    completed = subprocess.run(
        ["node", str(probe), str(ROOT), str(i18n_copy), mode],
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


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_analysis_cap_is_single_source_across_three_ends() -> None:
    """上限 120 是单一常量；服务端显式传、桌面 import、Webapp 只被断言防漂。"""
    from xionghan_chess.core.analysis import ANALYSIS_PLY_CAP, analyze_game

    assert ANALYSIS_PLY_CAP == 120
    assert inspect.signature(analyze_game).parameters["max_plies"].default == ANALYSIS_PLY_CAP, (
        "analyze_game 的 max_plies 默认值漂离 ANALYSIS_PLY_CAP —— 服务端一旦走默认值就重新分叉"
    )

    app_src = _read("src/xionghan_chess/service/app.py")
    assert "from xionghan_chess.core.analysis import ANALYSIS_PLY_CAP, analyze_game" in app_src
    assert "to_thread(analyze_game, game, request.difficulty, ANALYSIS_PLY_CAP)" in app_src, (
        "服务端调用点没有显式传上限"
    )
    request = re.search(r"class AnalyzeRequest\([^)]*\):\n((?:[ \t]+.*\n?)+)", app_src)
    assert request, "找不到 AnalyzeRequest 定义"
    assert "max_plies" not in request.group(1), "AnalyzeRequest 字段被改了：禁止让客户端传 max_plies"
    assert "document" in request.group(1) and "difficulty" in request.group(1)

    workers_src = _read("src/xionghan_chess/desktop/ui/workers.py")
    assert "from xionghan_chess.core.analysis import ANALYSIS_PLY_CAP, analyze_game" in workers_src
    assert "ANALYSIS_PLY_CAP = 120" not in workers_src, "桌面又留了第二份上限字面量"

    webapp = _read("webapp/js/ui/app.js")
    match = re.search(r"const CAP\s*=\s*(\d+)\s*;", webapp)
    assert match, "webapp 里找不到 const CAP"
    assert int(match.group(1)) == ANALYSIS_PLY_CAP, "webapp 的 const CAP 与 core 上限不一致（漂移即红）"


def test_capped_key_really_resolves_in_both_locales(tmp_path: Path) -> None:
    """真 import i18n.js + 真读 locales：中英都要拿到文案，不能是裸键 analysis.capped。"""
    output = _run_probe(tmp_path, "i18n")
    lines = [line for line in output.splitlines() if line.startswith(("zh|", "en|"))]
    assert len(lines) == 2, f"探针没输出两行取词结果：\n{output}"
    zh = lines[0].split("|", 1)[1]
    en = lines[1].split("|", 1)[1]
    assert zh == "（仅分析前 120 手）", f"中文真取词失败（裸键/未替换）：{zh!r}"
    assert en == "(first 120 plies only)", f"英文真取词失败（裸键/未替换）：{en!r}"
    assert "analysis.capped" not in (zh + en)
    assert "{n}" not in (zh + en), "{n} 没被替换"


def test_render_analysis_shows_capped_only_when_truncated(tmp_path: Path) -> None:
    """真执行 renderAnalysis：只有 analyzedPlies < history.length 才出现提示。"""
    output = _run_probe(tmp_path, "render")
    rows: dict[str, tuple[str, str]] = {}
    for line in output.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3 and parts[1].startswith("hidden=") and parts[2].startswith("text="):
            rows[parts[0]] = (parts[1][len("hidden=") :], parts[2][len("text=") :])
    assert {"truncated", "at-cap", "not-truncated", "en-truncated"} <= set(rows), (
        f"探针没输出完整三态 + 英文态：\n{output}"
    )
    assert rows["truncated"] == ("false", "（仅分析前 120 手）")
    assert rows["at-cap"] == ("true", ""), "恰好等于上限被误报为截断"
    assert rows["not-truncated"] == ("true", ""), "未截断却显示了提示"
    assert rows["en-truncated"] == ("false", "(first 120 plies only)")
    assert "{n}" not in output, "渲染结果里出现了字面量 {n}（t() 调用漏了 params）"


def test_capped_has_display_node_but_no_settext_registration() -> None:
    """capped 必须走 renderAnalysis 带参写入，不能挂 setText（t(key) 不带 params）。"""
    i18n = _read("web/js/i18n.js")
    assert "analysis.capped" not in i18n, (
        "capped 禁止进 setText 登记：t(key) 不带 params，会把 {n} 原样显示成字面量"
    )
    app = _read("web/js/app.js")
    assert "t('analysis.capped',{n:result.analyzedPlies})" in app, (
        "n 必须取服务端实际分析手数 result.analyzedPlies，不能写死上限"
    )
    assert "result.analyzedPlies<app.state.history.length" in app, "截断判据必须用服务端实际结果"
    assert 'id="analysisCapped"' in _read("web/index.html"), "Web 缺 capped 显示节点"
