/**
 * 训练进度纯函数（批次 A / P1-3 章节化 + P1-4 连对挑战）。
 *
 * 本模块**零 DOM、零 localStorage、零网络**：只做算法，便于 node 探针直接 import
 * 与 core/training_progress.py 逐项对拍。三端口径（桌面 / webapp / web 旧树）
 * 必须逐字一致，改这里就要同步改那两处。
 *
 * 命名纪律：
 * - 「坚持天数」= 每日一题的连续天数，存在 xh-daily，别碰；
 * - 「连对题数」= 连对挑战（一错即止）的成绩，单位题，存在 xh-web-prefs-v1 的
 *   training 分区（app.prefs.training.streak.best；web 旧树另存 xh-training）；
 * - Storm 已砍，不建任何 storm 函数 / 字段。
 */

// 章节顺序单一口径：从题库产物（由 core.CHAPTERS 生成）导入，勿在此另建副本。
import { CHAPTER_ORDER } from '../data/puzzles.js';
export { CHAPTER_ORDER };

export function chapterIndex(name) {
  const index = CHAPTER_ORDER.indexOf(name);
  return index < 0 ? CHAPTER_ORDER.length : index;
}

/** 星级：只罚错着与提示，不奖励速度。0→3、1–2→2、≥3→1。 */
export function starsFor(misses, hints) {
  const penalty = (misses || 0) + (hints || 0);
  return penalty === 0 ? 3 : penalty <= 2 ? 2 : 1;
}

function chapterPuzzles(puzzles, chapter) {
  return (puzzles || []).filter(
    (item) => item.chapter === chapter && !(item.tags || []).includes('drill'),
  );
}

/**
 * 章节解锁：首章默认开；第 N 章 = 第 N-1 章全部题都解出过（stars>=1）。
 * 「用过提示 / 错过也算解出」——所以判据是 stars>=1 而非 ===3。星级不做门槛。
 * 空章节视为已满足（避免题库缺章时把后续章节永久锁死）。
 */
export function unlockedChapters(stars, puzzles, chapters = CHAPTER_ORDER) {
  const solved = stars || {};
  const unlocked = [];
  for (let i = 0; i < chapters.length; i += 1) {
    if (i === 0) {
      unlocked.push(chapters[i]);
      continue;
    }
    // 严格链式：前一章没解锁，后面一律锁死，不许因中间某章空题而跳级。
    if (!unlocked.includes(chapters[i - 1])) continue;
    const previous = chapterPuzzles(puzzles, chapters[i - 1]);
    // 空章不算「全部解出」——那是题库数据缺陷，不能静默放行（真实五章都有题）。
    const allSolved = previous.length > 0 && previous.every((item) => (solved[item.id] || 0) >= 1);
    if (allSolved) unlocked.push(chapters[i]);
  }
  return unlocked;
}

/**
 * 连对挑战题池：已解锁章节 + 非 drill + 排除当日每日一题。
 * 只返回**按抽题优先级排好的池**，一轮内不重复由会话层维护 `used` 集合。
 * 优先级：未做过 → 星级<3 → 其余；同级按章节顺序，再按题库原序。
 */
export function poolFor(stars, unlocked, dailyId, puzzles) {
  const solved = stars || {};
  const open = unlocked || [];
  const eligible = (puzzles || []).filter(
    (item) =>
      item.chapter &&
      open.includes(item.chapter) &&
      !(item.tags || []).includes('drill') &&
      item.id !== dailyId,
  );
  const rank = (item) => {
    const star = solved[item.id] || 0;
    if (star === 0) return 0;
    if (star < 3) return 1;
    return 2;
  };
  return eligible
    .map((item, index) => ({ item, index, r: rank(item) }))
    .sort((a, b) => a.r - b.r || chapterIndex(a.item.chapter) - chapterIndex(b.item.chapter) || a.index - b.index)
    .map((entry) => entry.item);
}

/** 卡关软提示：某题连续错误达到阈值就问一句「要不要看条提示？」。 */
export function softHintDue(consecutiveMisses, threshold = 5) {
  return (consecutiveMisses || 0) >= threshold;
}

/** 章节汇总：返回每章 { chapter, total, solved, stars, max, unlocked }。 */
export function chapterSummary(stars, unlocked, puzzles) {
  const solved = stars || {};
  const open = unlocked || [];
  return CHAPTER_ORDER.map((chapter) => {
    const items = chapterPuzzles(puzzles, chapter);
    const earned = items.reduce((sum, item) => sum + (solved[item.id] || 0), 0);
    return {
      chapter,
      total: items.length,
      solved: items.filter((item) => (solved[item.id] || 0) >= 1).length,
      stars: earned,
      max: items.length * 3,
      unlocked: open.includes(chapter),
    };
  });
}
