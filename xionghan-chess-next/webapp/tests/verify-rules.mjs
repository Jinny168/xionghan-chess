#!/usr/bin/env node
/**
 * 规则一致性门禁。
 *
 * 用 Python 内核导出的黄金用例（scripts/gen_rule_fixtures.py），逐局面比对
 * JS 端的合法着法全集、将军判定、**移除集合**，并逐着法比对走子后的胜负结算。
 *
 * 运行：
 *   node webapp/tests/verify-rules.mjs              # 全量比对
 *   node webapp/tests/verify-rules.mjs --selftest   # 比较器自检 + W/V 定向用例 + 覆盖度
 *
 * 退出码 0 = 全绿；1 = 存在不一致。
 *
 * ## 为什么 `removals` 不能省
 * 三连吃子**不改变合法着法集合、不改变将军判定**：开关 on/off 时 `legal` 相同、
 * `check` 相同，唯 `removals` 是 `[advisor,black,6,5]` vs `[]`。只比 legal+check
 * 的门禁必然无感。`capturedTypes` 只留类型串、848 transitions 中仅 23 条非空，
 * 属「护栏不足」而非「零护栏」，保留但与 removals 并存互补。
 */

import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { stateFromDict, moveKey, createState, makePiece } from '../js/core/model.js';
import { getProfile, mergeOptions, DEFAULT_OPTIONS, RULE_VERSION } from '../js/core/profiles.js';
import { RulesEngine } from '../js/core/rules.js';
import { Game } from '../js/core/game.js';

const here = dirname(fileURLToPath(import.meta.url));
const WEBAPP = join(here, '..');
const ROOT = join(WEBAPP, '..');
const SELFTEST = process.argv.includes('--selftest');
const fixture = JSON.parse(readFileSync(join(here, 'fixtures', 'rules.json'), 'utf8'));

// sourceDigest 的固定拼接顺序，必须与 scripts/gen_rule_fixtures.py::SOURCE_DIGEST_FILES 逐字一致。
// 把「bundle 产物」纳入哈希，故 S3/S4 必须先于 S5；顺序错 → fail('build-order')。
const SOURCE_DIGEST_FILES = [
  ['webapp/js/core/profiles.js', join(WEBAPP, 'js', 'core', 'profiles.js')],
  ['webapp/js/core/rules.js', join(WEBAPP, 'js', 'core', 'rules.js')],
  ['online/core/profiles.js', join(ROOT, 'online', 'core', 'profiles.js')],
  ['online/core/rules.js', join(ROOT, 'online', 'core', 'rules.js')],
  ['online/public/index.html', join(ROOT, 'online', 'public', 'index.html')],
];

const failures = [];
const failureCounts = new Map();
const stats = {
  cases: 0,
  transitions: 0,
  legalTotal: 0,
  removalsCompared: 0, // 实际比对的 (case_id, move_key) 条数
  removalsNonEmpty: 0,
  removalsMulti: 0,
  threeLineCases: 0,
};

/** 分 kind 汇总计数 + 只留前 25 条明细（原来的 25 条上限会把批量红灯截断）。 */
function fail(kind, id, detail) {
  failureCounts.set(kind, (failureCounts.get(kind) || 0) + 1);
  if (failures.length < 25) failures.push({ kind, id, detail });
}

function buildEngine(profileId, options) {
  const profile = getProfile(profileId);
  if (!profile) throw new Error(`unknown profile ${profileId}`);
  const merged = mergeOptions(profile.options, options);
  return { profile, options: merged, engine: new RulesEngine(profile, merged) };
}

function sha256(absolutePath) {
  return createHash('sha256').update(readFileSync(absolutePath)).digest('hex');
}

/** 逐文件 hash（打印 changed 明细）。 */
function diskSourceFiles() {
  const out = {};
  for (const [name, path] of SOURCE_DIGEST_FILES) {
    out[name] = existsSync(path) ? sha256(path) : null;
  }
  return out;
}

