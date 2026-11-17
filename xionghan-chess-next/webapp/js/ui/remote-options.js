/**
 * 联机规则取源（纯函数）——房间权威 options > 快照 options > 档案默认。
 *
 * 背景：webapp 联机走 Node HTTP 长轮询，online/server.mjs::snapshot() 不下发
 * options；房间由 createRoom() 按档案默认 options 创建。本机 app.prefs.options
 * 只用于单机/人机/残局/读档，绝不参与联机呈现，否则合法着法高亮、胜负预判、
 * 复活按钮显隐会与房间规则分叉。
 *
 * 三段优先级集中于此：将来服务端若开始下发 options，只需让 data 带上即可，
 * 前端调用点无需再改。
 */

import { mergeOptions } from '../core/profiles.js';

export function resolveRemoteOptions(data, profile) {
  const roomOptions = data?.state?.options ?? data?.options ?? null;
  return mergeOptions(profile.options, roomOptions);
}
