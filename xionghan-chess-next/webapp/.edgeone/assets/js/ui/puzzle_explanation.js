/** Webapp 的解析接线：纯函数，不碰 DOM，便于 Node 探针真跑同一条链路。 */

import { PUZZLE_EXPLANATIONS } from '../data/puzzle_explanations.js';

/** 把解析作为**最后一条**提示追加；返回新数组，不改题库里的原始 hints。 */
export function withExplanation(hints, puzzleId) {
  const base = Array.isArray(hints) ? hints.slice() : [];
  const item = PUZZLE_EXPLANATIONS[puzzleId];
  if (!item) return base; // 13 条 drill / 自定义题：没有解析，保持原样
  base.push(`${item.key_move}\n${item.why}`);
  return base;
}

/** 现有揭示口径原样保留：按 step 取一条，越界取最后一条（解析）。 */
export function hintAt(hints, step, fallback) {
  const list = Array.isArray(hints) ? hints : [];
  return list[Math.min(step, list.length - 1)] || fallback;
}
