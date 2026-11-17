/** 每日一题：选题规则与连续天数（本地日期种子，零联网零采集）。
 *
 * 本文件是 core/daily.py 的 JS 镜像，**算法必须逐字等价** —— 否则两个朋友
 * 同一天会看到不同的题，破坏"每日"这个约定。tests/test_daily_parity.py
 * 用逐日对拍把这一点钉死：Python 算 N 天、JS 算同样 N 天，逐日比对 level/id。
 *
 * 与 core 一致的三条约束：
 * 1. 题目只由本地日期决定，不读统计、不上报；
 * 2. 难度按星期固定轮换（不做自适应）；
 * 3. 桶内指针是纯函数：只由日期 + 题库 id 排序推出，不存"做到第几题"。
 */

export const BASE_MONDAY = '2026-01-05';
export const WEEKDAY_LEVELS = [
  'beginner', 'advanced', 'beginner', 'advanced', 'beginner', 'master', 'master',
];
const PER_WEEK = {};
for (const level of WEEKDAY_LEVELS) PER_WEEK[level] = (PER_WEEK[level] || 0) + 1;
const FALLBACK = { master: ['advanced', 'beginner'], advanced: ['beginner'], beginner: [] };
export const DAILY_KEY = 'xh-daily';

function parseISO(s) {
  // 用 UTC 锚定，避免本地时区把日期拨快/拨慢一天（core 用 date 对象，无时区）。
  const [y, m, d] = s.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

export function isoDate(date) {
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
}

export function todayLocal() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

export function levelFor(dayStr) {
  // core: WEEKDAY_LEVELS[day.weekday()]，周一=0；UTC 锚定后 getUTCDay 周一=1。
  return WEEKDAY_LEVELS[(parseISO(dayStr).getUTCDay() + 6) % 7];
}

export function dayIndex(dayStr, level) {
  // core: delta = (day - BASE_MONDAY).days；<0 按 0；divmod(delta,7)；
  // within_week = sum(1 for i in range(remainder+1) if WEEKDAY_LEVELS[i]==level)
  let delta = Math.round((parseISO(dayStr) - parseISO(BASE_MONDAY)) / 86400000);
  if (delta < 0) delta = 0;
  const fullWeeks = Math.floor(delta / 7);
  const remainder = delta % 7;
  let withinWeek = 0;
  for (let i = 0; i <= remainder; i++) if (WEEKDAY_LEVELS[i] === level) withinWeek += 1;
  return fullWeeks * (PER_WEEK[level] || 0) + withinWeek;
}

export function bucketOf(puzzles, level) {
  // core: 按 id 字典序排；tags 含 drill 的不参与每日一题。
  return puzzles
    .filter((p) => p.level === level && !p.drill)
    .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

export function pickDaily(puzzles, dayStr) {
  const level = levelFor(dayStr);
  for (const candidate of [level, ...(FALLBACK[level] || [])]) {
    const bucket = bucketOf(puzzles, candidate);
    if (!bucket.length) continue;
    const index = ((dayIndex(dayStr, candidate) - 1) % bucket.length + bucket.length) % bucket.length;
    return bucket[index];
  }
  return null;
}

export function readRecord() {
  try {
    const raw = JSON.parse(localStorage.getItem(DAILY_KEY) || '{}');
    return raw && typeof raw === 'object' ? raw : {};
  } catch { return {}; }
}

export function saveRecord(record) {
  try { localStorage.setItem(DAILY_KEY, JSON.stringify(record)); } catch { /* 隐私模式忽略 */ }
}

function gapDays(from, to) {
  return Math.round((parseISO(to) - parseISO(from)) / 86400000);
}

export function lazyStreak(record, dayStr) {
  // core::_lazy_streak：昨天没做完就断；断了两天以上也断。
  if (!record.day) return 0;
  const gap = gapDays(record.day, dayStr);
  if (gap > 1) return 0;
  if (gap === 1 && !record.done) return 0;
  return record.streak || 0;
}

export function solveToday(record, dayStr, puzzle) {
  // core::solve_today：同一天重解不涨，隔天做完才 +1。
  if (record.day === dayStr && record.done) return record;
  let streak = 1;
  if (record.day) {
    const gap = gapDays(record.day, dayStr);
    if (gap === 1 && record.done) streak = (record.streak || 0) + 1;
  }
  return {
    day: dayStr,
    id: puzzle.id,
    done: true,
    streak,
    best: Math.max(streak, record.best || 0),
  };
}
