/**
 * 离屏调试桥静态门禁（批次 G）。
 *
 * 仅对 `web/js/app.js` 做源码静态断言，不在 Node 里执行该模块（它依赖 DOM /
 * localStorage，离屏无头环境无法直接加载）。校验四条：
 *
 *  1. 桥只在 `window.__XH_DEBUG__ === 'offscreen'` 条件内挂载；
 *  2. 无标记时不产生 `window.__xh`（除条件块外无第二处赋值）；
 *  3. 桥不在任何 export / 公开 API 清单里；
 *  4. 条件块体生产路径零副作用（不写 storage、不改 DOM）。
 *
 * 退出码：全部通过 0；任一失败 1。可独立运行：`node scripts/verify_debug_bridge.mjs`。
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const appJs = join(here, '..', 'web', 'js', 'app.js');
const source = readFileSync(appJs, 'utf-8');

const failures = [];

/** 从首个 `if (...) {` 起按大括号配平，取出块体文本；取不到返回 null。 */
function extractIfBlock(text, ifHead) {
  const headIndex = text.search(ifHead);
  if (headIndex < 0) return null;
  const openBrace = text.indexOf('{', headIndex);
  if (openBrace < 0) return null;
  let depth = 0;
  for (let i = openBrace; i < text.length; i += 1) {
    if (text[i] === '{') depth += 1;
    else if (text[i] === '}') {
      depth -= 1;
      if (depth === 0) return text.slice(openBrace + 1, i);
    }
  }
  return null;
}

// 1. 条件包裹存在，且桥成员在条件块体内。
const block = extractIfBlock(source, /if\s*\(\s*window\.__XH_DEBUG__\s*===\s*'offscreen'\s*\)/);
if (block === null) {
  failures.push("未找到 `if (window.__XH_DEBUG__ === 'offscreen')` 条件块");
} else {
  if (!/window\.__xh\s*=\s*\{\s*app,\s*draw,\s*resizeBoard,\s*geometry\s*\}/.test(block)) {
    failures.push('条件块内未按约定挂载 `window.__xh = { app, draw, resizeBoard, geometry }`');
  }
}

// 2. `window.__xh` 赋值语句只出现一次（注释里的提及不计），没有第二处挂载。
const assignments = source.match(/window\.__xh\s*=/g) || [];
if (assignments.length !== 1) {
  failures.push(`window.__xh 赋值 ${assignments.length} 处，应为仅桥块内 1 处（无标记时不挂全局）`);
}

// 3. 桥不进入 export / 公开 API 清单。
const exportLeaks = source.match(/export\s*(default|const|function|let|var|\{)/g) || [];
if (exportLeaks.length > 0) {
  failures.push(`app.js 出现 export 泄漏：${exportLeaks.join(', ')}`);
}
const exportXh = source.split('\n').some((line) => line.includes('export') && line.includes('__xh'));
if (exportXh) {
  failures.push('`__xh` 与 `export` 出现在同一行：调试桥不得进入公开导出');
}

// 4. 条件块体零副作用：不写 storage、不改 DOM。
if (block !== null) {
  for (const forbidden of ['localStorage', 'setItem', 'sessionStorage', 'document.']) {
    if (block.includes(forbidden)) {
      failures.push(`桥条件块体内出现生产副作用项 \`${forbidden}\``);
    }
  }
}

if (failures.length > 0) {
  console.error('[verify-debug-bridge] 失败：');
  for (const f of failures) console.error('  ✗ ' + f);
  process.exit(1);
}

console.log('[verify-debug-bridge] ✓ 桥条件包裹 / 无第二处挂载 / 无 export 泄漏 / 零副作用');
