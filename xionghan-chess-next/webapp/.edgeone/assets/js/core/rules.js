/**
 * 走法判定（等价于 Python `core/rules.py`）。
 *
 * 设计原则：这里的每一个函数都逐行对应 Python 端实现，命名保持一致，
 * 便于用黄金用例做逐着法比对。任何性能优化都必须以「不改变判定结果」
 * 为前提，并由 tests/verify-rules.mjs 交叉验证。
 */

import { opponent, pieceAt, forkState, samePos, pos } from './model.js';
import { archerStarPoints, pieceEnabled, RULE_VERSION } from './profiles.js';

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

  /**
   * 兵「三连吃子」v3 —— 只结算落点所在的线。
   *
   * 逐字对齐 Android 黄金参考 offline.js::threeLineCaptures 的 11 条判据
   * （开关 / 兵种 / 位移 / 4 轴 / 两端外侧 / 窗口 3 格全有子 / 两己一敌 /
   * 至少一兵 / 移动兵在窗口 / 排除 KING / 按 id 去重），与 Python
   * rules.py::_three_line_removals 同源。
   *
   * ⚠️ 网页 `get()` 是 `state._grid` 惰性网格（O(1) 查表），不像 offline.js /
   * Python 那样线性扫描，所以这里**不做** Python/offline 的「外侧判据后移」
   * 性能重排：额外 2 次查表几乎无成本，照搬反而会改变 `_grid` 失效时机。
   * 全部判据是 AND 关系，顺序不影响语义。
   * 位移 ≤ 1 格的闸门由调用方（applyUnchecked）负责，对齐 `_three_line_mover`。
   */
  threeLineCaptures(state, color, landing) {
    if (!this.options.pawn_three_line_capture) return [];
    const found = new Map();
    for (const [dr, dc] of [[0, 1], [1, 0], [1, 1], [1, -1]]) {
      for (const off of [-2, -1, 0]) {
        if (this.get(state, pos(landing.row + (off - 1) * dr, landing.col + (off - 1) * dc))
          || this.get(state, pos(landing.row + (off + 3) * dr, landing.col + (off + 3) * dc))) continue;
        const group = [0, 1, 2].map((i) => this.get(
          state, pos(landing.row + (off + i) * dr, landing.col + (off + i) * dc),
        ));
        if (group.some((x) => !x)) continue;
        const allies = group.filter((x) => x.color === color);
        const enemies = group.filter((x) => x.color !== color);
        if (allies.length !== 2 || enemies.length !== 1 || !allies.some((x) => x.type === 'pawn')) continue;
        if (!allies.some((x) => x.row === landing.row && x.col === landing.col)) continue;
        if (enemies[0].type === 'king') continue;
        found.set(enemies[0].id, enemies[0]);
      }
    }
    return [...found.values()];
  }

  /**
   * 全色移除集合：before/after piece id 差集，与 offline.js::boardRemovals /
   * Python RulesEngine.board_removals 同源。capturedByMove 是它 narrowed to
   * the enemy 的变体，跨端比对一律用本方法（能看到己方被三连一起带走的子）。
   */
  boardRemovals(state, move) {
    if (!this.get(state, move.source)) return [];
    const next = this.applyUnchecked(state, move, false);
    const afterIds = new Set(next.pieces.map((p) => p.id));
    return state.pieces.filter((p) => !afterIds.has(p.id));
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

    // 三连吃子结算：顺序必须是「先改 moving 坐标，再结算」（对齐
    // offline.js::applyUnchecked 与 rules.py::_apply_move），否则窗口里找不到
    // 刚落位的兵。位移 ≤ 1 格闸门同源 `_three_line_mover`：快速行军 /
    // 敌阵冲锋的多格着法不结算旁吃。
    if (piece.type === 'pawn' && this.options.pawn_three_line_capture
      && Math.max(Math.abs(move.target.row - move.source.row),
        Math.abs(move.target.col - move.source.col)) <= 1) {
      const ids = new Set(this.threeLineCaptures(
        clone, piece.color, pos(move.target.row, move.target.col),
      ).map((x) => x.id));
      if (ids.size) {
        clone.pieces = clone.pieces.filter((x) => !ids.has(x.id));
        delete clone._grid; // threeLineCaptures 建过惰性网格，pieces 变了必须失效
      }
    }

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

  /**
   * 重复局面键，与 Python `rules.py::position_key` / Android `offline.js::positionKey`
   * **逐字节一致**。契约：
   *   `<turn>|<board>||pool:<pool>||opt:rs{RULE_VERSION}-p3l{0|1}-promo{0|1}-self{0|1}`
   * - `<board>`：每子 `color:type:row:col`，按 (color,type,row,col) **数值** tuple 排序、
   *   `;` join，**不含 id**。字符串排序会把 "10" 排在 "2" 前，故 row/col 必须数值比。
   * - `<pool>`：每枚阵亡子 `color:type`，字典序排序、`,` join；空池为空串；
   *   `captured` 缺失按空处理。
   * - `<opt>` 三位齐全，取自 options；`rs` 前缀引用生成脚本输出的 `RULE_VERSION`
   *   常量（禁止写死 `rs3-` 字面量，否则下次升位又漏同一处）。
   */
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
    const pool = [];
    for (const color of ['red', 'black']) {
      for (const piece of ((state.captured && state.captured[color]) || [])) {
        pool.push(`${color}:${piece.type}`);
      }
    }
    pool.sort();
    return `${state.turn}|${parts.join(';')}||pool:${pool.join(',')}`
      + `||opt:rs${RULE_VERSION}-`
      + `p3l${this.options.pawn_three_line_capture ? 1 : 0}`
      + `-promo${this.options.pawn_promotion ? 1 : 0}`
      + `-self${this.options.enforce_self_check ? 1 : 0}`;
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
      // 直走三格：默认可吃子；开 `horse_straight_three_move_only` 后是纯机动手段
      // （落点有子整着不合法）。对齐 rules.py::_horse `:555-563`。
      if (this.options.horse_straight_three_move_only && this.get(state, move.target) !== null) return false;
      return this._clear(state, move.source, move.target);
    }
    if (!((ar === 2 && ac === 1) || (ar === 1 && ac === 2))) return false;
    // 别马腿只管日字这一路；`horse_blocked_by_leg`（默认开）关掉后日字同国际象棋。
    // 对齐 rules.py::_horse `:564-570`；1.9.x 无条件别腿是分叉。
    if (!this.options.horse_blocked_by_leg) return true;
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
    // 阴山行本身不算敌境（对齐 rules.py::_elephant `:592-594`）：
    // 红 source.row < middle、黑 source.row > middle，`<= / >=` 是 1.9.x 分叉。
    const inEnemyTerritory = (piece.color === 'red' && move.source.row < middle)
      || (piece.color === 'black' && move.source.row > middle);
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
    // 阴山（中间行）不算进入敌境：红 source.row < middle、黑 > middle 才可横走。
    // `<= / >=` 是 1.9.x 分叉（对齐 rules.py::_pawn `:648`）。
    // 2.0.0 删掉了底线兵的「四向早返回」（1.9.x 死开关，已整体移除）：
    // 底线兵的「后退」由 `pawn_backward_at_base`（默认关）单独管。
    const crossed = piece.color === 'red' ? move.source.row < middle : move.source.row > middle;
    const enemyBase = move.source.row === (piece.color === 'red' ? 0 : this.profile.rows - 1);
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
    // 敌阵冲锋（对齐 rules.py::_pawn `:678-684`）：过阴山后沿直线任意格前进，
    // 不吃子、路径须全空。**只在能走通时返回 true**，走不通落到常规判定
    // （否则开启冲锋会连正前方一格吃子一起吞掉，连带 inCheck 漏判）。
    if (this.options.pawn_charge && dc === 0 && dr === forward * distance && distance >= 1) {
      if (crossed && this.get(state, move.target) === null) {
        let clear = true;
        for (let step = 1; step < distance; step += 1) {
          if (this.get(state, { row: move.source.row + forward * step, col: move.source.col })) {
            clear = false;
            break;
          }
        }
        if (clear) return true;
      }
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
    // 尉＝标准主教：斜向任意距离、路径必须无子、遇敌子即吃。
    // 1.9.x 的 `隔一子跳`（_jumpOverOne）是分叉，对齐 rules.py::_guard `:696-705`
    // 与 offline.js::validates 的 guard 分支。
    if (!this._diagonal(move)) return false;
    if (this._diagonalPathPinched(state, move)) return false;
    return this._clear(state, move.source, move.target);
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
    // 位移仍要求路径无子；**吃子无视阻挡**（射程/星点/夹逼三项不变）。
    // 对齐 rules.py::_archer `:729-734` / offline.js::validates 的 archer 分支；
    // 1.9.x 无条件检查路径会吞掉「隔子吃」。
    if (target === null) {
      for (let step = 1; step < distance; step += 1) {
        const p = {
          row: move.source.row + step * stepRow,
          col: move.source.col + step * stepCol,
        };
        if (this.get(state, p)) return false;
      }
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
    // 巡：**只沿横线**走偶数格，吃子仅限距离 2。竖线禁行是硬规则，
    // 判据只认「起点终点同行」，**不查 {5,7} 行白名单** —— 残局摆子会把它
    // 放在任意行，白名单会让残局里的巡凭空失效（对齐 rules.py::_patrol `:805`）。
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
    // 两王同一**直线**（同列或同行）且中间无子 → 照面，计入被将。
    // 同源：Python `rules.py::kings_facing`（docstring「两王同一直线（同列或同行）」）
    // 与 Android `offline.js:59::kingsFacing`（`||kings[0].row===kings[1].row`）。
    // 1.9.x 只认同列，会让双王同行时放行 Python 判非法的着法（走法分叉）。
    const kings = state.pieces.filter((p) => p.type === 'king');
    if (kings.length !== 2) return false;
    const sameLine = kings[0].col === kings[1].col || kings[0].row === kings[1].row;
    return sameLine && this._clear(state, kings[0], kings[1]);
  }
}
