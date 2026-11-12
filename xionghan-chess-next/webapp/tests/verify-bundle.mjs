#!/usr/bin/env node
/**
 * T15 · bundle 内嵌引擎运行时判据（静态计数替代不了）。
 *
 * 主理人裁决记录：
 *  - A：阈值一律限定在**两份内嵌 `__mods["js/core/rules.js"]` 引擎快照**（vm 提取），
 *    整页 HTML 字符串计数只作「记录值」、不作断言（注释/UI 文案会污染计数）。
 *  - B：`_armorCaptures == 0` 是 QA Q-ART-01 的**条件性期望**（「若 profiles 重生后
 *    已移除甲/楯/刺」），前提未成立（§0 明令不动软删分支）→ **本轮不适用**，不删代码，
 *    按「两份快照与唯一源逐字一致」+ Q-ART-03 运行时判据收口。
 *  - C：`pawn_full_movement_at_base` 的 app.js:65 UI 文案按 §0 不动，登记为
 *    「已知展示层文案债」；补产物侧语义断言（内嵌 profiles.js 的 DEFAULT_OPTIONS 键集）。
 *  - D：`__mods[...] = (function` 恰好 2 = `js/core/rules.js` 引擎快照恰好 2 份
 *    （主 inline 1 + WORKER_SRC 解码 1）；总模块赋值数 20 不作断言。
 *  - rs3：经裁决「不写死 `rs3-` 字面量」优先，文本哨兵认 `rs${RULE_VERSION}-`（≥2），
 *    运行时串由 T14 的 Q-PK-01/02 逐字全等覆盖；不留逐字 `rs3-` 的假断言。
 *
 * Q-ART-03 运行时（每份内嵌引擎各跑一遍）：
 *   1. `typeof RulesEngine.prototype.threeLineCaptures === 'function'`
 *   2. W-01：applyUnchecked 移除集合 == [[advisor,black,5,6]]
 *   3. 双王同行照面（rand:desktop_complete:17，红王 2,9 / 黑王 2,3）→ inCheck=true
 *   4. 同列正对照（红王 2,9 / 黑王 8,9，中间无子）→ inCheck=true（防过剪）
 *   5. 双王不同行不同列（红王 12,0 / 黑王 0,12）→ inCheck=false（防误判）
 *
 * 运行：node webapp/tests/verify-bundle.mjs
 */

import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { readHtml, loadEngines, rulesSnapshots, w01Case } from './lib/bundle-vm.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const WEBAPP = join(here, '..');
const HTML = join(WEBAPP, '..', 'online', 'public', 'index.html');
const HTML_DIST = join(WEBAPP, 'dist', 'index.html');

const failures = [];
function fail(id, detail) {
  failures.push({ id, detail });
}

// ---------------------------------------------------------------- Q-ART-01
/** 阈值只按**两份内嵌规则引擎快照**计（裁决 A）；整页计数仅打印记录值。 */
function checkMarkers(html, label) {
  const snap = rulesSnapshots(html);
  const blocks = snap.all;
  // 记录值（不作断言）：整页字符串计数，含注释/UI 文案
  console.log(`  [${label}/记录值] 整页 rs3-=${html.split('rs3-').length - 1} `
    + `pawn_full_movement_at_base=${html.split('pawn_full_movement_at_base').length - 1} `
    + `_armorCaptures=${html.split('_armorCaptures').length - 1} `
    + `_kingsFacing=${html.split('_kingsFacing').length - 1}`);
  if (blocks.length !== 2) {
    fail(`${label}/snapshot-count`, {
      reason: '__mods["js/core/rules.js"] 引擎快照数不等于 2',
      actual: blocks.length, main: snap.main.length, worker: snap.worker.length,
      fix: 'python scripts/build_webapp_bundle.py',
    });
  }
  // 裁决 D：全文件 _kingsFacing 出现 4 次（两份 rules.js 快照 × 2 处：定义+调用），
  // 这里按快照内计数，不按整页（整页含 profiles/其它模块不会被误计）。
  const joined = blocks.join('\n');
  const thresholds = [
    ['threeLineCaptures', 2],
    ['pawn_three_line_capture', 2],
    ['p3l', 2],
    ['rs${RULE_VERSION}-', 2], // 裁决 rs3：不写死字面量，等价形式
    ['||opt:', 2],
    ['||pool:', 2],
    ['_kingsFacing', 4], // 裁决补充：全文件 4 次（两份快照各 2）
  ];
  for (const [token, min] of thresholds) {
    const count = joined.split(token).length - 1;
    if (count < min) {
      fail(`${label}/marker`, {
        reason: `内嵌规则快照标记 ${token} 计数 ${count} < ${min}（两份快照都要有）`,
        fix: 'python scripts/build_webapp_bundle.py',
      });
    }
  }
  // 每份快照单独判：任一缺标记也必须红（等价于「两份都更新」）
  for (let index = 0; index < blocks.length; index += 1) {
    for (const token of ['threeLineCaptures', 'p3l', '||opt:', '||pool:', 'rs${RULE_VERSION}-', '_kingsFacing']) {
      if (!blocks[index].includes(token)) {
        fail(`${label}/snapshot-${index}`, {
          reason: `第 ${index + 1} 份引擎快照缺 ${token}`,
          fix: 'python scripts/build_webapp_bundle.py',
        });
      }
    }
    // 裁决 C-1：rules.js 快照内不得残留 1.9.x 死开关键名（注释已改措辞）
    if (blocks[index].includes('pawn_full_movement_at_base')) {
      fail(`${label}/stale-token-${index}`, {
        reason: `第 ${index + 1} 份 rules.js 快照残留 pawn_full_movement_at_base`,
        fix: 'python scripts/build_webapp_bundle.py',
      });
    }
    // 裁决 A/B：_armorCaptures 两份快照与唯一源逐字一致（前提未成立 → 不判 0）
    const sourceRules = readHtml(join(WEBAPP, 'js', 'core', 'rules.js'));
    const sourceArmor = sourceRules.split('_armorCaptures').length - 1;
    const count = blocks[index].split('_armorCaptures').length - 1;
    if (count !== sourceArmor) {
      fail(`${label}/armor-snapshot-${index}`, {
        reason: `第 ${index + 1} 份快照 _armorCaptures 计数=${count} != 唯一源 ${sourceArmor}（疑似旧引擎）`,
        fix: 'python scripts/build_webapp_bundle.py',
      });
    }
  }
  return snap;
}

