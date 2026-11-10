/**
 * 走法判定（等价于 Python `core/rules.py`）。
 *
 * 设计原则：这里的每一个函数都逐行对应 Python 端实现，命名保持一致，
 * 便于用黄金用例做逐着法比对。任何性能优化都必须以「不改变判定结果」
 * 为前提，并由 tests/verify-rules.mjs 交叉验证。
 */

import { opponent, pieceAt, forkState, samePos } from './model.js';
import { archerStarPoints, pieceEnabled } from './profiles.js';

const DIRECTIONS = [
  [-1, 0], [1, 0], [0, -1], [0, 1],
];

export class RulesEngine {
  constructor(profile, options = null) {
    this.profile = profile;
    this.options = options || profile.options;
    this.enabledPieceTypes = new Set();
    for (const type of profile.enabledPieceTypes) {
      if (pieceEnabled(this.options, type)) this.enabledPieceTypes.add(type);
    }
    this._starCache = null;
    this._starKey = null;
    this._starSet = null;
  }

  inside(p) {
    return p.row >= 0 && p.row < this.profile.rows && p.col >= 0 && p.col < this.profile.cols;
  }

  get archerStarPoints() {
    const key = `${this.profile.id}|${this.options.archer_appear}`;
    if (this._starKey !== key) {
      this._starKey = key;
      this._starCache = archerStarPoints(this.profile, this.options);
      this._starSet = new Set(this._starCache.map((p) => `${p.row},${p.col}`));
    }
    return this._starCache;
  }

  get starPointSet() {
    if (!this._starSet) this.archerStarPoints;
    return this._starSet;
  }

  isStarPoint(p) {
    return this.starPointSet.has(`${p.row},${p.col}`);
  }

  palace(color, p) {
    let rows;
    let cols;
    if (this.profile.rows === 10) {
      rows = color === 'red' ? [7, 9] : [0, 2];
      cols = [3, 5];
    } else {
      rows = color === 'red' ? [9, 11] : [1, 3];
      cols = [5, 7];
    }
    return p.row >= rows[0] && p.row <= rows[1] && p.col >= cols[0] && p.col <= cols[1];
  }

  enemyPalace(color, p) {
    return this.palace(opponent(color), p);
  }

  get(state, p) {
    if (!this.inside(p)) return null;
    let grid = state._grid;
    if (grid === undefined) {
      grid = new Array(this.profile.rows * 32).fill(null);
      for (const piece of state.pieces) grid[piece.row * 32 + piece.col] = piece;
      state._grid = grid;
    }
    return grid[p.row * 32 + p.col] || null;
  }

  pseudoLegal(state, move) {
    if (!this.inside(move.source) || !this.inside(move.target)) return false;
    if (samePos(move.source, move.target)) return false;
    const piece = this.get(state, move.source);
    if (!piece) return false;
    if (piece.color !== state.turn) return false;
    if (!this.enabledPieceTypes.has(piece.type)) return false;
    const target = this.get(state, move.target);
    if (target && (target.color === piece.color || target.type === 'shield')) return false;

    if (move.promotion) {
      if (piece.type !== 'pawn' || !this.options.pawn_promotion) return false;
      if (move.promotion === 'pawn' || move.promotion === 'king') return false;
      if (!this.enabledPieceTypes.has(move.promotion)) return false;
      if (!state.captured[piece.color].some((p) => p.type === move.promotion)) return false;
    } else if (piece.type === 'pawn' && this.options.pawn_promotion) {
      const lastRow = piece.color === 'red' ? 0 : this.profile.rows - 1;
      if (move.target.row === lastRow) {
        const promotable = state.captured[piece.color].filter(
          (p) => p.type !== 'pawn' && p.type !== 'king' && this.enabledPieceTypes.has(p.type),
        );
        if (promotable.length) return false;
      }
    }

    if (target && this._protectedByEnemyShield(state, target)) return false;

    switch (piece.type) {
      case 'rook': return this._rook(state, piece, move);
      case 'horse': return this._horse(state, piece, move);
      case 'elephant': return this._elephant(state, piece, move);
      case 'advisor': return this._advisor(state, piece, move);
      case 'king': return this._king(state, piece, move);
      case 'cannon': return this._cannon(state, piece, move);
      case 'pawn': return this._pawn(state, piece, move);
      case 'guard': return this._guard(state, piece, move);
      case 'archer': return this._archer(state, piece, move);
      case 'thunder': return this._thunder(state, piece, move);
      case 'armor': return this._armor(state, piece, move);
      case 'assassin': return this._assassin(state, piece, move);
      case 'shield': return this._shield(state, piece, move);
      case 'patrol': return this._patrol(state, piece, move);
      default: return false;
    }
  }

