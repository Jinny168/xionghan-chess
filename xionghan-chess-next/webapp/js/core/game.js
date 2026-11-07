/**
 * 对局流程（等价于 Python `core/game.py`）。
 *
 * 负责：开局摆子、落子、悔棋、计时、结果判定、棋谱记法、快照。
 */

import {
  cloneState, createState, forkState, isFinished, makePiece, opponent,
  stateFromDict, stateToDict,
} from './model.js';
import { getProfile, initialPieceSpecs, mergeOptions, pieceEnabled, RED_NAMES, BLACK_NAMES } from './profiles.js';
import { RulesEngine } from './rules.js';

export const MAX_SNAPSHOTS = 512;

const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

export class GameError extends Error {}

export const PIECE_NAMES = { red: RED_NAMES, black: BLACK_NAMES };

export function slotId(color, type, row, col) {
  return `${color}:${type}:${row}:${col}`;
}

export function buildSetup(profile, options, {
  firstMove = 'red', redSlots = null, blackSlots = null,
} = {}) {
  const available = { red: [], black: [] };
  for (const spec of profile.pieces) {
    if (!pieceEnabled(options, spec.type)) continue;
    available[spec.color].push(slotId(spec.color, spec.type, spec.row, spec.col));
  }
  const selected = {
    red: redSlots ? redSlots.slice() : available.red.slice(),
    black: blackSlots ? blackSlots.slice() : available.black.slice(),
  };
  for (const color of ['red', 'black']) {
    if (new Set(selected[color]).size !== selected[color].length) {
      throw new GameError(`${color} setup contains duplicate piece slots`);
    }
    const unknown = selected[color].filter((id) => !available[color].includes(id));
    if (unknown.length) throw new GameError(`${color} setup contains unavailable piece slots`);
    if (!selected[color].some((id) => id.startsWith(`${color}:king:`))) {
      throw new GameError(`${color} king must appear`);
    }
  }
  if (selected.red.length !== selected.black.length) {
    throw new GameError('red and black must field the same number of pieces');
  }
  const resolved = firstMove === 'random'
    ? (Math.random() < 0.5 ? 'red' : 'black')
    : firstMove;
  return { firstMove, resolvedFirstMove: resolved, redSlots: selected.red, blackSlots: selected.black };
}

export function setupInitialPieces(profile, setup) {
  const chosen = new Set([...setup.redSlots, ...setup.blackSlots]);
  return profile.pieces
    .filter((spec) => chosen.has(slotId(spec.color, spec.type, spec.row, spec.col)))
    .map((spec) => makePiece(spec.type, spec.color, spec.row, spec.col));
}

export class Game {
  constructor(profileOrId = 'desktop_complete', optionOverrides = null, {
    initialMinutes = 20, language = 'zh-CN', setup = null, state = null,
  } = {}) {
    this.language = language;
    this.profile = typeof profileOrId === 'string' ? getProfile(profileOrId) : profileOrId;
    this.options = mergeOptions(this.profile.options, optionOverrides);
    this.rules = new RulesEngine(this.profile, this.options);
    this.setup = setup && setup.resolvedFirstMove
      ? setup
      : buildSetup(this.profile, this.options, setup || {});
    this._snapshots = [];
    if (state) {
      this.state = state;
    } else {
      this.state = createState(this.profile.id, setupInitialPieces(this.profile, this.setup),
        this.setup.resolvedFirstMove);
      this.state.clocksMs = {
        red: initialMinutes * 60000,
        black: initialMinutes * 60000,
      };
    }
    this.state.turnStartedAt = now();
    this._recordPosition();
  }

  setInitialMinutes(minutes) {
    this.state.clocksMs = { red: minutes * 60000, black: minutes * 60000 };
  }

  get finished() {
    return isFinished(this.state);
  }

  get snapshots() {
    return this._snapshots;
  }

