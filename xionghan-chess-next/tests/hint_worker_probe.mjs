// 常规对局提示的 worker 闭环探针：真跑 ai-worker 的 hint 分支，不触碰 DOM。
// 由 tests/test_webapp_hint_worker.py 用 node 执行并断言输出。
import { Game } from '../webapp/js/core/game.js';
import { getProfile, mergeOptions } from '../webapp/js/core/profiles.js';
import { stateToDict } from '../webapp/js/core/model.js';

const out = [];
globalThis.self = { postMessage: (message) => out.push(message) };
await import('../webapp/js/ai-worker.js');

const profile = getProfile('web');
const game = new Game(profile, mergeOptions(profile.options, {}));
const started = performance.now();
self.onmessage({
  data: {
    type: 'hint', id: 7,
    state: stateToDict(game.state), profileId: 'web', options: {},
    difficulty: 'easy', timeMs: 250, depth: 2,
  },
});
const elapsed = Math.round(performance.now() - started);
const types = out.map((message) => message.type);
console.log(JSON.stringify({
  elapsed,
  types,
  hasMove: Boolean(out[0] && out[0].move),
  depth: out[0] && out[0].meta ? out[0].meta.depth : null,
}));
if (types.length !== 1 || types[0] !== 'hint' || !out[0].move) process.exit(2);