/** 按固定顺序拼接字节 → sha256，与 gen_rule_fixtures.py 完全同构。 */
function diskSourceDigest() {
  const h = createHash('sha256');
  for (const [_name, path] of SOURCE_DIGEST_FILES) {
    if (existsSync(path)) h.update(readFileSync(path));
  }
  h.update(String(RULE_VERSION));
  return h.digest('hex');
}

/** 返回 build-order 不一致明细（纯函数，供 --selftest 的「顺序错必 fail」样本复用）。 */
function sourceDigestDiff(fx, diskDigest, diskFiles) {
  const changed = [];
  const recorded = fx.sourceDigestFiles || {};
  for (const [name, hash] of Object.entries(diskFiles)) {
    if (hash === null) changed.push(`${name}: 磁盘缺失`);
    else if (recorded[name] !== undefined && recorded[name] !== hash) {
      changed.push(`${name}: fixtures=${String(recorded[name]).slice(0, 12)}… disk=${hash.slice(0, 12)}…`);
    }
  }
  return { mismatch: fx.sourceDigest !== diskDigest, changed };
}

// ------------------------------------------------------------ 规范化/比较器
/** 与 Python `removals_of` 的排序口径逐字一致：(type,color,row,col) 字典序。 */
function compareQuad(a, b) {
  for (let i = 0; i < 2; i += 1) {
    if (a[i] < b[i]) return -1;
    if (a[i] > b[i]) return 1;
  }
  for (let i = 2; i < 4; i += 1) {
    if (a[i] !== b[i]) return a[i] - b[i];
  }
  return 0;
}

/** boardRemovals 的 Piece[] → [[type,color,row,col], ...]，排序后返回。 */
function normalizeRemovals(engine, state, move) {
  return engine.boardRemovals(state, move)
    .map((p) => [p.type, p.color, p.row, p.col])
    .sort(compareQuad);
}

/** 四元组数组全等比较（先看长度，再逐字段比；坐标错一位也要判不一致）。 */
function removalsEqual(expected, actual) {
  if (!Array.isArray(expected) || !Array.isArray(actual)) return false;
  if (expected.length !== actual.length) return false;
  const a = expected.slice().sort(compareQuad);
  const b = actual.slice().sort(compareQuad);
  for (let i = 0; i < a.length; i += 1) {
    for (let j = 0; j < 4; j += 1) {
      if (a[i][j] !== b[i][j]) return false;
    }
  }
  return true;
}

// ------------------------------------------------------------ stale-fixtures
/**
 * 前置断言（早于 legal/settle 比对）：区分「产物过期」与「规则实现有 bug」。
 * 否则重生成后一次性暴露的差异会被误读成规则分叉。
 *
 * 两类失败分开 kind：
 *   - `stale-fixtures`：ruleVersion / 双 hash / optionsKeys / bundle 哨兵
 *   - `build-order`：sourceDigest 不等（S3/S4 没跑或跑在 S5 之后）
 */
