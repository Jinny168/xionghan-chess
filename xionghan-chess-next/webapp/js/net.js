/**
 * 联机对战客户端：HTTP 长轮询。
 *
 * 与后端同源时用相对路径；本地调试可用 ?online=http://127.0.0.1:8131 指定测试服。
 * 服务端权威：走子由后端校验，前端只负责把结果状态渲染出来。
 */

const params = new URLSearchParams(location.search);
export const BASE = (params.get('online') || '').replace(/\/$/, '');

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'content-type': 'application/json' },
    ...options,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const error = new Error((data && data.error) || `http-${res.status}`);
    error.payload = data;
    error.status = res.status;
    throw error;
  }
  return data;
}

export function createRoom(profileId) {
  return request('/api/room', { method: 'POST', body: JSON.stringify({ profileId }) });
}

export function joinRoom(code) {
  return request('/api/join', { method: 'POST', body: JSON.stringify({ code }) });
}

export function fetchState(code, since) {
  return request(`/api/state?code=${encodeURIComponent(code)}&since=${since}`);
}

export function sendMove(code, color, move) {
  return request('/api/move', {
    method: 'POST',
    body: JSON.stringify({
      code,
      color,
      move: { from: move.source, to: move.target, promotion: move.promotion || null },
    }),
  });
}

export function sendResign(code, color) {
  return request('/api/resign', { method: 'POST', body: JSON.stringify({ code, color }) });
}
