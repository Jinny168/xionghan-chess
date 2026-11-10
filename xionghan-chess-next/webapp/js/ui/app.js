/**
 * 应用主控。
 *
 * 负责：对局生命周期、交互、AI 调度、复盘、棋子图谱、设置持久化。
 * 规则与 AI 都在 core/ 下，这里只做编排与呈现。
 */

import { Game, gameFromDocument, gameToDocument, GameError, slotId } from '../core/game.js';
import {
  getProfile, mergeOptions, PROFILES, PROFILE_ORDER, RED_NAMES, BLACK_NAMES, pieceEnabled,
} from '../core/profiles.js';
import { makePiece, stateFromDict, stateToDict, createState } from '../core/model.js';
import { RulesEngine } from '../core/rules.js';
import { suggestMove, evaluate, DIFFICULTIES } from '../core/ai.js';
import { PUZZLES } from '../data/puzzles.js';
import * as net from '../net.js';
import * as cloud from './cloud.js';
import { BoardRenderer } from './board.js';
import * as sound from './sound.js';
import { t, setLanguage, getLanguage, applyI18n } from '../i18n.js';

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

const PREFS_KEY = 'xh-web-prefs-v1';
const SESSION_KEY = 'xh-web-session-v1';

const DEFAULT_PREFS = {
  theme: 'classic',
  pieceStyle: 'traditional',
  language: 'zh-CN',
  animation: true,
  legal: true,
  captureHint: true,
  sound: true,
  mode: 'ai',
  profileId: 'desktop_complete',
  difficulty: 'normal',
  side: 'red',
  firstMove: 'red',
  minutes: 20,
  options: {},
  appear: {},
  volume: 0.55,
  music: false,
  musicVolume: 0.35,
  background: '',
  sideHidden: false,
  customPuzzles: [],
};

const RULE_LABELS = {
  king_can_leave_palace: '汉/汗可出九宫',
  king_diagonal_in_palace: '九宫内可斜走',
  king_lose_diagonal_outside_palace: '出宫后失去斜走',
  invasion_victory: '入敌宫即胜',
  advisor_can_leave_palace: '仕/士可出宫',
  advisor_gain_straight_outside_palace: '出宫后可直走',
  elephant_can_cross_river: '相/象可过长城',
  elephant_gain_jump_two_enemy_territory: '入境后可横竖两格',
  horse_straight_three: '马可直走三格',
  archer_enhanced_mode: '射强化（脱离星轨）',
  pawn_fast_move_before_enemy_territory: '兵卒快速行军',
  pawn_backward_at_base: '到底线可后退',
  pawn_full_movement_at_base: '到底线四向移动',
  pawn_resurrection: '兵卒复活',
  pawn_promotion: '兵卒升变',
  enforce_self_check: '禁止送将',
  threefold_draw: '三次重复和棋',
};

const PIECE_INFO = {
  king: {
    name: '汉 / 汗',
    desc: '主帅。默认可以走出九宫，九宫内可斜走；走出九宫后失去斜走能力。攻入对方九宫可直接取胜。',
    en: 'The king. May leave the palace and step diagonally inside it; diagonal power is lost outside. Entering the enemy palace wins.',
  },
  rook: { name: '车', desc: '横竖直行，路径不可有子。', en: 'Moves any distance orthogonally; the path must be clear.' },
  horse: { name: '马', desc: '走日字，受蹩马腿限制；开启「直走三格」后可沿直线走三格。', en: 'Knight move with a blocking leg; an option adds a straight three-square leap.' },
  elephant: { name: '相 / 象', desc: '斜走两格，受象眼与夹逼限制；可过长城，进入敌境后还能横竖走两格。', en: 'Two-square diagonal, blocked by the eye and by pinches; may cross the Wall and gain orthogonal jumps in enemy territory.' },
  advisor: { name: '仕 / 士', desc: '九宫内斜走一格；可出宫，出宫后还能直走一格。', en: 'One diagonal step in the palace; may leave it and then also step orthogonally.' },
  cannon: { name: '炮', desc: '直线移动，吃子时必须隔且仅隔一子。', en: 'Slides orthogonally; captures by jumping exactly one screen.' },
  pawn: { name: '兵 / 卒', desc: '向前推进，进入敌境后可横走；过境前可以快速行军，到底线可后退、升变或复活。', en: 'Advances; steps sideways after crossing, may march several squares before crossing, and can retreat, promote or revive at the far rank.' },
  guard: { name: '尉 / 卫', desc: '沿直线或斜线隔一子跳跃，落点必须为空。', en: 'Leaps over exactly one piece along a line or diagonal, landing on an empty square.' },
  archer: { name: '射 / 䠶', desc: '沿对角星轨行走，路径须畅通且逐段通过夹逼检查；强化后可脱离星轨，最远三格。', en: 'Travels the diagonal star lattice, one pinch-check per step; the enhanced mode frees it, up to three squares.' },
  thunder: { name: '檑 / 礌', desc: '八方向直行；吃子时必须贴身在落单敌子旁，形成近身攻击。', en: 'Slides in eight directions; captures only an adjacent, isolated enemy.' },
  armor: { name: '甲 / 胄', desc: '横竖直行且只能走到空位；三子连成一线且含甲时，可夹杀其中敌子。', en: 'Slides orthogonally to empty squares; three in a line with an armor can crush the enemy inside.' },
  assassin: { name: '刺 / 伺', desc: '横竖直行至空位，并与反方向的敌子同归于尽。', en: 'Slides orthogonally to an empty square and trades itself for the enemy directly behind.' },
  shield: { name: '楯 / 碷', desc: '沿直线隔一子跳跃，自身不可被吃，并庇护相邻的己方棋子。', en: 'Leaps over one piece orthogonally, cannot be captured, and shields adjacent allies.' },
  patrol: { name: '巡 / 廵', desc: '只能在长城两侧的巡界线上横移偶数格，距离为二时可吃子。', en: 'Patrols the two boundary lines, moving an even number of squares; captures only at distance two.' },
};

const app = {
  game: null,
  prefs: { ...DEFAULT_PREFS },
  mode: 'ai',
  humanColor: 'red',
  difficulty: 'normal',
  minutes: 20,
  unlimited: false,
  selected: null,
  legal: [],
  flipped: false,
  thinking: false,
  anim: null,
  raf: 0,
  replay: { open: false, index: 0, states: [], timer: null },
  pendingPromotion: null,
  requestId: 0,
  worker: null,
  clockTimer: 0,
  lastMove: null,
  atlasType: 'rook',
  started: false,
  resurrecting: false,
  resurrectTargets: [],
  statsRecorded: false,
  puzzle: null,
  analysis: null,
  analysisId: 0,
  online: null,
};

const SOLVED_KEY = 'xh-web-puzzle-solved';

let board;
let replayBoard;
let atlasBoard;

/* ---------------------------------------------------------------- 初始化 */

function loadPrefs() {
  try {
    const stored = JSON.parse(localStorage.getItem(PREFS_KEY) || '{}');
    app.prefs = { ...DEFAULT_PREFS, ...stored };
    app.prefs.options = { ...(stored.options || {}) };
    app.prefs.appear = { ...(stored.appear || {}) };
  } catch {
    app.prefs = { ...DEFAULT_PREFS };
  }
}

function savePrefs() {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(app.prefs));
  } catch {
    /* 隐私模式下忽略 */
  }
}

function boot() {
  loadPrefs();
  setLanguage(app.prefs.language || 'zh-CN');

  board = new BoardRenderer($('#board'));
  replayBoard = new BoardRenderer($('#replayCanvas'));
  atlasBoard = new BoardRenderer($('#atlasCanvas'));

  applyBackground();
  applySideHidden();
  buildProfileCards();
  buildAppearGrid();
  buildThemeSwatches();
  buildRuleList();
  buildAtlasPieces();
  bindGlobal();
  bindDialogs();
  bindBoard();
  initWorker();

  app.mode = app.prefs.mode;
  app.humanColor = app.prefs.side;
  app.difficulty = app.prefs.difficulty;
  app.minutes = app.prefs.minutes;

  const restored = restoreSession();
  if (!restored) startGame({ silent: true });

  resizeAll();
  if (window.ResizeObserver) {
    new ResizeObserver(() => resizeAll()).observe($('#boardHolder'));
  }
  window.addEventListener('resize', resizeAll);

  app.clockTimer = setInterval(tickClock, 240);

  document.body.addEventListener('pointerdown', () => sound.unlock(), { once: true });
  document.body.classList.add('ready');
  app.started = true;

  if (!localStorage.getItem('xh-web-visited')) {
    localStorage.setItem('xh-web-visited', '1');
    setTimeout(() => toast(getLanguage() === 'en'
      ? 'Tap a piece, then tap a square to move.'
      : '点选棋子，再点落点即可落子'), 900);
  }

  if (!globalThis.__xhBundled && 'serviceWorker' in navigator && location.protocol.startsWith('http')) {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  }
}

/* ---------------------------------------------------------------- 对局 */

function startGame({ silent = false } = {}) {
  const profile = getProfile(app.prefs.profileId);
  const options = mergeOptions(profile.options, app.prefs.options);
  app.mode = app.prefs.mode;
  app.humanColor = app.prefs.side;
  app.difficulty = app.prefs.difficulty;
  app.minutes = Number(app.prefs.minutes) || 0;
  app.unlimited = app.minutes === 0;
  app.flipped = app.mode === 'ai' && app.humanColor === 'black';

  const slots = appearanceSlots(profile, options);
  const setup = {
    firstMove: app.prefs.firstMove,
    redSlots: slots ? slots.redSlots : null,
    blackSlots: slots ? slots.blackSlots : null,
  };
  app.game = new Game(profile, options, {
    initialMinutes: app.minutes || 600,
    language: getLanguage(),
    setup,
  });
  if (app.unlimited) app.game.state.clocksMs = { red: 0, black: 0 };
  app.puzzle = null;
  app.analysis = null;
  stopPolling();
  app.online = null;
  clearSelection();
  app.resurrecting = false;
  app.resurrectTargets = [];
  app.statsRecorded = false;
  app.lastMove = null;
  app.anim = null;
  $('#pauseMask').hidden = true;
  $('#resurrectPill').hidden = true;
  closeReplay();
  resizeAll();
  saveSession();
  if (!silent) hideDialog('dlgNew');
  maybeAI();
}

function isHumanTurn() {
  if (!app.game) return false;
  const turn = app.game.state.turn;
  if (app.mode === 'local') return true;
  return turn === app.humanColor;
}

