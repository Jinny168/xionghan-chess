/**
 * bundle 内嵌引擎的 vm 静态求值工具（T14 / T15 共用）。
 *
 * 单文件 HTML 里有**两份**规则引擎快照：
 *   1. `var __WORKER_SRC = "...";` 里的转义串（AI Worker 副本）
 *   2. 主 inline script 里的 `__mods["js/core/rules.js"] = (function(){...})();`
 * 只更新一份时，按全文计数 ≥1 会假绿，故两份都必须能 vm 求值并跑通 W-01。
 *
 * 为什么需要 vm：`build_webapp_bundle.py --check` 的「重算结果 == 磁盘文件」是
 * 充分判据（严过关 M32 实测脚本无 Date/random/uuid/time/performance），但静态
 * 计数替代不了「这份引擎真的能算出三连吃子」。这里把两份快照都装进 vm context
 * 求值，拿真正的 `RulesEngine` 跑一遍 W-01。
 */

import vm from 'node:vm';
import { readFileSync } from 'node:fs';

/** 最小 document/window stub：让剩余的 UI 模块也能求值（严过关 M26 实测）。 */
function makeSandbox() {
  const noop = () => undefined;
  const elementStub = new Proxy({}, {
    get(_t, prop) {
      if (prop === 'style' || prop === 'dataset' || prop === 'classList' || prop === 'children') {
        return new Proxy({}, { get: () => noop, set: () => true });
      }
      if (prop === 'getContext') return () => new Proxy({}, { get: () => noop, set: () => true });
      if (prop === 'addEventListener' || prop === 'removeEventListener'
        || prop === 'appendChild' || prop === 'setAttribute' || prop === 'remove'
        || prop === 'querySelector' || prop === 'querySelectorAll' || prop === 'click'
        || prop === 'focus' || prop === 'getBoundingClientRect') {
        return prop === 'querySelectorAll' ? () => [] : noop;
      }
      if (prop === 'then') return undefined; // 别被当 Promise thenable
      return noop;
    },
    set: () => true,
  });
  const storage = {
    getItem: () => null, setItem: noop, removeItem: noop, clear: noop,
  };
  const doc = new Proxy({}, {
    get(_t, prop) {
      if (prop === 'getElementById' || prop === 'querySelector') return () => elementStub;
      if (prop === 'querySelectorAll') return () => [];
      if (prop === 'createElement') return () => elementStub;
      if (prop === 'addEventListener' || prop === 'removeEventListener') return noop;
      if (prop === 'body' || prop === 'documentElement' || prop === 'head') return elementStub;
      if (prop === 'hidden' || prop === 'visibilityState') return 'visible';
      if (prop === 'then') return undefined;
      return noop;
    },
    set: () => true,
  });
  const sandbox = {
    console,
    performance: { now: () => 0 },
    setTimeout: noop, clearTimeout: noop, setInterval: noop, clearInterval: noop,
    requestAnimationFrame: noop, cancelAnimationFrame: noop,
    URLSearchParams,
    localStorage: storage, sessionStorage: storage,
    document: doc,
    navigator: { language: 'zh-CN', userAgent: 'node' },
    location: { search: '', href: 'http://localhost/', hash: '' },
    history: { pushState: noop, replaceState: noop },
    addEventListener: noop, removeEventListener: noop,
    matchMedia: () => ({ matches: false, addEventListener: noop }),
    ResizeObserver: class { observe() {} unobserve() {} disconnect() {} },
    IntersectionObserver: class { observe() {} unobserve() {} disconnect() {} },
    Audio: class { constructor() {} play() { return Promise.resolve(); } },
    Image: class { constructor() {} },
    Blob: class { constructor() {} },
    URL: { createObjectURL: () => 'blob:stub', revokeObjectURL: noop },
    Worker: class { constructor() {} postMessage() {} },
    fetch: () => Promise.resolve({ ok: false, json: () => Promise.resolve({}) }),
    alert: noop, confirm: () => false, prompt: () => null,
    __mods: {},
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;
  return sandbox;
}

/** 取 `var __WORKER_SRC = ("...");` 并 JSON.parse 解码成 Worker 源码。 */
export function workerSource(html) {
  const match = html.match(/var __WORKER_SRC = ("(?:[^"\\]|\\.)*");/);
  if (!match) return null;
  try {
    return JSON.parse(match[1]);
  } catch {
    return null;
  }
}

/** 按序切出 `__mods["x"] = (function () {...})();` 块（bundle 的 chunk 用 \n\n 连接）。 */
export function moduleBlocks(source) {
  return source.match(/__mods\["[^"]+"\] = \(function \(\) \{[\s\S]*?\n\}\)\(\);/g) || [];
}

/** 取内嵌规则引擎快照文本（用于标记计数，不按全文计）。 */
export function rulesSnapshots(html) {
  const main = html.match(/__mods\["js\/core\/rules\.js"\] = \(function \(\) \{[\s\S]*?\n\}\)\(\);/g) || [];
  const worker = workerSource(html);
  const workerBlocks = worker
    ? (worker.match(/__mods\["js\/core\/rules\.js"\] = \(function \(\) \{[\s\S]*?\n\}\)\(\);/g) || [])
    : [];
  return { main, worker: workerBlocks, all: [...main, ...workerBlocks] };
}

/** 把一份源码里的所有模块块按序求值，返回 { mods, evaluated, failed }。 */
export function evaluateInto(source, ctx) {
  const blocks = moduleBlocks(source);
  let evaluated = 0;
  let failed = 0;
  for (const block of blocks) {
    try {
      vm.runInContext(block, ctx, { timeout: 5000 });
      evaluated += 1;
    } catch {
      failed += 1; // UI 模块可能仍因 DOM stub 不全而失败；核心模块先求值即可
    }
  }
  return { mods: ctx.__mods, evaluated, failed, total: blocks.length };
}

/**
 * 从 bundle HTML 装出两份引擎：
 *   - WORKER_SRC：解码后求值（含 `var __mods = {};` 前缀，需重置为独立对象）
 *   - 主 inline：按序求值全部模块块
 */
export function loadEngines(html) {
  const worker = workerSource(html);
  if (worker === null) return { worker: null, main: null, error: 'WORKER_SRC 缺失或解码失败' };

  const workerCtx = vm.createContext(makeSandbox());
  const workerResult = evaluateInto(worker, workerCtx);

  const mainCtx = vm.createContext(makeSandbox());
  const mainResult = evaluateInto(html, mainCtx);

  return {
    worker: {
      mods: workerResult.mods, evaluated: workerResult.evaluated,
      failed: workerResult.failed, total: workerResult.total,
      engine: workerResult.mods['js/core/rules.js']?.RulesEngine ?? null,
    },
    main: {
      mods: mainResult.mods, evaluated: mainResult.evaluated,
      failed: mainResult.failed, total: mainResult.total,
      engine: mainResult.mods['js/core/rules.js']?.RulesEngine ?? null,
    },
    error: null,
  };
}

/** W-01 的稀疏局面（固定双王省略；每子唯一 id；turn='red'）。 */
export function w01Case(mods, options) {
  const model = mods['js/core/model.js'];
  const Engine = mods['js/core/rules.js']?.RulesEngine;
  const profiles = mods['js/core/profiles.js'];
  if (!model || !Engine || !profiles) return null;
  const pieces = [
    model.makePiece('king', 'red', 12, 0, 'w01:rk'),
    model.makePiece('king', 'black', 0, 12, 'w01:bk'),
    model.makePiece('pawn', 'red', 6, 4, 'w01:p1'),
    model.makePiece('pawn', 'red', 5, 5, 'w01:p2'),
    model.makePiece('advisor', 'black', 5, 6, 'w01:a1'),
  ];
  const state = model.createState('web', pieces, 'red');
  const move = {
    source: { row: 6, col: 4 }, target: { row: 5, col: 4 }, promotion: null,
  };
  const profile = profiles.getProfile('web');
  const merged = profiles.mergeOptions(profile.options, {
    ...options,
    pawn_three_line_capture: true,
  });
  const engine = new Engine(profile, merged);
  const hasThreeLine = typeof Engine.prototype.threeLineCaptures === 'function';
  // 旧引擎没有 boardRemovals / threeLineCaptures：用 applyUnchecked 的 before/after
  // id 差集兜底，让 T15 能给出「removals=[]」的红灯明细而不是抛 TypeError。
  const boardRemovals = typeof engine.boardRemovals === 'function'
    ? engine.boardRemovals(state, move)
    : (() => {
      const next = engine.applyUnchecked(state, move, false);
      const afterIds = new Set(next.pieces.map((p) => p.id));
      return state.pieces.filter((p) => !afterIds.has(p.id));
    })();
  const removed = boardRemovals.map((p) => [p.type, p.color, p.row, p.col])
    .sort((a, b) => {
      for (let i = 0; i < 4; i += 1) {
        if (a[i] < b[i]) return -1;
        if (a[i] > b[i]) return 1;
      }
      return 0;
    });
  const pseudo = engine.pseudoLegal(state, move) === true;
  return { engine, state, move, removed, pseudo, hasThreeLine };
}

export function readHtml(absolutePath) {
  return readFileSync(absolutePath, 'utf8');
}