function preflightStale(fx = fixture, opts = {}) {
  const problems = [];
  const buildOrder = [];
  if (fx.ruleVersion !== RULE_VERSION) {
    problems.push(`[rule-version] fixture.ruleVersion=${fx.ruleVersion} != RULE_VERSION=${RULE_VERSION}`);
  }
  const profilesPath = join(WEBAPP, 'js', 'core', 'profiles.js');
  const rulesPath = join(WEBAPP, 'js', 'core', 'rules.js');
  if (existsSync(profilesPath) && fx.profilesHash !== sha256(profilesPath)) {
    problems.push('[profiles-hash] fixture.profilesHash != sha256(webapp/js/core/profiles.js)');
  }
  if (existsSync(rulesPath) && fx.rulesHash !== sha256(rulesPath)) {
    problems.push('[rules-hash] fixture.rulesHash != sha256(webapp/js/core/rules.js)');
  }
  const canonicalKeys = Object.keys(DEFAULT_OPTIONS).sort();
  if (JSON.stringify(fx.optionsKeys) !== JSON.stringify(canonicalKeys)) {
    problems.push('[options-keys] fixture.optionsKeys 与规范键集不一致');
  }

  // ---- build-order：sourceDigest 必须等于磁盘重算值（S3/S4 先于 S5）----
  const diskFiles = opts.diskFiles || diskSourceFiles();
  const diskDigest = opts.diskDigest || diskSourceDigest();
  const diff = sourceDigestDiff(fx, diskDigest, diskFiles);
  if (fx.sourceDigest === undefined) {
    buildOrder.push('fixtures 缺 sourceDigest —— 按 S1–S6 重生成');
  } else if (diff.mismatch) {
    buildOrder.push(
      `fixtures.sourceDigest=${fx.sourceDigest} / disk.sourceDigest=${diskDigest} / `
      + `changed=${JSON.stringify(diff.changed)}`,
    );
  }

  // ---- online/public/index.html 内嵌哨兵（两份引擎快照，阈值 ≥2）----
  const onlineHtml = join(WEBAPP, '..', 'online', 'public', 'index.html');
  if (!existsSync(onlineHtml)) {
    problems.push('[bundle-sentinel] online/public/index.html 不存在 —— 跑 S3 build_webapp_bundle.py');
  } else {
    const html = readFileSync(onlineHtml, 'utf8');
    // `__mods["js/core/rules.js"] = (function` 引擎快照恰好 2 份：
    // 1 份主 inline 明文 + 1 份 __WORKER_SRC 转义串（需 JSON.parse 解码后计数）。
    // 只更新一份时 ≥1 会假绿（严过关 M26）。
    const assignment = '__mods["js/core/rules.js"] = (function () {';
    const plain = html.split(assignment).length - 1;
    const workerMatch = html.match(/var __WORKER_SRC = ("(?:[^"\\]|\\.)*");/);
    let workerCount = 0;
    if (workerMatch) {
      try {
        workerCount = JSON.parse(workerMatch[1]).split(assignment).length - 1;
      } catch {
        workerCount = 0;
      }
    }
    const assignmentCount = plain + workerCount;
    if (assignmentCount !== 2) {
      problems.push(`[bundle-sentinel] rules.js 引擎快照数=${assignmentCount}（明文${plain}+worker${workerCount}），期望恰好 2`);
    }
    // 主理人裁决：不写死 `rs3-` 字面量（§2.2(c) 防复发优先）；文本哨兵认
    // `rs${RULE_VERSION}-`（≥2），运行时串由 T14 的 Q-PK-01/02 逐字全等覆盖。
    // 逐字 `rs3-` 残留只可能来自注释，不留「永远为 0」的假断言。
    const sentinels = [
      ['threeLineCaptures', 2], ['pawn_three_line_capture', 2], ['p3l', 2],
      ['rs${RULE_VERSION}-', 2], ['||opt:', 2], ['||pool:', 2],
    ];
    for (const [token, min] of sentinels) {
      const count = html.split(token).length - 1;
      if (count < min) problems.push(`[bundle-sentinel] online/public/index.html ${token} 计数 ${count} < ${min}`);
    }
    // 内嵌规则内核里不得残留已删除的 1.9.x 开关（app.js 的 UI 文案不算，故按内嵌块取）
    const block = embeddedModule(html, 'js/core/rules.js');
    if (block === null) {
      problems.push('[bundle-sentinel] online/public/index.html 缺 __mods["js/core/rules.js"] 内嵌块');
    } else if (block.includes('pawn_full_movement_at_base')) {
      problems.push('[bundle-sentinel] 内嵌 rules.js 仍残留 pawn_full_movement_at_base');
    }
  }

  // ---- 防空跑三断言（启动即跑，失败信息三选一）----
  const threeLineCases = (fx.cases || []).filter((c) => (c.threeLineMoves || []).length > 0).length;
  stats.threeLineCases = threeLineCases;
  if (threeLineCases < 1) {
    fail('fixtures-empty', 'guard-rail', {
      reason: '[fixtures-empty] threeLineCases=0 → 护栏空跑（没有带 threeLineMoves 的 case）',
      fix: 'python scripts/gen_rule_fixtures.py --write',
    });
  }
  const ids = new Set((fx.cases || []).map((c) => c.id));
  for (const required of ['opt:tl:exact3', 'opt:tl:exact3:off']) {
    if (!ids.has(required)) {
      fail('variant-missing', 'guard-rail', {
        reason: `[variant-missing] 缺 ${required}`,
        fix: 'python scripts/gen_rule_fixtures.py --write',
      });
    }
  }
  // 第三条 removalsCompared >= 1 在 verifyCases() 之后断言（此刻还不知道条数）

  for (const line of problems) {
    fail('stale-fixtures', 'fixtures/rules.json', { reason: line });
  }
  for (const line of buildOrder) {
    fail('build-order', 'fixtures/rules.json', {
      reason: line,
      fix: 'S1 python scripts/gen_web_profiles.py --write → S2 --check → S3 python scripts/build_webapp_bundle.py → S4 --check → S5 python scripts/gen_rule_fixtures.py --write → S6 本命令',
    });
  }
  const ok = problems.length === 0 && buildOrder.length === 0;
  if (ok && !opts.quiet) {
    console.log(`[stale-fixtures] OK: ruleVersion=${RULE_VERSION} / hashes / optionsKeys / sourceDigest / bundle 哨兵(≥2)`);
  }
  return ok;
}

