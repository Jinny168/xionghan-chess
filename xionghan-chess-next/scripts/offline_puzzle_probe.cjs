'use strict';

// Android 离线包的题库校验：把生成的 offline-puzzles.js 逐条喂给
// offline.js 里的 gameFromDocument()，确认「题面能载入、解法在该引擎下合法」。
//
// 为什么不只看数据对不对：三端的题面是同一份 JSON，但离线引擎是另一套实现，
// 只有真跑一遍才知道它认不认这个 document 结构（字段、formatVersion、棋子 id）。
//
// 用法：node scripts/offline_puzzle_probe.cjs <offline.js> <offline-puzzles.js>
const fs = require('fs');
const vm = require('vm');

const [, , enginePath, dataPath] = process.argv;
if (!enginePath || !dataPath) throw new Error('usage: node offline_puzzle_probe.cjs <offline.js> <offline-puzzles.js>');

const engineSource = fs.readFileSync(enginePath, 'utf8');
const start = engineSource.indexOf('const TYPES=');
const end = engineSource.indexOf('const canvas=');
if (start < 0 || end < 0) throw new Error('offline rules markers not found');

// `tr` / `opposite` / `pos` 在切片之上定义，引擎层需要自己的替身。
const sliced = 'const opposite=c=>c===\'red\'?\'black\':\'red\',pos=(row,col)=>({row,col}),tr=key=>key;\n'
  + engineSource.slice(start, end)
  + '\n;globalThis.__offline={Rules,PROFILES,OfflineGame,gameFromDocument,NAMES};';

const context = {console, performance};
vm.createContext(context);
vm.runInContext(sliced, context);

// 数据文件是给浏览器用的（window.XH_OFFLINE_PUZZLES），这里造一个 window。
context.window = {};
vm.runInContext(fs.readFileSync(dataPath, 'utf8'), context);
const puzzles = context.window.XH_OFFLINE_PUZZLES || [];

const results = puzzles.map(puzzle => {
  try {
    const game = context.__offline.gameFromDocument(puzzle.document, 20);
    const move = puzzle.solution && puzzle.solution[0];
    const legal = !!(move && game.rules.isLegal(game.state, {from: move.from, to: move.to}));
    return {
      id: puzzle.id,
      ok: legal,
      pieces: game.state.pieces.length,
      expected: (puzzle.document.state && puzzle.document.state.pieces || []).length,
      turn: game.state.turn,
      message: legal ? '' : 'solution move rejected by the offline engine',
    };
  } catch (error) {
    return {id: puzzle.id, ok: false, pieces: 0, expected: 0, turn: '', message: String(error && error.message || error)};
  }
});

process.stdout.write(JSON.stringify(results));
