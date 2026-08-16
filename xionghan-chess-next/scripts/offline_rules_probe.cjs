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
const rulesSource = "const opposite=c=>c==='red'?'black':'red',pos=(row,col)=>({row,col});\n" +
  source.slice(start, end) +
  '\n;globalThis.__offline={Rules,PROFILES};';
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
process.stdout.write(JSON.stringify({moves, check: rules.inCheck(state, state.turn)}));
