#!/usr/bin/env node
/**
 * 规则一致性门禁。
 *
 * 用 Python 内核导出的黄金用例（scripts/gen_rule_fixtures.py），逐局面比对
 * JS 端的合法着法全集与将军判定，并逐着法比对走子后的胜负结算。
 *
 * 运行：node webapp/tests/verify-rules.mjs
 * 退出码 0 = 全绿；1 = 存在不一致。
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { stateFromDict, moveKey } from '../js/core/model.js';
import { getProfile, mergeOptions } from '../js/core/profiles.js';
import { RulesEngine } from '../js/core/rules.js';
import { Game } from '../js/core/game.js';

const here = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(join(here, 'fixtures', 'rules.json'), 'utf8'));

const failures = [];
const stats = {
  cases: 0,
  transitions: 0,
  legalTotal: 0,
};

function fail(kind, id, detail) {
  if (failures.length < 25) failures.push({ kind, id, detail });
}

function buildEngine(profileId, options) {
  const profile = getProfile(profileId);
  if (!profile) throw new Error(`unknown profile ${profileId}`);
  const merged = mergeOptions(profile.options, options);
  return { profile, options: merged, engine: new RulesEngine(profile, merged) };
}

// ---------------------------------------------------------------- 局面比对
for (const testCase of fixture.cases) {
  stats.cases += 1;
  const state = stateFromDict(testCase.state);
  const { engine } = buildEngine(testCase.profileId, testCase.options);
  let legal;
  try {
    legal = engine.legalMoves(state).map(moveKey).sort();
  } catch (error) {
    fail('legal-throw', testCase.id, error.stack || String(error));
    continue;
  }
  stats.legalTotal += legal.length;
  const expected = testCase.legal.slice().sort();

  if (legal.length !== expected.length) {
    const missing = expected.filter((k) => !legal.includes(k));
    const extra = legal.filter((k) => !expected.includes(k));
    fail('legal-count', testCase.id, {
      expected: expected.length,
      actual: legal.length,
      missing: missing.slice(0, 12),
      extra: extra.slice(0, 12),
    });
    continue;
  }
  for (let i = 0; i < expected.length; i += 1) {
    if (legal[i] !== expected[i]) {
      const missing = expected.filter((k) => !legal.includes(k));
      const extra = legal.filter((k) => !expected.includes(k));
      fail('legal-diff', testCase.id, { missing: missing.slice(0, 12), extra: extra.slice(0, 12) });
      break;
    }
  }

  let check;
  try {
    check = engine.inCheck(state, state.turn);
  } catch (error) {
    fail('check-throw', testCase.id, error.stack || String(error));
    continue;
  }
  if (check !== testCase.check) {
    fail('check', testCase.id, { expected: testCase.check, actual: check });
  }
}

// ---------------------------------------------------------------- 走子结算
for (const item of fixture.transitions) {
  stats.transitions += 1;
  const before = stateFromDict(item.before);
  const { profile, options } = buildEngine(item.profileId, item.options);
  const game = new Game(profile, options, { state: before });
  const move = {
    source: { row: item.move.from.row, col: item.move.from.col },
    target: { row: item.move.to.row, col: item.move.to.col },
    promotion: item.move.promotion || null,
  };
  let record;
  try {
    record = game.move(move);
  } catch (error) {
    fail('move-throw', `${item.profileId}@${JSON.stringify(item.move)}`, error.message);
    continue;
  }
  const state = game.state;
  const actual = {
    turn: state.turn,
    winner: state.winner,
    draw: state.draw,
    reason: state.resultReason,
    capturedTypes: record.captured.map((p) => p.type).sort(),
    pieceCount: state.pieces.length,
    historyLength: state.history.length,
  };
  const expected = item.after;
  for (const key of Object.keys(expected)) {
    const a = JSON.stringify(actual[key]);
    const e = JSON.stringify(expected[key]);
    if (a !== e) {
      fail('settle', `${item.profileId}@${JSON.stringify(item.move)}`, { key, expected: expected[key], actual: actual[key] });
    }
  }
}

// ---------------------------------------------------------------- 汇总
const total = stats.cases + stats.transitions;
if (failures.length) {
  console.error(`\n✗ 规则比对失败：${failures.length} 处，前 ${failures.length} 条如下\n`);
  for (const item of failures) {
    console.error(`[${item.kind}] ${item.id}`);
    console.error(JSON.stringify(item.detail, null, 2));
    console.error('');
  }
  console.error(`局面 ${stats.cases} / 走子 ${stats.transitions} / 合法着法 ${stats.legalTotal}`);
  process.exit(1);
}

console.log('✓ 规则一致');
console.log(`  局面比对      ${stats.cases}`);
console.log(`  走子结算      ${stats.transitions}`);
console.log(`  合法着法总数  ${stats.legalTotal}`);
console.log(`  合计校验项    ${total}`);