function selectPiece(piece) {
  app.selected = { row: piece.row, col: piece.col, type: piece.type, color: piece.color };
  app.legal = app.game.rules
    .legalMoves(app.game.state)
    .filter((m) => m.source.row === piece.row && m.source.col === piece.col);
  sound.play('select');
  render();
}

function clearSelection() {
  app.selected = null;
  app.legal = [];
}

function handleSquare(point) {
  if (!app.game || app.replay.open) return;
  const state = app.game.state;
  if (isOver(state) || state.paused || app.thinking) return;
  if (!isHumanTurn()) return;

  if (app.resurrecting) {
    const hit = app.resurrectTargets.find((p) => p.row === point.row && p.col === point.col);
    if (!hit) return;
    try {
      app.game.resurrectPawn(app.game.state.turn, hit);
      sound.play('move');
      exitResurrect();
      clearSelection();
      render();
      saveSession();
      toast(t('action.resurrect'));
      setTimeout(maybeAI, 160);
    } catch {
      toast(t('toast.illegal'));
    }
    return;
  }

  const piece = state.pieces.find((p) => p.row === point.row && p.col === point.col);

  if (app.selected) {
    const candidates = app.legal.filter(
      (m) => m.target.row === point.row && m.target.col === point.col,
    );
    if (candidates.length === 1) {
      commitMove(candidates[0]);
      return;
    }
    if (candidates.length > 1) {
      askPromotion(candidates);
      return;
    }
  }

  if (piece && piece.color === state.turn
    && (app.mode === 'local' || piece.color === app.humanColor)) {
    selectPiece(piece);
  } else {
    clearSelection();
    render();
  }
}

function commitMove(move) {
  if (app.online) {
    net.sendMove(app.online.code, app.online.color, move)
      .then((data) => applyRemote(data, true))
      .catch(() => toast(t('online.moveRejected')));
    return;
  }
  const state = app.game.state;
  const moving = state.pieces.find(
    (p) => p.row === move.source.row && p.col === move.source.col,
  );
  if (!moving) return;
  const captured = state.pieces.some(
    (p) => p.row === move.target.row && p.col === move.target.col,
  );

  let record;
  try {
    record = app.game.move(move);
  } catch (error) {
    if (error instanceof GameError) {
      toast(t('toast.illegal'));
      return;
    }
    throw error;
  }

  if (app.prefs.animation) {
    app.anim = {
      from: { row: move.source.row, col: move.source.col },
      to: { row: move.target.row, col: move.target.col },
      piece: moving,
      capture: captured,
      started: performance.now(),
      duration: 190,
    };
    animate();
  }

  app.lastMove = { source: move.source, target: move.target };
  clearSelection();
  playMoveSound(record);
  render();
  saveSession();

  if (app.puzzle) {
    checkPuzzle(record);
    return;
  }

  if (isOver(app.game.state)) {
    setTimeout(onGameFinished, 260);
    return;
  }
  setTimeout(maybeAI, 140);
}

function playMoveSound(record) {
  if (!app.prefs.sound) return;
  const inCheck = app.game.rules.inCheck(app.game.state, app.game.state.turn);
  if (inCheck) sound.play('check');
  else if (record.captured.length) sound.play('capture');
  else sound.play('move');
}

function onGameFinished() {
  const state = app.game.state;
  recordStats();
  saveToLibrary();
  const winner = state.winner;
  const reason = t(`result.reason.${state.resultReason || 'draw'}`);
  let title;
  if (state.draw) {
    title = t('result.draw');
  } else if (app.mode === 'local') {
    title = t('result.win', { side: t(`side.${winner}`) });
  } else {
    title = winner === app.humanColor ? t('result.youWin') : t('result.youLose');
  }
  $('#resultTitle').textContent = title;
  $('#resultReason').textContent = reason;
  $('#resultMark').textContent = state.draw ? '和' : (winner === 'red' ? '漢' : '汗');
  $('#resultMark').style.background = state.draw ? '#6d6255' : (winner === 'red' ? '#9c2b22' : '#2b2622');
  sound.play(!state.draw && app.mode === 'ai' && winner !== app.humanColor ? 'lose' : 'win');
  showDialog('dlgResult');
  saveSession();
}

/* ---------------------------------------------------------------- AI */

function initWorker() {
  try {
    const factory = globalThis.__xhCreateWorker;
    app.worker = factory
      ? factory()
      : new Worker(new URL('js/ai-worker.js', document.baseURI), { type: 'module' });
    app.worker.onmessage = (event) => {
      const data = event.data;
      if (!data) return;
      if (data.type === 'analyze-progress') {
        if (data.id === app.analysisId) updateAnalysisProgress(data);
        return;
      }
      if (data.type === 'analyze-done') {
        if (data.id === app.analysisId) finishAnalysis(data.results);
        return;
      }
      if (data.type === 'analyze-error') {
        if (data.id === app.analysisId) analysisFailed();
        return;
      }
      if (data.id !== app.requestId) return;
      app.thinking = false;
      $('#thinking').hidden = true;
      if (data.error) {
        aiFallback();
        return;
      }
      if (!data.move) {
        render();
        return;
      }
      commitMove({
        source: { row: data.move.from.row, col: data.move.from.col },
        target: { row: data.move.to.row, col: data.move.to.col },
        promotion: data.move.promotion || null,
      });
    };
    app.worker.onerror = () => {
      app.worker = null;
    };
  } catch {
    app.worker = null;
  }
}

function maybeAI() {
  if (!app.game || app.replay.open) return;
  const state = app.game.state;
  if (app.puzzle) return;
  if (app.mode !== 'ai' || isOver(state) || state.paused) return;
  if (state.turn === app.humanColor) return;
  if (app.thinking) return;

  app.thinking = true;
  $('#thinking').hidden = false;
  const config = DIFFICULTIES[app.difficulty] || DIFFICULTIES.normal;
  const id = ++app.requestId;
  const payload = {
    id,
    state: stateToDict(state),
    profileId: app.game.profile.id,
    options: app.game.options,
    difficulty: app.difficulty,
    timeMs: config.timeMs,
  };

  if (app.worker) {
    app.worker.postMessage(payload);
  } else {
    aiFallback();
  }
}

function aiFallback() {
  if (!app.game) return;
  const id = ++app.requestId;
  const config = DIFFICULTIES[app.difficulty] || DIFFICULTIES.normal;
  setTimeout(() => {
    const result = suggestMove(app.game.state, app.game.rules, config.timeMs);
    app.thinking = false;
    $('#thinking').hidden = true;
    if (id !== app.requestId || !result.move) return;
    commitMove(result.move);
  }, 40);
}

/* ---------------------------------------------------------------- 渲染 */

function viewState() {
  if (app.replay.open && app.replay.states.length) {
    return app.replay.states[Math.min(app.replay.index, app.replay.states.length - 1)];
  }
  return app.game.state;
}

function render() {
  if (!app.game) return;
  const state = viewState();
  const profile = app.game.profile;
  const isReplay = app.replay.open;
  const checkSide = !isReplay && state.check ? state.turn : null;

  board.draw({
    state,
    profile: {
      ...profile,
      archerStarPoints: app.game.rules.archerStarPoints,
    },
    selected: isReplay ? null : app.selected,
    legal: isReplay ? []
      : (app.resurrecting ? app.resurrectTargets
        : (app.prefs.legal ? app.legal : [])),
    flipped: app.flipped,
    theme: app.prefs.theme,
    pieceStyle: app.prefs.pieceStyle,
    lastMove: isReplay ? replayLastMove() : app.lastMove,
    checkSide: isReplay ? null : (app.game.rules.inCheck(state, state.turn) ? state.turn : null),
    anim: isReplay ? null : app.anim,
    showCoordinates: false,
    showMarks: !app.puzzle,
  });

  updateHud(state, checkSide);
}

function replayLastMove() {
  const state = viewState();
  const record = state.history?.[app.replay.index - 1];
  return record ? record.move : null;
}

function updateHud(state, checkSide) {
  const profile = app.game.profile;
  const isReplay = app.replay.open;
  const turn = state.turn;

  let badgeText;
  if (app.mode === 'online' && app.online) {
    const ready = $('.room-code') ? true : true;
    badgeText = isOver(state) ? t('online.ended')
      : (state.turn === app.online.color ? t('online.yourTurn') : t('online.opponentTurn'));
    void ready;
  } else if (app.puzzle) {
    const total = app.puzzle.data.type === 'mate' ? 1 : (app.puzzle.data.solution.length || 1);
    badgeText = `${app.puzzle.data.title} · ${t('puzzle.progress', {
      n: Math.min(app.puzzle.step + 1, total), total,
    })}`;
  } else if (isReplay) {
    badgeText = `${app.replay.index} / ${app.replay.states.length - 1}`;
  } else if (isOver(state)) {
    badgeText = state.draw ? t('result.draw') : t('result.win', { side: t(`side.${state.winner}`) });
  } else if (state.paused) {
    badgeText = t('status.paused');
  } else if (checkSide) {
    badgeText = `${t('status.check')} · ${t('side.turn', { side: t(`side.${turn}`) })}`;
  } else {
    badgeText = t('side.turn', { side: t(`side.${turn}`) });
  }
  const badge = $('#turnBadge');
  badge.textContent = badgeText;
  badge.classList.toggle('show', !app.replay.open);

  let redName;
  let blackName;
  if (app.mode === 'local') {
    redName = t('side.local1');
    blackName = t('side.local2');
  } else if (app.mode === 'online') {
    redName = app.humanColor === 'red' ? t('online.you') : t('online.rival');
    blackName = app.humanColor === 'black' ? t('online.you') : t('online.rival');
  } else {
    redName = app.humanColor === 'red' ? t('side.you') : t('side.ai');
    blackName = app.humanColor === 'black' ? t('side.you') : t('side.ai');
  }
  $('#seatRed').querySelector('strong').textContent = `${t('side.red')} · ${redName}`;
  $('#seatBlack').querySelector('strong').textContent = `${t('side.black')} · ${blackName}`;
  const levelLabel = t(`diff.${app.difficulty}`) || '';
  $('#redNote').textContent = app.mode === 'local' ? '' : (app.humanColor === 'red' ? '' : levelLabel);
  $('#blackNote').textContent = app.mode === 'local' ? '' : (app.humanColor === 'black' ? '' : levelLabel);

  const active = !isOver(state) && !isReplay;
  $('#seatRed').classList.toggle('active', active && turn === 'red');
  $('#seatBlack').classList.toggle('active', active && turn === 'black');

  updateClock('red', state);
  updateClock('black', state);

  renderMoveList(state);
  renderCaptured(state);

  $('#metaProfile').textContent = t(`profile.${profile.id}`);
  $('#metaMode').textContent = app.mode === 'local' ? t('setup.mode.local') : t('setup.mode.ai');
  $('#metaLevel').textContent = app.mode === 'local' ? '—' : (t(`diff.${app.difficulty}`) || '');

  const inPuzzle = Boolean(app.puzzle);
  const inOnline = Boolean(app.online);
  const canAct = !isOver(state) && !isReplay && !app.thinking && !state.paused && !inPuzzle;
  $$('.toolbar [data-act="undo"]').forEach((b) => { b.disabled = inPuzzle || inOnline || !app.game.canUndo(1) || isReplay; });
  $$('.toolbar [data-act="hint"]').forEach((b) => { b.disabled = !canAct || !isHumanTurn(); });
  $$('.toolbar [data-act="resign"]').forEach((b) => { b.disabled = !canAct; });
  $$('.toolbar [data-act="pause"]').forEach((b) => {
    b.disabled = isOver(state) || isReplay || inPuzzle || inOnline;
    b.textContent = state.paused ? t('action.resume') : t('action.pause');
  });
  $$('.toolbar [data-act="draw"]').forEach((b) => { b.disabled = !canAct || inOnline; });
  const revive = $('#resurrectBtn');
  if (revive) {
    const allowed = !isReplay && !inPuzzle && !inOnline && canResurrect();
    revive.hidden = !allowed;
    revive.disabled = !allowed;
  }
  if (app.resurrecting && !canResurrect()) exitResurrect();
  const exitBtn = $('#puzzleExit');
  if (exitBtn) exitBtn.hidden = !inPuzzle;
  $('#pauseMask').hidden = !(state.paused && !isReplay);
  $('#resurrectPill').hidden = !app.resurrecting;

  $('#boardTip').classList.toggle('hide', !app.selected && (state.history.length > 0 || isReplay));
}

