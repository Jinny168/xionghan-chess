#!/usr/bin/env node
/**
 * M5 · 联机 options 取源真断言（node 原生，无新增依赖）。
 *
 * 测的是纯函数 resolveRemoteOptions(data, profile) 本身：签名只接 (data, profile)，
 * "本机偏好"在测试上下文里体现为**不传入**——结果只取决于房间快照与档案，
 * 与任何全局 prefs 无关。快照缺 options 时回退档案默认，等价于房间
 * createRoom() 用档案默认 options 建局，因此服务端无需下发 options 也已一致。
 *
 * 运行：node webapp/tests/verify-online-options.mjs
 */

import assert from 'node:assert/strict';

import { getProfile } from '../js/core/profiles.js';
import { resolveRemoteOptions } from '../js/ui/remote-options.js';

// T1：房间 state.options 明确关掉两个开关，结果逐键等于房间值（不被本机偏好污染）。
{
  const profile = getProfile('desktop_complete'); // 档案默认这两键都是 true
  const data = { state: { options: { invasion_victory: false, pawn_resurrection: false } } };
  const options = resolveRemoteOptions(data, profile);
  assert.equal(resolveRemoteOptions.length, 2, '纯函数签名应严格是 (data, profile)');
  assert.equal(options.invasion_victory, false, 'T1: invasion_victory 必须取房间值');
  assert.equal(options.pawn_resurrection, false, 'T1: pawn_resurrection 必须取房间值');
  console.log('T1 PASS 房间 options 覆盖档案默认，无本机偏好通道');
}

// T2：state.options 与 data.options 均缺 → 回退档案默认（= 房间建局口径）。
{
  const profile = getProfile('desktop_complete');
  const options = resolveRemoteOptions({ state: { profileId: 'desktop_complete' } }, profile);
  assert.deepEqual(options, profile.options, 'T2: fallback 应逐键等于档案默认');
  console.log('T2 PASS 快照无 options 时回退档案默认');
}

// T3：房间只下发部分键 → 档案默认补齐全键，房间键覆盖，且无 undefined。
{
  const profile = getProfile('desktop_complete');
  const data = { state: { options: { invasion_victory: false } } };
  const options = resolveRemoteOptions(data, profile);
  assert.deepEqual(Object.keys(options), Object.keys(profile.options), 'T3: 键集应等于档案默认');
  for (const [key, value] of Object.entries(options)) {
    assert.notEqual(value, undefined, `T3: ${key} 不得为 undefined`);
  }
  assert.equal(options.invasion_victory, false, 'T3: 房间键应覆盖');
  assert.equal(options.pawn_resurrection, profile.options.pawn_resurrection, 'T3: 缺键应取档案默认');
  console.log('T3 PASS 部分键覆盖 + 默认值补全');
}

// T4：房间 profileId=desktop_light、传入轻量档 → 取到轻量档 options。
{
  const data = { state: { profileId: 'desktop_light' } };
  const profile = getProfile(data.state.profileId);
  const options = resolveRemoteOptions(data, profile);
  assert.equal(options.invasion_victory, false, 'T4: 轻量档 invasion_victory=false');
  assert.equal(options.archer_enhanced_mode, true, 'T4: 轻量档 archer_enhanced_mode=true');
  assert.equal(options.pawn_resurrection, false, 'T4: 轻量档 pawn_resurrection=false');
  console.log('T4 PASS 轻量档房间取轻量档选项');
}

// T5：历史别名归一到当前键名，未知键丢弃（不污染引擎 options）。
{
  const profile = getProfile('desktop_complete');
  const data = { state: { options: { pawn_resurrection_enabled: false, totally_unknown_key: true } } };
  const options = resolveRemoteOptions(data, profile);
  assert.equal(options.pawn_resurrection, false, 'T5: 别名应归一到 pawn_resurrection');
  assert.equal('pawn_resurrection_enabled' in options, false, 'T5: 别名旧键不得残留');
  assert.equal('totally_unknown_key' in options, false, 'T5: 未知键必须丢弃');
  assert.deepEqual(Object.keys(options), Object.keys(profile.options), 'T5: 键集不得被污染');
  console.log('T5 PASS 别名归一 + 未知键丢弃');
}

console.log('verify-online-options: 5/5 PASS');
