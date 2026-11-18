/**
 * 匈汉象棋 —— 数据模型（Python `core/model.py` 的等价实现）
 *
 * 与 Python 端保持完全一致的字段名与序列化格式，确保 `.xhgame` 棋谱
 * 可以在桌面端 / 网页端之间互通。
 */

export const COLORS = ['red', 'black'];

export const PIECE_TYPES = [
  'king', 'rook', 'horse', 'elephant', 'advisor', 'cannon', 'pawn',
  'guard', 'archer', 'thunder', 'armor', 'assassin', 'shield', 'patrol',
];

export const opponent = (color) => (color === 'red' ? 'black' : 'red');

export const pos = (row, col) => ({ row, col });

export const samePos = (a, b) => !!a && !!b && a.row === b.row && a.col === b.col;

export const posKey = (p) => `${p.row},${p.col}`;

let pieceSeq = 0;
export function nextPieceId() {
  pieceSeq = (pieceSeq + 1) % 0xffffff;
  const rand = Math.floor(Math.random() * 0xffff).toString(16).padStart(4, '0');
  return `${pieceSeq.toString(16).padStart(4, '0')}${rand}${Date.now().toString(16).slice(-4)}`;
}

export function makePiece(type, color, row, col, id = null) {
  return { id: id || nextPieceId(), type, color, row, col };
}

export function pieceAt(state, row, col) {
  const pieces = state.pieces;
  for (let i = 0; i < pieces.length; i += 1) {
    const p = pieces[i];
    if (p.row === row && p.col === col) return p;
  }
  return null;
}

export function moveKey(move) {
  const suffix = move.promotion ? `=${move.promotion}` : '';
  return `${move.source.row},${move.source.col}-${move.target.row},${move.target.col}${suffix}`;
}

export function moveToDict(move) {
  if (!move) return null;
  return {
    from: { row: move.source.row, col: move.source.col },
    to: { row: move.target.row, col: move.target.col },
    promotion: move.promotion || null,
  };
}

export function moveFromDict(data) {
  return {
    source: { row: data.from.row, col: data.from.col },
    target: { row: data.to.row, col: data.to.col },
    promotion: data.promotion || null,
  };
}

export function createState(profileId, pieces, turn = 'red') {
  return {
    profileId,
    pieces,
    turn,
    history: [],
    captured: { red: [], black: [] },
    winner: null,
    resultReason: null,
    draw: false,
    pendingDrawOffer: null,
    pendingUndoOffer: null,
    pendingRestartOffer: null,
    paused: false,
    pausedBy: null,
    clocksMs: { red: 20 * 60000, black: 20 * 60000 },
    turnStartedAt: 0,
    positionCounts: {},
  };
}

/** 轻量复制：供走子推演使用，片元对象按需替换，不深拷贝。 */
export function forkState(state) {
  return {
    profileId: state.profileId,
    pieces: state.pieces.slice(),
    turn: state.turn,
    history: state.history,
    captured: { red: state.captured.red.slice(), black: state.captured.black.slice() },
    winner: state.winner,
    resultReason: state.resultReason,
    draw: state.draw,
    pendingDrawOffer: state.pendingDrawOffer,
    pendingUndoOffer: state.pendingUndoOffer,
    pendingRestartOffer: state.pendingRestartOffer,
    paused: state.paused,
    pausedBy: state.pausedBy,
    clocksMs: state.clocksMs,
    turnStartedAt: state.turnStartedAt,
    positionCounts: state.positionCounts,
  };
}