  isLegal(state, move) {
    if (!this.pseudoLegal(state, move)) return false;
    if (!this.options.enforce_self_check) return true;
    const next = this.applyUnchecked(state, move, false);
    return !this.inCheck(next, state.turn);
  }

  legalMoves(state, color = null) {
    const side = color || state.turn;
    const probe = state.turn === side ? state : { ...forkState(state), turn: side };
    const result = [];
    for (const piece of probe.pieces) {
      if (piece.color !== side) continue;
      for (let row = 0; row < this.profile.rows; row += 1) {
        for (let col = 0; col < this.profile.cols; col += 1) {
          let promotions = [null];
          if (piece.type === 'pawn' && this.options.pawn_promotion) {
            const lastRow = side === 'red' ? 0 : this.profile.rows - 1;
            if (row === lastRow) {
              const available = new Set();
              for (const captured of probe.captured[side]) {
                if (captured.type !== 'pawn' && captured.type !== 'king'
                  && this.enabledPieceTypes.has(captured.type)) {
                  available.add(captured.type);
                }
              }
              if (available.size) {
                promotions = [...available].sort();
              }
            }
          }
          for (const promotion of promotions) {
            const move = {
              source: { row: piece.row, col: piece.col },
              target: { row, col },
              promotion,
            };
            if (this.isLegal(probe, move)) result.push(move);
          }
        }
      }
    }
    return result;
  }

  capturedByMove(state, move) {
    const moving = this.get(state, move.source);
    if (!moving) return [];
    const after = this.applyUnchecked(state, move, false);
    const afterIds = new Set(after.pieces.map((p) => p.id));
    return state.pieces.filter((p) => p.color !== moving.color && !afterIds.has(p.id));
  }

  applyUnchecked(state, move, switchTurn = true) {
    const clone = forkState(state);
    const pieceIndex = clone.pieces.findIndex(
      (p) => p.row === move.source.row && p.col === move.source.col,
    );
    if (pieceIndex < 0) return clone;
    const piece = clone.pieces[pieceIndex];

    const targetIndex = clone.pieces.findIndex(
      (p) => p.row === move.target.row && p.col === move.target.col,
    );
    const removed = [];
    if (targetIndex >= 0) {
      removed.push(clone.pieces[targetIndex]);
      clone.pieces.splice(targetIndex, 1);
    }
    const movedIndex = clone.pieces.indexOf(piece);
    clone.pieces[movedIndex] = { ...piece, row: move.target.row, col: move.target.col };

    if (piece.type === 'armor') {
      for (const captured of this._armorCaptures(clone, piece.color)) {
        const at = clone.pieces.findIndex((p) => p.id === captured.id);
        if (at >= 0) {
          clone.pieces.splice(at, 1);
          removed.push(captured);
        }
      }
      delete clone._grid;
    }

    if (piece.type === 'assassin') {
      const dr = move.target.row - move.source.row;
      const dc = move.target.col - move.source.col;
      const reverse = { row: move.source.row - dr, col: move.source.col - dc };
      const dragged = this.get(clone, reverse);
      const movedPiece = this.get(clone, move.target);
      if (dragged && dragged.color !== piece.color && dragged.type !== 'shield') {
        const draggedIndex = clone.pieces.findIndex((p) => p.id === dragged.id);
        if (draggedIndex >= 0) {
          clone.pieces.splice(draggedIndex, 1);
          removed.push(dragged);
        }
        if (movedPiece) {
          const movedAt = clone.pieces.findIndex((p) => p.id === movedPiece.id);
          if (movedAt >= 0) clone.pieces.splice(movedAt, 1);
        }
      }
    }

    if (move.promotion && piece.type === 'pawn' && this.options.pawn_promotion) {
      const promoted = this.get(clone, move.target);
      if (promoted) {
        const at = clone.pieces.findIndex((p) => p.id === promoted.id);
        if (at >= 0) clone.pieces[at] = { ...promoted, type: move.promotion };
        const deadIndex = clone.captured[piece.color].findIndex((p) => p.type === move.promotion);
        if (deadIndex >= 0) clone.captured[piece.color].splice(deadIndex, 1);
      }
    }

    delete clone._grid;
    if (switchTurn) clone.turn = opponent(clone.turn);
    return clone;
  }

