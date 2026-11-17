/**
 * 星轨锚点跨端对拍探针（由 tests/test_star_lattice_parity.py 驱动）。
 *
 * 同一组 (points, source, rows, cols) 喂给两份实现：
 *   · webapp/js/ui/star_hints.js —— 用真实 webapp RulesEngine 的
 *     `_nearestArcherStarDistance`（星点集替换为同一份 points，判定逻辑仍是 core 的）；
 *   · web/js/star-hints.js      —— 旧树没有该方法，用纯几何版。
 * 输出只保留 [row, col]，避免实现里的附加字段造成假差异。
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { pathToFileURL } from 'node:url';

import { RulesEngine } from '../webapp/js/core/rules.js';

const [webappPath, webPath] = process.argv.slice(2);
const { archerAnchorRays: webappAnchors } = await import(pathToFileURL(path.resolve(webappPath)).href);
vm.runInThisContext(readFileSync(path.resolve(webPath), 'utf8'), { filename: path.resolve(webPath) });
const webAnchors = globalThis.XHStarHints?.archerAnchorRays;
if (typeof webAnchors !== 'function') throw new Error('web/js/star-hints.js 未挂 globalThis.XHStarHints');

const payload = JSON.parse(readFileSync(0, 'utf8'));
const key = (p) => `${p.row},${p.col}`;
const normalise = (list) => list.map(({ row, col }) => [row, col]);
const output = [];

for (const testCase of payload.cases) {
  const { points, rows, cols, source } = testCase;
  const profile = {
    id: 'parity',
    rows,
    cols,
    options: { archer_appear: true },
    enabledPieceTypes: ['archer'],
  };
  const rules = new RulesEngine(profile);
  const starSet = new Set(points.map(key));
  rules.isStarPoint = (p) => starSet.has(key(p));

  output.push({
    webapp: normalise(webappAnchors(rules, source)),
    web: normalise(webAnchors(points, source, rows, cols)),
  });
}

process.stdout.write(JSON.stringify(output));