/** 从 bundle HTML 里抠出 `__mods["<key>"] = (function () {...})();` 的模块体。 */
function embeddedModule(html, key) {
  const marker = `__mods[${JSON.stringify(key)}] = (function () {`;
  const start = html.indexOf(marker);
  if (start < 0) return null;
  const bodyStart = start + marker.length;
  const tail = '\nreturn {';
  const tailAt = html.indexOf(tail, bodyStart);
  return tailAt < 0 ? null : html.slice(bodyStart, tailAt);
}

// ------------------------------------------------------------ 局面比对
function verifyCases() {
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
      fail('legal-count', testCase.id, {
        expected: expected.length, actual: legal.length,
        missing: expected.filter((k) => !legal.includes(k)).slice(0, 12),
        extra: legal.filter((k) => !expected.includes(k)).slice(0, 12),
      });
      // 不 continue：removals 仍要独立比对，分开 kind 归因
    } else {
      for (let i = 0; i < expected.length; i += 1) {
        if (legal[i] !== expected[i]) {
          fail('legal-diff', testCase.id, {
            missing: expected.filter((k) => !legal.includes(k)).slice(0, 12),
            extra: legal.filter((k) => !expected.includes(k)).slice(0, 12),
          });
          break;
        }
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

    // ------------------------------------------------ removals 分支
    verifyRemovals(testCase, state, engine);
  }
  // 防空跑第三条：实际逐 (case_id, move_key) 比对条数必须 > 0
  if (stats.removalsCompared < 1) {
    fail('removals-empty', 'guard-rail', {
      reason: '[removals-empty] 比对条数=0 → 空绿',
      fix: 'python scripts/gen_rule_fixtures.py --write',
    });
  }
}

