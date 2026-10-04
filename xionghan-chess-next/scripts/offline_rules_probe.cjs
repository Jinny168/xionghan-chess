'use strict';

// Test adapter for the Android offline engine. It evaluates the exact Rules
// implementation shipped in offline.js, stopping before browser UI startup.
const fs = require('fs');
const vm = require('vm');

const sourcePath = process.argv[2];
const source = fs.readFileSync(sourcePath, 'utf8');
const start = source.indexOf("const TYPES=");
const end = source.indexOf("const canvas=");
if (start < 0 || end < 0) throw new Error('offline rules markers not found');
// `tr` lives above the slice, so the engine layer needs its own stub for any
// message OfflineGame builds (resurrect notation included).
const rulesSource = "const opposite=c=>c==='red'?'black':'red',pos=(row,col)=>({row,col}),tr=key=>key;\n" +
  source.slice(start, end) +
  '\n;globalThis.__offline={Rules,PROFILES,OfflineGame};';
const context = {console, performance};
vm.createContext(context);
vm.runInContext(rulesSource, context);

const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const profile = context.__offline.PROFILES.get(request.profileId);
if (!profile) throw new Error(`unknown profile: ${request.profileId}`);
const options = {...profile.options, ...(request.options || {})};
const rules = new context.__offline.Rules(profile, options);
const state = request.state;
const moves = rules.legalAll(state).map(move => ({
  from: move.from,
  to: move.to,
  promotion: move.promotion || null,
}));
const result = {moves, check: rules.inCheck(state, state.turn)};

// Optional resurrection leg: replays the same payload through OfflineGame so a
// Python Game can be compared against it on the same board change. The payload
// already carries Python's `positionCounts`, so only the resurrection's own +1
// is applied -- seeding an extra count here would diverge from
// Game.move(), which counts the resulting position exactly once.
if (request.resurrect) {
  const {color, row, col} = request.resurrect;
  const game = new context.__offline.OfflineGame(request.profileId);
  game.options = {...profile.options, ...(request.options || {})};
  game.rules = new context.__offline.Rules(game.profile, game.options);
  game.state = JSON.parse(JSON.stringify(state));
  try {
    game.resurrectPawn(color, {row, col});
    // publicState() already flattens the live state on top.
    result.resurrect = {ok: true, state: game.publicState(), error: null};
  } catch (error) {
    result.resurrect = {ok: false, state: null, error: error.message};
  }
}

process.stdout.write(JSON.stringify(result));