  inCheck(state, color) {
    const king = state.pieces.find((p) => p.color === color && p.type === 'king');
    if (!king) return true;
    const probe = { ...forkState(state), turn: opponent(color) };
    for (const piece of probe.pieces) {
      if (piece.color !== opponent(color)) continue;
      const move = {
        source: { row: piece.row, col: piece.col },
        target: { row: king.row, col: king.col },
        promotion: null,
      };
      if (this.pseudoLegal(probe, move)) return true;
    }
    return this._kingsFacing(state);
  }

  checkmate(state, color) {
    return this.inCheck(state, color) && this.legalMoves(state, color).length === 0;
  }

  stalemate(state, color) {
    return !this.inCheck(state, color) && this.legalMoves(state, color).length === 0;
  }

  positionKey(state) {
    const parts = state.pieces
      .map((p) => [p.color, p.type, p.row, p.col])
      .sort((a, b) => {
        if (a[0] !== b[0]) return a[0] < b[0] ? -1 : 1;
        if (a[1] !== b[1]) return a[1] < b[1] ? -1 : 1;
        if (a[2] !== b[2]) return a[2] - b[2];
        return a[3] - b[3];
      })
      .map(([c, t, r, k]) => `${c}:${t}:${r}:${k}`);
    return `${state.turn}|${parts.join(';')}`;
  }

  _clear(state, source, target) {
    const dr = Math.sign(target.row - source.row);
    const dc = Math.sign(target.col - source.col);
    let row = source.row + dr;
    let col = source.col + dc;
    while (row !== target.row || col !== target.col) {
      if (this.get(state, { row, col })) return false;
      row += dr;
      col += dc;
    }
    return true;
  }

  _between(state, source, target) {
    const dr = Math.sign(target.row - source.row);
    const dc = Math.sign(target.col - source.col);
    let row = source.row + dr;
    let col = source.col + dc;
    let count = 0;
    while (row !== target.row || col !== target.col) {
      if (this.get(state, { row, col })) count += 1;
      row += dr;
      col += dc;
    }
    return count;
  }

  _line(move) {
    return move.source.row === move.target.row || move.source.col === move.target.col;
  }

  _diagonal(move) {
    return Math.abs(move.target.row - move.source.row)
      === Math.abs(move.target.col - move.source.col);
  }

  _rook(state, piece, move) {
    return this._line(move) && this._clear(state, move.source, move.target);
  }

  _horse(state, piece, move) {
    const dr = move.target.row - move.source.row;
    const dc = move.target.col - move.source.col;
    const ar = Math.abs(dr);
    const ac = Math.abs(dc);
    if (this.options.horse_straight_three && ((ar === 3 && ac === 0) || (ar === 0 && ac === 3))) {
      return this._clear(state, move.source, move.target);
    }
    if (!((ar === 2 && ac === 1) || (ar === 1 && ac === 2))) return false;
    const leg = {
      row: move.source.row + (ar === 2 ? Math.trunc(dr / 2) : 0),
      col: move.source.col + (ac === 2 ? Math.trunc(dc / 2) : 0),
    };
    return this.get(state, leg) === null;
  }

  _elephant(state, piece, move) {
    const dr = move.target.row - move.source.row;
    const dc = move.target.col - move.source.col;
    const middle = Math.floor(this.profile.rows / 2);
    const diagonal = Math.abs(dr) === 2 && Math.abs(dc) === 2;
    const orthogonal = (Math.abs(dr) === 2 && dc === 0) || (dr === 0 && Math.abs(dc) === 2);
    if (!diagonal && !orthogonal) return false;
    const eye = { row: move.source.row + Math.trunc(dr / 2), col: move.source.col + Math.trunc(dc / 2) };
    if (this.get(state, eye)) return false;
    if (diagonal) {
      if (!this.options.elephant_can_cross_river) {
        if (piece.color === 'red' && move.target.row < middle) return false;
        if (piece.color === 'black' && move.target.row > middle) return false;
      }
      if (this._diagonalPathPinched(state, move)) return false;
      return true;
    }
    const inEnemyTerritory = (piece.color === 'red' && move.source.row <= middle)
      || (piece.color === 'black' && move.source.row >= middle);
    return this.options.elephant_can_cross_river
      && this.options.elephant_gain_jump_two_enemy_territory
      && inEnemyTerritory;
  }

