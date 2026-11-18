/**
 * 星轨**训练态守卫**行为探针（由 tests/test_star_hints_training_guard.py 驱动）。
 *
 * 回答一个行为问题：**章节闯关（scored=false）时，星轨几何层会不会显形？**
 *
 * 做法是从 `webapp/js/ui/app.js` 里**原样抠出** `showStarHints` 的判定表达式，
 * 放进一个只有 mock 上下文的函数里求值。刻意**不复刻**判定逻辑 ——
 * 复刻了就等于用第二份实现自证，守卫会假绿；这里求值的就是产物本体里那段代码，
 * 谁把 `&& !app.puzzle` 改成 `&& !app.puzzle.scored`，探针立刻看出来。
 *
 * 抠取方式：按 `const selectedPiece` → `const showStarHints = Boolean(` 定位，
 * 再用括号配平扫出 `Boolean(...)` 的闭合括号，两段拼成一个最小可求值片段。
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';

const appPath = process.argv[2];
if (!appPath) throw new Error('用法：node star_hints_guard_probe.mjs <webapp/js/ui/app.js>');

const source = readFileSync(path.resolve(appPath), 'utf8');

const selectedStart = source.indexOf('const selectedPiece');
if (selectedStart < 0) throw new Error('webapp/js/ui/app.js 里找不到 `const selectedPiece`');
const showStart = source.indexOf('const showStarHints = Boolean(', selectedStart);
if (showStart < 0) throw new Error('webapp/js/ui/app.js 里找不到 `const showStarHints = Boolean(`');

const open = source.indexOf('(', showStart);
let depth = 0;
let close = -1;
for (let i = open; i < source.length; i += 1) {
  const ch = source[i];
  if (ch === '(') depth += 1;
  else if (ch === ')') {
    depth -= 1;
    if (depth === 0) { close = i; break; }
  }
}
if (close < 0) throw new Error('`Boolean(` 没有闭合，webapp/js/ui/app.js 结构变了');

// 片段 = selectedPiece 声明 + showStarHints 声明（含结尾的 `;`）。
const body = source.slice(selectedStart, close + 2);
const evaluator = new Function('app', 'state', 'profile', 'isReplay', `${body}\nreturn showStarHints;`);

const makeApp = (puzzle) => ({
  prefs: { starHints: true },
  game: { rules: { options: { archer_enhanced_mode: false } } },
  selected: { row: 8, col: 8 },
  puzzle,
  replay: { open: false },
});
const state = { pieces: [{ row: 8, col: 8, type: 'archer' }] };
const profile = { rows: 13 };

const scenarios = {
  // 常规对局（不在训练态）：星轨**应当**显形 —— 用来证明探针不是恒假的空门禁。
  normal: makeApp(null),
  // 章节闯关：scored=false。星轨几何层**必须**仍然屏蔽（这条线只放开文字提示层）。
  chapter: makeApp({ data: {}, step: 0, scored: false, streak: false, misses: 0, hints: 0 }),
  // 每日一题：scored=true。屏蔽。
  daily: makeApp({ data: {}, step: 0, scored: true, streak: false, misses: 0, hints: 0 }),
  // 连对挑战：scored=true + streak。屏蔽。
  streak: makeApp({ data: {}, step: 0, scored: true, streak: true, misses: 0, hints: 0 }),
};

const output = {};
for (const [name, app] of Object.entries(scenarios)) {
  output[name] = Boolean(evaluator(app, state, profile, false));
}

process.stdout.write(JSON.stringify(output));
