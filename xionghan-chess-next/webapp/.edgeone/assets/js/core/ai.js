/**
 * 浏览器端对弈引擎。
 *
 * 与桌面端 `core/ai.py` 同源思路：迭代加深 + alpha-beta + 静态搜索 +
 * MVV-LVA 排序。搜索层使用「伪合法着法 + 王被吃即终局」的标准做法
 * （这才是引擎的常规写法），根节点再用完整合法性过滤，保证最终落子
 * 一定通过规则校验。
 */

import { opponent } from './model.js';
import { legalMovesFast, pseudoCaptures, pseudoMovesFrom } from './movegen.js';

export const VALUES = {
  king: 50000, rook: 900, cannon: 500, horse: 450, elephant: 260, advisor: 240,
  pawn: 120, guard: 520, archer: 480, thunder: 650, armor: 420, assassin: 430,
  shield: 600, patrol: 360,
};

const MOBILE = new Set(['rook', 'horse', 'cannon', 'guard', 'archer', 'thunder', 'armor', 'assassin', 'shield', 'patrol']);

const CENTRAL_WEIGHTS = {
  king: -1.0, rook: 1.4, cannon: 1.8, horse: 2.8, elephant: 0.8, advisor: 0.5,
  pawn: 1.4, guard: 1.7, archer: 1.8, thunder: 2.4, armor: 1.8, assassin: 2.2,
  shield: 1.0, patrol: 1.2,
};

const MATE = 900000;

export const DIFFICULTIES = {
  novice: { id: 'novice', label: '入门', depth: 1, timeMs: 200, randomness: 0.45, quiescence: 1 },
  easy: { id: 'easy', label: '初级', depth: 2, timeMs: 550, randomness: 0.12, quiescence: 2 },
  normal: { id: 'normal', label: '中级', depth: 3, timeMs: 1300, randomness: 0.02, quiescence: 4 },
  hard: { id: 'hard', label: '高级', depth: 4, timeMs: 2800, randomness: 0, quiescence: 6 },
  master: { id: 'master', label: '大师', depth: 5, timeMs: 4200, randomness: 0, quiescence: 8 },
};

export const DIFFICULTY_ORDER = ['novice', 'easy', 'normal', 'hard', 'master'];

const TYPE_INDEX = {
  king: 0, rook: 1, horse: 2, elephant: 3, advisor: 4, cannon: 5, pawn: 6,
  guard: 7, archer: 8, thunder: 9, armor: 10, assassin: 11, shield: 12, patrol: 13,
};

function rootMoveKey(move) {
  return `${move.source.row},${move.source.col}-${move.target.row},${move.target.col}`;
}

function now() {
  return typeof performance !== 'undefined' ? performance.now() : Date.now();
}

class Timeout extends Error {}

function hasKing(state, color) {
  for (const p of state.pieces) if (p.type === 'king' && p.color === color) return true;
  return false;
}

/** 局面评估：红方视角为正。 */
export function evaluate(state, rules) {
  const rows = rules.profile.rows;
  const cols = rules.profile.cols;
  const centerRow = (rows - 1) / 2;
  const centerCol = (cols - 1) / 2;
  const maxDist = centerRow + centerCol;
  let score = 0;

  const kingPos = { red: null, black: null };
  for (const piece of state.pieces) {
    if (piece.type === 'king') kingPos[piece.color] = piece;
  }

  for (const piece of state.pieces) {
    const sign = piece.color === 'red' ? 1 : -1;
    let value = VALUES[piece.type] || 0;

    const dist = Math.abs(piece.row - centerRow) + Math.abs(piece.col - centerCol);
    if (MOBILE.has(piece.type)) {
      value += (CENTRAL_WEIGHTS[piece.type] || 1) * 3 * (1 - dist / maxDist);
    }

    if (piece.type === 'pawn') {
      const advance = piece.color === 'red' ? rows - 1 - piece.row : piece.row;
      value += advance * 4;
      if (advance >= Math.floor(rows / 2)) value += 30;
    }

    if (piece.type === 'shield') {
      const king = kingPos[piece.color];
      if (king) {
        const d = Math.max(Math.abs(king.row - piece.row), Math.abs(king.col - piece.col));
        if (d === 1) value += 70;
      }
    }

    if (piece.type === 'king') {
      const distToHome = piece.color === 'red'
        ? Math.abs(piece.row - (rows - 2)) + Math.abs(piece.col - centerCol)
        : Math.abs(piece.row - 1) + Math.abs(piece.col - centerCol);
      value -= distToHome * 3;
    }

    score += sign * value;
  }
  return state.turn === 'red' ? score : -score;
}

