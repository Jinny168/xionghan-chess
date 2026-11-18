// 训练进度纯函数对拍探针（由 tests/test_training_parity.py 驱动）。
// 把一组固定的 (stars, unlocked, dailyId, puzzles) 输入喂给 webapp 的
// training_progress.js，导出各函数结果 JSON，供 Python core/training_progress.py
// 逐项比对。零 DOM、零存储。
// 用法：node tests/training_progress_probe.mjs <path-to-training_progress.js>
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const modPath = process.argv[2];
if (!modPath) throw new Error('need path to training_progress.js');
const mod = await import(pathToFileURL(path.resolve(modPath)).href);

const CHAPTER_ORDER = mod.CHAPTER_ORDER;
const { starsFor, unlockedChapters, poolFor, softHintDue, chapterSummary, chapterIndex } = mod;

// 固定的题库切片：覆盖 drill / 五章 / defense / feature / 各星级。
const puzzles = [
  { id: 'drill-1', chapter: '', tags: ['drill'] },
  { id: 'a1', chapter: '揭竿', tags: ['mate3'] },
  { id: 'a2', chapter: '揭竿', tags: ['mate3'] },
  { id: 'b1', chapter: '破釜', tags: ['defense'] },
  { id: 'b2', chapter: '破釜', tags: ['feature:archer'] },
  { id: 'c1', chapter: '逐鹿', tags: ['mate5'] },
  { id: 'c2', chapter: '逐鹿', tags: ['equilibrium'] },
  { id: 'd1', chapter: '垓下', tags: ['mate7'] },
  { id: 'd2', chapter: '垓下', tags: ['counter'] },
  { id: 'e1', chapter: '定鼎', tags: ['mate7'] },
  { id: 'e2', chapter: '定鼎', tags: ['feature:guard'] },
];

const starCases = [
  {},
  { a1: 3, a2: 2 },
  { a1: 3, a2: 3, b1: 1, b2: 2 },
  { a1: 3, a2: 3, b1: 3, b2: 3, c1: 1, c2: 1 },
  Object.fromEntries(puzzles.filter((p) => p.chapter).map((p) => [p.id, 3])),
];

const out = {
  chapterOrder: CHAPTER_ORDER,
  chapterIndex: ['', '揭竿', '破釜', '逐鹿', '垓下', '定鼎', '不存在'].map((c) => chapterIndex(c)),
  stars: [0, 1, 2, 3, 4, 9].map((m) => [m, starsFor(m, 0), starsFor(0, m), starsFor(m, m)]),
  softHint: [0, 4, 5, 6, 20].map((n) => softHintDue(n)),
  unlocked: starCases.map((s) => unlockedChapters(s, puzzles)),
  pool: starCases.map((s, i) => poolFor(s, unlockedChapters(s, puzzles), i % 2 ? 'a1' : null, puzzles).map((p) => p.id)),
  summary: starCases.map((s) => chapterSummary(s, unlockedChapters(s, puzzles), puzzles)),
};

console.log(JSON.stringify(out));
