// 网页「棋子图谱」：左列表 / 中演示盘 / 右规则正文。
// 首屏只读 `data/piece_atlas.json`（静态快照，零请求）；真的走第二步是后面那笔的事。
import { t } from './i18n.js?v=1.7.0';

const PRESET_LABELS = { clamp: '夹逼', three: '三连', facing: '照面', free: '自由' };

let snapshot = null;
let currentPreset = 'clamp';
let currentKind = null;

async function ensureSnapshot() {
  if (!snapshot) snapshot = await (await fetch('/assets/data/atlas_presets.json')).json();
  return snapshot;
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
  // 演示盘留到下一笔（本笔只出数据 + 规则正文）
  const slot = document.getElementById('atlasDemoSlot');
  if (slot) slot.textContent = `走法演示（下一笔）· 该预设 ${preset.moves.length} 个可走格`;
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