function moveScore(move, state, ctx) {
  let score = 0;
  const target = findPiece(state, move.target.row, move.target.col);
  if (target) {
    const attacker = findPiece(state, move.source.row, move.source.col);
    score += 10000 + (VALUES[target.type] || 0) - (VALUES[attacker?.type] || 0) / 10;
  }
  if (move.promotion) score += 8000 + (VALUES[move.promotion] || 0);
  const key = `${move.source.row},${move.source.col}-${move.target.row},${move.target.col}`;
  if (ctx.killers[0]?.key === key) score += 900;
  else if (ctx.killers[1]?.key === key) score += 600;
  score += ctx.history.get(key) || 0;
  return score;
}

function findPiece(state, row, col) {
  const grid = state._grid;
  if (grid) return grid[row * 64 + col] || null;
  for (const p of state.pieces) if (p.row === row && p.col === col) return p;
  return null;
}

function orderMoves(moves, state, ctx) {
  const scored = moves.map((move) => ({ move, score: moveScore(move, state, ctx) }));
  scored.sort((a, b) => b.score - a.score);
  return scored.map((item) => item.move);
}

function quiescence(state, rules, alpha, beta, depth, ctx, ply) {
  ctx.nodes += 1;
  if ((ctx.nodes & 1023) === 0 && now() > ctx.deadline) throw new Timeout();

  const standPat = evaluate(state, rules);
  if (depth <= 0) return standPat;
  if (standPat >= beta) return beta;
  if (standPat > alpha) alpha = standPat;

  const ordered = orderMoves(pseudoCaptures(state, rules), state, ctx);
  for (const move of ordered) {
    const next = rules.applyUnchecked(state, move);
    const score = -quiescence(next, rules, -beta, -alpha, depth - 1, ctx, ply + 1);
    if (score >= beta) return beta;
    if (score > alpha) alpha = score;
  }
  return alpha;
}

function negamax(state, rules, depth, alpha, beta, ctx, ply) {
  ctx.nodes += 1;
  if ((ctx.nodes & 511) === 0 && now() > ctx.deadline) throw new Timeout();
  if (!hasKing(state, state.turn)) return -MATE + ply;

  if (depth <= 0) {
    return quiescence(state, rules, alpha, beta, ctx.config.quiescence, ctx, ply);
  }

  const moves = pseudoMovesFrom(state, rules);
  if (!moves.length) return -MATE + ply;

  const ordered = orderMoves(moves, state, ctx);
  let best = -Infinity;
  let bestKey = null;
  let first = true;
  let moveIndex = 0;
  for (const move of ordered) {
    const next = rules.applyUnchecked(state, move);
    if (!hasKing(next, opponent(state.turn))) {
      best = MATE - ply;
      break;
    }
    const quiet = !findPiece(state, move.target.row, move.target.col);
    // LMR：靠后的安静着法先减深度搜，改进了再补搜
    let reduce = 0;
    if (!first && quiet && depth >= 3) {
      if (moveIndex >= 8 && depth >= 4) reduce = 2;
      else if (moveIndex >= 4) reduce = 1;
    }
    let score;
    if (first) {
      score = -negamax(next, rules, depth - 1, -beta, -alpha, ctx, ply + 1);
      first = false;
    } else {
      // PVS：先用零窗口试探，确认能改进再全窗口重搜
      score = -negamax(next, rules, depth - 1 - reduce, -alpha - 1, -alpha, ctx, ply + 1);
      if (score > alpha) {
        score = -negamax(next, rules, depth - 1, -beta, -alpha, ctx, ply + 1);
      }
    }
    moveIndex += 1;
    if (score > best) {
      best = score;
      bestKey = `${move.source.row},${move.source.col}-${move.target.row},${move.target.col}`;
    }
    if (score > alpha) alpha = score;
    if (alpha >= beta) {
      if (!findPiece(state, move.target.row, move.target.col)) {
        ctx.killers[1] = ctx.killers[0];
        ctx.killers[0] = { key: bestKey };
        const prev = ctx.history.get(bestKey) || 0;
        ctx.history.set(bestKey, prev + depth * depth);
      }
      break;
    }
  }
  return best;
}

