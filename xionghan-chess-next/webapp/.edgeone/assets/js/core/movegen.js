/**
 * 快速着法生成。
 *
 * `rules.legalMoves` 是逐格枚举的「参考实现」，正确但慢；搜索需要按棋子
 * 攻击形状直接生成候选落点。两者必须给出完全一致的结果，由
 * tests/verify-movegen.mjs 用同一批黄金用例交叉验证。
 *
 * 约定：这里生成的是「候选着法」，是否合法仍交给 RulesEngine.isLegal 判定，
 * 因此不会出现第二套规则语义。
 */

const ORTHO = [[-1, 0], [1, 0], [0, -1], [0, 1]];
const DIAG = [[-1, -1], [-1, 1], [1, -1], [1, 1]];
const ALL8 = ORTHO.concat(DIAG);

const HORSE_STEPS = [
  [-2, -1], [-2, 1], [-1, -2], [-1, 2], [1, -2], [1, 2], [2, -1], [2, 1],
];

export function generateCandidates(state, rules, piece, capturesOnly = false) {
  const out = [];
  const { rows, cols } = rules.profile;
  const options = rules.options;
  const at = (row, col) => {
    if (row < 0 || row >= rows || col < 0 || col >= cols) return undefined;
    return rules.get(state, { row, col });
  };
  const push = (row, col) => {
    if (row < 0 || row >= rows || col < 0 || col >= cols) return false;
    if (capturesOnly && !at(row, col)) return false;
    out.push({ row, col });
    return true;
  };
  const walk = (dirs, maxStep = 99) => {
    for (const [dr, dc] of dirs) {
      for (let step = 1; step <= maxStep; step += 1) {
        const row = piece.row + dr * step;
        const col = piece.col + dc * step;
        if (row < 0 || row >= rows || col < 0 || col >= cols) break;
        const occupant = at(row, col);
        if (!capturesOnly || occupant) out.push({ row, col });
        if (occupant) break;
      }
    }
  };
  // 隔一子跳跃：越过恰好一枚棋子后，其后所有空点均为可达落点。
  const jumpWalk = (dirs) => {
    for (const [dr, dc] of dirs) {
      let screen = false;
      for (let step = 1; step < Math.max(rows, cols); step += 1) {
        const row = piece.row + dr * step;
        const col = piece.col + dc * step;
        if (row < 0 || row >= rows || col < 0 || col >= cols) break;
        const occupant = at(row, col);
        if (!occupant) {
          if (screen && !capturesOnly) out.push({ row, col });
        } else if (screen) {
          if (capturesOnly) out.push({ row, col });
          break;
        } else {
          screen = true;
        }
      }
    }
  };

  switch (piece.type) {
    case 'rook':
      walk(ORTHO);
      break;
    case 'cannon':
      for (const [dr, dc] of ORTHO) {
        let screen = false;
        for (let step = 1; step < Math.max(rows, cols); step += 1) {
          const row = piece.row + dr * step;
          const col = piece.col + dc * step;
          if (row < 0 || row >= rows || col < 0 || col >= cols) break;
          const occupant = at(row, col);
          if (!screen) {
            if (!capturesOnly || occupant) out.push({ row, col });
            if (occupant) screen = true;
          } else if (occupant) {
            out.push({ row, col });
            break;
          }
        }
      }
      break;
    case 'horse': {
      for (const [dr, dc] of HORSE_STEPS) push(piece.row + dr, piece.col + dc);
      if (options.horse_straight_three) {
        for (const [dr, dc] of ORTHO) push(piece.row + dr * 3, piece.col + dc * 3);
      }
      break;
    }
    case 'elephant': {
      for (const [dr, dc] of [[-2, -2], [-2, 2], [2, -2], [2, 2]]) {
        push(piece.row + dr, piece.col + dc);
      }
      for (const [dr, dc] of [[-2, 0], [2, 0], [0, -2], [0, 2]]) {
        push(piece.row + dr, piece.col + dc);
      }
      break;
    }
    case 'advisor':
      // 出宫后可直走，故八方向全部纳入候选，由 pseudoLegal 做最终裁决
      for (const [dr, dc] of ALL8) push(piece.row + dr, piece.col + dc);
      break;
    case 'king':
      for (const [dr, dc] of ALL8) push(piece.row + dr, piece.col + dc);
      break;
    case 'pawn': {
      const forward = piece.color === 'red' ? -1 : 1;
      const middle = Math.floor(rows / 2);
      // 阴山（中间行）不算敌境：红 row < middle、黑 row > middle（rules.py::_pawn `:648`）。
      const crossed = piece.color === 'red' ? piece.row < middle : piece.row > middle;
      const enemyBase = piece.row === (piece.color === 'red' ? 0 : rows - 1);
      // 候选是**超集**：快速行军 / 敌阵冲锋都是沿 forward 的直线长距离走，
      // 统一把 1..max(rows,cols) 的直线落点全列出，由 pseudoLegal/isLegal 逐条裁决。
      // 多列无害（isLegal 会剔除），漏列才会让 legalMovesFast 少于参考实现。
      for (let step = 1; step < Math.max(rows, cols); step += 1) {
        if (!push(piece.row + forward * step, piece.col)) break;
      }
      if (crossed) {
        push(piece.row, piece.col - 1);
        push(piece.row, piece.col + 1);
      }
      if (enemyBase && options.pawn_backward_at_base) push(piece.row - forward, piece.col);
      break;
    }
    case 'guard':
      // 尉＝标准主教：斜向任意距离、路径无子（rules.js::_guard 同源）。
      // 1.9.x 的 `jumpWalk`（隔一子跳）会漏掉斜线多格落点，让
      // legalMovesFast 少于参考实现。
      walk(DIAG);
      break;
    case 'archer': {
      let limit;
      if (options.archer_enhanced_mode) {
        limit = 3;
      } else {
        limit = 0;
        for (const [dr, dc] of DIAG) {
          for (let step = 1; step < Math.max(rows, cols); step += 1) {
            const p = { row: piece.row + dr * step, col: piece.col + dc * step };
            if (p.row < 0 || p.row >= rows || p.col < 0 || p.col >= cols) break;
            if (rules.isStarPoint(p)) {
              limit = Math.max(limit, step);
              break;
            }
          }
        }
      }
      for (const [dr, dc] of DIAG) {
        for (let step = 1; step <= limit; step += 1) push(piece.row + dr * step, piece.col + dc * step);
      }
      break;
    }
    case 'thunder':
      walk(ALL8);
      break;
    case 'armor':
      walk(ORTHO);
      break;
    case 'assassin':
      walk(ORTHO);
      break;
    case 'shield':
      jumpWalk(ORTHO);
      break;
    case 'patrol':
      for (let step = 2; step < cols; step += 2) {
        push(piece.row, piece.col - step);
        push(piece.row, piece.col + step);
      }
      break;
    default:
      break;
  }
  return out;
}

