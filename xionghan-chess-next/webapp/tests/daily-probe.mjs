// 每日一题选题对拍探针：把一段日期区间内每天的选题结果导出为 JSON，
// 供 tests/test_daily_parity.py 与 Python core/daily.py 逐日比对。
// 用法：node webapp/tests/daily-probe.mjs <start> <days>
//   start: YYYY-MM-DD；days: 天数
import { PUZZLES } from '../js/data/puzzles.js';
import { levelFor, dayIndex, pickDaily, bucketOf } from '../js/ui/daily.js';

const start = process.argv[2];
const days = Number(process.argv[3] || 60);
const [y, m, d] = start.split('-').map(Number);
const base = Date.UTC(y, m - 1, d);

const rows = [];
for (let i = 0; i < days; i++) {
  const dt = new Date(base + i * 86400000);
  const iso = `${dt.getUTCFullYear()}-${String(dt.getUTCMonth() + 1).padStart(2, '0')}-${String(dt.getUTCDate()).padStart(2, '0')}`;
  const level = levelFor(iso);
  const puzzle = pickDaily(PUZZLES, iso);
  rows.push({
    day: iso,
    level,
    id: puzzle ? puzzle.id : null,
    dayIndexBeginner: dayIndex(iso, 'beginner'),
    dayIndexAdvanced: dayIndex(iso, 'advanced'),
    dayIndexMaster: dayIndex(iso, 'master'),
    bucketBeginner: bucketOf(PUZZLES, 'beginner').map((p) => p.id),
    bucketAdvanced: bucketOf(PUZZLES, 'advanced').map((p) => p.id),
    bucketMaster: bucketOf(PUZZLES, 'master').map((p) => p.id),
  });
}
console.log(JSON.stringify(rows));