function updateClock(color, state) {
  const node = $(color === 'red' ? '#clockRed' : '#clockBlack');
  if (app.unlimited) {
    node.textContent = t('clock.unlimited');
    node.classList.remove('urgent');
    return;
  }
  let ms = state.clocksMs[color] || 0;
  if (!isOver(state) && !state.paused && state.turn === color && !app.replay.open) {
    ms -= performance.now() - state.turnStartedAt;
  }
  ms = Math.max(0, ms);
  const total = Math.ceil(ms / 1000);
  node.textContent = `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
  node.classList.toggle('urgent', ms <= 30000 && !isOver(state));
}

function renderMoveList(state) {
  const list = $('#moveList');
  const empty = $('#moveEmpty');
  const history = state.history || [];
  list.innerHTML = '';
  empty.hidden = history.length > 0;
  history.forEach((record, index) => {
    const li = document.createElement('li');
    li.className = record.color;
    const idx = document.createElement('span');
    idx.className = 'idx';
    idx.textContent = `${index + 1}.`;
    li.append(idx, document.createTextNode(record.notation));
    list.append(li);
  });
  if (app.replay.open) {
    [...list.children].forEach((li, i) => li.classList.toggle('current', i + 1 === app.replay.index));
  }
  list.scrollTop = list.scrollHeight;
}

function renderCaptured(state) {
  const make = (color) => (state.captured[color] || []).map((p) => {
    const span = document.createElement('span');
    span.className = color;
    span.textContent = (color === 'red' ? RED_NAMES : BLACK_NAMES)[p.type] || p.type;
    return span;
  });
  $('#capturedRed').replaceChildren(...make('red'));
  $('#capturedBlack').replaceChildren(...make('black'));
}

function animate() {
  cancelAnimationFrame(app.raf);
  const step = () => {
    render();
    if (app.anim && performance.now() - app.anim.started < app.anim.duration) {
      app.raf = requestAnimationFrame(step);
    } else {
      app.anim = null;
      render();
    }
  };
  app.raf = requestAnimationFrame(step);
}

function tickClock() {
  if (!app.game || app.replay.open || app.unlimited) return;
  const state = app.game.state;
  if (isOver(state) || state.paused) return;
  const timedOut = app.game.tick();
  if (timedOut) {
    render();
    onGameFinished();
  } else {
    updateClock('red', state);
    updateClock('black', state);
  }
}

/* ---------------------------------------------------------------- 复盘 */

function updateAnalysisProgress({ done, total }) {
  const box = $('#analysisProgress');
  const bar = box.querySelector('.bar i');
  box.hidden = false;
  bar.style.width = `${Math.round((done / total) * 100)}%`;
  $('#analysisProgressText').textContent = t('analysis.running', { done, total });
}

function analysisFailed() {
  $('#analysisProgress').hidden = true;
  toast(t('analysis.failed'));
}

/** 逐手分析：把每个局面交给工作线程跑一次浅层搜索，取根着法分数。 */
function runAnalysis() {
  if (!app.game) return;
  const history = app.game.state.history;
  if (!history.length) {
    toast(t('analysis.empty'));
    return;
  }
  if (!app.worker) {
    analysisFailed();
    return;
  }
  const CAP = 120;
  const total = Math.min(history.length, CAP);
  const replay = app.game.publicState().replay;
  const states = replay.slice(0, total);
  const moves = history.slice(0, total).map((record) => ({
    from: record.move.source,
    to: record.move.target,
    color: record.color,
    notation: record.notation,
  }));

  app.analysisId += 1;
  app.analysis = null;
  $('#curveCanvas').hidden = true;
  $('#analysisSummary').hidden = true;
  updateAnalysisProgress({ done: 0, total });

  app.worker.postMessage({
    type: 'analyze',
    id: app.analysisId,
    states,
    moves,
    profileId: app.game.profile.id,
    options: app.game.options,
    perMoveMs: 80,
    depth: 2,
  });
}

function finishAnalysis(results) {
  app.analysis = results;
  $('#analysisProgress').hidden = true;

  const stats = { best: 0, good: 0, inaccuracy: 0, mistake: 0, blunder: 0 };
  for (const item of results) stats[item.quality] += 1;

  const summary = $('#analysisSummary');
  summary.hidden = false;
  summary.textContent = `${t('analysis.done', {
    n: results.length,
    best: stats.best + stats.good,
    mistake: stats.inaccuracy + stats.mistake,
    blunder: stats.blunder,
  })}${results.length >= 120 ? ` ${t('analysis.capped', { n: 120 })}` : ''}`;

  drawCurve(results);
  drawReplay();
}

function drawCurve(results) {
  const canvas = $('#curveCanvas');
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const W = 920;
  const H = 320;
  canvas.width = W;
  canvas.height = H;
  canvas.hidden = false;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, W, H);

  const padX = 26;
  const padY = 26;
  const plotW = W - padX * 2;
  const plotH = H - padY * 2;
  const xAt = (i) => padX + (results.length === 1 ? plotW / 2 : (i / (results.length - 1)) * plotW);
  const yAt = (rate) => padY + (1 - rate / 100) * plotH;

  ctx.strokeStyle = 'rgba(90,70,40,.16)';
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 8]);
  ctx.beginPath();
  ctx.moveTo(padX, yAt(50));
  ctx.lineTo(padX + plotW, yAt(50));
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.beginPath();
  ctx.moveTo(xAt(0), padY + plotH);
  results.forEach((item, i) => ctx.lineTo(xAt(i), yAt(item.winRate)));
  ctx.lineTo(xAt(results.length - 1), padY + plotH);
  ctx.closePath();
  ctx.fillStyle = 'rgba(156,43,34,.12)';
  ctx.fill();

  ctx.beginPath();
  results.forEach((item, i) => {
    const x = xAt(i);
    const y = yAt(item.winRate);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#9c2b22';
  ctx.lineWidth = 3;
  ctx.lineJoin = 'round';
  ctx.stroke();

  for (const [i, item] of results.entries()) {
    if (item.quality !== 'blunder' && item.quality !== 'mistake') continue;
    ctx.beginPath();
    ctx.arc(xAt(i), yAt(item.winRate), 5, 0, Math.PI * 2);
    ctx.fillStyle = item.quality === 'blunder' ? '#b03a2e' : '#d07a2a';
    ctx.fill();
  }
}

function openReplay() {
  if (!app.game) return;
  const publicState = app.game.publicState();
  const states = publicState.replay.map((item) => stateFromDict(item));
  if (!states.length) return;
  app.replay.open = true;
  app.replay.states = states;
  app.replay.index = states.length - 1;
  clearSelection();
  showDialog('dlgReplay');
  requestAnimationFrame(() => {
    resizeReplay();
    drawReplay();
  });
}

function drawReplay() {
  const state = app.replay.states[app.replay.index];
  if (!state) return;
  replayBoard.draw({
    state,
    profile: { ...app.game.profile, archerStarPoints: app.game.rules.archerStarPoints },
    selected: null,
    legal: [],
    flipped: app.flipped,
    theme: app.prefs.theme,
    pieceStyle: app.prefs.pieceStyle,
    lastMove: state.history?.[app.replay.index - 1]?.move || null,
    checkSide: null,
    anim: null,
    showCoordinates: false,
  });
  $('#replayRange').max = String(app.replay.states.length - 1);
  $('#replayRange').value = String(app.replay.index);
  $('#replayStep').textContent = `${app.replay.index} / ${app.replay.states.length - 1}`;
  const list = $('#replayMoves');
  list.innerHTML = '';
  (state.history || []).forEach((record, index) => {
    const li = document.createElement('li');
    const quality = app.analysis && app.analysis[index] ? ` q-${app.analysis[index].quality}` : '';
    li.className = `${record.color}${index + 1 === app.replay.index ? ' current' : ''}${quality}`;
    li.dataset.ply = String(index + 1);
    const idx = document.createElement('span');
    idx.className = 'idx';
    idx.textContent = `${index + 1}.`;
    li.append(idx, document.createTextNode(record.notation));
    list.append(li);
  });
  list.scrollTop = list.scrollHeight;
}

function setReplayIndex(index) {
  const max = app.replay.states.length - 1;
  app.replay.index = Math.max(0, Math.min(max, index));
  drawReplay();
  updateHud(viewState(), null);
}

function toggleReplayPlay() {
  if (app.replay.timer) {
    clearInterval(app.replay.timer);
    app.replay.timer = null;
    $('[data-replay="play"]').textContent = '▶';
    return;
  }
  if (app.replay.index >= app.replay.states.length - 1) setReplayIndex(0);
  app.replay.timer = setInterval(() => {
    if (app.replay.index >= app.replay.states.length - 1) {
      clearInterval(app.replay.timer);
      app.replay.timer = null;
      $('[data-replay="play"]').textContent = '▶';
      return;
    }
    setReplayIndex(app.replay.index + 1);
  }, 620);
  $('[data-replay="play"]').textContent = '❚❚';
}

function closeReplay() {
  app.replay.open = false;
  if (app.replay.timer) {
    clearInterval(app.replay.timer);
    app.replay.timer = null;
  }
  hideDialog('dlgReplay');
  if (app.game) render();
}

/* ---------------------------------------------------------------- 升变 */

function askPromotion(moves) {
  const options = [...new Set(moves.map((m) => m.promotion))];
  const root = $('#promoOptions');
  root.innerHTML = '';
  for (const type of options) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = RED_NAMES[type] || type;
    button.title = PIECE_INFO[type]?.name || type;
    button.onclick = () => {
      const chosen = moves.find((m) => m.promotion === type);
      hideDialog('dlgPromotion');
      if (chosen) commitMove(chosen);
    };
    root.append(button);
  }
  showDialog('dlgPromotion');
}

/* ---------------------------------------------------------------- 操作 */

function undo() {
  if (!app.game || app.replay.open) return;
  try {
    let plies = app.mode === 'local' ? 1 : 2;
    if (!app.game.canUndo(plies)) plies = 1;
    app.game.undo(plies);
    if (app.mode === 'ai' && app.game.state.turn !== app.humanColor && app.game.canUndo(1)) {
      app.game.undo(1);
    }
    app.lastMove = app.game.state.history.at(-1)?.move || null;
    clearSelection();
    app.thinking = false;
    $('#thinking').hidden = true;
    sound.play('undo');
    render();
    saveSession();
    toast(t('toast.undone'));
    // 悔棋后如果轮到棋灵，继续让它走，避免卡住
    if (app.mode === 'ai' && app.game.state.turn !== app.humanColor) {
      setTimeout(maybeAI, 180);
    }
  } catch {
    toast(t('toast.noUndo'));
  }
}

function hint() {
  if (!app.game || app.thinking) return;
  if (app.puzzle) {
    const list = app.puzzle.data.hints || [];
    const text = list[Math.min(app.puzzle.step, list.length - 1)] || app.puzzle.data.desc;
    toast(t('puzzle.hint', { hint: text }));
    return;
  }
  app.thinking = true;
  $('#thinking').hidden = false;
  setTimeout(() => {
    const result = suggestMove(app.game.state, app.game.rules, 600);
    app.thinking = false;
    $('#thinking').hidden = true;
    if (!result.move) {
      toast(t('toast.noHint'));
      return;
    }
    const moving = app.game.state.pieces.find(
      (p) => p.row === result.move.source.row && p.col === result.move.source.col,
    );
    if (moving) {
      selectPiece(moving);
      app.legal = [result.move];
      render();
      toast(t('toast.hint', { move: app.game.notation(moving, result.move, []) }));
      setTimeout(() => {
        if (app.selected && app.legal.length === 1 && app.legal[0] === result.move) {
          clearSelection();
          render();
        }
      }, 2600);
    }
  }, 30);
}

function resign() {
  if (!app.game || isOver(app.game.state)) return;
  if (app.online) {
    net.sendResign(app.online.code, app.online.color)
      .then((data) => applyRemote(data, true))
      .catch(() => { /* 忽略 */ });
    return;
  }
  const color = app.mode === 'local' ? app.game.state.turn : app.humanColor;
  app.game.resign(color);
  render();
  onGameFinished();
}

function flip() {
  app.flipped = !app.flipped;
  render();
}

const SYNC_PREFS = [
  'theme', 'pieceStyle', 'language', 'animation', 'legal', 'captureHint',
  'sound', 'volume', 'music', 'musicVolume', 'background', 'sideHidden',
  'difficulty', 'profileId', 'mode', 'side', 'firstMove', 'minutes', 'options', 'appear',
];

let cloudPending = null;

function collectSnapshot() {
  const prefs = {};
  for (const key of SYNC_PREFS) prefs[key] = app.prefs[key];
  return {
    v: 1,
    savedAt: new Date().toISOString(),
    prefs,
    library: JSON.parse(localStorage.getItem('xh-web-library') || '[]'),
    stats: JSON.parse(localStorage.getItem('xh-web-stats') || '{}'),
    solved: JSON.parse(localStorage.getItem('xh-web-puzzle-solved') || '[]'),
  };
}

function applySnapshot(snap) {
  if (!snap) return false;
  if (snap.prefs) {
    for (const [key, value] of Object.entries(snap.prefs)) {
      if (key in app.prefs) app.prefs[key] = value;
    }
    savePrefs();
  }
  if (Array.isArray(snap.library)) localStorage.setItem('xh-web-library', JSON.stringify(snap.library.slice(0, 12)));
  if (snap.stats) localStorage.setItem('xh-web-stats', JSON.stringify(snap.stats));
  if (Array.isArray(snap.solved)) localStorage.setItem('xh-web-puzzle-solved', JSON.stringify(snap.solved));
  return true;
}

function cloudStatus(text) {
  const node = $('#cloudStatus');
  if (node) node.textContent = text || '';
}

async function openCloudDialog() {
  showDialog('dlgCloud');
  cloudStatus('');
  if (!cloud.cloudConfigured()) {
    cloudStatus(t('cloud.notConfigured'));
    return;
  }
  try {
    const session = await cloud.currentSession();
    renderCloudState(session, null);
  } catch {
    renderCloudState(null, t('cloud.failed'));
  }
}

function renderCloudState(session, errorText) {
  const signedOut = $('#cloudSignedOut');
  const signedIn = $('#cloudSignedIn');
  if (!signedOut || !signedIn) return;
  const signed = Boolean(session && session.user);
  signedOut.hidden = signed;
  signedIn.hidden = !signed;
  if (signed) {
    const who = session.user.email || session.user.name || session.user.id || '';
    $('#cloudWho').textContent = t('cloud.who', { who });
  }
  if (errorText) cloudStatus(errorText);
}

async function cloudSendCode() {
  const email = ($('#cloudEmail').value || '').trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    cloudStatus(t('cloud.badEmail'));
    return;
  }
  cloudStatus(t('cloud.busy'));
  try {
    const data = await cloud.sendCode(email);
    cloudPending = { email, verificationId: data.verificationId, isExistingUser: data.isExistingUser };
    cloudStatus(t('cloud.codeSent'));
  } catch (error) {
    cloudStatus((error && error.message) || t('cloud.failed'));
  }
}

async function cloudSubmitCode() {
  const email = ($('#cloudEmail').value || '').trim();
  const token = ($('#cloudCode').value || '').trim();
  if (!cloudPending || cloudPending.email !== email) {
    cloudStatus(t('cloud.codeRequired'));
    return;
  }
  cloudStatus(t('cloud.busy'));
  try {
    const result = await cloud.verifyCode({ ...cloudPending, token });
    const emailUsed = cloudPending.email;
    cloudPending = null;
    const session = result && result.user ? result : await cloud.currentSession();
    renderCloudState(session, '');
    // 会话里的 user 可能只有数字 id，登录后优先显示本次使用的邮箱
    if (emailUsed) $('#cloudWho').textContent = t('cloud.who', { who: emailUsed });
    const row = await cloud.pullState().catch(() => null);
    if (row && row.updated_at) {
      $('#cloudLast').textContent = t('cloud.lastSync', { time: new Date(row.updated_at).toLocaleString('zh-CN') });
    } else {
      $('#cloudLast').textContent = t('cloud.never');
    }
  } catch (error) {
    cloudStatus((error && error.message) || t('cloud.failed'));
  }
}

async function cloudBackup() {
  cloudStatus(t('cloud.busy'));
  try {
    const row = await cloud.pushState(collectSnapshot());
    const when = row && row.updated_at ? new Date(row.updated_at).toLocaleString('zh-CN') : new Date().toLocaleString('zh-CN');
    $('#cloudLast').textContent = t('cloud.lastSync', { time: when });
    cloudStatus(t('cloud.done'));
  } catch (error) {
    cloudStatus((error && error.message) || t('cloud.failed'));
  }
}

async function cloudRestore() {
  cloudStatus(t('cloud.busy'));
  try {
    const row = await cloud.pullState();
    if (!row || !row.payload) {
      cloudStatus(t('cloud.empty'));
      return;
    }
    applySnapshot(row.payload);
    cloudStatus(t('cloud.restored'));
    setTimeout(() => location.reload(), 700);
  } catch (error) {
    cloudStatus((error && error.message) || t('cloud.failed'));
  }
}

async function cloudSignOut() {
  try {
    await cloud.signOut();
    renderCloudState(null, t('cloud.signedOut'));
  } catch (error) {
    cloudStatus((error && error.message) || t('cloud.failed'));
  }
}

function applyBackground() {
  const bg = app.prefs.background;
  if (bg) {
    document.body.style.setProperty('--page-bg', `url("${bg}")`);
    document.body.classList.add('has-bg');
  } else {
    document.body.classList.remove('has-bg');
    document.body.style.removeProperty('--page-bg');
  }
}

function clearBackground() {
  app.prefs.background = '';
  applyBackground();
  savePrefs();
  toast(t('settings.clearBackground'));
}

async function handleBackgroundFile(file) {
  if (!file) return;
  try {
    const bitmap = await createImageBitmap(file);
    const max = 1600;
    const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    let data = canvas.toDataURL('image/jpeg', 0.82);
    if (data.length > 1_600_000) data = canvas.toDataURL('image/jpeg', 0.68);
    if (data.length > 1_900_000) {
      toast(t('settings.bgTooBig'));
      return;
    }
    app.prefs.background = data;
    applyBackground();
    savePrefs();
  } catch {
    toast(t('settings.bgTooBig'));
  }
}

function toggleSide() {
  app.prefs.sideHidden = !app.prefs.sideHidden;
  applySideHidden();
  savePrefs();
  resizeAll();
}

function applySideHidden() {
  const shell = $('.shell');
  if (shell) shell.classList.toggle('side-hidden', Boolean(app.prefs.sideHidden));
  const restore = $('#sideRestore');
  if (restore) restore.hidden = !app.prefs.sideHidden;
}

function restartGame() {
  if (!app.game) return;
  startGame({ silent: true });
  toast(t('action.restart'));
}

function normalizePuzzles(raw) {
  const list = Array.isArray(raw) ? raw : (raw && Array.isArray(raw.puzzles) ? raw.puzzles : null);
  if (!list) return null;
  const out = [];
  for (const item of list) {
    if (!item || !Array.isArray(item.solution) || !item.solution.length) continue;
    const type = item.type === 'mate' ? 'mate' : 'move';
    if (type === 'mate' && (!Array.isArray(item.pieces) || !item.pieces.length)) continue;
    out.push({
      id: `custom-${String(item.id || out.length).slice(0, 16)}-${Math.random().toString(36).slice(2, 6)}`,
      title: String(item.title || '自定义题').slice(0, 18),
      level: 'custom',
      desc: String(item.desc || '').slice(0, 80),
      profileId: item.profileId || 'desktop_complete',
      type,
      start: type === 'move' && !item.pieces ? 'initial' : undefined,
      turn: item.turn === 'black' ? 'black' : 'red',
      pieces: Array.isArray(item.pieces) ? item.pieces.slice(0, 40) : [],
      solution: item.solution.slice(0, 8).map((m) => ({
        from: m.from, to: m.to, promotion: m.promotion || null,
      })),
      hints: Array.isArray(item.hints) ? item.hints.slice(0, 3) : [],
    });
  }
  return out;
}

async function handlePuzzleFile(file) {
  if (!file) return;
  try {
    const text = await file.text();
    const parsed = normalizePuzzles(JSON.parse(text));
    if (!parsed || !parsed.length) {
      toast(t('puzzle.importFailed'));
      return;
    }
    const merged = [...(app.prefs.customPuzzles || []), ...parsed].slice(-30);
    app.prefs.customPuzzles = merged;
    savePrefs();
    renderPuzzleList();
    toast(t('puzzle.imported', { n: parsed.length }));
  } catch {
    toast(t('puzzle.importFailed'));
  }
}

function toggleFullscreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen?.();
    return;
  }
  document.documentElement.requestFullscreen?.().catch(() => toast(t('toast.fullscreenFailed')));
}

function openOnlineDialog() {
  const lobby = $('#onlineLobby');
  const room = $('#onlineRoom');
  if (app.online) {
    lobby.hidden = true;
    room.hidden = false;
    $('#roomCode').textContent = app.online.code;
    $('#onlineMsg').textContent = t('online.waiting');
  } else {
    lobby.hidden = false;
    room.hidden = true;
  }
  showDialog('dlgOnline');
}

async function createOnlineRoom() {
  try {
    const data = await net.createRoom(app.prefs.profileId);
    enterOnline(data, 'red');
  } catch {
    toast(t('online.failed'));
  }
}

async function joinOnlineRoom() {
  const input = $('#roomInput');
  const code = (input.value || '').trim().toUpperCase();
  if (code.length !== 4) {
    toast(t('online.badCode'));
    return;
  }
  try {
    const data = await net.joinRoom(code);
    enterOnline(data, 'black');
  } catch (error) {
    toast(error.status === 409 ? t('online.full') : t('online.notFound'));
  }
}

function enterOnline(data, color) {
  app.online = { code: data.code, color, since: data.ply, resultShown: false };
  app.mode = 'online';
  app.humanColor = color;
  app.flipped = color === 'black';
  app.puzzle = null;
  app.analysis = null;
  app.unlimited = true;
  hideDialog('dlgOnline');
  applyRemote(data, true);
  startPolling();
}

function copyRoomCode() {
  if (!app.online) return;
  navigator.clipboard?.writeText(app.online.code).then(
    () => toast(t('online.copied')),
    () => toast(app.online.code),
  );
}

function stopPolling() {
  if (app.online) app.online.stopped = true;
}

function startPolling() {
  if (!app.online) return;
  const loop = async () => {
    const session = app.online;
    if (!session || session.stopped) return;
    try {
      const data = await net.fetchState(session.code, session.since);
      if (!app.online || app.online !== session) return;
      applyRemote(data);
      if (data.finished) return;
    } catch (error) {
      if (error.status === 404 || error.status === 410) {
        toast(t('online.roomClosed'));
        leaveOnline(false);
        return;
      }
    }
    if (app.online === session) setTimeout(loop, 120);
  };
  loop();
}

function applyRemote(data, force = false) {
  if (!data || !data.state) return;
  if (!force && app.online && data.ply === app.online.since) return;
  const profile = getProfile(data.state.profileId || app.prefs.profileId);
  const options = mergeOptions(profile.options, app.prefs.options);
  app.game = new Game(profile, options, { state: stateFromDict(data.state) });
  app.game.state.clocksMs = { red: 0, black: 0 };
  app.unlimited = true;
  if (app.online) {
    app.online.since = data.ply;
    $('#onlineMsg').textContent = data.finished
      ? t('online.ended')
      : (data.players.red && data.players.black
        ? (data.turn === app.online.color ? t('online.yourTurn') : t('online.opponentTurn'))
        : t('online.waiting'));
  }
  clearSelection();
  app.anim = null;
  app.lastMove = app.game.state.history.at(-1)?.move || null;
  resizeAll();
  render();
  if (data.finished && app.online && !app.online.resultShown) {
    app.online.resultShown = true;
    setTimeout(onGameFinished, 220);
  }
}

function leaveOnline(showToast) {
  stopPolling();
  app.online = null;
  hideDialog('dlgOnline');
  startGame({ silent: true });
  if (showToast) toast(t('online.leave'));
}

function togglePause() {
  if (!app.game || app.replay.open) return;
  const state = app.game.state;
  if (isOver(state)) return;
  try {
    app.game.setPaused(!state.paused, app.mode === 'ai' ? app.humanColor : state.turn);
  } catch {
    return;
  }
  clearSelection();
  render();
  saveSession();
  if (!app.game.state.paused) setTimeout(maybeAI, 200);
}

/** 桌面版的「复活」：把阵亡兵卒放回己方底线。 */
function canResurrect() {
  if (!app.game || app.replay.open) return false;
  const state = app.game.state;
  if (isOver(state) || state.paused) return false;
  if (!app.game.options.pawn_resurrection) return false;
  if (app.mode === 'ai' && state.turn !== app.humanColor) return false;
  const color = state.turn;
  if (!state.captured[color].some((p) => p.type === 'pawn')) return false;
  const alive = state.pieces.filter((p) => p.type === 'pawn' && p.color === color).length;
  return alive < 7;
}

function enterResurrect() {
  if (!canResurrect()) {
    toast(t('toast.noResurrect'));
    return;
  }
  const state = app.game.state;
  const row = state.turn === 'red' ? 8 : 4;
  app.resurrectTargets = [];
  for (let col = 0; col < app.game.profile.cols; col += 2) {
    if (!state.pieces.some((p) => p.row === row && p.col === col)) {
      app.resurrectTargets.push({ row, col });
    }
  }
  if (!app.resurrectTargets.length) {
    toast(t('toast.noResurrect'));
    return;
  }
  app.resurrecting = true;
  clearSelection();
  render();
  toast(t('resurrect.hint'));
}

function exitResurrect() {
  app.resurrecting = false;
  app.resurrectTargets = [];
}

function offerDraw() {
  if (!app.game || app.replay.open) return;
  const state = app.game.state;
  if (isOver(state) || state.paused) return;

  if (app.mode === 'local') {
    if (!window.confirm(t('draw.confirmLocal'))) return;
    state.draw = true;
    state.resultReason = 'draw_agreement';
    render();
    onGameFinished();
    return;
  }

  if (state.turn !== app.humanColor) return;
  const redScore = evaluate(state, app.game.rules);
  const own = app.humanColor === 'red' ? redScore : -redScore;
  // 均势会同意；对手明显落后也会同意；自己明显落后则拒绝
  const accepted = Math.abs(own) < 100 || own > 250;
  if (!accepted) {
    toast(t('draw.declined'));
    return;
  }
  state.draw = true;
  state.resultReason = 'draw_agreement';
  toast(t('draw.accepted'));
  render();
  setTimeout(onGameFinished, 260);
}

const STATS_KEY = 'xh-web-stats';

function emptyStats() {
  return { games: 0, wins: 0, losses: 0, draws: 0, moves: 0 };
}

function loadStats() {
  try {
    return { ...emptyStats(), ...JSON.parse(localStorage.getItem(STATS_KEY) || '{}') };
  } catch {
    return emptyStats();
  }
}

function saveStats(stats) {
  try {
    localStorage.setItem(STATS_KEY, JSON.stringify(stats));
  } catch {
    /* 忽略 */
  }
}

function recordStats() {
  if (app.statsRecorded || !app.game) return;
  const state = app.game.state;
  if (!isOver(state)) return;
  app.statsRecorded = true;
  const stats = loadStats();
  stats.games += 1;
  stats.moves += state.history.length;
  if (state.draw) {
    stats.draws += 1;
  } else if (state.winner === 'red') {
    stats.wins += 1;
  } else {
    stats.losses += 1;
  }
  saveStats(stats);
}

function renderStats() {
  const stats = loadStats();
  const rate = stats.games ? `${Math.round((stats.wins / stats.games) * 100)}%` : '—';
  const cards = [
    [t('stats.games'), stats.games],
    [t('stats.wins'), stats.wins],
    [t('stats.losses'), stats.losses],
    [t('stats.draws'), stats.draws],
    [t('stats.moves'), stats.moves],
    [t('stats.rate'), rate],
  ];
  const grid = $('#statsGrid');
  grid.innerHTML = '';
  for (const [label, value] of cards) {
    const card = document.createElement('div');
    card.className = 'stat-card';
    const b = document.createElement('b');
    b.textContent = String(value);
    const span = document.createElement('span');
    span.textContent = label;
    card.append(b, span);
    grid.append(card);
  }
  if (!stats.games) {
    const note = document.createElement('p');
    note.className = 'empty';
    note.style.gridColumn = '1 / -1';
    note.textContent = t('stats.empty');
    grid.append(note);
  }
}

/** ---------------------------------------------------------------- 残局训练 */

function solvedIds() {
  try {
    return new Set(JSON.parse(localStorage.getItem(SOLVED_KEY) || '[]'));
  } catch {
    return new Set();
  }
}

function markSolved(id) {
  const set = solvedIds();
  set.add(id);
  try {
    localStorage.setItem(SOLVED_KEY, JSON.stringify([...set]));
  } catch {
    /* 忽略 */
  }
}

function allPuzzles() {
  const custom = Array.isArray(app.prefs.customPuzzles) ? app.prefs.customPuzzles : [];
  return [...PUZZLES, ...custom];
}

function renderPuzzleList() {
  const root = $('#puzzleList');
  root.innerHTML = '';
  const solved = solvedIds();
  const groups = ['beginner', 'advanced', 'master', 'tactics', 'custom'];
  const pool = allPuzzles();
  for (const level of groups) {
    const items = pool.filter((p) => p.level === level);
    if (!items.length) continue;
    const title = document.createElement('div');
    title.className = 'puzzle-group';
    title.textContent = level === 'custom' ? t('puzzle.customGroup') : t(`puzzle.level.${level}`);
    root.append(title);
    for (const item of items) {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = `puzzle-card${solved.has(item.id) ? ' solved' : ''}`;
      const strong = document.createElement('strong');
      strong.textContent = item.title;
      const desc = document.createElement('span');
      desc.textContent = item.desc;
      card.append(strong, desc);
      if (solved.has(item.id)) {
        const tag = document.createElement('em');
        tag.textContent = t('puzzle.solvedTag');
        strong.append(tag);
      }
      card.onclick = () => startPuzzle(item);
      root.append(card);
    }
  }
}

function startPuzzle(data) {
  const profile = getProfile(data.profileId);
  const options = mergeOptions(profile.options, app.prefs.options);
  let game;
  if (data.start === 'initial') {
    game = new Game(profile, options, { initialMinutes: 0 });
  } else {
    const pieces = (data.pieces || []).map((p) => makePiece(p.type, p.color, p.row, p.col));
    const state = createState(profile.id, pieces, data.turn || 'red');
    state.clocksMs = { red: 0, black: 0 };
    game = new Game(profile, options, { state });
  }
  game.state.clocksMs = { red: 0, black: 0 };

  app.game = game;
  app.unlimited = true;
  app.puzzle = { data, step: 0 };
  app.humanColor = data.turn || game.state.turn;
  app.flipped = app.humanColor === 'black';
  app.anim = null;
  app.lastMove = null;
  app.resurrecting = false;
  app.resurrectTargets = [];
  clearSelection();
  hideDialog('dlgPuzzles');
  resizeAll();
  render();
  toast(data.desc);
}

function checkPuzzle(record) {
  const data = app.puzzle.data;
  let ok = false;
  if (data.type === 'mate') {
    const state = app.game.state;
    ok = app.game.rules.inCheck(state, state.turn)
      && app.game.rules.legalMoves(state, state.turn).length === 0;
  } else {
    const expected = data.solution[app.puzzle.step];
    const move = record.move;
    ok = Boolean(expected)
      && move.source.row === expected.from.row && move.source.col === expected.from.col
      && move.target.row === expected.to.row && move.target.col === expected.to.col;
  }

  if (!ok) {
    toast(t('puzzle.wrong'));
    setTimeout(() => {
      try { app.game.undo(1); } catch { /* 忽略 */ }
      clearSelection();
      render();
    }, 380);
    return;
  }

  app.puzzle.step += 1;
  const total = data.type === 'mate' ? 1 : (data.solution.length || 1);
  if (app.puzzle.step >= total) {
    markSolved(data.id);
    sound.play('win');
    toast(t('puzzle.success'));
    setTimeout(() => exitPuzzle(), 1100);
  } else {
    toast(t('puzzle.progress', { n: app.puzzle.step + 1, total }));
  }
}

function exitPuzzle() {
  if (!app.puzzle) return;
  app.puzzle = null;
  app.unlimited = Number(app.minutes) === 0;
  startGame({ silent: true });
}

function resetStats() {
  saveStats(emptyStats());
  renderStats();
  toast(t('settings.reset'));
}

/* ---------------------------------------------------------------- 会话持久化 */

function saveSession() {
  if (!app.game) return;
  try {
    const payload = {
      document: gameToDocument(app.game),
      minutes: app.minutes,
      mode: app.mode,
      humanColor: app.humanColor,
      difficulty: app.difficulty,
    };
    localStorage.setItem(SESSION_KEY, JSON.stringify(payload));
  } catch {
    /* 忽略容量问题 */
  }
}

function restoreSession() {
  let payload;
  try {
    payload = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
  } catch {
    return false;
  }
  if (!payload?.document || payload.document.formatVersion !== 1) return false;
  try {
    const document_ = payload.document;
    app.game = gameFromDocument(document_, getLanguage());
    app.prefs.profileId = document_.profileId || app.prefs.profileId;
    app.mode = payload.mode || 'ai';
    app.humanColor = payload.humanColor || 'red';
    app.difficulty = payload.difficulty || 'normal';
    app.minutes = Number(payload.minutes ?? 0);
    app.unlimited = !app.minutes;
    const last = app.game.state.history.at(-1);
    app.lastMove = last ? last.move : null;
    render();
    return true;
  } catch {
    return false;
  }
}

/* ---------------------------------------------------------------- 弹层与绑定 */

function showDialog(id) {
  const dialog = document.getElementById(id);
  if (!dialog) return;
  if (typeof dialog.showModal === 'function') {
    if (!dialog.open) dialog.showModal();
  } else {
    dialog.setAttribute('open', '');
  }
}

function hideDialog(id) {
  const dialog = document.getElementById(id);
  if (!dialog) return;
  if (typeof dialog.close === 'function' && dialog.open) dialog.close();
  else dialog.removeAttribute('open');
}

function toast(message) {
  const node = $('#toast');
  node.textContent = message;
  node.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove('show'), 2200);
}

function buildProfileCards() {
  const root = $('#profileGrid');
  root.innerHTML = '';
  for (const id of PROFILE_ORDER) {
    const profile = PROFILES[id];
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `profile-card${id === app.prefs.profileId ? ' on' : ''}`;
    button.dataset.profile = id;
    const title = document.createElement('strong');
    title.textContent = t(`profile.${id}`);
    const copy = document.createElement('span');
    copy.textContent = profile.description;
    button.append(title, copy);
    button.onclick = () => {
      app.prefs.profileId = id;
      [...root.children].forEach((node) => node.classList.toggle('on', node === button));
      buildAppearGrid();
    };
    root.append(button);
  }
}

/** 登场棋子：按类型同步增减双方棋子，主帅固定。 */
function appearanceSlots(profile, options) {
  const appear = app.prefs.appear || {};
  const off = Object.keys(appear).filter((type) => appear[type] === false);
  if (!off.length) return null;
  const red = [];
  const black = [];
  for (const spec of profile.pieces) {
    if (!pieceEnabled(options, spec.type)) continue;
    if (appear[spec.type] === false) continue;
    const id = slotId(spec.color, spec.type, spec.row, spec.col);
    (spec.color === 'red' ? red : black).push(id);
  }
  return { redSlots: red, blackSlots: black };
}

function buildAppearGrid() {
  const root = $('#appearGrid');
  if (!root) return;
  root.innerHTML = '';
  const profile = getProfile(app.prefs.profileId);
  const counts = new Map();
  for (const spec of profile.pieces) counts.set(spec.type, (counts.get(spec.type) || 0) + 1);
  for (const [type, total] of counts) {
    const perSide = Math.max(1, Math.round(total / 2));
    const on = app.prefs.appear[type] !== false;
    const chip = document.createElement('label');
    chip.className = `appear-chip${on ? '' : ' off'}`;
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = on;
    input.disabled = type === 'king';
    const glyph = document.createElement('span');
    glyph.className = 'glyph';
    glyph.textContent = RED_NAMES[type] || type;
    const small = document.createElement('small');
    small.textContent = `×${perSide}`;
    chip.title = PIECE_INFO[type]?.name || type;
    input.onchange = () => {
      app.prefs.appear[type] = input.checked;
      chip.classList.toggle('off', !input.checked);
      savePrefs();
    };
    chip.append(input, glyph, small);
    root.append(chip);
  }
}

/** ---------------------------------------------------------------- 棋谱库 */

const LIB_KEY = 'xh-web-library';
const LIB_MAX = 12;

function loadLibrary() {
  try {
    return JSON.parse(localStorage.getItem(LIB_KEY) || '[]');
  } catch {
    return [];
  }
}

function writeLibrary(list) {
  try {
    localStorage.setItem(LIB_KEY, JSON.stringify(list.slice(0, LIB_MAX)));
  } catch {
    /* 容量不足时忽略 */
  }
}

function saveToLibrary() {
  if (!app.game) return;
  const state = app.game.state;
  if (!isOver(state)) return;
  const entry = {
    id: Date.now().toString(36),
    date: new Date().toISOString(),
    profileId: app.game.profile.id,
    options: app.game.options,
    setup: app.game.setup,
    plies: state.history.length,
    result: state.draw ? 'draw' : state.winner,
    reason: state.resultReason,
    moves: state.history.map((record) => ({
      from: { row: record.move.source.row, col: record.move.source.col },
      to: { row: record.move.target.row, col: record.move.target.col },
      promotion: record.move.promotion || null,
    })),
  };
  const list = loadLibrary();
  list.unshift(entry);
  writeLibrary(list);
  toast(t('library.saved'));
}

function buildFromEntry(entry) {
  const profile = getProfile(entry.profileId);
  const options = mergeOptions(profile.options, entry.options);
  const game = new Game(profile, options, { setup: entry.setup, initialMinutes: 0 });
  for (const move of entry.moves) {
    try {
      game.move({ source: move.from, target: move.to, promotion: move.promotion || null });
    } catch {
      break;
    }
  }
  return game;
}

function useEntry(entry, thenReplay) {
  app.game = buildFromEntry(entry);
  app.unlimited = true;
  app.puzzle = null;
  app.analysis = null;
  app.lastMove = app.game.state.history.at(-1)?.move || null;
  clearSelection();
  hideDialog('dlgLibrary');
  resizeAll();
  render();
  if (thenReplay) openReplay();
  else toast(t('library.loaded'));
}

function renderLibrary() {
  const root = $('#libraryList');
  root.innerHTML = '';
  const list = loadLibrary();
  if (!list.length) {
    const empty = document.createElement('p');
    empty.className = 'library-empty';
    empty.textContent = t('library.empty');
    root.append(empty);
    return;
  }
  for (const entry of list) {
    const row = document.createElement('div');
    row.className = 'library-row';
    const info = document.createElement('div');
    info.className = 'info';
    const strong = document.createElement('strong');
    strong.textContent = `${t(`profile.${entry.profileId}`)} · ${entry.plies} 手`;
    const meta = document.createElement('span');
    const resultText = entry.result === 'draw'
      ? t('result.draw')
      : t('result.win', { side: t(`side.${entry.result}`) });
    meta.textContent = `${new Date(entry.date).toLocaleString('zh-CN')} · ${resultText}`;
    info.append(strong, meta);

    const replay = document.createElement('button');
    replay.type = 'button';
    replay.textContent = t('library.replay');
    replay.onclick = () => useEntry(entry, true);

    const load = document.createElement('button');
    load.type = 'button';
    load.textContent = t('library.load');
    load.onclick = () => useEntry(entry, false);

    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'del';
    del.textContent = t('library.delete');
    del.onclick = () => {
      writeLibrary(loadLibrary().filter((item) => item.id !== entry.id));
      renderLibrary();
    };

    row.append(info, replay, load, del);
    root.append(row);
  }
}

function buildThemeSwatches() {
  const root = $('#themeSwatches');
  root.innerHTML = '';
  for (const theme of ['classic', 'jade', 'ink']) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `swatch${app.prefs.theme === theme ? ' on' : ''}`;
    button.dataset.theme = theme;
    button.title = t(`theme.${theme}`);
    button.onclick = () => {
      app.prefs.theme = theme;
      savePrefs();
      [...root.children].forEach((node) => node.classList.toggle('on', node === button));
      render();
      if (app.replay.open) drawReplay();
      if (app.atlasType) drawAtlas();
    };
    root.append(button);
  }
}

function buildRuleList() {
  const root = $('#ruleList');
  root.innerHTML = '';
  const profile = getProfile(app.prefs.profileId);
  for (const [key, label] of Object.entries(RULE_LABELS)) {
    if (!(key in profile.options)) continue;
    const wrapper = document.createElement('label');
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.dataset.rule = key;
    const value = key in app.prefs.options ? app.prefs.options[key] : profile.options[key];
    input.checked = Boolean(value);
    input.onchange = () => {
      app.prefs.options[key] = input.checked;
      savePrefs();
    };
    const span = document.createElement('span');
    span.textContent = label;
    wrapper.append(input, span);
    root.append(wrapper);
  }
}

function bindDialogs() {
  $$('[data-close]').forEach((button) => {
    button.onclick = () => hideDialog(button.dataset.close);
  });

  $$('.segmented').forEach((group) => {
    group.addEventListener('click', (event) => {
      const button = event.target.closest('button[data-value]');
      if (!button) return;
      [...group.children].forEach((node) => node.classList.toggle('on', node === button));
      const key = group.dataset.group;
      const value = button.dataset.value;
      if (key === 'mode') { app.prefs.mode = value; syncNewDialog(); }
      if (key === 'difficulty') app.prefs.difficulty = value;
      if (key === 'side') app.prefs.side = value;
      if (key === 'pieceStyle') { app.prefs.pieceStyle = value; savePrefs(); render(); if (app.replay.open) drawReplay(); drawAtlas(); }
      if (key === 'language') { app.prefs.language = value; savePrefs(); setLanguage(value); refreshTexts(); }
      sound.play('click');
    });
  });

  $('#firstMove').onchange = (event) => { app.prefs.firstMove = event.target.value; };
  $('#minutes').onchange = (event) => { app.prefs.minutes = Number(event.target.value); };

  $('#optAnimation').onchange = (event) => { app.prefs.animation = event.target.checked; savePrefs(); };
  $('#optLegal').onchange = (event) => { app.prefs.legal = event.target.checked; savePrefs(); render(); };
  $('#optCapture').onchange = (event) => { app.prefs.captureHint = event.target.checked; savePrefs(); render(); };
  $('#optSound').onchange = (event) => {
    app.prefs.sound = event.target.checked;
    sound.setSoundEnabled(app.prefs.sound);
    savePrefs();
    if (app.prefs.sound) sound.play('click');
  };

  const musicInput = $('#optMusic');
  if (musicInput) {
    musicInput.onchange = (event) => {
      app.prefs.music = event.target.checked;
      sound.setMusicEnabled(app.prefs.music);
      savePrefs();
    };
  }
  const musicVolumeInput = $('#optMusicVolume');
  if (musicVolumeInput) {
    musicVolumeInput.oninput = (event) => {
      const value = Number(event.target.value) / 100;
      app.prefs.musicVolume = value;
      sound.setMusicVolume(value);
      savePrefs();
    };
  }

  const volumeInput = $('#optVolume');
  if (volumeInput) {
    volumeInput.oninput = (event) => {
      const value = Number(event.target.value) / 100;
      app.prefs.volume = value;
      sound.setVolume(value);
      savePrefs();
    };
    volumeInput.onchange = () => sound.play('click');
  }

  const backgroundFile = $('#bgFile');
  if (backgroundFile) {
    backgroundFile.onchange = () => {
      handleBackgroundFile(backgroundFile.files[0]);
      backgroundFile.value = '';
    };
  }

  const puzzleFile = $('#puzzleFile');
  if (puzzleFile) {
    puzzleFile.onchange = () => {
      handlePuzzleFile(puzzleFile.files[0]);
      puzzleFile.value = '';
    };
  }

  $$('[data-replay]').forEach((button) => {
    button.onclick = () => {
      const action = button.dataset.replay;
      if (action === 'first') setReplayIndex(0);
      if (action === 'prev') setReplayIndex(app.replay.index - 1);
      if (action === 'next') setReplayIndex(app.replay.index + 1);
      if (action === 'last') setReplayIndex(app.replay.states.length - 1);
      if (action === 'play') toggleReplayPlay();
    };
  });

  $('#replayRange').oninput = (event) => setReplayIndex(Number(event.target.value));
  $('#replayMoves').onclick = (event) => {
    const li = event.target.closest('li[data-ply]');
    if (li) setReplayIndex(Number(li.dataset.ply));
  };

  $('#fileInput').onchange = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      app.game = gameFromDocument(data, getLanguage());
      app.unlimited = true;
      app.lastMove = app.game.state.history.at(-1)?.move || null;
      clearSelection();
      closeReplay();
      render();
      toast(t('toast.imported'));
    } catch {
      toast(t('toast.importFailed'));
    }
  };
}

function syncNewDialog() {
  const isAI = app.prefs.mode === 'ai';
  $$('[data-when="ai"]').forEach((node) => { node.hidden = !isAI; });
  $$('#dlgNew .segmented').forEach((group) => {
    const map = { mode: app.prefs.mode, difficulty: app.prefs.difficulty, side: app.prefs.side };
    const value = map[group.dataset.group];
    if (value === undefined) return;
    [...group.children].forEach((node) => node.classList.toggle('on', node.dataset.value === value));
  });
  $$('#dlgNew .profile-card').forEach((node) => {
    node.classList.toggle('on', node.dataset.profile === app.prefs.profileId);
  });
  $('#firstMove').value = app.prefs.firstMove;
  $('#minutes').value = String(app.prefs.minutes);
}

function refreshTexts() {
  applyI18n();
  buildProfileCards();
  syncNewDialog();
  render();
  if (app.replay.open) drawReplay();
  drawAtlas();
}

function bindGlobal() {
  document.addEventListener('click', (event) => {
    const action = event.target.closest('[data-act]');
    if (action) {
      const name = action.dataset.act;
      if (name === 'new') { buildAppearGrid(); syncNewDialog(); showDialog('dlgNew'); }
      if (name === 'start') {
        app.prefs.mode = app.prefs.mode;
        savePrefs();
        startGame();
      }
      if (name === 'replay') openReplay();
      if (name === 'atlas') { hideDialog('dlgRules'); showDialog('dlgAtlas'); drawAtlas(); }
      if (name === 'rules') showDialog('dlgRules');
      if (name === 'settings') { syncSettings(); showDialog('dlgSettings'); }
      if (name === 'about') { hideDialog('dlgSettings'); hideDialog('dlgRules'); showDialog('dlgAbout'); }
      if (name === 'undo') undo();
      if (name === 'pause') togglePause();
      if (name === 'draw') offerDraw();
      if (name === 'resurrect') enterResurrect();
      if (name === 'stats') { renderStats(); showDialog('dlgStats'); }
      if (name === 'library') { renderLibrary(); showDialog('dlgLibrary'); }
      if (name === 'puzzles') { renderPuzzleList(); showDialog('dlgPuzzles'); }
      if (name === 'exitPuzzle') exitPuzzle();
      if (name === 'analyze') runAnalysis();
      if (name === 'fullscreen') toggleFullscreen();
      if (name === 'pickBackground') $('#bgFile').click();
      if (name === 'clearBackground') clearBackground();
      if (name === 'restart') restartGame();
      if (name === 'toggleSide') toggleSide();
      if (name === 'importPuzzles') $('#puzzleFile').click();
      if (name === 'cloud') openCloudDialog();
      if (name === 'cloudSendCode') cloudSendCode();
      if (name === 'cloudVerify') cloudSubmitCode();
      if (name === 'cloudBackup') cloudBackup();
      if (name === 'cloudRestore') cloudRestore();
      if (name === 'cloudSignOut') cloudSignOut();
      if (name === 'online') openOnlineDialog();
      if (name === 'createRoom') createOnlineRoom();
      if (name === 'joinRoom') joinOnlineRoom();
      if (name === 'copyCode') copyRoomCode();
      if (name === 'leaveRoom') leaveOnline(true);
      if (name === 'resetStats') resetStats();
      if (name === 'hint') hint();
      if (name === 'flip') flip();
      if (name === 'resign') resign();
      if (name === 'again') { hideDialog('dlgResult'); startGame({ silent: true }); }
      if (name === 'review') { hideDialog('dlgResult'); openReplay(); }
      if (name === 'export') exportGame();
      if (name === 'snapshot') exportSnapshot();
      if (name === 'import') $('#fileInput').click();
      if (name === 'resetSettings') resetSettings();
      if (name === 'menu') $('.topnav').classList.toggle('open');
    }
    if (!event.target.closest('.topnav') && !event.target.closest('.nav-toggle')) {
      $('.topnav').classList.remove('open');
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.target.matches('input, select, textarea')) return;
    const key = event.key.toLowerCase();
    if (key === 'escape') {
      if (app.replay.open) closeReplay();
      return;
    }
    if (event.ctrlKey || event.metaKey) {
      if (key === 'z') { event.preventDefault(); undo(); }
      return;
    }
    if (document.querySelector('dialog[open]')) return;
    if (key === ' ') { event.preventDefault(); togglePause(); return; }
    if (key === 'm') {
      app.prefs.sound = !app.prefs.sound;
      sound.setSoundEnabled(app.prefs.sound);
      savePrefs();
      toast(t('settings.sound'));
      return;
    }
    if (key === '\\') { toggleSide(); return; }
    if (key === 'f') flip();
    if (key === 'h') hint();
    if (key === 'r') openReplay();
    if (key === 'n') { syncNewDialog(); showDialog('dlgNew'); }
  });
}

function syncSettings() {
  $$('#dlgSettings .segmented').forEach((group) => {
    const map = { pieceStyle: app.prefs.pieceStyle, language: app.prefs.language };
    const value = map[group.dataset.group];
    if (value === undefined) return;
    [...group.children].forEach((node) => node.classList.toggle('on', node.dataset.value === value));
  });
  $$('#themeSwatches .swatch').forEach((node) => {
    node.classList.toggle('on', node.dataset.theme === app.prefs.theme);
  });
  $('#optAnimation').checked = app.prefs.animation;
  $('#optLegal').checked = app.prefs.legal;
  $('#optCapture').checked = app.prefs.captureHint;
  $('#optSound').checked = app.prefs.sound;
  const vol = $('#optVolume');
  if (vol) vol.value = String(Math.round((app.prefs.volume ?? 0.55) * 100));
  const music = $('#optMusic');
  if (music) music.checked = Boolean(app.prefs.music);
  const musicVol = $('#optMusicVolume');
  if (musicVol) musicVol.value = String(Math.round((app.prefs.musicVolume ?? 0.35) * 100));
  buildRuleList();
}

function resetSettings() {
  app.prefs = { ...DEFAULT_PREFS, options: {} };
  sound.setSoundEnabled(app.prefs.sound !== false);
  sound.setVolume(app.prefs.volume ?? 0.55);
  sound.setMusicVolume(app.prefs.musicVolume ?? 0.35);
  sound.setMusicEnabled(Boolean(app.prefs.music));
  setLanguage(app.prefs.language);
  savePrefs();
  syncSettings();
  buildThemeSwatches();
  refreshTexts();
  toast(t('settings.reset'));
}

function exportGame() {
  if (!app.game) return;
  const document_ = gameToDocument(app.game);
  const blob = new Blob([JSON.stringify(document_, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `xionghan_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.xhgame`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  toast(t('toast.exported'));
}

/** 把当前局面渲染成一张带落款的图片，便于分享。 */
function exportSnapshot() {
  if (!app.game) return;
  const source = $('#board');
  const pad = Math.round(source.width * 0.07);
  const footer = Math.round(source.width * 0.13);
  const out = document.createElement('canvas');
  out.width = source.width + pad * 2;
  out.height = source.height + pad * 2 + footer;
  const ctx = out.getContext('2d');
  const scale = out.width / 1000;

  const bg = ctx.createLinearGradient(0, 0, out.width, out.height);
  bg.addColorStop(0, '#fbf6ec');
  bg.addColorStop(1, '#efe4d0');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, out.width, out.height);
  ctx.drawImage(source, pad, pad);

  const state = app.game.state;
  const title = `匈汉象棋 · ${t(`profile.${app.game.profile.id}`)}`;
  const line = state.history.length
    ? `${t('panel.total', { n: state.history.length })} · ${t(`side.${state.turn}`)}`
    : t('app.tagline');

  ctx.fillStyle = '#2b2620';
  ctx.textBaseline = 'middle';
  ctx.font = `600 ${Math.round(26 * scale)}px "Songti SC","Noto Serif SC",serif`;
  ctx.fillText(title, pad, pad + source.height + footer * 0.34);

  ctx.fillStyle = '#8a7c68';
  ctx.font = `400 ${Math.round(15 * scale)}px "PingFang SC","Microsoft YaHei",sans-serif`;
  ctx.fillText(line, pad, pad + source.height + footer * 0.68);

  ctx.textAlign = 'right';
  ctx.fillStyle = '#9c2b22';
  ctx.font = `600 ${Math.round(15 * scale)}px "PingFang SC","Microsoft YaHei",sans-serif`;
  ctx.fillText('十三路 · 长城阴山', out.width - pad, pad + source.height + footer * 0.52);

  const link = document.createElement('a');
  link.href = out.toDataURL('image/png');
  link.download = `xionghan_${new Date().toISOString().slice(0, 10)}.png`;
  document.body.append(link);
  link.click();
  link.remove();
  toast(t('toast.image'));
}

/* ---------------------------------------------------------------- 棋盘交互 */

function bindBoard() {
  const canvas = $('#board');
  let down = null;

  canvas.addEventListener('pointerdown', (event) => {
    down = { x: event.clientX, y: event.clientY };
  });

  canvas.addEventListener('pointerup', (event) => {
    if (!app.game) return;
    const point = board.hitTest(event.clientX, event.clientY, { flipped: app.flipped });
    if (!point) { down = null; return; }
    const dragged = down && Math.hypot(event.clientX - down.x, event.clientY - down.y) > 8;
    down = null;
    if (dragged) {
      const piece = app.game.state.pieces.find((p) => p.row === point.row && p.col === point.col);
      if (piece && isHumanTurn() && piece.color === app.game.state.turn) {
        selectPiece(piece);
        return;
      }
    }
    handleSquare(point);
  });

  canvas.addEventListener('contextmenu', (event) => event.preventDefault());
}

/* ---------------------------------------------------------------- 图谱 */

function buildAtlasPieces() {
  const root = $('#atlasPieces');
  root.innerHTML = '';
  const types = Object.keys(RED_NAMES);
  for (const type of types) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.type = type;
    const glyph = document.createElement('span');
    glyph.className = 'glyph';
    glyph.textContent = RED_NAMES[type];
    const label = document.createElement('span');
    label.textContent = PIECE_INFO[type]?.name.split(' / ')[0] || type;
    button.append(glyph, label);
    button.onclick = () => {
      app.atlasType = type;
      [...root.children].forEach((node) => node.classList.toggle('on', node === button));
      drawAtlas();
    };
    root.append(button);
  }
}

function atlasDemoState(type) {
  const profile = getProfile('desktop_complete');
  const options = { ...profile.options };
  // 演示点位要能体现该棋子的规则特征：射必须在星轨上，巡必须在巡界线上
  const spots = {
    king: [10, 6],
    advisor: [10, 5],
    elephant: [8, 2],
    pawn: [8, 4],
    patrol: [5, 6],
    archer: [9, 3],
  };
  const [row, col] = spots[type] || [7, 6];
  // 两个主帅分开放，避免「将帅照面」把演示局面的合法性全部封死
  const pieces = [makePiece('king', 'black', 1, 3)];
  if (type !== 'king') pieces.push(makePiece('king', 'red', 11, 6));
  pieces.push(makePiece(type, 'red', row, col));
  const state = createState(profile.id, pieces, 'red');
  state.clocksMs = { red: 0, black: 0 };
  return state;
}

function drawAtlas() {
  if (!app.atlasType) return;
  const type = app.atlasType;
  const profile = getProfile('desktop_complete');
  const options = { ...profile.options };
  const state = atlasDemoState(type);
  const engine = new RulesEngine(profile, options);
  const from = { row: state.pieces.at(-1).row, col: state.pieces.at(-1).col };
  const legal = engine.legalMoves(state).filter(
    (m) => m.source.row === from.row && m.source.col === from.col,
  );

  const cssSize = Math.min(420, $('#atlasCanvas').parentElement.clientWidth || 420);
  atlasBoard.resize(cssSize, profile.rows, profile.cols);
  atlasBoard.draw({
    state,
    profile: { ...profile, archerStarPoints: engine.archerStarPoints },
    selected: from,
    legal: legal.map((m) => m.target),
    flipped: false,
    theme: app.prefs.theme,
    pieceStyle: app.prefs.pieceStyle,
    lastMove: null,
    checkSide: null,
    anim: null,
    showCoordinates: false,
    showMarks: false,
  });

  const info = PIECE_INFO[type];
  $('#atlasName').textContent = info?.name || type;
  $('#atlasDesc').textContent = getLanguage() === 'en' ? info?.en : info?.desc;
  $('#atlasCount').textContent = t('atlas.moves', { n: legal.length });
}

/* ---------------------------------------------------------------- 尺寸 */

const PAD_RATIO = 0.062;

/** 对局是否已结束（state 可能是回放快照，没有 finished getter）。 */
const isOver = (state) => Boolean(state && (state.winner || state.draw));

/** 在给定可用空间内，按棋盘行列比算出最大宽度。 */
function fitWidth(rows, cols, maxWidth, maxHeight) {
  const ratio = ((rows - 1) + PAD_RATIO * 2) / ((cols - 1) + PAD_RATIO * 2);
  return Math.max(180, Math.floor(Math.min(maxWidth, maxHeight / ratio)));
}

function resizeAll() {
  const holder = $('#boardHolder');
  if (!holder || !app.game) return;
  const rect = holder.getBoundingClientRect();
  const narrow = window.innerWidth <= 980;
  const reserved = 26; // 顶部回合徽标预留
  const { rows, cols } = app.game.profile;
  const width = fitWidth(
    rows,
    cols,
    rect.width,
    narrow ? window.innerHeight - 248 : rect.height - reserved,
  );
  board.resize(width, rows, cols);
  document.documentElement.style.setProperty('--board-size', `${width}px`);
  render();
  if (app.replay.open) resizeReplay();
  if (app.atlasType) drawAtlas();
}

function resizeReplay() {
  const canvas = $('#replayCanvas');
  const parent = canvas.parentElement;
  const { rows, cols } = app.game.profile;
  // 右侧还有 230px 的复盘面板 + 间距，必须从可用宽度里扣掉，否则棋盘会盖住面板
  const available = Math.max(240, (parent.clientWidth || 520) - 250);
  const width = fitWidth(rows, cols, available, Math.floor(window.innerHeight * 0.58));
  replayBoard.resize(width, rows, cols);
  drawReplay();
}

/* ---------------------------------------------------------------- 启动 */

boot();

// 便于自动化验证与问题排查（不影响正常使用）
window.__xh = app;
