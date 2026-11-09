'use strict';

// Test adapter for the Android offline engine. It evaluates the exact Rules
// implementation shipped in offline.js, stopping before browser UI startup.
const fs = require('fs');
const vm = require('vm');

const sourcePath = process.argv[2];
const source = fs.readFileSync(sourcePath, 'utf8');
const start = source.indexOf("const TYPES=");
const end = source.indexOf("const canvas=");
if (start < 0 || end < 0) throw new Error('offline rules markers not found');
// `tr` lives above the slice, so the engine layer needs its own stub for any
// message OfflineGame builds (resurrect notation included).
const rulesSource = "const opposite=c=>c==='red'?'black':'red',pos=(row,col)=>({row,col}),tr=key=>key;\n" +
  source.slice(start, end) +
  '\n;globalThis.__offline={Rules,PROFILES,OfflineGame,gameFromDocument};';
const context = {console, performance};
vm.createContext(context);
vm.runInContext(rulesSource, context);

const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const profile = context.__offline.PROFILES.get(request.profileId);
if (!profile) throw new Error(`unknown profile: ${request.profileId}`);
const options = {...profile.options, ...(request.options || {})};
const rules = new context.__offline.Rules(profile, options);
const state = request.state;
const moves = rules.legalAll(state).map(move => ({
  from: move.from,
  to: move.to,
  promotion: move.promotion || null,
}));
// `checkFor` lets a caller ask about the side that is not on the move. Without
// it a side that has no king on the board always reads as "in check", which is
// true but useless for comparing against a specific `RulesEngine` verdict.
const result = {moves, check: rules.inCheck(state, request.checkFor || state.turn)};

// Optional legs so a Python game can be compared against the offline engine on
// more than legal moves and check. `checkmate`/`stalemate` have no JS twin, so
// they are composed from `inCheck` plus `legalAll`, which is exactly how the
// Python RulesEngine defines them (`rules.py:checkmate` / `stalemate`).
if (request.capturedByMove) {
  const {from, to, promotion} = request.capturedByMove;
  const move = {from, to, promotion: promotion || null};
  result.capturedByMove = rules.capturedByMove(state, move).map(piece => ({
    type: piece.type,
    color: piece.color,
  }));
}
// Capture-spec leg: `targets` (optional) is the point-query list of victim
// squares; without it the whole board is enumerated. The returned array is
// keyed by victim square and already carries each removal's `kind`, so the
// Python side compares victim set *and* capture kind, not just who died.
if (request.capturableSquares) {
  const {color, targets} = request.capturableSquares;
  const queried = targets ? targets.map(item => ({row: item.row, col: item.col})) : null;
  result.capturableSquares = rules.capturableSquares(state, color, queried);
}
// Position-key leg: the repetition key must be byte-identical on both engines,
// else the Python and offline ledgers split (方案 A folded the capture pool in).
if (request.positionKey) {
  result.positionKey = rules.positionKey(state);
}
if (request.checkmate !== undefined || request.stalemate !== undefined) {
  const moves = rules.legalAll(state, state.turn);
  if (request.checkmate !== undefined) {
    result.checkmate = rules.inCheck(state, state.turn) && moves.length === 0;
  }
  if (request.stalemate !== undefined) {
    result.stalemate = !rules.inCheck(state, state.turn) && moves.length === 0;
  }
}

// Optional resurrection leg: replays the same payload through OfflineGame so a
// Python Game can be compared against it on the same board change. The payload
// already carries Python's `positionCounts`, so only the resurrection's own +1
// is applied -- seeding an extra count here would diverge from
// Game.move(), which counts the resulting position exactly once.
if (request.resurrect) {
  const {color, row, col} = request.resurrect;
  const game = new context.__offline.OfflineGame(request.profileId);
  game.options = {...profile.options, ...(request.options || {})};
  game.rules = new context.__offline.Rules(game.profile, game.options);
  game.state = JSON.parse(JSON.stringify(state));
  try {
    game.resurrectPawn(color, {row, col});
    // publicState() already flattens the live state on top.
    result.resurrect = {ok: true, state: game.publicState(), error: null};
  } catch (error) {
    result.resurrect = {ok: false, state: null, error: error.message};
  }
}