/** 逐 move_key 用 `engine.boardRemovals`（= applyUnchecked 的 before/after id 差集）比对。 */
function verifyRemovals(testCase, state, engine) {
  const exp = testCase.removals;
  if (!exp) {
    fail('removals-missing', testCase.id, { reason: 'case 缺 removals 字段 —— 未重生成 fixtures？' });
    return;
  }
  const moves = engine.legalMoves(state);
  const legalKeys = moves.map(moveKey);
  const expKeys = Object.keys(exp);
  // 键集合恒等于 set(legal)：缺键/多键都是产物错，单独 kind
  const missingKeys = legalKeys.filter((k) => !(k in exp));
  const extraKeys = expKeys.filter((k) => !legalKeys.includes(k));
  if (missingKeys.length || extraKeys.length) {
    fail('removals-keys', testCase.id, {
      missing: missingKeys.slice(0, 12), extra: extraKeys.slice(0, 12),
    });
  }
  for (const move of moves) {
    const key = moveKey(move);
    if (!(key in exp)) continue;
    let actual;
    try {
      actual = normalizeRemovals(engine, state, move);
    } catch (error) {
      fail('removals-throw', `${testCase.id}@${key}`, error.stack || String(error));
      continue;
    }
    stats.removalsCompared += 1;
    if (actual.length) stats.removalsNonEmpty += 1;
    if (actual.length >= 2) stats.removalsMulti += 1;
    if (!removalsEqual(exp[key], actual)) {
      fail('removals', `${testCase.id}@${key}`, { expected: exp[key], actual });
    }
  }
}

// ------------------------------------------------------------ 走子结算
function verifyTransitions() {
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
}

// ------------------------------------------------------------ --selftest
/** 稀疏局面：固定双王（不同行不同列，避开 kingsFacing），每子唯一 id。 */
function sparseState(placements, kings = [['king', 'red', 12, 0], ['king', 'black', 0, 12]]) {
  const pieces = [];
  let seq = 0;
  for (const [type, color, row, col] of [...kings, ...placements]) {
    pieces.push(makePiece(type, color, row, col, `st:p:${seq++}`));
  }
  return createState('web', pieces, 'red');
}

const TL_OPTIONS = { ...DEFAULT_OPTIONS, pawn_three_line_capture: true };

/** 计算一步的四元组移除集合，先做 S3 合法性前置断言（boardRemovals 不校验着法）。 */
function probeRemovals(placements, from, to, opts = {}) {
  const state = sparseState(placements, opts.kings);
  const profile = getProfile('web');
  const engine = new RulesEngine(profile, { ...TL_OPTIONS, ...(opts.options || {}) });
  const move = { source: { row: from[0], col: from[1] }, target: { row: to[0], col: to[1] }, promotion: null };
  const pseudo = engine.pseudoLegal(state, move) === true;
  const inLegal = engine.legalMoves(state).map(moveKey).includes(moveKey(move));
  return {
    state, engine, move, pseudo, inLegal,
    removed: engine.boardRemovals(state, move)
      .map((p) => [p.type, p.color, p.row, p.col]).sort(compareQuad),
  };
}