  move(move) {
    if (this.finished) throw new GameError('game-finished');
    if (this.state.paused) throw new GameError('game-paused');
    const elapsed = now() - this.state.turnStartedAt;
    this.tick();
    if (this.finished) throw new GameError('turn-timeout');
    if (!this.rules.isLegal(this.state, move)) throw new GameError('illegal-move');

    this._pushSnapshot();
    const moving = this.state.pieces.find(
      (p) => p.row === move.source.row && p.col === move.source.col,
    );
    if (!moving) throw new GameError('illegal-move');
    const before = new Map(this.state.pieces.map((p) => [p.id, p]));
    const next = this.rules.applyUnchecked(this.state, move);
    const afterIds = new Set(next.pieces.map((p) => p.id));
    const captured = [...before.values()].filter((p) => !afterIds.has(p.id));
    for (const piece of captured) next.captured[piece.color].push(piece);

    const record = {
      move: { source: { ...move.source }, target: { ...move.target }, promotion: move.promotion || null },
      color: moving.color,
      pieceType: moving.type,
      captured: captured.map((p) => ({ ...p })),
      notation: this.notation(moving, move, captured),
      timestamp: Date.now() / 1000,
      elapsedMs: Math.max(0, Math.round(elapsed)),
    };
    next.history.push(record);
    next.turnStartedAt = now();
    next.pendingDrawOffer = null;
    next.pendingUndoOffer = null;
    next.pendingRestartOffer = null;
    this.state = next;
    this._recordPosition();
    this._settleAfterMove(moving.color, move);
    return record;
  }

  undo(plies = 1) {
    if (plies < 1 || this._snapshots.length < plies) throw new GameError('no-undo');
    const snapshot = this._snapshots[this._snapshots.length - plies];
    this._snapshots.splice(this._snapshots.length - plies, plies);
    this.state = stateFromDict(snapshot);
    this.state.pendingDrawOffer = null;
    this.state.pendingUndoOffer = null;
    this.state.pendingRestartOffer = null;
    this.state.paused = false;
    this.state.pausedBy = null;
    this.state.turnStartedAt = now();
  }

  canUndo(count = 1) {
    return this._snapshots.length >= count;
  }

  setPaused(paused, color = null) {
    if (this.finished) throw new GameError('game-finished');
    if (paused === this.state.paused) return;
    if (paused) {
      this.tick();
      if (this.finished) return;
      this.state.paused = true;
      this.state.pausedBy = color;
    } else {
      this.state.paused = false;
      this.state.pausedBy = null;
      this.state.turnStartedAt = now();
    }
  }

  resign(color) {
    this.state.winner = opponent(color);
    this.state.resultReason = 'resignation';
  }

  offerDraw(color) {
    if (color !== this.state.turn) throw new GameError('draw-own-turn');
    this.state.pendingDrawOffer = color;
  }

  respondDraw(color, accept) {
    if (this.state.pendingDrawOffer === opponent(color)) {
      this.state.pendingDrawOffer = null;
      if (accept) {
        this.state.draw = true;
        this.state.resultReason = 'draw_agreement';
      }
      return;
    }
    this.state.pendingDrawOffer = null;
  }

  offerUndo(color) {
    if (!this.state.history.length) throw new GameError('no-undo-move');
    this.state.pendingUndoOffer = color;
  }

  respondUndo(color, accept) {
    this.state.pendingUndoOffer = null;
    if (accept) this.undo(this._snapshots.length >= 2 ? 2 : 1);
  }

  resurrectPawn(color, position) {
    if (this.state.paused) throw new GameError('game-paused');
    if (!this.options.pawn_resurrection || color !== this.state.turn) {
      throw new GameError('resurrect-not-allowed');
    }
    const homeRow = color === 'red' ? 8 : 4;
    if (position.row !== homeRow || position.col % 2 !== 0
      || this.state.pieces.some((p) => p.row === position.row && p.col === position.col)) {
      throw new GameError('invalid-resurrect-position');
    }
    const deadIndex = this.state.captured[color].findIndex((p) => p.type === 'pawn');
    const alive = this.state.pieces.filter((p) => p.type === 'pawn' && p.color === color).length;
    if (deadIndex < 0 || alive >= 7) throw new GameError('no-resurrect-pawn');
    this._pushSnapshot();
    this.state.captured[color].splice(deadIndex, 1);
    this.state.pieces.push(makePiece('pawn', color, position.row, position.col));
    delete this.state._grid;
    this.state.turn = opponent(color);
    this.state.turnStartedAt = now();
    this.state.pendingDrawOffer = null;
    this.state.pendingUndoOffer = null;
    this._recordPosition();
  }