/** 裁决 C-3：内嵌 profiles.js 的 DEFAULT_OPTIONS 键集语义断言（产物侧防复发）。 */
function checkProfilesSemantics(mods, label) {
  const profiles = mods['js/core/profiles.js'];
  if (!profiles || !profiles.DEFAULT_OPTIONS) {
    fail(`${label}/profiles-default`, {
      reason: '内嵌 profiles.js 缺 DEFAULT_OPTIONS 模块或导出',
      fix: 'python scripts/build_webapp_bundle.py',
    });
    return;
  }
  const keys = new Set(Object.keys(profiles.DEFAULT_OPTIONS));
  if (keys.has('pawn_full_movement_at_base')) {
    fail(`${label}/profiles-default`, {
      reason: '内嵌 DEFAULT_OPTIONS 仍含 pawn_full_movement_at_base（1.9.x 死开关复活）',
      fix: 'python scripts/gen_web_profiles.py --write && python scripts/build_webapp_bundle.py',
    });
  }
  for (const required of ['pawn_three_line_capture', 'pawn_charge']) {
    if (!keys.has(required)) {
      fail(`${label}/profiles-default`, {
        reason: `内嵌 DEFAULT_OPTIONS 缺 ${required}（护栏会空跑）`,
        fix: 'python scripts/gen_web_profiles.py --write && python scripts/build_webapp_bundle.py',
      });
    }
  }
  console.log(`  [${label}/profiles] DEFAULT_OPTIONS 键数=${keys.size} `
    + `p3l=${keys.has('pawn_three_line_capture')} charge=${keys.has('pawn_charge')} `
    + `旧键=${keys.has('pawn_full_movement_at_base')}`);
}

// ---------------------------------------------------------------- 双王照面
/** 用 vm 里的 model/profiles/rules 构造稀疏局面，返回 engine.inCheck(state, 'red')。 */
function facingCheck(mods, redKing, blackKing) {
  const model = mods['js/core/model.js'];
  const profiles = mods['js/core/profiles.js'];
  const Engine = mods['js/core/rules.js']?.RulesEngine;
  if (!model || !profiles || !Engine) return null;
  const pieces = [
    model.makePiece('king', 'red', redKing[0], redKing[1], 'fk:r'),
    model.makePiece('king', 'black', blackKing[0], blackKing[1], 'fk:b'),
  ];
  const state = model.createState('web', pieces, 'red');
  const profile = profiles.getProfile('web');
  const options = profiles.mergeOptions(profile.options, {});
  const engine = new Engine(profile, options);
  return engine.inCheck(state, 'red');
}

