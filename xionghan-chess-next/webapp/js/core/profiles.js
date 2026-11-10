/**
 * 规则档案与规则开关（等价于 Python `core/profiles.py`）。
 *
 * 四套档案共用同一套走法判定，只在棋盘尺寸、初始棋子、可用棋种与
 * 默认开关上不同 —— 这是本项目「一套内核、多种玩法」的核心设计。
 */

import { PIECE_TYPES } from './model.js';

export const DEFAULT_OPTIONS = {
  king_can_leave_palace: true,
  king_diagonal_in_palace: true,
  king_lose_diagonal_outside_palace: true,
  invasion_victory: true,
  advisor_can_leave_palace: true,
  advisor_gain_straight_outside_palace: true,
  elephant_can_cross_river: true,
  elephant_gain_jump_two_enemy_territory: true,
  horse_straight_three: true,
  archer_enhanced_mode: false,
  pawn_fast_move_before_enemy_territory: true,
  pawn_backward_at_base: true,
  pawn_full_movement_at_base: true,
  pawn_resurrection: true,
  pawn_promotion: true,
  enforce_self_check: true,
  threefold_draw: true,
  no_progress_draw_plies: 120,

  rook_appear: true,
  horse_appear: true,
  elephant_appear: true,
  advisor_appear: true,
  king_appear: true,
  cannon_appear: true,
  pawn_appear: true,
  guard_appear: true,
  archer_appear: true,
  thunder_appear: true,
  armor_appear: true,
  assassin_appear: true,
  shield_appear: true,
  patrol_appear: true,
};

const OPTION_ALIASES = {
  king_can_diagonal_in_palace: 'king_diagonal_in_palace',
  shi_can_leave_palace: 'advisor_can_leave_palace',
  shi_gain_straight_outside_palace: 'advisor_gain_straight_outside_palace',
  xiang_can_cross_river: 'elephant_can_cross_river',
  xiang_gain_jump_two_outside_river: 'elephant_gain_jump_two_enemy_territory',
  ma_can_straight_three: 'horse_straight_three',
  pawn_fast_move: 'pawn_fast_move_before_enemy_territory',
  pawn_fast_move_enabled: 'pawn_fast_move_before_enemy_territory',
  pawn_fast_move_before_enemy_territory_enabled: 'pawn_fast_move_before_enemy_territory',
  pawn_resurrection_enabled: 'pawn_resurrection',
  pawn_promotion_enabled: 'pawn_promotion',
  pawn_backward_at_base_enabled: 'pawn_backward_at_base',
  pawn_full_movement_at_base_enabled: 'pawn_full_movement_at_base',
  ju_appear: 'rook_appear',
  ma_appear: 'horse_appear',
  xiang_appear: 'elephant_appear',
  shi_appear: 'advisor_appear',
  pao_appear: 'cannon_appear',
  wei_appear: 'guard_appear',
  she_appear: 'archer_appear',
  lei_appear: 'thunder_appear',
  jia_appear: 'armor_appear',
  ci_appear: 'assassin_appear',
  dun_appear: 'shield_appear',
  xun_appear: 'patrol_appear',
};

export function mergeOptions(base, values) {
  const result = { ...base };
  if (!values) return result;
  const normalized = {};
  for (const [key, value] of Object.entries(values)) {
    if (['archer_weak_mode', 'sheWeakMode', 'she_weak_mode'].includes(key)) continue;
    normalized[OPTION_ALIASES[key] || key] = value;
  }
  if (!('archer_enhanced_mode' in normalized)) {
    for (const legacy of ['archer_weak_mode', 'sheWeakMode', 'she_weak_mode']) {
      if (legacy in values) {
        normalized.archer_enhanced_mode = !values[legacy];
        break;
      }
    }
  }
  normalized.king_appear = true;
  for (const key of Object.keys(normalized)) {
    if (key in result) result[key] = normalized[key];
  }
  return result;
}

export function pieceEnabled(options, type) {
  if (type === 'king') return true;
  return Boolean(options[`${type}_appear`]);
}

export const RED_NAMES = {
  king: '漢', rook: '俥', horse: '傌', elephant: '相', advisor: '仕', cannon: '炮',
  pawn: '兵', guard: '尉', archer: '射', thunder: '檑', armor: '甲',
  assassin: '刺', shield: '楯', patrol: '巡',
};

export const BLACK_NAMES = {
  king: '汗', rook: '車', horse: '馬', elephant: '象', advisor: '士', cannon: '砲',
  pawn: '卒', guard: '衛', archer: '䠶', thunder: '礌', armor: '胄',
  assassin: '伺', shield: '碷', patrol: '廵',
};

function specs(color, items) {
  return items.map(([type, row, col]) => ({ type, color, row, col }));
}

function xionghanSide(color, complete, web = false) {
  const flip = color === 'red' ? (row) => 12 - row : (row) => row;
  let items = [];
  if (complete) {
    items = items.concat([
      ['archer', 0, 0], ['shield', 0, 1], ['armor', 0, 2], ['assassin', 0, 3],
      ['thunder', 0, 4], ['guard', 0, 6], ['thunder', 0, 8], ['assassin', 0, 9],
      ['armor', 0, 10], ['shield', 0, 11], ['archer', 0, 12],
    ]);
  } else {
    items = items.concat([['archer', 0, 0], ['thunder', 0, 4], ['thunder', 0, 8], ['archer', 0, 12]]);
  }
  items = items.concat([
    ['rook', 1, 2], ['horse', 1, 3], ['elephant', 1, 4], ['advisor', 1, 5],
    ['king', 1, 6], ['advisor', 1, 7], ['elephant', 1, 8], ['horse', 1, 9],
    ['rook', 1, 10], ['cannon', 3, 1], ['cannon', 3, 11],
  ]);
  for (let col = 0; col < 13; col += 2) items.push(['pawn', 4, col]);
  if (complete || !web) items.push(['patrol', 5, 0], ['patrol', 5, 12]);
  return specs(color, items.map(([type, row, col]) => [type, flip(row), col]));
}

