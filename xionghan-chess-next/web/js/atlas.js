// 网页「棋子图谱」：左列表 / 中演示盘 / 右规则正文。
// 首屏只读 `data/piece_atlas.json`（静态快照，零请求）；真的走第二步是后面那笔的事。
import { t } from './i18n.js?v=1.7.0';

const PRESET_LABELS = { clamp: '夹逼', three: '三连', facing: '照面', free: '自由' };

let snapshot = null;
let currentPreset = 'clamp';
let currentKind = null;

async function ensureSnapshot() {
  if (!snapshot) snapshot = await (await fetch('/data/piece_atlas.json')).json();
  return snapshot;
}

function drawBoard(canvas, preset) {
  const ctx = canvas.getContext('2d');
  const size = canvas.width;
  const cell = size / (preset.cols + 1);
  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = '#f3e6c8';
  ctx.fillRect(0, 0, size, size);
  ctx.strokeStyle = '#b99a6b';
  ctx.lineWidth = 1;
  for (let i = 0; i <= preset.cols + 1; i += 1) {
    ctx.beginPath(); ctx.moveTo(i * cell, 0); ctx.lineTo(i * cell, size); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, i * cell); ctx.lineTo(size, i * cell); ctx.stroke();
  }
  const cx = (col) => (col + 1.5) * cell;
  const cy = (row) => (row + 1.5) * cell;

  // 可走格
  ctx.fillStyle = 'rgba(157,37,37,.55)';
  for (const move of preset.moves) {
    ctx.beginPath();
    ctx.arc(cx(move.col), cy(move.row), cell * 0.22, 0, Math.PI * 2);
    ctx.fill();
  }
  // 可吃格（三连）
  ctx.strokeStyle = '#9d2525';
  ctx.lineWidth = 3;
  for (const cap of preset.captures || []) {
    ctx.beginPath();
    ctx.arc(cx(cap.col), cy(cap.row), cell * 0.38, 0, Math.PI * 2);
    ctx.stroke();
  }
  // 棋子
  ctx.font = `${Math.round(cell * 0.72)}px KaiTi, serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  for (const piece of preset.pieces) {
    ctx.fillStyle = piece.color === 'red' ? '#a32828' : '#2c2926';
    ctx.fillText(pieceGlyph(piece), cx(piece.col), cy(piece.row));
  }
}

const GLYPHS = {
  red: { king: '漢', rook: '俥', horse: '傌', elephant: '相', advisor: '仕', cannon: '炮', pawn: '兵', guard: '尉', archer: '射', thunder: '檑', patrol: '巡' },
  black: { king: '汗', rook: '車', horse: '馬', elephant: '象', advisor: '士', cannon: '砲', pawn: '卒', guard: '衛', archer: '䠶', thunder: '礌', patrol: '廵' },
};

function pieceGlyph(piece) {
  return (GLYPHS[piece.color] || {})[piece.type] || '·';
}

function renderText() {
  const kind = currentKind;
  const box = document.getElementById('atlasText');
  if (!box || !kind) return;
  const long = t(`piece_rule.${kind}_long`);
  box.textContent = long.startsWith('piece_rule.') ? '（暂无该棋型规则文案）' : long;
}

async function render() {
  const data = await ensureSnapshot();
  const preset = data.presets.find((item) => item.id === currentPreset) || data.presets[0];
  if (!currentKind) currentKind = preset.spotlight.type;
  const canvas = document.getElementById('atlasBoard');
  if (canvas) drawBoard(canvas, preset);
  const note = document.getElementById('atlasNote');
  if (note) note.textContent = preset.note;
  renderText();
}

export async function openAtlas() {
  const dialog = document.getElementById('atlasDialog');
  if (!dialog) return;
  if (!dialog.dataset.wired) {
    const list = document.getElementById('atlasList');
    const kinds = ['king', 'rook', 'horse', 'elephant', 'advisor', 'cannon', 'pawn', 'guard', 'archer', 'thunder', 'patrol'];
    list.innerHTML = kinds.map((kind) => `<button data-kind="${kind}">${t(`piece.${kind}`)}</button>`).join('');
    list.onclick = (event) => {
      const button = event.target.closest('[data-kind]');
      if (!button) return;
      currentKind = button.dataset.kind;
      renderText();
    };
    const presets = document.getElementById('atlasPresets');
    presets.innerHTML = Object.entries(PRESET_LABELS)
      .map(([id, label]) => `<button data-preset="${id}">${label}</button>`).join('');
    presets.onclick = (event) => {
      const button = event.target.closest('[data-preset]');
      if (!button) return;
      currentPreset = button.dataset.preset;
      render();
    };
    document.getElementById('atlasClose').onclick = () => dialog.close();
    dialog.dataset.wired = '1';
  }
  dialog.showModal();
  await render();
}