  _advisor(state, piece, move) {
    const dr = Math.abs(move.target.row - move.source.row);
    const dc = Math.abs(move.target.col - move.source.col);
    const diagonal = dr === 1 && dc === 1;
    const straight = dr + dc === 1;
    const sourceInPalace = this.palace(piece.color, move.source);
    const targetInPalace = this.palace(piece.color, move.target);
    if (sourceInPalace) {
      return diagonal
        && (targetInPalace || this.options.advisor_can_leave_palace)
        && !this._diagonalPathPinched(state, move);
    }
    if (!this.options.advisor_can_leave_palace && !targetInPalace) return false;
    if (diagonal && this._diagonalPathPinched(state, move)) return false;
    return diagonal || (straight && this.options.advisor_can_leave_palace
      && this.options.advisor_gain_straight_outside_palace);
  }

  _king(state, piece, move) {
    const dr = Math.abs(move.target.row - move.source.row);
    const dc = Math.abs(move.target.col - move.source.col);
    if (Math.max(dr, dc) !== 1) return false;
    const sourceInPalace = this.palace(piece.color, move.source);
    const targetInPalace = this.palace(piece.color, move.target);
    if (!this.options.king_can_leave_palace && !targetInPalace) return false;
    if (dr + dc === 1) return true;
    if (sourceInPalace && !this.options.king_diagonal_in_palace) return false;
    if (!sourceInPalace && this.options.king_lose_diagonal_outside_palace) return false;
    return !this._diagonalPathPinched(state, move);
  }

  _cannon(state, piece, move) {
    if (!this._line(move)) return false;
    const target = this.get(state, move.target);
    return this._between(state, move.source, move.target) === (target ? 1 : 0);
  }

  _pawn(state, piece, move) {
    const dr = move.target.row - move.source.row;
    const dc = move.target.col - move.source.col;
    const forward = piece.color === 'red' ? -1 : 1;
    const middle = Math.floor(this.profile.rows / 2);
    const crossed = piece.color === 'red' ? move.source.row <= middle : move.source.row >= middle;
    const enemyBase = move.source.row === (piece.color === 'red' ? 0 : this.profile.rows - 1);
    if (enemyBase && this.options.pawn_full_movement_at_base) return Math.abs(dr) + Math.abs(dc) === 1;
    const distance = Math.abs(dr);
    const distanceToEnemyTerritory = piece.color === 'red'
      ? move.source.row - middle + 1
      : middle - move.source.row + 1;
    if (this.options.pawn_fast_move_before_enemy_territory && dc === 0
      && dr === forward * distance && distance > 1 && distance <= distanceToEnemyTerritory) {
      if (this.get(state, move.target)) return false;
      for (let step = 1; step < distance; step += 1) {
        if (this.get(state, { row: move.source.row + forward * step, col: move.source.col })) {
          return false;
        }
      }
      return true;
    }
    if (dr === forward && dc === 0) return true;
    if (crossed && dr === 0 && Math.abs(dc) === 1) return true;
    return enemyBase && this.options.pawn_backward_at_base && dr === -forward && dc === 0;
  }

  _jumpOverOne(state, move, diagonal) {
    if (!(this._line(move) || (diagonal && this._diagonal(move)))) return false;
    return this.get(state, move.target) === null
      && this._between(state, move.source, move.target) === 1;
  }

  _guard(state, piece, move) {
    return this._jumpOverOne(state, move, true)
      && (!this._diagonal(move) || !this._diagonalPathPinched(state, move));
  }

  _archer(state, piece, move) {
    if (!this._diagonal(move)) return false;
    const dr = move.target.row - move.source.row;
    const dc = move.target.col - move.source.col;
    const distance = Math.abs(dr);
    const stepRow = dr > 0 ? 1 : -1;
    const stepCol = dc > 0 ? 1 : -1;
    const target = this.get(state, move.target);

    if (this.options.archer_enhanced_mode) {
      if (distance > 3) return false;
      if (target && !this.isStarPoint(move.source)) return false;
    } else {
      const starDistance = this._nearestArcherStarDistance(move.source, stepRow, stepCol);
      if (starDistance === 0 || distance > starDistance) return false;
    }

    if (this._diagonalPathPinched(state, move)) return false;
    for (let step = 1; step < distance; step += 1) {
      const p = {
        row: move.source.row + step * stepRow,
        col: move.source.col + step * stepCol,
      };
      if (this.get(state, p)) return false;
    }
    return true;
  }