  /** 返回本次 tick 是否导致超时。 */
  tick() {
    if (this.finished || this.state.paused) return false;
    const elapsed = now() - this.state.turnStartedAt;
    const left = this.state.clocksMs[this.state.turn];
    if (left <= 0) return false; // 0 表示不限时
    if (elapsed >= left) {
      this.state.clocksMs[this.state.turn] = 0;
      this.state.winner = opponent(this.state.turn);
      this.state.resultReason = 'timeout';
      return true;
    }
    this.state.clocksMs[this.state.turn] = left - elapsed;
    this.state.turnStartedAt = now();
    return false;
  }

  notation(piece, move, captured) {
    const names = piece.color === 'red' ? RED_NAMES : BLACK_NAMES;
    const name = names[piece.type] || piece.type;
    const action = captured.length ? (this.language === 'en' ? 'captures' : '吃') : (this.language === 'en' ? 'to' : '至');
    return `${name} ${move.source.row + 1},${move.source.col + 1} ${action} ${move.target.row + 1},${move.target.col + 1}`;
  }

  publicState() {
    const data = stateToDict(this.state);
    data.profile = {
      id: this.profile.id,
      title: this.profile.title,
      rows: this.profile.rows,
      cols: this.profile.cols,
      options: { ...this.options },
      archerStarPoints: this.rules.archerStarPoints.slice(),
    };
    data.check = this.finished ? false : this.rules.inCheck(this.state, this.state.turn);
    data.setup = this.setup;
    data.replay = this._snapshots.concat([stateToDict(this.state)]);
    data.replayBaseIndex = 0;
    data.replayComplete = true;
    return data;
  }

  _pushSnapshot() {
    this._snapshots.push(stateToDict(this.state));
    if (this._snapshots.length > MAX_SNAPSHOTS) {
      this._snapshots.splice(0, this._snapshots.length - MAX_SNAPSHOTS);
    }
  }

  _recordPosition() {
    const key = this.rules.positionKey(this.state);
    this.state.positionCounts[key] = (this.state.positionCounts[key] || 0) + 1;
  }

  _settleAfterMove(mover, move) {
    const enemy = opponent(mover);
    const enemyKing = this.state.pieces.find((p) => p.type === 'king' && p.color === enemy);
    const moved = this.state.pieces.find(
      (p) => p.row === move.target.row && p.col === move.target.col,
    );
    if (!enemyKing) {
      this.state.winner = mover;
      this.state.resultReason = 'king_captured';
    } else if (moved && moved.type === 'king' && this.options.invasion_victory
      && this.rules.enemyPalace(mover, moved)) {
      this.state.winner = mover;
      this.state.resultReason = 'palace_invasion';
    } else if (this.rules.checkmate(this.state, enemy)) {
      this.state.winner = mover;
      this.state.resultReason = 'checkmate';
    } else if (this.rules.stalemate(this.state, enemy)) {
      this.state.winner = mover;
      this.state.resultReason = 'stalemate';
    } else if (this.options.threefold_draw
      && Math.max(0, ...Object.values(this.state.positionCounts)) >= 3) {
      this.state.draw = true;
      this.state.resultReason = 'threefold_repetition';
    } else if (this.options.no_progress_draw_plies
      && this._noProgressPlies() >= this.options.no_progress_draw_plies) {
      this.state.draw = true;
      this.state.resultReason = 'no_progress';
    }
  }

  _noProgressPlies() {
    let count = 0;
    for (let i = this.state.history.length - 1; i >= 0; i -= 1) {
      const record = this.state.history[i];
      if (record.captured.length || record.pieceType === 'pawn') break;
      count += 1;
    }
    return count;
  }
}

/** 从棋谱文档恢复对局（用于读取 .xhgame 与残局训练）。 */
export function gameFromDocument(document, language = 'zh-CN') {
  const profile = getProfile(document.profileId);
  const options = mergeOptions(profile.options, document.options);
  const game = new Game(profile, options, { language, state: stateFromDict(document.state) });
  game.setup = document.setup || game.setup;
  game._snapshots = (document.snapshots || []).map((item) => ({ ...item }));
  return game;
}

/** 导出为 `.xhgame` 文档。 */
export function gameToDocument(game, savedAt = new Date().toISOString()) {
  const state = stateToDict(game.state);
  delete state.profile;
  delete state.check;
  delete state.replay;
  delete state.setup;
  return {
    formatVersion: 1,
    profileId: game.profile.id,
    options: { ...game.options },
    setup: game.setup,
    state,
    snapshots: game._snapshots.slice(),
    savedAt,
  };
}

export function isDrawish(state) {
  return state.draw || (!state.winner && state.history.length === 0);
}
