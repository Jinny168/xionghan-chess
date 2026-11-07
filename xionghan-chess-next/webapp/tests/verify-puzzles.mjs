#!/usr/bin/env node
/**
 * 题库校验：每一道题都必须「开始时未结束、解法合法、走完即达成目标」。
 * 杀法题要求终局确实是将死；走法题要求解法着法在初始局面合法。
 */

import { PUZZLES } from '../js/data/puzzles.js';
import { Game } from '../js/core/game.js';
import { getProfile, mergeOptions } from '../js/core/profiles.js';
import { createState, makePiece } from '../js/core/model.js';

function build(item) {
  const profile = getProfile(item.profileId);
  const options = mergeOptions(profile.options, {});
  if (item.start === 'initial') {
    return new Game(profile, options, { initialMinutes: 0 });
  }
  const pieces = item.pieces.map((p) => makePiece(p.type, p.color, p.row, p.col));
  const state = createState(profile.id, pieces, item.turn || 'red');
  state.clocksMs = { red: 0, black: 0 };
  return new Game(profile, options, { state });
}

const failures = [];
let mateCount = 0;
let moveCount = 0;

for (const item of PUZZLES) {
  const game = build(item);
  if (game.finished) {
    failures.push({ id: item.id, why: '初始局面已结束' });
    continue;
  }
  const side = game.state.turn;
  if (game.rules.legalMoves(game.state, side).length === 0) {
    failures.push({ id: item.id, why: '初始局面无合法着法' });
    continue;
  }
  if (!item.solution.length) {
    failures.push({ id: item.id, why: '缺少解法' });
    continue;
  }
  if (item.type === 'mate') {
    mateCount += 1;
    for (const step of item.solution) {
      const probe = build(item);
      const legal = probe.rules.legalMoves(probe.state, probe.state.turn).some(
        (m) => m.source.row === step.from.row && m.source.col === step.from.col
          && m.target.row === step.to.row && m.target.col === step.to.col,
      );
      if (!legal) {
        failures.push({ id: item.id, why: `杀法着法不合法 ${JSON.stringify(step.from)}→${JSON.stringify(step.to)}` });
        continue;
      }
      probe.move({
        source: { row: step.from.row, col: step.from.col },
        target: { row: step.to.row, col: step.to.col },
        promotion: step.promotion || null,
      });
      const mated = probe.rules.inCheck(probe.state, probe.state.turn)
        && probe.rules.legalMoves(probe.state, probe.state.turn).length === 0;
      if (!mated) failures.push({ id: item.id, why: '该杀法着法走完并非将死' });
    }
    continue;
  }

  let ok = true;
  for (const step of item.solution) {
    const legal = game.rules.legalMoves(game.state, game.state.turn).some(
      (m) => m.source.row === step.from.row && m.source.col === step.from.col
        && m.target.row === step.to.row && m.target.col === step.to.col,
    );
    if (!legal) {
      failures.push({ id: item.id, why: `解法着法不合法 ${JSON.stringify(step.from)}→${JSON.stringify(step.to)}` });
      ok = false;
      break;
    }
    game.move({
      source: { row: step.from.row, col: step.from.col },
      target: { row: step.to.row, col: step.to.col },
      promotion: step.promotion || null,
    });
  }
  if (!ok) continue;

  moveCount += 1;
}

if (failures.length) {
  console.error(`✗ 题库校验失败 ${failures.length} 处`);
  for (const f of failures) console.error(' ', f.id, f.why);
  process.exit(1);
}

console.log('✓ 题库全部通过');
console.log(`  走法题   ${moveCount}`);
console.log(`  一步杀   ${mateCount}`);
console.log(`  合计     ${PUZZLES.length}`);
