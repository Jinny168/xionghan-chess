/**
 * 匈汉象棋联机后端。
 *
 * 用 HTTP 长轮询而不是 WebSocket：发布平台的代理对 upgrade 支持不确定，
 * 而象棋这类回合制对局对延迟不敏感，轮询足够且更稳。
 *
 * 规则校验复用与前端完全相同的内核（./core），服务端权威。
 */

import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Game } from './core/game.js';
import { stateToDict } from './core/model.js';

const PORT = Number(process.env.PORT || 3000);
const PUBLIC = path.join(path.dirname(fileURLToPath(import.meta.url)), 'public');
const CLOUD_CONFIG = path.join(path.dirname(fileURLToPath(import.meta.url)), 'cloud-config.json');

// 把云服务配置注入页面：publicConfig 由服务端持有，前端不硬编码 endpoint
let cloudScript = '';
try {
  const cfg = JSON.parse(await readFile(CLOUD_CONFIG, 'utf8'));
  cloudScript = `<script>window.__CLOUD_CONFIG__ = ${JSON.stringify(cfg)};</script>`;
} catch {
  cloudScript = '';
}
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.webmanifest': 'application/manifest+json',
};
const ROOM_TTL = 2 * 60 * 60 * 1000;
const POLL_TIMEOUT = 20000;

const rooms = new Map();

function makeCode() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  for (let attempt = 0; attempt < 50; attempt += 1) {
    let code = '';
    for (let i = 0; i < 4; i += 1) code += alphabet[Math.floor(Math.random() * alphabet.length)];
    if (!rooms.has(code)) return code;
  }
  return `X${Date.now().toString(36).slice(-3).toUpperCase()}`;
}

function snapshot(room) {
  const game = room.game;
  return {
    code: room.code,
    ply: game.state.history.length,
    turn: game.state.turn,
    finished: game.finished,
    winner: game.state.winner,
    draw: Boolean(game.state.draw),
    reason: game.state.resultReason,
    players: { red: Boolean(room.red), black: Boolean(room.black) },
    state: stateToDict(game.state),
  };
}

function waiters(room) {
  if (!room.waiters) room.waiters = [];
  return room.waiters;
}

function notify(room) {
  const list = waiters(room);
  room.waiters = [];
  for (const resolve of list) resolve();
}

function createRoom(profileId) {
  const code = makeCode();
  const game = new Game(profileId || 'desktop_complete', null, { initialMinutes: 0 });
  game.state.clocksMs = { red: 0, black: 0 };
  const room = { code, game, red: null, black: null, createdAt: Date.now(), lastActive: Date.now(), waiters: [] };
  rooms.set(code, room);
  return room;
}

function cleanup() {
  const now = Date.now();
  for (const [code, room] of rooms) {
    if (now - room.lastActive > ROOM_TTL) rooms.delete(code);
  }
}

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'access-control-allow-origin': '*',
    'access-control-allow-headers': 'content-type',
    'access-control-allow-methods': 'GET,POST,OPTIONS',
    'cache-control': 'no-store',
    'content-length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