/**
 * 选取一步棋。
 * @returns {{move: object|null, score: number, depth: number, nodes: number, elapsed: number}}
 */
export function chooseMove(state, rules, difficulty = 'normal', options = {}) {
  const config = DIFFICULTIES[difficulty] || DIFFICULTIES.normal;
  const timeMs = options.timeMs ?? config.timeMs;
  const maxDepth = options.depth ?? config.depth;
  // 复盘需要每个根着法的「真实分」，PVS 的零窗口只会给出边界，故提供全窗口模式
  const exactRoot = Boolean(options.exactRoot);
  const start = now();
  const deadline = start + timeMs;

  const rootMoves = legalMovesFast(state, rules);
  if (!rootMoves.length) {
    return { move: null, score: 0, depth: 0, nodes: 0, elapsed: 0 };
  }

  const ctx = {
    nodes: 0,
    deadline,
    config,
    killers: [null, null],
    history: new Map(),
  };

  let ordered = orderMoves(rootMoves, state, ctx);
  let bestMove = ordered[0];
  let bestScore = 0;
  let completedDepth = 0;
  let rootScores = new Map();

  for (let depth = 1; depth <= maxDepth; depth += 1) {
    let alpha = -Infinity;
    let beta = Infinity;
    let localBest = null;
    let localScore = -Infinity;
    const scored = [];
    try {
      let rootFirst = true;
      for (const move of ordered) {
        const next = rules.applyUnchecked(state, move);
        let score;
        if (exactRoot) {
          score = -negamax(next, rules, depth - 1, -Infinity, Infinity, ctx, 1);
        } else if (rootFirst) {
          score = -negamax(next, rules, depth - 1, -beta, -alpha, ctx, 1);
          rootFirst = false;
        } else {
          score = -negamax(next, rules, depth - 1, -alpha - 1, -alpha, ctx, 1);
          if (score > alpha) score = -negamax(next, rules, depth - 1, -beta, -alpha, ctx, 1);
        }
        scored.push({ move, score });
        if (score > localScore) {
          localScore = score;
          localBest = move;
        }
        if (score > alpha) alpha = score;
      }
    } catch (error) {
      if (error instanceof Timeout) break;
      throw error;
    }
    if (localBest) {
      bestMove = localBest;
      bestScore = localScore;
      completedDepth = depth;
      rootScores = new Map(scored.map((item) => [rootMoveKey(item.move), item.score]));
      scored.sort((a, b) => b.score - a.score);
      ordered = scored.map((item) => item.move);
      // 局面已分胜负就不必再深搜
      if (Math.abs(localScore) > MATE - 1000) break;
      if (now() > deadline) break;
    }
  }

  if (config.randomness > 0) {
    const pool = ordered.slice(0, 3);
    if (pool.length > 1 && Math.random() < config.randomness) {
      bestMove = pool[Math.floor(Math.random() * pool.length)];
      bestScore = 0;
    }
  }

  return {
    move: bestMove,
    score: bestScore,
    depth: completedDepth,
    nodes: ctx.nodes,
    elapsed: Math.round(now() - start),
    rootScores,
  };
}

/** 给人类玩家的一步提示。 */
export function suggestMove(state, rules, timeMs = 700) {
  return chooseMove(state, rules, 'normal', { timeMs, depth: 5 });
}

export { MATE, TYPE_INDEX };