// W 系列（网页端 9 条，固定双王由 sparseState 补齐）。坐标/期望逐字来自 §4。
const W_CASES = [
  { id: 'W-01', placements: [['pawn', 'red', 6, 4], ['pawn', 'red', 5, 5], ['advisor', 'black', 5, 6]],
    from: [6, 4], to: [5, 4], expected: [['advisor', 'black', 5, 6]] },
  { id: 'W-02', placements: [['pawn', 'red', 6, 4], ['pawn', 'red', 5, 5], ['advisor', 'black', 5, 6], ['advisor', 'black', 5, 7]],
    from: [6, 4], to: [5, 4], expected: [] },
  { id: 'W-03', placements: [['pawn', 'red', 6, 3], ['pawn', 'red', 4, 3], ['advisor', 'black', 3, 3], ['rook', 'black', 2, 3], ['rook', 'red', 1, 3]],
    from: [6, 3], to: [5, 3], expected: [] },
  { id: 'W-04', placements: [['pawn', 'red', 6, 6], ['pawn', 'red', 5, 5], ['advisor', 'black', 5, 4], ['advisor', 'black', 4, 6], ['rook', 'red', 3, 6], ['rook', 'red', 2, 6]],
    from: [6, 6], to: [5, 6], expected: [['advisor', 'black', 5, 4]] },
  { id: 'W-05a', placements: [['pawn', 'red', 9, 1], ['pawn', 'red', 7, 2], ['advisor', 'black', 6, 3], ['rook', 'red', 5, 4]],
    from: [9, 1], to: [8, 1], expected: [] },
  { id: 'W-05b', placements: [['pawn', 'red', 9, 1], ['pawn', 'red', 7, 2], ['advisor', 'black', 6, 3]],
    from: [9, 1], to: [8, 1], expected: [['advisor', 'black', 6, 3]] },
  // W-06a 位移 5 格（R1 已落地）：期望必须是 []，写成 {(5,4)} 而绿灯 = 有人把 R1 误撤。
  { id: 'W-06a', placements: [['pawn', 'red', 10, 6], ['pawn', 'red', 5, 5], ['advisor', 'black', 5, 4]],
    from: [10, 6], to: [5, 6], expected: [] },
  // W-06b 位移 1 格：同一窗口正对照，变红 = R2 过剪或三连整体被关掉。
  { id: 'W-06b', placements: [['pawn', 'red', 6, 6], ['pawn', 'red', 5, 5], ['advisor', 'black', 5, 4]],
    from: [6, 6], to: [5, 6], expected: [['advisor', 'black', 5, 4]] },
  { id: 'W-06c', placements: [['pawn', 'red', 7, 6], ['pawn', 'red', 5, 5], ['advisor', 'black', 5, 4]],
    from: [7, 6], to: [5, 6], expected: [] },
];

// V 系列（裁决 1 回归）：网页/online 的 inCheck 不同源，只断言
// 合法性前置 / 移除为空 / 黑王仍在 / 正对照成立。
const V_KINGS_BK = [['king', 'red', 12, 0], ['king', 'black', 2, 4]];
const V_KINGS_DEFAULT = [['king', 'red', 12, 0], ['king', 'black', 0, 12]];

