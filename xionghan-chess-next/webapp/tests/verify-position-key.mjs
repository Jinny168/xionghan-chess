#!/usr/bin/env node
/**
 * T14 · positionKey 五端全等（架构侧 G11）。
 *
 * 统一局面：turn='red'；红王(12,0) 黑王(0,12) 红兵(6,4) 黑士(5,6)；
 * captured.red=[红车]、captured.black=[]；pawn_promotion=True、
 * enforce_self_check=True；**只翻** pawn_three_line_capture。
 *
 * 两个可直接写死的期望串（逐字，禁止改写）：
 *   Q-PK-01 (p3l=True)  = red|black:advisor:5:6;black:king:0:12;red:king:12:0;red:pawn:6:4||pool:red:rook||opt:rs3-p3l1-promo1-self1
 *   Q-PK-02 (p3l=False) = red|black:advisor:5:6;black:king:0:12;red:king:12:0;red:pawn:6:4||pool:red:rook||opt:rs3-p3l0-promo1-self1
 *
 * 5 个生产者做**全等字符串比较**（不做 contains/正则）：
 *   ① Python core.rules.position_key
 *   ② Android offline.js（经 offline_rules_probe.cjs 的 positionKey 支路）
 *   ③ webapp/js/core/rules.js
 *   ④ online/core/rules.js
 *   ⑤ online/public/index.html 的两份内嵌引擎（vm 求值）各一次 → 共 6 处
 *
 * webapp 现状曾两态同串且缺 pool/opt 段；本脚本一次暴露三个错：
 * pool 段缺失 / 规则位缺失 / 开关不敏感。
 *
 * 运行：node webapp/tests/verify-position-key.mjs
 */

import { existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

import { stateFromDict, createState, makePiece } from '../js/core/model.js';
import { getProfile, mergeOptions, DEFAULT_OPTIONS, RULE_VERSION } from '../js/core/profiles.js';
import { RulesEngine } from '../js/core/rules.js';
import { readHtml, loadEngines } from './lib/bundle-vm.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const WEBAPP = join(here, '..');
const ROOT = join(WEBAPP, '..');

const Q_PK_01 = 'red|black:advisor:5:6;black:king:0:12;red:king:12:0;red:pawn:6:4||pool:red:rook||opt:rs3-p3l1-promo1-self1';
const Q_PK_02 = 'red|black:advisor:5:6;black:king:0:12;red:king:12:0;red:pawn:6:4||pool:red:rook||opt:rs3-p3l0-promo1-self1';

function pythonExe() {
  for (const candidate of ['.venv/Scripts/python.exe', '.venv/bin/python3', '.venv/bin/python']) {
    if (existsSync(join(ROOT, candidate))) return join(ROOT, candidate);
  }
  return 'python';
}

// 统一局面（dict 形状，Python / Android / JS / vm 四处共用）
const STATE_DICT = {
  profileId: 'web',
  turn: 'red',
  pieces: [
    { id: 'rk', type: 'king', color: 'red', row: 12, col: 0 },
    { id: 'bk', type: 'king', color: 'black', row: 0, col: 12 },
    { id: 'p', type: 'pawn', color: 'red', row: 6, col: 4 },
    { id: 'a', type: 'advisor', color: 'black', row: 5, col: 6 },
  ],
  captured: {
    red: [{ id: 'cap', type: 'rook', color: 'red', row: -1, col: -1 }],
    black: [],
  },
  history: [],
  winner: null,
  resultReason: null,
  draw: false,
  paused: false,
  positionCounts: {},
  clocksMs: { red: 1200000, black: 1200000 },
};

function optionsFor(p3l) {
  return { pawn_three_line_capture: p3l, pawn_promotion: true, enforce_self_check: true };
}

// ---------------------------------------------------------------- ① Python
function pythonKeys() {
  const code = `
import sys, json
sys.path.insert(0, 'src')
from xionghan_chess.core.model import Color, GameState, Piece, PieceType, Position
from xionghan_chess.core.profiles import get_profile, RuleOptions
from xionghan_chess.core.rules import RulesEngine
state = GameState.from_dict(json.loads(${JSON.stringify(JSON.stringify(STATE_DICT))}))
out = {}
for p3l in (True, False):
    o = RuleOptions(pawn_three_line_capture=p3l, pawn_promotion=True, enforce_self_check=True)
    out['p3l1' if p3l else 'p3l0'] = RulesEngine(get_profile('web'), o).position_key(state)
print(json.dumps(out))
`;
  const stdout = execFileSync(pythonExe(), ['-c', code], { cwd: ROOT, encoding: 'utf8' });
  return JSON.parse(stdout.trim().split('\n').pop());
}

// ---------------------------------------------------------------- ② Android
function androidKeys() {
  const probe = join(ROOT, 'scripts', 'offline_rules_probe.cjs');
  const offline = join(ROOT, 'android', 'Resources', 'assets', 'offline', 'offline.js');
  const out = {};
  for (const [label, p3l] of [['p3l1', true], ['p3l0', false]]) {
    const request = {
      profileId: 'web',
      positionKey: true,
      options: optionsFor(p3l),
      state: STATE_DICT,
    };
    const stdout = execFileSync('node', [probe, offline], {
      cwd: ROOT, encoding: 'utf8', input: JSON.stringify(request),
    });
    out[label] = JSON.parse(stdout).positionKey;
  }
  return out;
}

// ---------------------------------------------------------------- ③ / ④ JS 源
function sourceKeys(rulesModulePath, profilesModulePath) {
  // 动态 import 绝对路径（online/core 与 webapp/js/core 是两份同步副本）
  return import(pathToFileURL(rulesModulePath).href).then(async (rulesMod) => {
    const profMod = await import(pathToFileURL(profilesModulePath).href);
    const profile = profMod.getProfile('web');
    const state = stateFromDict(STATE_DICT);
    const out = {};
    for (const [label, p3l] of [['p3l1', true], ['p3l0', false]]) {
      const options = profMod.mergeOptions(profile.options, optionsFor(p3l));
      out[label] = new rulesMod.RulesEngine(profile, options).positionKey(state);
    }
    return out;
  });
}

// ---------------------------------------------------------------- ⑤ 内嵌引擎
function embeddedKeys(html) {
  const loaded = loadEngines(html);
  if (loaded.error) throw new Error(loaded.error);
  const out = {};
  for (const which of ['worker', 'main']) {
    const info = loaded[which];
    if (!info || !info.engine) throw new Error(`${which} 拿不到内嵌 RulesEngine`);
    const Engine = info.engine;
    const mods = info.mods;
    const profiles = mods['js/core/profiles.js'];
    const model = mods['js/core/model.js'];
    const profile = profiles.getProfile('web');
    const pieces = STATE_DICT.pieces.map((p) => model.makePiece(p.type, p.color, p.row, p.col, p.id));
    const state = model.createState('web', pieces, 'red');
    state.captured = {
      red: STATE_DICT.captured.red.map((p) => model.makePiece(p.type, p.color, p.row, p.col, p.id)),
      black: [],
    };
    for (const [label, p3l] of [['p3l1', true], ['p3l0', false]]) {
      const options = profiles.mergeOptions(profile.options, optionsFor(p3l));
      out[`${which}:${label}`] = new Engine(profile, options).positionKey(state);
    }
  }
  return out;
}

// ---------------------------------------------------------------- 汇总
const failures = [];
function compare(label, actual, expected, p3lLabel) {
  if (actual !== expected) {
    failures.push({ label: `${label}/${p3lLabel}`, expected, actual });
  }
  console.log(`  ${label.padEnd(28)} ${p3lLabel}  ${actual === expected ? '✓' : '✗'}  ${actual}`);
}

async function main() {
  console.log(`[verify-position-key] RULE_VERSION=${RULE_VERSION}`);
  console.log(`  Q-PK-01 = ${Q_PK_01}`);
  console.log(`  Q-PK-02 = ${Q_PK_02}`);

  // 三条不变量
  if (Q_PK_01 === Q_PK_02) failures.push({ label: 'invariant/differ', reason: 'Q-PK-01 === Q-PK-02' });
  for (const s of [Q_PK_01, Q_PK_02]) {
    if (!s.includes('||pool:red:rook')) failures.push({ label: 'invariant/pool', reason: `缺 ||pool:red:rook: ${s}` });
  }
  const opt1 = Q_PK_01.split('||opt:')[1];
  const opt2 = Q_PK_02.split('||opt:')[1];
  if (opt1 !== 'rs3-p3l1-promo1-self1') failures.push({ label: 'invariant/opt1', actual: opt1 });
  if (opt2 !== 'rs3-p3l0-promo1-self1') failures.push({ label: 'invariant/opt2', actual: opt2 });

  const producers = {};

  const py = pythonKeys();
  producers['① Python'] = py;
  compare('① Python', py.p3l1, Q_PK_01, 'Q-PK-01');
  compare('① Python', py.p3l0, Q_PK_02, 'Q-PK-02');

  const android = androidKeys();
  producers['② Android'] = android;
  compare('② Android offline.js', android.p3l1, Q_PK_01, 'Q-PK-01');
  compare('② Android offline.js', android.p3l0, Q_PK_02, 'Q-PK-02');

  const webapp = await sourceKeys(
    join(WEBAPP, 'js', 'core', 'rules.js'),
    join(WEBAPP, 'js', 'core', 'profiles.js'),
  );
  producers['③ webapp'] = webapp;
  compare('③ webapp/js/core/rules.js', webapp.p3l1, Q_PK_01, 'Q-PK-01');
  compare('③ webapp/js/core/rules.js', webapp.p3l0, Q_PK_02, 'Q-PK-02');

  const online = await sourceKeys(
    join(ROOT, 'online', 'core', 'rules.js'),
    join(ROOT, 'online', 'core', 'profiles.js'),
  );
  producers['④ online/core'] = online;
  compare('④ online/core/rules.js', online.p3l1, Q_PK_01, 'Q-PK-01');
  compare('④ online/core/rules.js', online.p3l0, Q_PK_02, 'Q-PK-02');

  const htmlPath = join(ROOT, 'online', 'public', 'index.html');
  if (!existsSync(htmlPath)) {
    failures.push({ label: '⑤ online/public/index.html', reason: '文件不存在，先跑 S3' });
  } else {
    const embedded = embeddedKeys(readHtml(htmlPath));
    producers['⑤ embedded'] = embedded;
    for (const which of ['worker', 'main']) {
      const tag = which === 'worker' ? '⑤ WORKER_SRC' : '⑤ 主inline';
      compare(tag, embedded[`${which}:p3l1`], Q_PK_01, 'Q-PK-01');
      compare(tag, embedded[`${which}:p3l0`], Q_PK_02, 'Q-PK-02');
    }
  }

  if (failures.length) {
    console.error(`\n✗ [position-key] ${failures.length} 处不一致：`);
    for (const f of failures) {
      console.error(`  [${f.label}] ${f.reason || ''}`);
      if (f.expected !== undefined) console.error(`    expected: ${f.expected}`);
      if (f.actual !== undefined) console.error(`    actual:   ${f.actual}`);
    }
    console.error('\n  → Q-PK 五端串必须逐字相等（不做 contains/正则）。');
    process.exit(1);
  }
  console.log('✓ [verify-position-key] 五端 6 处 positionKey 两态逐字全等，三条不变量成立');
}

main().catch((error) => {
  console.error('[verify-position-key] 异常:', error.stack || String(error));
  process.exit(1);
});