/** 完整深拷贝：用于棋谱快照与悔棋。 */
export function cloneState(state) {
  return {
    profileId: state.profileId,
    pieces: state.pieces.map((p) => ({ ...p })),
    turn: state.turn,
    history: state.history.map(cloneRecord),
    captured: {
      red: state.captured.red.map((p) => ({ ...p })),
      black: state.captured.black.map((p) => ({ ...p })),
    },
    winner: state.winner,
    resultReason: state.resultReason,
    draw: state.draw,
    pendingDrawOffer: state.pendingDrawOffer,
    pendingUndoOffer: state.pendingUndoOffer,
    pendingRestartOffer: state.pendingRestartOffer,
    paused: state.paused,
    pausedBy: state.pausedBy,
    clocksMs: { ...state.clocksMs },
    turnStartedAt: state.turnStartedAt,
    positionCounts: { ...state.positionCounts },
  };
}

function cloneRecord(record) {
  return {
    move: {
      source: { ...record.move.source },
      target: { ...record.move.target },
      promotion: record.move.promotion || null,
    },
    color: record.color,
    pieceType: record.pieceType,
    captured: record.captured.map((p) => ({ ...p })),
    notation: record.notation,
    timestamp: record.timestamp,
    elapsedMs: record.elapsedMs,
  };
}

export function pieceToDict(p) {
  return { id: p.id, type: p.type, color: p.color, row: p.row, col: p.col };
}

export function pieceFromDict(d) {
  return {
    id: String(d.id),
    type: d.type,
    color: d.color,
    row: Number(d.row),
    col: Number(d.col),
  };
}

export function stateToDict(state) {
  return {
    profileId: state.profileId,
    turn: state.turn,
    pieces: state.pieces.map(pieceToDict),
    history: state.history.map((r) => ({
      move: {
        from: { row: r.move.source.row, col: r.move.source.col },
        to: { row: r.move.target.row, col: r.move.target.col },
        promotion: r.move.promotion || null,
      },
      color: r.color,
      pieceType: r.pieceType,
      captured: r.captured.map(pieceToDict),
      notation: r.notation,
      timestamp: r.timestamp,
      elapsedMs: r.elapsedMs,
    })),
    captured: {
      red: state.captured.red.map(pieceToDict),
      black: state.captured.black.map(pieceToDict),
    },
    winner: state.winner,
    resultReason: state.resultReason,
    draw: state.draw,
    pendingDrawOffer: state.pendingDrawOffer,
    pendingUndoOffer: state.pendingUndoOffer,
    pendingRestartOffer: state.pendingRestartOffer,
    paused: state.paused,
    pausedBy: state.pausedBy,
    clocksMs: { ...state.clocksMs },
    positionCounts: { ...state.positionCounts },
  };
}

export function stateFromDict(data) {
  const state = createState(
    data.profileId,
    (data.pieces || []).map(pieceFromDict),
    data.turn || 'red',
  );
  state.winner = data.winner || null;
  state.resultReason = data.resultReason || null;
  state.draw = Boolean(data.draw);
  state.pendingDrawOffer = data.pendingDrawOffer || null;
  state.pendingUndoOffer = data.pendingUndoOffer || null;
  state.pendingRestartOffer = data.pendingRestartOffer || null;
  state.paused = Boolean(data.paused);
  state.pausedBy = data.pausedBy || null;
  state.clocksMs = data.clocksMs
    ? { red: Number(data.clocksMs.red ?? 1200000), black: Number(data.clocksMs.black ?? 1200000) }
    : { red: 1200000, black: 1200000 };
  state.positionCounts = { ...(data.positionCounts || {}) };
  state.captured = {
    red: (data.captured?.red || []).map(pieceFromDict),
    black: (data.captured?.black || []).map(pieceFromDict),
  };
  state.history = (data.history || []).map((item) => ({
    move: {
      source: { row: item.move.from.row, col: item.move.from.col },
      target: { row: item.move.to.row, col: item.move.to.col },
      promotion: item.move.promotion || null,
    },
    color: item.color,
    pieceType: item.pieceType,
    captured: (item.captured || []).map(pieceFromDict),
    notation: item.notation,
    timestamp: Number(item.timestamp || 0),
    elapsedMs: Number(item.elapsedMs || 0),
  }));
  return state;
}

export function isFinished(state) {
  return state.winner !== null || state.draw;
}