function runSelftest() {
  const checks = [];
  const record = (name, ok, detail) => {
    checks.push({ name, ok, detail });
    if (!ok) fail('selftest', name, detail);
  };

  // ---- S-A / S-B / S-C：比较器自身能验出差异（防「两边都返回 [] 也绿」）----
  const seed = [['advisor', 'black', 6, 5]];
  const hit = fixture.cases.find((c) => Object.values(c.removals || {}).some((v) => v.length === 1));
  const sample = hit ? Object.values(hit.removals).find((v) => v.length === 1) : seed;
  // S-A：非空 → [] 应判不一致
  record('S-A 非空改空', removalsEqual(sample, []) === false, { sample, mutated: [] });
  // S-B：坐标 (6,5) → (6,6) 应判不一致（证明看坐标而非只看类型/数量）
  const coordMutated = sample.map((q) => [q[0], q[1], q[2], q[3] + 1]);
  record('S-B 坐标改错', removalsEqual(sample, coordMutated) === false, { sample, coordMutated });
  // S-C：两端完全一致应判一致
  record('S-C 完全一致', removalsEqual(sample, sample.map((q) => q.slice())) === true, { sample });
  // 附加：数量不同（≥2 枚子）也应判不一致
  record('S-D 数量差异', removalsEqual(sample, [...sample, ...sample]) === false, { sample });

  // ---- W 系列 9 条 ----
  console.log('\n[W 系列] 网页端定向用例（固定双王省略；先断言 pseudoLegal + inLegalMoves）');
  for (const c of W_CASES) {
    const r = probeRemovals(c.placements, c.from, c.to);
    const pre = r.pseudo && r.inLegal;
    const ok = pre && removalsEqual(c.expected, r.removed)
      && (c.expected.length === 0 || r.removed.length > 0);
    record(c.id, ok, {
      pseudoLegal: r.pseudo, inLegalMoves: r.inLegal, expected: c.expected, actual: r.removed,
    });
    console.log(`  ${c.id.padEnd(7)} pseudoLegal=${r.pseudo} inLegal=${r.inLegal} `
      + `expected=${JSON.stringify(c.expected)} actual=${JSON.stringify(r.removed)} ${ok ? '✓' : '✗'}`);
  }

  // ---- V 系列 ----
  console.log('\n[V 系列] 裁决 1 回归（王在窗口内不被移除 / 换成车要被移除）');
  const v1 = probeRemovals([['pawn', 'red', 3, 3], ['elephant', 'red', 2, 5]],
    [3, 3], [2, 3], { kings: V_KINGS_BK });
  const kingAlive = v1.state.pieces.some((p) => p.type === 'king' && p.color === 'black' && p.row === 2 && p.col === 4)
    && v1.engine.boardRemovals(v1.state, v1.move).every((p) => p.type !== 'king');
  const v1ok = v1.pseudo && v1.inLegal && v1.removed.length === 0 && kingAlive;
  record('V-01 王不吃', v1ok, {
    pseudoLegal: v1.pseudo, inLegalMoves: v1.inLegal, removed: v1.removed, kingAlive,
  });
  console.log(`  V-01   pseudoLegal=${v1.pseudo} inLegal=${v1.inLegal} removed=${JSON.stringify(v1.removed)} kingAlive=${kingAlive} ${v1ok ? '✓' : '✗'}`);

  const v2 = probeRemovals([['pawn', 'red', 3, 3], ['elephant', 'red', 2, 5], ['rook', 'black', 2, 4]],
    [3, 3], [2, 3], { kings: V_KINGS_DEFAULT });
  const v2expected = [['rook', 'black', 2, 4]];
  const v2ok = v2.pseudo && v2.inLegal && v2.removed.length > 0 && removalsEqual(v2expected, v2.removed);
  record('V-02 车正对照', v2ok, {
    pseudoLegal: v2.pseudo, inLegalMoves: v2.inLegal, expected: v2expected, actual: v2.removed,
  });
  console.log(`  V-02   pseudoLegal=${v2.pseudo} inLegal=${v2.inLegal} removed=${JSON.stringify(v2.removed)} ${v2ok ? '✓' : '✗'}`);

  // ---- 覆盖度断言（否则「绿」只证明两边都算出了同一个零）----
  const tl = fixture.cases.filter((c) => c.id.startsWith('rem:tl:'));
  const emptyNonEmptyPairs = tl.filter((c) => (c.expectedRemovals || []).length === 0).length
    && tl.filter((c) => (c.expectedRemovals || []).length > 0).length;
  record('覆盖度: rem:tl 定向 case 存在', tl.length >= 13, { count: tl.length });
  record('覆盖度: 王/车正反例成对',
    Boolean(tl.find((c) => c.id === 'rem:tl:king-in-window'))
      && Boolean(tl.find((c) => c.id === 'rem:tl:king-replaced-rook'))
      && Boolean(emptyNonEmptyPairs),
    { kingInWindow: Boolean(tl.find((c) => c.id === 'rem:tl:king-in-window')),
      kingReplacedRook: Boolean(tl.find((c) => c.id === 'rem:tl:king-replaced-rook')) });

  // ---- 顺序错必 fail 样本（T17）：不改磁盘，纯函数验证 build-order 判定 ----
  const diskFiles = diskSourceFiles();
  const diskDigest = diskSourceDigest();
  const realDiff = sourceDigestDiff(fixture, diskDigest, diskFiles);
  // ① 用旧 profiles 重生成的 fixtures（sourceDigest 指向旧 bundle）→ 必须判不一致
  const staleFixture = { ...fixture, sourceDigest: '0'.repeat(64), sourceDigestFiles: {} };
  const staleDiff = sourceDigestDiff(staleFixture, diskDigest, diskFiles);
  record('顺序样本① 旧 profiles 的 fixtures 必 fail', staleDiff.mismatch === true, {
    fixtures: staleFixture.sourceDigest, disk: diskDigest,
  });
  // ② 手改 sourceDigest → 必须判不一致
  const tampered = { ...fixture, sourceDigest: `${fixture.sourceDigest.slice(0, 63)}x` };
  const tamperedDiff = sourceDigestDiff(tampered, diskDigest, diskFiles);
  record('顺序样本② 手改 sourceDigest 必 fail', tamperedDiff.mismatch === true, {
    fixtures: tampered.sourceDigest, disk: diskDigest,
  });
  // ③ 按 S1–S6 生成的 fixtures → 必须一致（pass）
  record('顺序样本③ 按 S1–S6 必 pass', realDiff.mismatch === false, {
    fixtures: fixture.sourceDigest, disk: diskDigest, changed: realDiff.changed,
  });
  // sourceDigest 不等却仍跑 = 失败：preflight 在真实 fixture 上必须不产生 build-order
  const trueFixtureOk = preflightStale(fixture, { diskFiles, diskDigest, quiet: true });
  record('T02\' sourceDigest 不等却仍跑即失败', trueFixtureOk === true && realDiff.mismatch === false, {
    preflightOk: trueFixtureOk, mismatch: realDiff.mismatch,
  });

  // 真实跑一遍 fixtures 的 removals 比对，统计条数（为 0 即空绿、门禁无效）
  verifyCases();
  verifyTransitions();
  record('覆盖度: removals 实际比对条数 > 0', stats.removalsCompared > 0, { count: stats.removalsCompared });
  record('覆盖度: removals 非空条目 ≥ 1', stats.removalsNonEmpty >= 1, { count: stats.removalsNonEmpty });
  record('覆盖度: 一次移除 ≥ 2 枚子', stats.removalsMulti >= 1, { count: stats.removalsMulti });

  const passed = checks.filter((c) => c.ok).length;
  console.log(`\n[removals-selftest] ${passed}/${checks.length} 通过`);
  console.log(`  removals 实际比对 (case_id, move_key) 条数: ${stats.removalsCompared}`);
  console.log(`  非空条目 ${stats.removalsNonEmpty} / 一次≥2 枚 ${stats.removalsMulti}`);
}