// Document-load leg: runs the DOM-free core of `loadGameDocument`
// (`gameFromDocument`) so the repetition-ledger rebuild can be checked without a
// browser. `thenPlay` replays moves after the load to observe the threefold
// verdict, which is the very thing a re-derived ledger has to preserve.
if (request.loadDocument !== undefined) {
  const payload = request.loadDocument;
  try {
    const game = context.__offline.gameFromDocument(payload.document, payload.initialMinutes || 20);
    // Snapshot the ledger right after the load: `recordPosition` mutates
    // `positionCounts` in place, so a later replay would rewrite this reference.
    const leg = {ok: true, error: null,
                 loadedPositionCounts: JSON.parse(JSON.stringify(game.state.positionCounts))};
    if (payload.thenPlay) {
      for (const move of payload.thenPlay) {
        game.move({from: move.from, to: move.to, promotion: move.promotion || null});
      }
      leg.draw = game.state.draw;
      leg.resultReason = game.state.resultReason;
      leg.positionCounts = game.state.positionCounts;
    }
    result.loadDocument = leg;
  } catch (error) {
    result.loadDocument = {ok: false, error: error.message, positionCounts: null};
  }
}

// Settlement leg: plays ONE move through `OfflineGame.move()` and reports the
// verdict it settles on. `Rules.legalAll` has no repetition notion -- the draw
// lives in `OfflineGame.settle()`, which is the code this leg pins. The caller
// sends the pre-move state (Python's, ledger included), so a verdict difference
// here is a *rule* difference, not a bookkeeping one.
if (request.playMove) {
  const game = new context.__offline.OfflineGame(request.profileId);
  game.options = {...profile.options, ...(request.options || {})};
  game.rules = new context.__offline.Rules(game.profile, game.options);
  game.state = JSON.parse(JSON.stringify(state));
  // `_offline_state` (the Python helper every leg shares) deliberately drops the
  // clocks -- the `Rules` legs never tick. This leg drives `OfflineGame.move()`,
  // which calls `tick()` and therefore needs `state.clocksMs`. Give it the same
  // 20-minute default `new OfflineGame()` would have used, so the settlement
  // verdict is never a timeout.
  game.state.clocksMs = game.state.clocksMs || {red: 20 * 60000, black: 20 * 60000};
  const {from, to, promotion} = request.playMove;
  try {
    game.move({from, to, promotion: promotion || null});
    // `null`-normalise: the payload's state (via `_offline_state`) carries no
    // `resultReason`/`winner`, so the fields arrive `undefined` and
    // `JSON.stringify` would drop the keys entirely -- a missing key and a
    // `null` verdict are different things to the caller.
    result.playMove = {ok: true, error: null,
                       draw: game.state.draw,
                       winner: game.state.winner ?? null,
                       resultReason: game.state.resultReason ?? null,
                       pieceCount: game.state.pieces.length,
                       positionCounts: game.state.positionCounts};
  } catch (error) {
    result.playMove = {ok: false, error: error.message, draw: null, winner: null,
                       resultReason: null, pieceCount: null, positionCounts: null};
  }
}

// Native-opening leg: reports the board `new OfflineGame(profileId)` builds BY
// ITSELF -- not the board the payload carries. Every other leg overwrites
// `game.state` with Python's pieces, so the JS-side roster (`side()` /
// `PROFILES` / `DEFAULT_OPTIONS`) has never been compared against
// `profiles.py`. That blind spot is why the 2026-10-31 guard/advisor swap in
// `profiles.py` shipped with `offline.js` untouched and all 81 parity cases
// stayed green. `perft1` is `legalAll().length` (perft at depth 1).
if (request.nativeOpening) {
  const game = new context.__offline.OfflineGame(request.profileId);
  const state = game.state;
  result.nativeOpening = {
    profileId: game.profile.id,
    rows: game.profile.rows,
    cols: game.profile.cols,
    pieces: state.pieces.map(p => ({type: p.type, color: p.color, row: p.row, col: p.col})),
    options: game.options,
    perft1: game.rules.legalAll(state).length,
  };
}

process.stdout.write(JSON.stringify(result));