  _nearestArcherStarDistance(source, stepRow, stepCol) {
    const limit = Math.max(this.profile.rows, this.profile.cols);
    for (let distance = 1; distance < limit; distance += 1) {
      const p = { row: source.row + distance * stepRow, col: source.col + distance * stepCol };
      if (!this.inside(p)) return 0;
      if (this.isStarPoint(p)) return distance;
    }
    return 0;
  }

  _diagonalPinched(state, position, stepRow, stepCol) {
    const sideA = { row: position.row, col: position.col + stepCol };
    const sideB = { row: position.row + stepRow, col: position.col };
    if (!this.inside(sideA) || !this.inside(sideB)) return false;
    return this.get(state, sideA) !== null && this.get(state, sideB) !== null;
  }

  _diagonalPathPinched(state, move) {
    if (!this._diagonal(move)) return false;
    const stepRow = move.target.row > move.source.row ? 1 : -1;
    const stepCol = move.target.col > move.source.col ? 1 : -1;
    const distance = Math.abs(move.target.row - move.source.row);
    for (let step = 0; step < distance; step += 1) {
      const p = {
        row: move.source.row + step * stepRow,
        col: move.source.col + step * stepCol,
      };
      if (this._diagonalPinched(state, p, stepRow, stepCol)) return true;
    }
    return false;
  }

  _thunder(state, piece, move) {
    if (!(this._line(move) || this._diagonal(move))) return false;
    const target = this.get(state, move.target);
    if (target) {
      return Math.max(
        Math.abs(move.target.row - move.source.row),
        Math.abs(move.target.col - move.source.col),
      ) === 1
        && this._isolated(state, target)
        && (!this._diagonal(move) || !this._diagonalPathPinched(state, move));
    }
    return this._clear(state, move.source, move.target)
      && (!this._diagonal(move) || !this._diagonalPathPinched(state, move));
  }

  _armor(state, piece, move) {
    return this.get(state, move.target) === null && this._rook(state, piece, move);
  }

  _assassin(state, piece, move) {
    return this.get(state, move.target) === null && this._rook(state, piece, move);
  }

  _shield(state, piece, move) {
    return this._jumpOverOne(state, move, false);
  }

  _patrol(state, piece, move) {
    if (move.source.row !== 5 && move.source.row !== 7) return false;
    if (move.target.row !== move.source.row) return false;
    const distance = Math.abs(move.target.col - move.source.col);
    if (distance === 0 || distance % 2 !== 0) return false;
    if (!this._clear(state, move.source, move.target)) return false;
    return this.get(state, move.target) === null || distance === 2;
  }

  _isolated(state, target) {
    for (const [dr, dc] of DIRECTIONS) {
      const other = this.get(state, { row: target.row + dr, col: target.col + dc });
      if (other && other.color === target.color) return false;
    }
    return true;
  }

  _protectedByEnemyShield(state, target) {
    return state.pieces.some((p) => p.type === 'shield' && p.color === target.color
      && Math.max(Math.abs(p.row - target.row), Math.abs(p.col - target.col)) === 1);
  }

  _armorCaptures(state, color) {
    const captures = new Map();
    const directions = [[0, 1], [1, 0], [1, 1], [1, -1]];
    for (let row = 0; row < this.profile.rows; row += 1) {
      for (let col = 0; col < this.profile.cols; col += 1) {
        for (const [dr, dc] of directions) {
          const group = [0, 1, 2].map((i) => this.get(state, { row: row + i * dr, col: col + i * dc }));
          if (group.some((p) => !p)) continue;
          const allies = group.filter((p) => p.color === color);
          const enemies = group.filter((p) => p.color !== color);
          const hasArmor = allies.some((p) => p.type === 'armor');
          if (allies.length !== 2 || enemies.length !== 1 || !hasArmor) continue;
          if (allies.some((p) => p.type === 'shield')) continue;
          if (allies.some((p) => this._adjacentEnemyShield(state, p))) continue;
          if (enemies[0].type !== 'shield') captures.set(enemies[0].id, enemies[0]);
        }
      }
    }
    return [...captures.values()];
  }

  _adjacentEnemyShield(state, piece) {
    return state.pieces.some((p) => p.type === 'shield' && p.color !== piece.color
      && Math.max(Math.abs(p.row - piece.row), Math.abs(p.col - piece.col)) === 1);
  }

  _kingsFacing(state) {
    const kings = state.pieces.filter((p) => p.type === 'king');
    return kings.length === 2 && kings[0].col === kings[1].col
      && this._clear(state, kings[0], kings[1]);
  }
}