/** 裁决 A 补充：两份内嵌引擎各验证双王同行 / 同列正对照 / 不同行不同列反例。 */
function checkKingsFacing(mods, label) {
  const cases = [
    ['同行照面', [2, 9], [2, 3], true], // rand:desktop_complete:17
    ['同列正对照', [2, 9], [8, 9], true], // 防过剪：原实现本就认同列
    ['不同行不同列', [12, 0], [0, 12], false], // 防误判
  ];
  for (const [name, redKing, blackKing, expected] of cases) {
    const actual = facingCheck(mods, redKing, blackKing);
    if (actual === null) {
      fail(`${label}/kings-facing`, { reason: `${name} 无法求值（缺 model/profiles/rules）` });
      continue;
    }
    if (actual !== expected) {
      fail(`${label}/kings-facing`, {
        reason: `[bundle-stale] ${label} ${name} inCheck=${actual}，期望 ${expected}（红王 ${redKing} / 黑王 ${blackKing}）→ 运行 python scripts/build_webapp_bundle.py 重建`,
        fix: 'python scripts/build_webapp_bundle.py',
      });
    }
    console.log(`  [${label}/${name}] inCheck(red)=${actual} 期望=${expected} ${actual === expected ? '✓' : '✗'}`);
  }
}

// ---------------------------------------------------------------- Q-ART-03
function checkRuntime(html, label) {
  const loaded = loadEngines(html);
  if (loaded.error) {
    fail(`${label}/vm`, { reason: loaded.error, fix: 'python scripts/build_webapp_bundle.py' });
    return;
  }
  for (const which of ['worker', 'main']) {
    const engineInfo = loaded[which];
    const tag = which === 'worker' ? 'WORKER_SRC' : '主inline';
    if (!engineInfo || !engineInfo.engine) {
      fail(`${label}/${tag}`, {
        reason: `${tag} 拿不到 RulesEngine（求值 ${engineInfo?.evaluated ?? 0}/${engineInfo?.total ?? 0}）`,
        fix: 'python scripts/build_webapp_bundle.py',
      });
      continue;
    }
    const w = w01Case(engineInfo.mods, {});
    if (!w) {
      fail(`${label}/${tag}`, { reason: `${tag} 缺 model/profiles/rules 模块`, fix: 'python scripts/build_webapp_bundle.py' });
      continue;
    }
    if (!w.hasThreeLine) {
      fail(`${label}/${tag}`, {
        reason: `[bundle-stale] ${tag} threeLineCaptures 缺失 → 运行 python scripts/build_webapp_bundle.py 重建`,
        fix: 'python scripts/build_webapp_bundle.py',
      });
    }
    const expected = [['advisor', 'black', 5, 6]];
    if (JSON.stringify(w.removed) !== JSON.stringify(expected)) {
      fail(`${label}/${tag}`, {
        reason: `[bundle-stale] ${tag} W-01 removals=${JSON.stringify(w.removed)}（期望 ${JSON.stringify(expected)}）→ 运行 python scripts/build_webapp_bundle.py 重建`,
        expected, actual: w.removed,
        fix: 'python scripts/build_webapp_bundle.py',
      });
    }
    console.log(`  [${label}/${tag}] 求值 ${engineInfo.evaluated}/${engineInfo.total} 块，`
      + `threeLineCaptures=${w.hasThreeLine} W-01 removals=${JSON.stringify(w.removed)}`);
    checkProfilesSemantics(engineInfo.mods, `${label}/${tag}`);
    checkKingsFacing(engineInfo.mods, `${label}/${tag}`);
  }
}

if (!existsSync(HTML)) {
  console.error('[bundle-stale] online/public/index.html 不存在 → 运行 python scripts/build_webapp_bundle.py 重建');
  process.exit(1);
}
const html = readHtml(HTML);
console.log(`[verify-bundle] ${HTML} (${html.length} chars)`);
console.log('Q-ART-01 标记阈值（两份引擎快照，≥2；整页计数仅记录）：');
checkMarkers(html, 'online');
console.log('Q-ART-03 运行时（vm 求值 + W-01 + profiles 语义 + 双王照面）：');
checkRuntime(html, 'online');

// webapp/dist/index.html 是同一份 bundle 的另一产物，也要过
if (!existsSync(HTML_DIST)) {
  fail('dist/missing', { reason: 'webapp/dist/index.html 不存在', fix: 'python scripts/build_webapp_bundle.py' });
} else {
  const distHtml = readHtml(HTML_DIST);
  checkMarkers(distHtml, 'dist');
  checkRuntime(distHtml, 'dist');
}

if (failures.length) {
  console.error(`\n✗ [bundle-stale] ${failures.length} 处：`);
  for (const item of failures) {
    console.error(`  [${item.id}] ${item.detail.reason}`);
    if (item.detail.actual !== undefined) console.error(`    actual=${JSON.stringify(item.detail.actual)}`);
    console.error(`    → ${item.detail.fix}`);
  }
  process.exit(1);
}
console.log('✓ [verify-bundle] Q-ART-01 + Q-ART-03 全通过（两份引擎：三连/W-01/profiles语义/双王同行/同列正对照/反例）');