async function readBody(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 64 * 1024) throw new Error('body too large');
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    return {};
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = url.pathname;

  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'access-control-allow-origin': '*',
      'access-control-allow-headers': 'content-type',
      'access-control-allow-methods': 'GET,POST,OPTIONS',
    });
    res.end();
    return;
  }

  try {
    if (pathname === '/healthz') {
      res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
      res.end('ok');
      return;
    }

    if (pathname === '/health' || pathname === '/api/health') {
      json(res, 200, { ok: true, service: 'xionghan-online', rooms: rooms.size, uptime: Math.round(process.uptime()) });
      return;
    }

    if (pathname === '/api/room' && req.method === 'POST') {
      const body = await readBody(req);
      const room = createRoom(body.profileId);
      room.red = body.clientId || 'red';
      json(res, 200, { code: room.code, color: 'red', ...snapshot(room) });
      return;
    }

    if (pathname === '/api/join' && req.method === 'POST') {
      const body = await readBody(req);
      const room = rooms.get(String(body.code || '').toUpperCase());
      if (!room) { json(res, 404, { error: 'room-not-found' }); return; }
      if (room.black) { json(res, 409, { error: 'room-full' }); return; }
      room.black = body.clientId || 'black';
      room.lastActive = Date.now();
      notify(room);
      json(res, 200, { code: room.code, color: 'black', ...snapshot(room) });
      return;
    }

    if (pathname === '/api/state' && req.method === 'GET') {
      const code = String(url.searchParams.get('code') || '').toUpperCase();
      const since = Number(url.searchParams.get('since') || -1);
      const room = rooms.get(code);
      if (!room) { json(res, 404, { error: 'room-not-found' }); return; }
      room.lastActive = Date.now();
      if (room.game.state.history.length === since) {
        await new Promise((resolve) => {
          const timer = setTimeout(resolve, POLL_TIMEOUT);
          waiters(room).push(() => { clearTimeout(timer); resolve(); });
        });
        if (!rooms.has(code)) { json(res, 410, { error: 'room-closed' }); return; }
      }
      json(res, 200, snapshot(room));
      return;
    }

    if (pathname === '/api/move' && req.method === 'POST') {
      const body = await readBody(req);
      const room = rooms.get(String(body.code || '').toUpperCase());
      if (!room) { json(res, 404, { error: 'room-not-found' }); return; }
      if (room.game.finished) { json(res, 409, { error: 'game-over' }); return; }
      if (room.game.state.turn !== body.color) { json(res, 409, { error: 'not-your-turn' }); return; }
      try {
        room.game.move({
          source: body.move.from,
          target: body.move.to,
          promotion: body.move.promotion || null,
        });
      } catch (error) {
        json(res, 400, { error: 'illegal-move', detail: String(error && error.message || error) });
        return;
      }
      room.lastActive = Date.now();
      notify(room);
      json(res, 200, snapshot(room));
      return;
    }

    if (pathname === '/api/resign' && req.method === 'POST') {
      const body = await readBody(req);
      const room = rooms.get(String(body.code || '').toUpperCase());
      if (!room) { json(res, 404, { error: 'room-not-found' }); return; }
      if (!room.game.finished) room.game.resign(body.color);
      room.lastActive = Date.now();
      notify(room);
      json(res, 200, snapshot(room));
      return;
    }

    // 静态资源：单文件应用 + 脱敏记录页
    if (req.method === 'GET' || req.method === 'HEAD') {
      const target = pathname === '/' ? '/index.html' : pathname;
      const rel = path.normalize(decodeURIComponent(target)).replace(/^([/\\])+/, '');
      if (rel.startsWith('..')) { json(res, 403, { error: 'forbidden' }); return; }
      const file = path.join(PUBLIC, rel);
      try {
        let body = await readFile(file);
        if (cloudScript && rel.endsWith('index.html')) {
          const html = body.toString('utf8').replace('</head>', `${cloudScript}</head>`);
          body = Buffer.from(html, 'utf8');
        }
        res.writeHead(200, {
          'content-type': MIME[path.extname(file)] || 'application/octet-stream',
          'cache-control': 'no-cache',
          'content-length': body.length,
        });
        res.end(req.method === 'HEAD' ? undefined : body);
        return;
      } catch {
        json(res, 404, { error: 'not-found' });
        return;
      }
    }

    json(res, 404, { error: 'not-found' });
  } catch (error) {
    json(res, 500, { error: 'server-error', detail: String(error && error.message || error) });
  }
});

process.on('uncaughtException', (error) => {
  console.error('[fatal] uncaught', error && error.stack || error);
});
process.on('unhandledRejection', (error) => {
  console.error('[fatal] rejection', error && error.stack || error);
});

server.on('error', (error) => {
  console.error('[fatal] listen failed', error && error.message || error);
  process.exit(1);
});

setInterval(cleanup, 10 * 60 * 1000);

server.listen(PORT, '0.0.0.0', () => {
  const info = server.address();
  console.log(`xionghan-online pid=${process.pid} listening on ${info && info.address}:${info && info.port} public=${PUBLIC}`);
});