/** 某方所有「候选着法」（已按棋子筛选，未做将军自检）。 */
export function pseudoMovesFrom(state, rules, color = state.turn) {
  const moves = [];
  const lastRow = { red: 0, black: rules.profile.rows - 1 };
  for (const piece of state.pieces) {
    if (piece.color !== color) continue;
    if (!rules.enabledPieceTypes.has(piece.type)) continue;
    const targets = generateCandidates(state, rules, piece);
    const promotionReady = piece.type === 'pawn' && rules.options.pawn_promotion;
    const available = promotionReady ? promotionsFor(state, rules, piece.color) : [];
    for (const target of targets) {
      const source = { row: piece.row, col: piece.col };
      const variants = (promotionReady && target.row === lastRow[piece.color] && available.length)
        ? available.map((promotion) => ({ source, target, promotion }))
        : [{ source, target, promotion: null }];
      for (const move of variants) {
        // 静态搜索也必须是合法着法：否则炮会「无架吃子」，引擎会虚算丢子
        if (rules.pseudoLegal(state, move)) moves.push(move);
      }
    }
  }
  return moves;
}

function promotionsFor(state, rules, color) {
  const available = new Set();
  for (const captured of state.captured[color]) {
    if (captured.type !== 'pawn' && captured.type !== 'king'
      && rules.enabledPieceTypes.has(captured.type)) available.add(captured.type);
  }
  return [...available].sort();
}

/** 过滤掉自检违规后的完整合法着法（快速路径）。 */
export function legalMovesFast(state, rules, color = state.turn) {
  const result = [];
  const side = color;
  const probe = state.turn === side ? state : { ...state, turn: side };
  const lastRow = side === 'red' ? 0 : rules.profile.rows - 1;
  for (const piece of probe.pieces) {
    if (piece.color !== side) continue;
    if (!rules.enabledPieceTypes.has(piece.type)) continue;
    const targets = generateCandidates(probe, rules, piece);
    const promotionReady = piece.type === 'pawn' && rules.options.pawn_promotion;
    const available = promotionReady ? promotionsFor(probe, rules, side) : [];
    for (const target of targets) {
      const source = { row: piece.row, col: piece.col };
      if (promotionReady && target.row === lastRow && available.length) {
        for (const promotion of available) {
          const move = { source, target, promotion };
          if (rules.isLegal(probe, move)) result.push(move);
        }
      } else {
        const move = { source, target, promotion: null };
        if (rules.isLegal(probe, move)) result.push(move);
      }
    }
  }
  return result;
}


function findOccupant(state, row, col) {
  for (const p of state.pieces) if (p.row === row && p.col === col) return p;
  return null;
}

/** 仅吃子着法，供静态搜索使用。 */
export function pseudoCaptures(state, rules, color = state.turn) {
  const moves = [];
  const lastRow = { red: 0, black: rules.profile.rows - 1 };
  for (const piece of state.pieces) {
    if (piece.color !== color) continue;
    if (!rules.enabledPieceTypes.has(piece.type)) continue;
    if (piece.type === 'armor' || piece.type === 'assassin' || piece.type === 'shield') continue;
    const targets = generateCandidates(state, rules, piece, true).filter((target) => {
      const occupant = findOccupant(state, target.row, target.col);
      return occupant && occupant.color !== piece.color;
    });
    if (!targets.length) continue;
    const promotionReady = piece.type === 'pawn' && rules.options.pawn_promotion;
    const available = promotionReady ? promotionsFor(state, rules, color) : [];
    for (const target of targets) {
      const source = { row: piece.row, col: piece.col };
      const variants = (promotionReady && target.row === lastRow[piece.color] && available.length)
        ? available.map((promotion) => ({ source, target, promotion }))
        : [{ source, target, promotion: null }];
      for (const move of variants) {
        // 静态搜索也必须是合法着法：否则炮会「无架吃子」，引擎会虚算丢子
        if (rules.pseudoLegal(state, move)) moves.push(move);
      }
    }
  }
  return moves;
}