function traditionalSide(color) {
  const flip = color === 'red' ? (row) => 9 - row : (row) => row;
  const base = [
    ['rook', 0, 0], ['horse', 0, 1], ['elephant', 0, 2], ['advisor', 0, 3],
    ['king', 0, 4], ['advisor', 0, 5], ['elephant', 0, 6], ['horse', 0, 7],
    ['rook', 0, 8], ['cannon', 2, 1], ['cannon', 2, 7],
  ];
  for (let col = 0; col < 9; col += 2) base.push(['pawn', 3, col]);
  return specs(color, base.map(([type, row, col]) => [type, flip(row), col]));
}

const STANDARD = ['king', 'rook', 'horse', 'elephant', 'advisor', 'cannon', 'pawn'];
const ALL = PIECE_TYPES.slice();
const WEB = STANDARD.concat(['archer', 'thunder']);
const CLASSIC = WEB.concat(['patrol']);

const TRADITIONAL_OPTIONS = {
  ...DEFAULT_OPTIONS,
  king_can_leave_palace: false,
  king_diagonal_in_palace: false,
  king_lose_diagonal_outside_palace: true,
  invasion_victory: false,
  advisor_can_leave_palace: false,
  advisor_gain_straight_outside_palace: false,
  elephant_can_cross_river: false,
  elephant_gain_jump_two_enemy_territory: false,
  horse_straight_three: false,
  pawn_fast_move_before_enemy_territory: false,
  pawn_backward_at_base: false,
  pawn_full_movement_at_base: false,
  pawn_resurrection: false,
  pawn_promotion: false,
};

export const PROFILES = {
  desktop_complete: {
    id: 'desktop_complete',
    title: '完整模式',
    shortTitle: '完整',
    rows: 13,
    cols: 13,
    pieces: xionghanSide('black', true).concat(xionghanSide('red', true)),
    enabledPieceTypes: ALL,
    options: { ...DEFAULT_OPTIONS },
    description: '十四种棋子全部登场，规则最完整，接近桌面原版。',
  },
  desktop_classic: {
    id: 'desktop_classic',
    title: '经典模式',
    shortTitle: '经典',
    rows: 13,
    cols: 13,
    pieces: xionghanSide('black', false).concat(xionghanSide('red', false)),
    enabledPieceTypes: CLASSIC,
    options: { ...DEFAULT_OPTIONS },
    description: '保留射、檑、巡，去掉甲、刺、楯，节奏更接近传统象棋。',
  },
  web: {
    id: 'web',
    title: '精简模式',
    shortTitle: '精简',
    rows: 13,
    cols: 13,
    pieces: xionghanSide('black', false, true).concat(xionghanSide('red', false, true)),
    enabledPieceTypes: WEB,
    options: { ...DEFAULT_OPTIONS, pawn_resurrection: false, pawn_promotion: false },
    description: '只有射与檑两枚特色棋子，规则最好懂，适合首次上手。',
  },
  traditional: {
    id: 'traditional',
    title: '传统象棋',
    shortTitle: '传统',
    rows: 10,
    cols: 9,
    pieces: traditionalSide('black').concat(traditionalSide('red')),
    enabledPieceTypes: STANDARD,
    options: TRADITIONAL_OPTIONS,
    description: '标准 9×10 中国象棋，用来对照手感与验证内核通用性。',
  },
};

export const PROFILE_ORDER = ['desktop_complete', 'desktop_classic', 'web', 'traditional'];

export function getProfile(id) {
  return PROFILES[id] || PROFILES.desktop_complete;
}

/** 返回某一档案下、按当前开关生效的初始棋子（不含 id，id 在开局时生成）。 */
export function initialPieceSpecs(profile, options) {
  return profile.pieces.filter((spec) => pieceEnabled(options, spec.type));
}

/** 星轨点位：弱化射只能沿对角星轨行走。 */
export function archerStarPoints(profile, options) {
  if (profile.rows !== 13 || profile.cols !== 13) return [];
  if (!profile.enabledPieceTypes.includes('archer')) return [];
  if (!pieceEnabled(options, 'archer')) return [];
  const points = [];
  for (let row = 0; row < profile.rows; row += 3) {
    for (let col = 0; col < profile.cols; col += 3) {
      if ((row / 3 + col / 3) % 2 === 0) points.push({ row, col });
    }
  }
  return points;
}

export function profileToClient(profile) {
  return {
    id: profile.id,
    title: profile.title,
    shortTitle: profile.shortTitle,
    rows: profile.rows,
    cols: profile.cols,
    description: profile.description,
    enabledPieceTypes: profile.enabledPieceTypes.slice(),
    pieceSlots: profile.pieces
      .filter((spec) => spec.color === 'red')
      .map((spec) => ({ id: `${spec.color}:${spec.type}:${spec.row}:${spec.col}`, ...spec })),
    options: { ...profile.options },
  };
}