// ------------------------------------------------------------ 汇总
function summarize() {
  const total = stats.cases + stats.transitions;
  if (failureCounts.size) {
    console.error(`\n✗ 规则比对失败：${[...failureCounts.values()].reduce((a, b) => a + b, 0)} 处，分 kind 汇总：\n`);
    for (const [kind, count] of [...failureCounts].sort((a, b) => b[1] - a[1])) {
      console.error(`  ${kind.padEnd(22)} ${count}`);
    }
    console.error(`\n前 ${failures.length} 条明细：`);
    for (const item of failures) {
      console.error(`[${item.kind}] ${item.id}`);
      console.error(JSON.stringify(item.detail, null, 2));
      console.error('');
    }
    if ([...failureCounts.keys()].includes('stale-fixtures')) {
      console.error('下一步（产物过期）：');
      console.error('  python scripts/gen_web_profiles.py --write');
      console.error('  python scripts/gen_rule_fixtures.py --write');
      console.error('  python scripts/build_webapp_bundle.py');
    }
    console.error(`局面 ${stats.cases} / 走子 ${stats.transitions} / 合法着法 ${stats.legalTotal} / removals 比对 ${stats.removalsCompared}`);
    process.exit(1);
  }
  console.log('✓ 规则一致');
  console.log(`  局面比对      ${stats.cases}`);
  console.log(`  走子结算      ${stats.transitions}`);
  console.log(`  合法着法总数  ${stats.legalTotal}`);
  console.log(`  removals 比对 ${stats.removalsCompared}（非空 ${stats.removalsNonEmpty}，一次≥2 枚 ${stats.removalsMulti}）`);
  console.log(`  合计校验项    ${total}`);
}

if (!preflightStale()) {
  summarize();
} else if (SELFTEST) {
  runSelftest();
  summarize();
} else {
  verifyCases();
  verifyTransitions();
  summarize();
}
