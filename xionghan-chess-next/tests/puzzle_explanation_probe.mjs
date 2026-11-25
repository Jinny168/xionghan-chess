// Webapp 解析接线的真行为探针：真 import 生产模块、真走 app.puzzle.data.hints 链路，
// 由 tests/test_puzzle_explanations.py 用 node 执行并断言输出。
import assert from 'node:assert/strict';

import { PUZZLES } from '../webapp/js/data/puzzles.js';
import { PUZZLE_EXPLANATIONS } from '../webapp/js/data/puzzle_explanations.js';
import { withExplanation, hintAt } from '../webapp/js/ui/puzzle_explanation.js';

const gen = PUZZLES.filter((p) => p.id.startsWith('gen-'));
const drill = PUZZLES.filter((p) => !p.id.startsWith('gen-'));
assert.equal(gen.length, 35);
assert.equal(drill.length, 13);
assert.deepEqual(Object.keys(PUZZLE_EXPLANATIONS).sort(), gen.map((p) => p.id).sort());

const puzzle = gen.find((p) => p.id === 'gen-01');
const original = puzzle.hints.slice();
const hints = withExplanation(puzzle.hints, puzzle.id);
assert.equal(hints.length, original.length + 1, '解析必须作为最后一条追加');
assert.deepEqual(hints.slice(0, -1), original, '指路提示必须保持原顺序');
assert.deepEqual(puzzle.hints, original, '题库数据不能被接线改掉');

const expected = `${PUZZLE_EXPLANATIONS['gen-01'].key_move}\n${PUZZLE_EXPLANATIONS['gen-01'].why}`;
assert.equal(hints[hints.length - 1], expected);

// 真行为：答完题（step 越过原提示数）点提示 → 界面揭示解析。
const shown = hintAt(hints, puzzle.solution.length, puzzle.desc);
assert.equal(shown, expected, '答完题后揭示的不是解析文字');
assert.ok(shown.includes(PUZZLE_EXPLANATIONS['gen-01'].why), '解析正文没出现');
assert.ok(!/^(正确答案|AI\s*分析|为什么)[:：]/.test(shown), '出现了额外的权威前缀');
assert.ok(!/你应该/.test(shown), '出现指令式措辞');
assert.ok(!/\d+\s*分/.test(shown), '出现精确分值');

for (const item of gen) {
  const appended = withExplanation(item.hints, item.id);
  assert.equal(
    appended[appended.length - 1],
    `${PUZZLE_EXPLANATIONS[item.id].key_move}\n${PUZZLE_EXPLANATIONS[item.id].why}`,
    `${item.id} 没接到解析`,
  );
}
for (const item of drill) {
  assert.deepEqual(withExplanation(item.hints, item.id), item.hints || [], `${item.id} 误接入解析`);
}

console.log(JSON.stringify({
  gen: gen.length,
  drill: drill.length,
  appended: hints.length - original.length,
  shownHasWhy: shown.includes(PUZZLE_EXPLANATIONS['gen-01'].why),
  forbidden: /你应该|\d+\s*分|^(正确答案|AI\s*分析|为什么)[:：]/.test(shown),
}));
