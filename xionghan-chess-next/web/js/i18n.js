const DEFAULT_LANGUAGE = 'zh-CN';
const SUPPORTED = new Set(['zh-CN', 'en']);
let activeLanguage = DEFAULT_LANGUAGE;
let zhCatalog = {};
let activeCatalog = {};

function normalizeLanguage(language) {
  if (!language) return DEFAULT_LANGUAGE;
  const value = String(language).replace('_', '-').toLowerCase();
  if (value.startsWith('zh')) return 'zh-CN';
  if (value.startsWith('en')) return 'en';
  return DEFAULT_LANGUAGE;
}

function lookup(catalog, key) {
  return key.split('.').reduce((value, part) => value && value[part], catalog);
}

async function fetchCatalog(language) {
  const response = await fetch(`/locales/${language}.json`, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Cannot load locale ${language}`);
  return response.json();
}

export function t(key, params = {}) {
  const template = lookup(activeCatalog, key) ?? lookup(zhCatalog, key) ?? key;
  return String(template).replace(/\{(\w+)\}/g, (_, name) => params[name] ?? `{${name}}`);
}

export function currentLanguage() {
  return activeLanguage;
}

export function currentLocale() {
  return activeLanguage === 'en' ? 'en-US' : 'zh-CN';
}

export async function loadLanguage(language) {
  activeLanguage = normalizeLanguage(language);
  if (!Object.keys(zhCatalog).length) {
    zhCatalog = await fetchCatalog(DEFAULT_LANGUAGE);
  }
  activeCatalog = activeLanguage === DEFAULT_LANGUAGE ? zhCatalog : await fetchCatalog(activeLanguage);
  document.documentElement.lang = activeLanguage;
  localStorage.setItem('xh-language', activeLanguage);
  return activeLanguage;
}

export async function setLanguage(language) {
  const value = await loadLanguage(language);
  applyStaticI18n();
  return value;
}

function setText(selector, key) {
  document.querySelectorAll(selector).forEach(node => { node.textContent = t(key); });
}

function setAttr(selector, attr, key) {
  document.querySelectorAll(selector).forEach(node => { node.setAttribute(attr, t(key)); });
}

function setOption(select, value, key) {
  const option = document.querySelector(`${select} option[value="${value}"]`);
  if (option) option.textContent = t(key);
}

function setPlaceholder(selector, key) {
  setAttr(selector, 'placeholder', key);
}

export function applyStaticI18n() {
  document.title = t('app.name');
  setText('.brand h1', 'app.name');
  setText('.menubar .menu:nth-child(1) summary', 'menu.file');
  setText('.menubar .menu:nth-child(2) summary', 'menu.game');
  setText('.menubar .menu:nth-child(3) summary', 'menu.replay');
  setText('.menubar .menu:nth-child(4) summary', 'menu.view');
  setText('.menubar .menu:nth-child(5) summary', 'menu.settings');
  setText('.menubar .menu:nth-child(6) summary', 'menu.help');
  const commandKeys = {
    new: 'menu.new',
    'save-local': 'menu.save_local',
    history: 'menu.history',
    export: 'menu.export_game',
    import: 'menu.import_game',
    'mode-ai': 'menu.mode_ai',
    'mode-local': 'menu.mode_local',
    'mode-online': 'menu.mode_online',
    undo: 'menu.undo',
    pause: 'menu.pause_resume',
    draw: 'menu.draw_offer',
    resign: 'menu.resign',
    restart: 'menu.restart',
    replay: 'menu.enter_replay',
    'replay-begin': 'menu.replay_begin',
    'replay-prev': 'menu.replay_prev',
    'replay-next': 'menu.replay_next',
    'replay-end': 'menu.replay_end',
    fullscreen: 'menu.fullscreen',
    'toggle-panels': 'menu.toggle_panels',
    settings: 'menu.rules_appearance',
    sound: 'menu.sound_toggle',
    guide: 'menu.guide',
    rules: 'menu.piece_rules',
    about: 'menu.about',
  };
  for (const [command, key] of Object.entries(commandKeys)) {
    document.querySelectorAll(`[data-command="${command}"]`).forEach(button => {
      const shortcut = button.querySelector('kbd')?.outerHTML ?? '';
      button.innerHTML = shortcut ? `${t(key)} ${shortcut}` : t(key);
    });
  }
  setText('#newGameButton', 'action.start');
  setText('#joinButton', 'action.join');
  setText('#undoButton', 'action.undo');
  setText('#restartButton', 'action.restart');
  setText('#resignButton', 'action.resign');
  setText('#drawButton', 'action.draw');
  setText('#replayButton', 'action.replay');
  setText('#saveLocalButton', 'action.save');
  setText('#exportButton', 'action.export');
  setText('#resurrectButton', 'action.resurrect');
  setText('#showMovesButton', 'panel.moves');
  setText('#showChatButton', 'panel.chat');
  setText('#sendQuickChatButton,#sendChatButton', 'action.send');
  setText('#saveReplayButton', 'action.save_current');
  setText('#openReplayLibraryButton', 'action.open_replay_library');
  setText('#resetStatisticsButton', 'action.reset_statistics');
  setText('.black-player strong', 'common.black');
  setText('.red-player strong', 'common.red');
  setText('.captured-panel:nth-of-type(2) h2', 'panel.black_loss');
  setText('.record-column .captured-panel h2', 'panel.red_loss');
  setText('.room-card span', 'common.room');
  setText('#settingsDialog .dialog-title h2', 'settings.title');
  setText('#statisticsDialog .dialog-title h2', 'dialog.statistics_title');
  setText('#helpDialog .dialog-title h2', 'dialog.help_title');
  setText('#rulesDialog .dialog-title h2', 'dialog.rules_title');
  setText('#aboutDialog .dialog-title h2', 'dialog.about_title');
  setText('.replay-header strong', 'dialog.replay_title');
  setText('#resultRestart', 'dialog.result_restart');
  const thinking = document.getElementById('thinking');
  if (thinking) {
    thinking.innerHTML = `<span></span>${t('status.thinking')}`;
  }
  setText('#pauseOverlay strong', 'status.paused');
  setText('#pauseOverlay span', 'status.timer_stopped');
  setPlaceholder('#roomInput', 'placeholder.room');
  setPlaceholder('#chatInput', 'placeholder.chat');
  setAttr('#board', 'aria-label', 'dialog.rules_title');
  setAttr('#copyRoomButton', 'title', 'common.copy_room');
  setAttr('#copyRoomButton', 'aria-label', 'common.copy_room');
  setAttr('#closeReplayButton', 'title', 'dialog.exit_replay');
  setAttr('#closeReplayButton', 'aria-label', 'dialog.exit_replay');
  const labelKeys = [
    ['#modeSelect', 'mode.label'],
    ['#profileSelect', 'profile.label'],
    ['#difficultySelect', 'difficulty.label'],
    ['#colorSelect', 'settings.human_color'],
    ['#initialMinutesSelect', 'settings.initial_minutes'],
    ['#countdownSecondsSelect', 'settings.countdown'],
    ['#languageSelect', 'language.label'],
    ['#fontSelect', 'settings.font'],
    ['#boardThemeSelect', 'settings.board_theme'],
    ['#pageBackgroundSelect', 'settings.page_background'],
    ['#boardBackgroundSelect', 'settings.board_background'],
    ['#pieceStyleSelect', 'settings.piece_style'],
    ['#musicStyleSelect', 'settings.music_style'],
    ['#volumeSlider', 'settings.volume'],
  ];
  for (const [selector, key] of labelKeys) {
    const label = document.querySelector(selector)?.closest('label');
    if (label?.firstChild?.nodeType === Node.TEXT_NODE) label.firstChild.textContent = t(key);
  }
  setOption('#modeSelect', 'ai', 'mode.ai');
  setOption('#modeSelect', 'local', 'mode.local');
  setOption('#modeSelect', 'online', 'mode.online');
  for (const id of ['desktop_complete', 'desktop_classic', 'web', 'traditional']) setOption('#profileSelect', id, `profile.${id}`);
  for (const id of ['beginner', 'easy', 'medium', 'hard']) setOption('#difficultySelect', id, `difficulty.${id}`);
  setOption('#colorSelect', 'red', 'option.red_first');
  setOption('#colorSelect', 'black', 'option.black_second');
  for (const minutes of ['5', '10', '20', '30', '60']) {
    const option = document.querySelector(`#initialMinutesSelect option[value="${minutes}"]`);
    if (option) option.textContent = t('option.minutes', { count: minutes });
  }
  ['10', '30', '60'].forEach(value => {
    const option = document.querySelector(`#countdownSecondsSelect option[value="${value}"]`);
    if (option) option.textContent = t('option.last_seconds', { count: value });
  });
  setOption('#countdownSecondsSelect', '0', 'option.off');
  setOption('#languageSelect', 'zh-CN', 'language.zh-CN');
  setOption('#languageSelect', 'en', 'language.en');
  setOption('#fontSelect', 'system', 'option.font_system');
  setOption('#fontSelect', 'kaiti', 'option.font_kaiti');
  setOption('#fontSelect', 'songti', 'option.font_songti');
  setOption('#fontSelect', 'serif', 'option.font_serif');
  setOption('#boardThemeSelect', 'classic', 'option.theme_classic');
  setOption('#boardThemeSelect', 'green', 'option.theme_green');
  setOption('#boardThemeSelect', 'blue', 'option.theme_blue');
  setOption('#boardThemeSelect', 'purple', 'option.theme_purple');
  setOption('#boardThemeSelect', 'dark', 'option.theme_dark');
  for (const selector of ['#pageBackgroundSelect', '#boardBackgroundSelect']) {
    setOption(selector, 'none', selector.includes('board') ? 'option.board_background_none' : 'option.background_none');
    ['1', '2', '3', '4', '5'].forEach(value => setOption(selector, value, `option.background_${value}`));
  }
  setOption('#pieceStyleSelect', 'traditional', 'option.piece_traditional');
  setOption('#pieceStyleSelect', 'modern', 'option.piece_modern');
  setOption('#pieceStyleSelect', 'cartoon', 'option.piece_cartoon');
  setOption('#musicStyleSelect', 'fc', 'option.music_fc');
  setOption('#musicStyleSelect', 'qq', 'option.music_qq');
  setText('#appearanceSettings > legend', 'settings.appearance');
  setText('#soundSettings > legend', 'settings.sound');
  setText('#assistSettings > legend', 'settings.assist');
  setText('.custom-backgrounds > span', 'settings.custom_background');
  setText('#uploadBackgroundButton', 'action.upload');
  setText('#renameBackgroundButton', 'action.rename');
  setText('#deleteBackgroundButton', 'action.delete');
  const checkboxLabels = {
    soundEnabled: 'settings.sound_effects',
    musicEnabled: 'settings.music',
    animationEnabled: 'settings.animation',
    selectionEnabled: 'settings.selection',
    legalTargetsEnabled: 'settings.legal_targets',
    captureHintsEnabled: 'settings.capture_hints',
    autosaveEnabled: 'settings.autosave',
  };
  for (const [id, key] of Object.entries(checkboxLabels)) {
    const label = document.getElementById(id)?.closest('label');
    if (label) label.lastChild.textContent = t(key);
  }
  const docs = {
    helpDialog: 'docs.help',
    rulesDialog: 'docs.rules',
    aboutDialog: 'docs.about',
  };
  for (const [id, key] of Object.entries(docs)) {
    const body = document.querySelector(`#${id} .text-dialog-body`);
    if (body) body.innerHTML = t(key);
  }
}

export function translateError(message) {
  return message;
}
