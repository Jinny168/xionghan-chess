/**
 * AI 工作线程：搜索放在独立线程，避免思考时卡住界面。
 */

import { Game } from './core/game.js';
import { getProfile, mergeOptions } from './core/profiles.js';
import { stateFromDict, moveToDict } from './core/model.js';
import { chooseMove } from './core/ai.js';

const QUALITY = (loss, isBest) => {
  if (isBest || loss <= 20) return 'best';
  if (loss <= 90) return 'good';
  if (loss <= 220) return 'inaccuracy';
  if (loss <= 450) return 'mistake';
  return 'blunder';
};

function analyze({ id, states, moves, profileId, options, perMoveMs = 90, depth = 2 }) {
  const profile = getProfile(profileId);
  const merged = mergeOptions(profile.options, options);
  const results = [];
  for (let i = 0; i < states.length; i += 1) {
    const game = new Game(profile, merged, { state: stateFromDict(states[i]) });
    const outcome = chooseMove(game.state, game.rules, 'easy', { timeMs: perMoveMs, depth, exactRoot: true });
    const scores = outcome.rootScores || new Map();
    const record = moves[i];
    const key = `${record.from.row},${record.from.col}-${record.to.row},${record.to.col}`;
    let best = -Infinity;
    for (const value of scores.values()) best = Math.max(best, value);
    if (!Number.isFinite(best)) best = outcome.score || 0;
    const actual = scores.has(key) ? scores.get(key) : best - 400;
    const loss = Math.max(0, Math.round(best - actual));
    const perspective = record.color === 'red' ? actual : -actual;
    const winRate = 100 / (1 + Math.exp(-perspective / 500));
    results.push({
      ply: i + 1,
      notation: record.notation,
      color: record.color,
      loss,
      winRate: Math.round(winRate * 10) / 10,
      quality: QUALITY(loss, actual >= best),
    });
    if ((i + 1) % 2 === 0 || i === states.length - 1) {
      self.postMessage({ id, type: 'analyze-progress', done: i + 1, total: states.length });
    }
  }
  self.postMessage({ id, type: 'analyze-done', results });
}

self.onmessage = (event) => {
  if (event.data && event.data.type === 'analyze') {
    try {
      analyze(event.data);
    } catch (error) {
      self.postMessage({ id: event.data.id, type: 'analyze-error', error: String(error && error.message || error) });
    }
    return;
  }
  const { id, state, profileId, options, difficulty, timeMs, depth } = event.data;
  try {
    const profile = getProfile(profileId);
    const merged = mergeOptions(profile.options, options);
    const game = new Game(profile, merged, { state: stateFromDict(state) });
    const result = chooseMove(game.state, game.rules, difficulty, { timeMs, depth });
    self.postMessage({
      id,
      move: moveToDict(result.move),
      meta: { depth: result.depth, nodes: result.nodes, elapsed: result.elapsed, score: result.score },
    });
  } catch (error) {
    self.postMessage({ id, error: error.message || String(error) });
  }
};
