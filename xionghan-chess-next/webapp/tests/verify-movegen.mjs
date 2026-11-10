#!/usr/bin/env node
/**
 * 快速着法生成器 ↔ 参考实现交叉校验。
 *
 * 用与 verify-rules.mjs 相同的黄金用例，比较：
 *   RulesEngine.legalMoves（逐格枚举，参考实现）
 *   legalMovesFast       （攻击形状生成 + isLegal 过滤）
 * 两者必须给出完全相同的着法集合。
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { stateFromDict, moveKey } from '../js/core/model.js';
import { getProfile, mergeOptions } from '../js/core/profiles.js';
import { RulesEngine } from '../js/core/rules.js';
import { legalMovesFast } from '../js/core/movegen.js';

const here = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(join(here, 'fixtures', 'rules.json'), 'utf8'));

const failures = [];
let cases = 0;
let total = 0;
let slowMs = 0;
let fastMs = 0;

for (const testCase of fixture.cases) {
  cases += 1;
  const state = stateFromDict(testCase.state);
  const profile = getProfile(testCase.profileId);
  const engine = new RulesEngine(profile, mergeOptions(profile.options, testCase.options));

  const t0 = performance.now();
  const reference = engine.legalMoves(state).map(moveKey).sort();
  const t1 = performance.now();
  const fast = legalMovesFast(state, engine).map(moveKey).sort();
  const t2 = performance.now();
  slowMs += t1 - t0;
  fastMs += t2 - t1;
  total += reference.length;

  if (reference.length !== fast.length || reference.some((k, i) => k !== fast[i])) {
    const missing = reference.filter((k) => !fast.includes(k));
    const extra = fast.filter((k) => !reference.includes(k));
    if (failures.length < 20) {
      failures.push({ id: testCase.id, missing: missing.slice(0, 10), extra: extra.slice(0, 10) });
    }
  }
}

if (failures.length) {
  console.error(`\n✗ 快速生成器与参考实现不一致：${failures.length} 处\n`);
  for (const item of failures) {
    console.error(item.id, JSON.stringify(item));
  }
  process.exit(1);
}

console.log('✓ 快速生成器与参考实现一致');
console.log(`  比对局面   ${cases}`);
console.log(`  着法总数   ${total}`);
console.log(`  参考耗时   ${slowMs.toFixed(0)} ms`);
console.log(`  快速耗时   ${fastMs.toFixed(0)} ms  （${(slowMs / fastMs).toFixed(1)}×）`);
