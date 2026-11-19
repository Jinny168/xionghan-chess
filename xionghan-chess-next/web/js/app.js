import { applyStaticI18n, currentLanguage, currentLocale, setLanguage, t } from './i18n.js?v=2.1.0';
import { ribbonClass, CHECK_PULSE_MID } from './ribbon.js';

const $ = (selector) => document.querySelector(selector);

// E1 高对比棋子组：与桌面 contrast.py、webapp board.js 同一套 WCAG 派生公式。
// 零新增色值：输出色由既有令牌按盘底混色算出，源码不写新 hex 字面量。
const CONTRAST_TEXT_TARGET = 4.5;
const CONTRAST_GRAPHIC_TARGET = 3.0;
const _CONTRAST_LIGHT_THRESHOLD = 0.179;
const _MIX_STEP = 0.05;
// F1 高对比组内：可走点半径放大一档（授权上限 0.18 格）；仅开关开启时生效，默认主题不变。
const LEGAL_DOT_RATIO_HC = 0.16;

function _channelLinear(channel) {
  const s = channel / 255;
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

function _parseRgb(hex) {
  let h = hex.replace('#', '');
  if (h.length === 3) h = [...h].map((ch) => ch + ch).join('');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function relativeLuminance(hex) {
  const [r, g, b] = _parseRgb(hex);
  return 0.2126 * _channelLinear(r) + 0.7152 * _channelLinear(g) + 0.0722 * _channelLinear(b);
}

function contrastRatio(fg, bg) {
  let l1 = relativeLuminance(fg);
  let l2 = relativeLuminance(bg);
  if (l1 < l2) { [l1, l2] = [l2, l1]; }
  return (l1 + 0.05) / (l2 + 0.05);
}

function _mixRgb(token, target, mix) {
  return token.map((v, i) => Math.round(v + (target[i] - v) * mix));
}

function _rgbToHex([r, g, b]) {
  return '#' + [r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('');
}

function deriveRgb(tokenRgb, background, target = CONTRAST_TEXT_TARGET) {
  const token = _rgbToHex(tokenRgb);
  const base = contrastRatio(token, background);
  if (base >= target) return { color: token, ratio: base, met: true, mix: 0 };
  const darkBackground = relativeLuminance(background) <= _CONTRAST_LIGHT_THRESHOLD;
  const targetRgb = darkBackground ? [255, 255, 255] : [0, 0, 0];
  let best = { color: token, ratio: base, met: false, mix: 0 };
  for (let mix = _MIX_STEP; mix <= 1 + 1e-9; mix += _MIX_STEP) {
    const candidate = _rgbToHex(_mixRgb(tokenRgb, targetRgb, mix));
    const ratio = contrastRatio(candidate, background);
    if (ratio >= best.ratio) best = { color: candidate, ratio, met: ratio >= target, mix };
    if (ratio >= target) return best;
  }
  return best;
}

function deriveForBackground(token, background, target = CONTRAST_TEXT_TARGET) {
  return deriveRgb(_parseRgb(token), background, target);
}

const board = $('#board');
const ctx = board.getContext('2d');
const replayDialog = $('#replayDialog');
const replayBoard = $('#replayBoard');
const replayCtx = replayBoard.getContext('2d');
const app = {
  roomId: null, token: null, color: null, revision: 0, state: null, socket: null,
  mode: 'ai', selected: null, legal: [], capturable: [], victims: [], dragging: null,
  replayIndex: null, replaySource: null, replayTimer: null, sound: true, music: true,
  preferences: {systemTheme:'light',font:'system',boardTheme:'classic',pageBackground:'none',boardBackground:'1',pieceStyle:'traditional',musicStyle:'fc',volume:70,animation:true,selection:true,legalTargets:true,captureHints:true,starHints:false,highContrastPieces:false,pieceBadges:false,taunts:true,autosave:true,initialMinutes:10,countdownSeconds:30,language:'zh-CN',flipped:false},
  options: {}, profiles: new Map(), pieceImages: new Map(), animation: null, legalPromise: null, resultKey: null, reconnectTimer: null, reconnectAttempts: 0,
  // 走法语义版本：**从 /api/profiles 读**，别在这里写死第二份（2.0.0 的规则变更就是
  // 靠它拦下旧缓存网页：旧 app.js 不带这个字段 → 服务端按 1 处理 → 409 提示刷新）。
  ruleVersion: 1,
  setupSlots: {}, spectator: false, account: null, authToken: localStorage.getItem('xh-auth-token'), cloudTimer: null, puzzleSession: null, selectedPuzzle: null, customBackgrounds: new Map(),
};
const sounds={select:new Audio('/assets/sounds/choose.wav'),move:new Audio('/assets/sounds/drop.wav'),capture:new Audio('/assets/sounds/eat.wav'),check:new Audio('/assets/sounds/warn.wav'),win:new Audio('/assets/sounds/fc_victory_sound.wav'),lose:new Audio('/assets/sounds/fc_defeat_sound.wav'),button:new Audio('/assets/sounds/button.wav')};
const builtinAvatars=Array.from({length:9},(_,index)=>`avatar-${String(index+1).padStart(2,'0')}`);
// 系统级「减少动态」偏好；与用户手动关闭 preferences.animation 相互独立。
const systemReducedMotion=()=>typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
function avatarUrl(value){return value?.startsWith('builtin:')?`/assets/avatars/${value.slice(8)}.webp`:value||''}
function renderAvatarPicker(value=''){let root=$('#profileAvatarPicker');if(!root){root=document.createElement('div');root.id='profileAvatarPicker';root.className='avatar-picker';$('#profileAvatarUrl').closest('label').before(root)}root.innerHTML=[`<button type="button" data-avatar="" title="Default">Default</button>`,...builtinAvatars.map(id=>`<button type="button" data-avatar="builtin:${id}" title="${id}" style="background-image:url('/assets/avatars/${id}.webp')"></button>`)].join('');root.querySelectorAll('button').forEach(button=>button.classList.toggle('selected',button.dataset.avatar===value))}
let backgroundMusic=null;
const backgroundDatabase='xh-backgrounds';
function openBackgroundDatabase(){return new Promise((resolve,reject)=>{const request=indexedDB.open(backgroundDatabase,1);request.onupgradeneeded=()=>request.result.createObjectStore('images',{keyPath:'id'});request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error)})}
async function backgroundRecords(){const database=await openBackgroundDatabase();return new Promise((resolve,reject)=>{const request=database.transaction('images').objectStore('images').getAll();request.onsuccess=()=>{database.close();resolve(request.result)};request.onerror=()=>{database.close();reject(request.error)}})}
async function putBackground(record){const database=await openBackgroundDatabase();return new Promise((resolve,reject)=>{const transaction=database.transaction('images','readwrite');transaction.objectStore('images').put(record);transaction.oncomplete=()=>{database.close();resolve()};transaction.onerror=()=>{database.close();reject(transaction.error)}})}
async function removeBackground(id){const database=await openBackgroundDatabase();return new Promise((resolve,reject)=>{const transaction=database.transaction('images','readwrite');transaction.objectStore('images').delete(id);transaction.oncomplete=()=>{database.close();resolve()};transaction.onerror=()=>{database.close();reject(transaction.error)}})}
function backgroundUrl(value){if(!value||value==='none')return'none';if(value.startsWith('custom:'))return app.customBackgrounds.get(value.slice(7))?.url?`url("${app.customBackgrounds.get(value.slice(7)).url}")`:'none';return`url('/assets/backgrounds/${value}.jpg')`}
function refreshBackgroundOptions(){const selected=$('#customBackgroundSelect'),previous=selected.value;selected.innerHTML='';for(const record of app.customBackgrounds.values()){const option=new Option(record.name,record.id);selected.add(option)}if(!selected.options.length)selected.add(new Option(t('settings.custom_background_empty'),'',true,true));selected.value=app.customBackgrounds.has(previous)?previous:(selected.options[0]?.value||'');for(const target of [$('#pageBackgroundSelect'),$('#boardBackgroundSelect')]){target.querySelectorAll('option[data-custom]').forEach(option=>option.remove());for(const record of app.customBackgrounds.values()){const option=new Option(record.name,`custom:${record.id}`);option.dataset.custom='true';target.add(option)}}}
async function loadCustomBackgrounds(){try{for(const old of app.customBackgrounds.values())URL.revokeObjectURL(old.url);app.customBackgrounds.clear();for(const record of await backgroundRecords())app.customBackgrounds.set(record.id,{...record,url:URL.createObjectURL(record.blob)});refreshBackgroundOptions()}catch(error){console.warn('Custom backgrounds unavailable',error)}}
function safeStorageSet(key,value){try{localStorage.setItem(key,value);return true}catch(error){queueMicrotask(()=>toast(t('toast.storage_full')==='toast.storage_full'?'本地存储空间不足，数据未保存':t('toast.storage_full'),'warn'));console.warn('Storage write failed',error);return false}}
function persistPreferences(){safeStorageSet('xh-preferences',JSON.stringify(app.preferences));safeStorageSet('xh-sound',JSON.stringify({sound:app.sound,music:app.music}));if(app.authToken){clearTimeout(app.cloudTimer);app.cloudTimer=setTimeout(()=>{const {starHints:_omitStarHints,...syncable}=app.preferences;api('/api/me/preferences',{method:'PUT',body:JSON.stringify({preferences:syncable})}).catch(()=>{})},600)}}
function applyPreferences(){const p=app.preferences;const dark=p.systemTheme==='dark'||(p.systemTheme==='auto'&&matchMedia('(prefers-color-scheme: dark)').matches);document.body.dataset.systemTheme=dark?'dark':'light';document.body.dataset.font=p.font;document.body.dataset.boardTheme=p.boardTheme;document.body.dataset.background=p.pageBackground;document.body.dataset.boardBackground=p.boardBackground;document.documentElement.style.setProperty('--page-image',backgroundUrl(p.pageBackground));document.documentElement.style.setProperty('--board-image',backgroundUrl(p.boardBackground));document.documentElement.style.setProperty('--board-line',({classic:'#6d3c11',green:'#3a6b1e',blue:'#2471a3',purple:'#7d3c98',dark:'#aaa'})[p.boardTheme]||'#6d3c11');document.documentElement.style.setProperty('--board-text',({classic:'#8b4513',green:'#2d5016',blue:'#1a5276',purple:'#6c3483',dark:'#ddd'})[p.boardTheme]||'#8b4513');$('#systemThemeSelect').value=p.systemTheme||'light';$('#fontSelect').value=p.font;$('#boardThemeSelect').value=p.boardTheme;$('#languageSelect').value=p.language||currentLanguage();$('#pageBackgroundSelect').value=p.pageBackground;$('#boardBackgroundSelect').value=p.boardBackground;$('#pieceStyleSelect').value=p.pieceStyle;$('#musicStyleSelect').value=p.musicStyle;$('#volumeSlider').value=p.volume;$('#volumeValue').textContent=`${p.volume}%`;$('#soundEnabled').checked=app.sound;$('#musicEnabled').checked=app.music;$('#animationEnabled').checked=p.animation!==false;$('#selectionEnabled').checked=p.selection!==false;$('#legalTargetsEnabled').checked=p.legalTargets!==false;$('#captureHintsEnabled').checked=p.captureHints!==false;$('#starHintsEnabled').checked=p.starHints===true;$('#highContrastEnabled').checked=p.highContrastPieces===true;$('#pieceBadgesEnabled').checked=p.pieceBadges===true;$('#tauntsEnabled').checked=p.taunts!==false;$('#autosaveEnabled').checked=p.autosave!==false;$('#initialMinutesSelect').value=String(p.initialMinutes??10);$('#countdownSecondsSelect').value=String(p.countdownSeconds??30);Object.values(sounds).forEach(a=>{a.volume=p.volume/100});if(backgroundMusic)backgroundMusic.volume=p.volume/200;applyStaticI18n();refreshBackgroundOptions();refreshDailyButton();draw()}
async function loadPreferences(){try{const stored=JSON.parse(localStorage.getItem('xh-preferences')||'{}');app.preferences={...app.preferences,...stored};const legacyDifficulty={easy:'beginner',expert:'hard',master:'hard'};if(legacyDifficulty[app.preferences.difficulty])app.preferences.difficulty=legacyDifficulty[app.preferences.difficulty];if(!stored.pageBackground)app.preferences.pageBackground=stored.background||'1';// 迁移：老存档**缺** pageBackground 字段时才归一到默认 '1'；显式存了 'none' 是用户选择，保留不改写。
if(!stored.boardBackground)app.preferences.boardBackground='1';const s=JSON.parse(localStorage.getItem('xh-sound')||'{}');if(typeof s.sound==='boolean')app.sound=s.sound;if(typeof s.music==='boolean')app.music=s.music}catch{}await loadCustomBackgrounds();applyPreferences()}
function playSound(key){if(!app.sound)return;const audio=sounds[key];if(audio){audio.currentTime=0;audio.volume=app.preferences.volume/100;audio.play().catch(()=>{})}}
function startMusic(){if(!app.music)return;if(!backgroundMusic||backgroundMusic.dataset.style!==app.preferences.musicStyle){if(backgroundMusic)backgroundMusic.pause();backgroundMusic=new Audio(`/assets/sounds/${app.preferences.musicStyle==='qq'?'qq_background_sound.mp3':'fc_background_sound.mp3'}`);backgroundMusic.loop=true;backgroundMusic.dataset.style=app.preferences.musicStyle;backgroundMusic.volume=app.preferences.volume/200}backgroundMusic.play().catch(()=>{})}
function stopMusic(){if(backgroundMusic){backgroundMusic.pause();backgroundMusic.currentTime=0}}
function replayGame(){return app.replaySource||app.state}
function openReplay(source=null,title=t('dialog.current_game')){const game=source||app.state;if(!game?.history?.length)return toast(t('toast.replay_empty'),'warn');stopReplay();app.replaySource=source;app.replayIndex=game.history.length;$('#replayTitle').textContent=title;updateReplayUI();renderSavedReplays();if(!replayDialog.open)replayDialog.showModal();requestAnimationFrame(draw)}
function closeReplay(){stopReplay();app.replayIndex=null;app.replaySource=null;if(replayDialog.open)replayDialog.close();draw()}
function stopReplay(){if(app.replayTimer){clearInterval(app.replayTimer);app.replayTimer=null}$('#replayPlay').textContent='▶';$('#replayPlay').title='播放'}
function toggleReplay(){if(app.replayTimer){stopReplay();return}const total=replayGame()?.history?.length||0;if((app.replayIndex??total)>=total)setReplayIndex(0);app.replayTimer=setInterval(()=>{const current=app.replayIndex??0;if(current>=total){stopReplay();return}setReplayIndex(current+1)},850);$('#replayPlay').textContent='Ⅱ';$('#replayPlay').title='暂停'}
function setReplayIndex(step){const total=replayGame()?.history?.length||0;app.replayIndex=Math.max(0,Math.min(total,step));updateReplayUI();draw()}
function updateReplayUI(){const game=replayGame(),total=game?.history?.length||0,current=app.replayIndex===null?total:app.replayIndex;$('#replayProgress').max=total;$('#replayProgress').value=current;$('#replayStepInfo').textContent=`${current} / ${total}`;$('#replayMoves').innerHTML=(game?.history||[]).map((h,i)=>`<li data-index="${i+1}" class="${app.replayIndex===i+1?'active':''}">${i+1}. ${h.notation||''}</li>`).join('')}
function currentGameDocument(){if(!app.state)return null;const state=JSON.parse(JSON.stringify(app.state)),setup=state.setup;delete state.profile;delete state.check;delete state.replay;delete state.setup;return{formatVersion:1,profileId:app.state.profile.id,options:app.state.profile.options,setup,state,snapshots:(app.state.replay||[]).slice(0,-1),savedAt:new Date().toISOString()}}
function normalizeRecord(record){if(record?.document)return record;if(!record?.profile?.id||!record?.replay?.length)return null;const state=record.replay.at(-1);return{id:record.id||Date.now(),savedAt:record.savedAt||new Date().toISOString(),document:{formatVersion:1,profileId:record.profile.id,options:record.profile.options||{},state,snapshots:record.replay.slice(0,-1),savedAt:record.savedAt||new Date().toISOString()}}}
function replayRecords(){try{return JSON.parse(localStorage.getItem('xh-replays')||'[]').map(normalizeRecord).filter(Boolean)}catch{return[]}}
function stateFromDocument(document){const profile=app.profiles.get(document.profileId)||app.state?.profile||{id:document.profileId,title:document.profileId,rows:13,cols:13,archerStarPoints:[]};return{...JSON.parse(JSON.stringify(document.state)),profile:{...profile,options:document.options||profile.options||{}},check:false,replay:[...(document.snapshots||[]),document.state]}}
function storeReplay(document,{silent=false,autoKey=null}={}){const records=replayRecords();if(autoKey&&records.some(record=>record.autoKey===autoKey))return;records.unshift({id:Date.now(),savedAt:document.savedAt,document,autoKey});if(!safeStorageSet('xh-replays',JSON.stringify(records.slice(0,50))))return;renderSavedReplays();if(!silent)toast(t('toast.saved_library'),'success')}
function saveCurrentReplay(){const document=currentGameDocument();if(!document)return toast(t('toast.no_save_game'),'warn');storeReplay(document)}
function renderSavedReplays(){const list=$('#savedReplayList');if(!list)return;const records=replayRecords();list.innerHTML=records.length?records.map(r=>{const state=r.document.state,total=state.history?.length||0,result=state.winner?(state.winner==='red'?t('common.red_win'):t('common.black_win')):(state.draw?t('common.draw'):t('common.unfinished'));return `<div class="saved-replay"><div><strong>${result} · ${total} ${t('common.moves')}</strong><span>${new Date(r.savedAt).toLocaleString(currentLocale())}</span></div><div class="saved-replay-actions"><button data-replay-record="${r.id}">${t('action.replay')}</button><button data-continue-record="${r.id}">${t('common.continue')}</button><button data-export-record="${r.id}">${t('common.export')}</button><button data-delete-replay="${r.id}">${t('common.delete')}</button></div></div>`}).join(''):`<span>${t('toast.replay_library_empty')}</span>`}
function loadSavedReplay(id){const record=replayRecords().find(r=>r.id===id);if(!record)return;openReplay(stateFromDocument(record.document),new Date(record.savedAt).toLocaleString(currentLocale()))}
function openReplayLibrary(){if(app.state?.history?.length)return openReplay();const record=replayRecords()[0];if(record)return loadSavedReplay(record.id);toast(t('toast.replay_library_empty'),'warn')}
function loadStatistics(){const defaults={games:0,redWins:0,blackWins:0,draws:0,moves:0,totalTimeMs:0,fastestWinMs:0,winStreak:{current:0,max:0},perColor:{red:{games:0,wins:0},black:{games:0,wins:0}}};try{const stored=JSON.parse(localStorage.getItem('xh-statistics')||'{}');return{...defaults,...stored,winStreak:{...defaults.winStreak,...stored.winStreak},perColor:{red:{...defaults.perColor.red,...stored.perColor?.red},black:{...defaults.perColor.black,...stored.perColor?.black}}}}catch{return defaults}}
function recordFinishedGame(key){let recorded=[];try{recorded=JSON.parse(localStorage.getItem('xh-stat-keys')||'[]');if(!Array.isArray(recorded))recorded=[]}catch{}if(recorded.includes(key))return;const stats=loadStatistics(),duration=(app.state.history||[]).reduce((sum,item)=>sum+Math.max(0,item.elapsedMs||0),0),winner=app.state.winner;stats.games++;stats.moves+=app.state.history.length;stats.totalTimeMs+=duration;if(app.state.draw){stats.draws++;stats.winStreak.current=0}else if(winner){winner==='red'?stats.redWins++:stats.blackWins++;stats.perColor[winner].games++;stats.perColor[winner].wins++;stats.winStreak.current++;stats.winStreak.max=Math.max(stats.winStreak.max,stats.winStreak.current);if(duration&&(!stats.fastestWinMs||duration<stats.fastestWinMs))stats.fastestWinMs=duration}safeStorageSet('xh-statistics',JSON.stringify(stats));safeStorageSet('xh-stat-keys',JSON.stringify([key,...recorded].slice(0,200)));if(app.preferences.autosave!==false){const document=currentGameDocument();if(document)storeReplay(document,{silent:true,autoKey:key});if(app.authToken)saveCloudGame().catch(()=>{})}}
function statisticDuration(ms){if(!ms)return'-';const minutes=Math.floor(ms/60000),seconds=Math.floor(ms%60000/1000);return`${minutes}:${String(seconds).padStart(2,'0')}`}
function showStatistics(){const stats=loadStatistics(),decided=Math.max(1,stats.games-stats.draws),redRate=stats.redWins*100/decided,blackRate=stats.blackWins*100/decided;$('#statisticsSummary').innerHTML=`<strong>${stats.games}</strong><span>${t('statistics.total_games')}</span><strong>${stats.redWins}</strong><span>${t('statistics.red_wins')}</span><strong>${stats.blackWins}</strong><span>${t('statistics.black_wins')}</span><strong>${stats.draws}</strong><span>${t('statistics.draws')}</span><strong>${stats.moves}</strong><span>${t('statistics.moves')}</span><strong>${statisticDuration(stats.totalTimeMs)}</strong><span>${t('statistics.total_time')}</span><strong>${statisticDuration(stats.fastestWinMs)}</strong><span>${t('statistics.fastest_win')}</span><strong>${stats.winStreak.max}</strong><span>${t('statistics.max_streak')}</span><strong>${redRate.toFixed(1)}% / ${blackRate.toFixed(1)}%</strong><span>${t('statistics.color_rates')}</span>`;if(!$('#statisticsDialog').open)$('#statisticsDialog').showModal()}
function downloadDocument(gameDocument){const filename=`xionghan_${new Date().toISOString().replace(/[:.]/g,'-')}.xhgame`,content=JSON.stringify(gameDocument,null,2);if(window.XionghanAndroid?.saveGame){window.XionghanAndroid.saveGame(filename,content);toast(t('toast.choose_save_location'));return}const url=URL.createObjectURL(new Blob([content],{type:'application/json'})),link=documentNode('a',{href:url,download:filename});document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(t('toast.exported'),'success')}
function documentNode(tag,attrs){const node=document.createElement(tag);Object.assign(node,attrs);return node}
async function importDocument(document,mode){const targetMode=mode||(app.mode==='online'?'local':app.mode||'local');const data=await api('/api/rooms/import',{method:'POST',body:JSON.stringify({document,mode:targetMode,playerName:t('common.player'),playerColor:$('#colorSelect').value,difficulty:$('#difficultySelect').value,language:currentLanguage()})});closeReplay();acceptSession(data);$('#modeSelect').value=targetMode;syncModeControls();toast(targetMode==='local'?t('toast.imported_local'):t('toast.imported_ai'),'success')}

const pieceLabels = {
  king:'汉/汗登场',rook:'车登场',horse:'马登场',elephant:'相/象登场',advisor:'仕/士登场',
  cannon:'炮登场',pawn:'兵/卒登场',guard:'尉/卫登场',archer:'射登场',thunder:'檑登场',
  patrol:'巡/廵登场'
};
// 反向呈现的开关：存储值 true 表示"削弱"，界面勾选必须表示"增强"。
// 名单由 /api/profiles 下发（与 core/profiles.py 的 NEGATED_OPTIONS 同源）。
let negatedOptions=new Set();
const optionIsOn=key=>{const stored=app.options[key]!==false;return negatedOptions.has(key)?!stored:stored};
const optionStored=(key,shown)=>negatedOptions.has(key)?!shown:shown;
// 按钮**显隐**的规则判据：动作 → 必须全部开启的选项键，与 `optionIsOn` 不同源不重复：
// 名单来自 /api/profiles 的 `actionRequirements`（同源 core/profiles.py::UI_ACTION_REQUIRES）。
// 拿不到档案时（纯本地、接口失败、旧服务端没这个字段）退回"常驻"——
// 宁可多一个能点会报错的按钮，也不要让按钮在这种环境下凭空消失。
const actionVisible=action=>{const parents=app.profiles?.get(app.state?.profile?.id)?.actionRequirements?.[action];return !parents?.length||parents.every(parent=>optionIsOn(parent))};
const pieceRuleKeys={
  king:['king_can_leave_palace','king_diagonal_in_palace','king_lose_diagonal_outside_palace','invasion_victory'],
  horse:['horse_blocked_by_leg','horse_straight_three','horse_straight_three_move_only'],elephant:['elephant_can_cross_river','elephant_gain_jump_two_enemy_territory'],
  advisor:['advisor_can_leave_palace','advisor_gain_straight_outside_palace'],
  pawn:['pawn_fast_move_before_enemy_territory','pawn_charge','pawn_three_line_capture','pawn_backward_at_base','pawn_resurrection','pawn_promotion'],
  archer:['archer_enhanced_mode']
};
const names = {red:{king:'漢',rook:'俥',horse:'傌',elephant:'相',advisor:'仕',cannon:'炮',pawn:'兵',guard:'尉',archer:'射',thunder:'檑',patrol:'巡'},black:{king:'汗',rook:'車',horse:'馬',elephant:'象',advisor:'士',cannon:'砲',pawn:'卒',guard:'衛',archer:'䠶',thunder:'礌',patrol:'廵'}};

async function api(path, options={}) {const headers={'Content-Type':'application/json',...(app.authToken?{Authorization:`Bearer ${app.authToken}`}:{}),...(app.token?{'X-Room-Token':app.token}:{}),...(options.headers||{})};const response=await fetch(path,{...options,headers});const data=await response.json();if(!response.ok){// detail 现在有两种形状：普通错误是字符串，专用错误码（如 rule_version_mismatch）是
// `{code, message, ...}` —— 直接 `new Error(obj)` 会变成 "[object Object]"。
const detail=data.detail;throw new Error(typeof detail==='string'?detail:(detail?.message||t('error.request_failed')))}return data;}
function toast(message,level){const el=$('#toast');const lv=['info','success','warn','error'].includes(level)?level:'info';el.textContent=message;el.classList.remove('toast--info','toast--success','toast--warn','toast--error');el.classList.add('show','toast--'+lv);clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove('show'),lv==='error'?3200:lv==='warn'?2600:2200)}
function formatClock(ms=0){const total=Math.max(0,Math.ceil(ms/1000));return `${String(Math.floor(total/60)).padStart(2,'0')}:${String(total%60).padStart(2,'0')}`}

function profileSetup(){const profile=app.profiles.get($('#profileSelect').value),all=(profile?.pieceSlots||[]).filter(slot=>slot.type==='king'||app.options[`${slot.type}_appear`]!==false);if(!app.setupSlots[profile?.id])app.setupSlots[profile?.id]={red:all.filter(x=>x.color==='red').map(x=>x.id),black:all.filter(x=>x.color==='black').map(x=>x.id)};return{profile,all,selected:app.setupSlots[profile?.id]}}
function selectedSetup(){const {all,selected}=profileSetup(),available=new Set(all.map(slot=>slot.id));return selected?{red:selected.red.filter(id=>available.has(id)),black:selected.black.filter(id=>available.has(id))}:{red:null,black:null}}
function ruleText(kind){const long=t(`piece_rule.${kind}_long`);return long.startsWith('piece_rule.')?'':long}
function renderHandicap(){const {all,selected}=profileSetup();for(const color of ['red','black']){const root=$(`#${color}PieceSlots`),chosen=new Set(selected[color]);root.innerHTML=all.filter(slot=>slot.color===color).map(slot=>{const mandatory=slot.type==='king';return `<label><input type="checkbox" data-piece-slot="${slot.id}" data-color="${color}" ${chosen.has(slot.id)?'checked':''} ${mandatory?'disabled':''}><span>${names[color][slot.type]||slot.type}</span><small>${t(`piece.${slot.type}`)} · ${slot.row+1},${slot.col+1}</small></label>`}).join('');$(`#${color}PieceCount`).value=`${chosen.size} 枚`}$(`#applyHandicapButton`).disabled=selected.red.length!==selected.black.length}
function updateHandicapSelection(input){const setup=selectedSetup(),items=new Set(setup[input.dataset.color]);input.checked?items.add(input.dataset.pieceSlot):items.delete(input.dataset.pieceSlot);setup[input.dataset.color]=[...items];renderHandicap()}

async function createGame(){
  closeSocket();
  try{
    app.preferences.initialMinutes=Number($('#initialMinutesSelect').value);app.preferences.countdownSeconds=Number($('#countdownSecondsSelect').value);persistPreferences();
    const setup=selectedSetup();
    const data=await api('/api/rooms',{method:'POST',body:JSON.stringify({profileId:$('#profileSelect').value,mode:$('#modeSelect').value,playerName:app.account?.displayName||t('common.player'),avatarUrl:app.account?.avatarUrl||'',playerColor:$('#colorSelect').value,difficulty:$('#difficultySelect').value,options:app.options,initialMinutes:app.preferences.initialMinutes,language:currentLanguage(),firstMove:$('#firstMoveSelect').value,redSlots:setup.red,blackSlots:setup.black,tauntsEnabled:app.preferences.taunts!==false,ruleVersion:app.ruleVersion})});
    acceptSession(data);toast(data.snapshot.mode==='online'?t('toast.room_created',{room:data.roomId}):(data.snapshot.mode==='local'?t('toast.local_started'):t('toast.ai_started')),'success');
  }catch(error){toast(error.message,'error')}
}
async function joinGame(){
  const code=$('#roomInput').value.trim().toUpperCase(); if(!code)return toast(t('toast.enter_room'),'warn');
  try{const data=await api(`/api/rooms/${code}/join`,{method:'POST',body:JSON.stringify({playerName:app.account?.displayName||t('common.player_two'),avatarUrl:app.account?.avatarUrl||'',language:currentLanguage(),ruleVersion:app.ruleVersion})});acceptSession(data);toast(t('toast.joined_room'),'success')}catch(error){toast(error.message,'error')}
}
async function spectateGame(){const code=$('#roomInput').value.trim().toUpperCase();if(!code)return toast(t('toast.room_prompt'),'warn');try{const data=await api(`/api/rooms/${code}/spectate`,{method:'POST',body:JSON.stringify({displayName:app.account?.displayName||t('common.player')})});data.spectator=true;acceptSession(data);toast(t('toast.spectate_joined'),'success')}catch(error){toast(error.message,'error')}}
function acceptSession(data){app.roomId=data.roomId;app.token=data.token;app.color=data.color||null;app.spectator=!!data.spectator;app.resultKey=null;app.reconnectAttempts=0;receiveSnapshot(data.snapshot);safeStorageSet('xh-session',JSON.stringify({roomId:app.roomId,token:app.token,color:app.color,mode:app.mode,spectator:app.spectator}));connect()}
function connect(){
  if(!app.roomId||!app.token||app.socket?.readyState===WebSocket.CONNECTING||app.socket?.readyState===WebSocket.OPEN)return;clearTimeout(app.reconnectTimer);const protocol=location.protocol==='https:'?'wss':'ws',suffix=app.spectator?'/spectate':'',socket=new WebSocket(`${protocol}://${location.host}/ws/${app.roomId}${suffix}`);app.socket=socket;
  socket.onopen=()=>{if(app.socket!==socket)return;app.reconnectAttempts=0;clearTimeout(app.reconnectTimer);socket.send(JSON.stringify({type:'auth',token:app.token}));$('#connectionText').textContent=app.mode==='local'?t('status.local_sync'):t('status.connected')};
  socket.onmessage=e=>{if(app.socket!==socket)return;try{const message=JSON.parse(e.data);if(message.type==='state')receiveSnapshot(message.payload);else if(message.type==='chat')appendChat(message.payload);else if(message.type==='error'){toast(message.payload.message,'error');if(message.payload.state)receiveSnapshot(message.payload.state)}}catch{toast(t('error.request_failed'),'error')}};
  socket.onclose=event=>{if(app.socket!==socket)return;app.socket=null;clearTimeout(app.reconnectTimer);$('#connectionText').textContent=t('status.interrupted');if([4001,4403,1008].includes(event.code)||app.reconnectAttempts>=3)return;const delay=Math.min(8000,1200*2**app.reconnectAttempts++);app.reconnectTimer=setTimeout(()=>{if(app.roomId&&!app.socket)connect()},delay)};
}
function closeSocket(){clearTimeout(app.reconnectTimer);app.reconnectAttempts=0;if(app.socket){app.socket.onclose=null;app.socket.close()}app.socket=null}
function send(type,payload={}){if(!app.socket||app.socket.readyState!==WebSocket.OPEN)return toast(t('toast.socket_not_ready'),'warn');app.socket.send(JSON.stringify({type,roomId:app.roomId,revision:app.revision,payload,protocolVersion:1}))}
function appendChat(payload){if(payload.automated&&app.preferences.taunts===false)return;const list=$('#chatMessages'),item=document.createElement('div');item.className=`chat-message ${payload.color||''}`;const sender=document.createElement('strong');sender.textContent=`${payload.sender||t('common.player')}：`;item.append(sender,document.createTextNode(payload.text||''));list.append(item);list.scrollTop=list.scrollHeight}
function sendChat(quick=false){const input=$('#chatInput'),text=(quick?$('#quickChatSelect').value:input.value).trim();if(!text)return;send('chat',{text,quick});if(!quick)input.value=''}
function showRecordView(view){const chat=view==='chat';$('#chatView').hidden=!chat;$('#moveList').hidden=chat;$('#moveCount').hidden=chat;$('#showMovesButton').classList.toggle('active',!chat);$('#showChatButton').classList.toggle('active',chat)}
function receiveSnapshot(snapshot){
  const previous=app.state,revisionChanged=snapshot.revision!==app.revision;app.revision=snapshot.revision;app.state=snapshot.game;app.mode=snapshot.mode;app.options=snapshot.game.profile.options;$('#modeSelect').value=app.mode;syncModeControls();if(revisionChanged){app.selected=null;app.legal=[];app.capturable=[],app.victims=[]}
  if(!previous&&snapshot.chatHistory?.length){$('#chatMessages').innerHTML='';snapshot.chatHistory.forEach(appendChat)}
  $('#roomCode').textContent=snapshot.roomId;$('#roomInput').value=snapshot.roomId;const turnRibbon=$('#turnRibbon');turnRibbon.className=ribbonClass(app.state);turnRibbon.textContent=app.state.finished?t('status.game_over'):(app.state.paused?t('status.paused'):(app.state.check?`${t('status.check')} · `:'')+t('status.turn',{color:t(`common.${app.state.turn}`)}));if(app.state.check&&turnRibbon.animate&&!systemReducedMotion())turnRibbon.animate([{transform:'scale(1)',color:'inherit'},{transform:'scale(1.08)',color:CHECK_PULSE_MID},{transform:'scale(1)',color:'inherit'}],{duration:900,iterations:2});
  $('#spectatorCount').textContent=`${snapshot.spectatorCount||0} 人观战`;
  $('#thinking').hidden=!(snapshot.mode==='ai'&&app.state.turn!==app.color&&!app.state.finished&&!app.state.paused);$('#pauseOverlay').hidden=!app.state.paused;renderMeta(snapshot);resizeBoard();
  if(previous&&app.state.history.length>previous.history.length){const last=app.state.history.at(-1);playSound(last.captured?.length?'capture':app.state.check?'check':'move');
    if(isBigCapture(last.captured)){shakeBoard();toast(t('toast.big_capture',{name:t('piece_name.'+last.captured[0].type)}))}if(app.preferences.animation!==false&&!systemReducedMotion()){app.animation={source:last.move.from,target:last.move.to,capture:!!last.captured?.length,started:performance.now()};requestAnimationFrame(animate)}checkPuzzleProgress()}
  if(app.state.finished)showResult();
  if(app.state.pendingDrawOffer&&app.state.pendingDrawOffer!==app.color&&confirm(t('dialog.pending_draw')))send('draw_response',{accept:true});
  else if(app.state.pendingDrawOffer&&app.state.pendingDrawOffer!==app.color)send('draw_response',{accept:false});
  if(app.state.pendingUndoOffer&&app.state.pendingUndoOffer!==app.color&&confirm(t('dialog.pending_undo')))send('undo_response',{accept:true});
  else if(app.state.pendingUndoOffer&&app.state.pendingUndoOffer!==app.color)send('undo_response',{accept:false});
  if(app.state.pendingRestartOffer&&app.state.pendingRestartOffer!==app.color&&confirm(t('dialog.pending_restart')))send('restart_response',{accept:true,options:app.options});
  else if(app.state.pendingRestartOffer&&app.state.pendingRestartOffer!==app.color)send('restart_response',{accept:false});
}
function updateClockVisuals(){if(!app.state)return;for(const color of ['red','black']){const clock=$(`#${color}Clock`);clock.textContent=formatClock(app.state.clocksMs[color]);clock.classList.toggle('countdown',!app.state.paused&&app.preferences.countdownSeconds>0&&app.state.clocksMs[color]<=app.preferences.countdownSeconds*1000)}}
function renderMeta(snapshot){
  updateClockVisuals();
  for(const color of ['red','black']){const player=snapshot.players.find(p=>p.color===color);const panel=$(`#${color}Status`).closest('.player-panel');const avatar=panel?.querySelector('.avatar');if(avatar){const fallback=[...(player?.name||t(`common.${color}`))][0]||color[0].toUpperCase(),image=avatarUrl(player?.avatarUrl);avatar.textContent=fallback;avatar.style.backgroundImage=image?`url(${JSON.stringify(image)})`:'';avatar.classList.toggle('custom-avatar',!!image);avatar.setAttribute('aria-label',player?.name||t(`common.${color}`))}const name=panel?.querySelector('strong');if(name)name.textContent=player?.name||t(`common.${color}`);$(`#${color}Status`).textContent=snapshot.mode==='local'?(color==='red'?t('common.local_player_one'):t('common.local_player_two')):(player?(player.connected?t('common.online'):t('common.temporarily_offline')):t('common.waiting'));$(`#${color}Captured`).innerHTML=(app.state.captured[color]||[]).map(p=>`<span>${names[color][p.type]}</span>`).join('')}
  $('#moveList').innerHTML=app.state.history.map((h,i)=>`<li data-index="${i}">${h.notation}</li>`).join('');$('#moveCount').textContent=t('common.rounds',{count:Math.ceil(app.state.history.length/2)});const list=$('#moveList');list.scrollTop=list.scrollHeight;
  const myTurn=(app.mode==='local'||app.state.turn===app.color)&&!app.state.finished&&!app.state.paused;$('#resignButton').disabled=app.state.finished;$('#drawButton').disabled=!myTurn;$('#undoButton').disabled=!app.state.history.length||app.state.paused;
  // 「复活兵卒」：可见性由**规则**决定（`actionRequirements` 由 /api/profiles 下发，
  // 与 core/profiles.py::UI_ACTION_REQUIRES 同源），可用性由**对局状态**决定。
  // 原来这里只 disabled、从不隐藏，且不读 pawn_resurrection —— 关掉复活的规则集里
  // 玩家面对的是一个永远点不动的按钮。
  const resurrectVisible=actionVisible('resurrect');
  $('#resurrectButton').hidden=!resurrectVisible;
  $('#resurrectButton').disabled=!resurrectVisible||!myTurn;
  $('#pauseButton').disabled=app.state.finished;$('#pauseButton').textContent=app.state.paused?`▶ ${t('action.resume')}`:`Ⅱ ${t('action.pause')}`;
}
function showResult(){const winner=app.state.winner,key=`${app.roomId}:${winner||'draw'}:${app.state.resultReason}:${app.state.history.length}`,reason=t(`result.${app.state.resultReason}`);$('#resultMark').textContent=winner?(winner==='red'?'漢':'汗'):t('common.draw');$('#resultTitle').textContent=winner?t('result.victory',{color:t(`common.${winner}`)}):t('result.draw');$('#resultText').textContent=reason.startsWith('result.')?t('result.ended'):reason;if(app.resultKey!==key){playSound(app.mode==='local'||winner===app.color?'win':'lose');recordFinishedGame(key);app.resultKey=key}if(!$('#resultDialog').open)$('#resultDialog').showModal()}
function syncModeControls(){const mode=$('#modeSelect').value;$('#difficultyRow').hidden=mode!=='ai';$('#colorRow').hidden=mode==='local';$('#joinRow').hidden=mode!=='online';$('#connectionText').textContent=mode==='local'?t('status.local_sync'):(mode==='ai'?t('status.ai'):t('status.online'))}
function canControl(piece){return !app.spectator&&piece&&!app.state.paused&&piece.color===app.state.turn&&(app.mode==='local'||piece.color===app.color)}

function resizeBoard(){const rect=board.parentElement.getBoundingClientRect();if(rect.width<2||rect.height<2)return;const dpr=Math.min(devicePixelRatio||1,2),width=Math.max(1,Math.floor(rect.width*dpr)),height=Math.max(1,Math.floor(rect.height*dpr));if(board.width!==width)board.width=width;if(board.height!==height)board.height=height;board.style.width=`${rect.width}px`;board.style.height=`${rect.height}px`;draw()}
function geometry(){const model=replayGame(),rows=model?.profile?.rows||13,cols=model?.profile?.cols||13,w=board.clientWidth,h=board.clientHeight,pad=Math.min(w,h)*.055;return{rows,cols,pad,cw:(w-pad*2)/(cols-1),ch:(h-pad*2)/(rows-1),w,h}}
function displayPosition(g,p){return app.preferences.flipped?{row:g.rows-1-p.row,col:g.cols-1-p.col}:p}
function positionAt(event){const r=board.getBoundingClientRect(),g=geometry();let col=Math.round((event.clientX-r.left-g.pad)/g.cw),row=Math.round((event.clientY-r.top-g.pad)/g.ch);if(app.preferences.flipped){row=g.rows-1-row;col=g.cols-1-col}return row>=0&&row<g.rows&&col>=0&&col<g.cols?{row,col}:null}
function draw(){
  if(!app.state)return;const replay=replayGame(),shown=app.replayIndex===null?app.state:(replay.replay?.[app.replayIndex]||app.state);const originalPieces=app.state.pieces;app.state.pieces=shown.pieces;const g=geometry(),dpr=board.width/g.w,styles=getComputedStyle(document.documentElement);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,g.w,g.h);ctx.strokeStyle=styles.getPropertyValue('--board-line').trim()||'#604326';ctx.lineWidth=1.25;
  if(g.rows===13)drawXionghanGrid(g);else drawStandardGrid(g);
  drawPalaces(g);if(g.rows===13){drawInitialPositionMarks(g);drawStarPoints(g)}drawStarHints(g);drawHighlights(g);for(const piece of app.state.pieces)drawPiece(g,piece);drawCaptureHints(g);drawAnimation(g);app.state.pieces=originalPieces;mirrorReplayBoard();
}
function mirrorReplayBoard(){if(!replayDialog.open)return;const rect=replayBoard.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2),width=Math.max(1,Math.floor(rect.width*dpr)),height=Math.max(1,Math.floor(rect.height*dpr));if(replayBoard.width!==width)replayBoard.width=width;if(replayBoard.height!==height)replayBoard.height=height;replayCtx.setTransform(1,0,0,1,0,0);replayCtx.clearRect(0,0,width,height);const scale=Math.min(width/board.width,height/board.height),drawWidth=board.width*scale,drawHeight=board.height*scale;replayCtx.drawImage(board,(width-drawWidth)/2,(height-drawHeight)/2,drawWidth,drawHeight)}
function drawStandardGrid(g){
  for(let r=0;r<10;r++)line(g,r,0,r,8);
  for(let c=0;c<9;c++){if(c===0||c===8)line(g,0,c,9,c);else{line(g,0,c,4,c);line(g,5,c,9,c)}}
  const y=g.pad+4.5*g.ch;
  ctx.save();ctx.font=`${Math.max(16,g.cw*.38)}px KaiTi`;ctx.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--board-text').trim()||'#604326';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(t('board.chu_river'),g.pad+2*g.cw,y);ctx.fillText(t('board.han_boundary'),g.pad+6*g.cw,y);ctx.restore();
}
function drawXionghanGrid(g){
  for(let r=0;r<13;r++)if(r!==6)line(g,r,0,r,12);
  for(let c=0;c<13;c++){line(g,0,c,5,c);line(g,7,c,12,c)}
  const y=g.pad+6*g.ch,m=Math.min(g.cw,g.ch)*.16;
  for(let c=0;c<13;c++){const x=g.pad+c*g.cw;ctx.beginPath();ctx.moveTo(x-m,y);ctx.lineTo(x+m,y);if(c>0&&c<12){ctx.moveTo(x,y-m);ctx.lineTo(x,y+m)}ctx.stroke()}
  ctx.save();ctx.font=`${Math.max(17,g.cw*.38)}px KaiTi`;ctx.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--board-text').trim()||'#604326';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(t('board.great_wall'),g.pad+3*g.cw,y);ctx.fillText(t('board.yin_mountains'),g.pad+9*g.cw,y);ctx.restore();
}
function drawInitialPositionMarks(g){
  const positions=[];for(const r of [4,8])for(let c=0;c<13;c+=2)positions.push([r,c]);positions.push([3,1],[3,11],[9,1],[9,11]);
  const offset=Math.min(g.cw,g.ch)*.14,length=Math.min(g.cw,g.ch)*.2;
  ctx.save();ctx.lineWidth=1.25;for(const [r,c] of positions){const x=g.pad+c*g.cw,y=g.pad+r*g.ch;for(const [sx,sy] of [[-1,-1],[1,-1],[-1,1],[1,1]]){const cx=x+sx*offset,cy=y+sy*offset;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx+sx*length,cy);ctx.moveTo(cx,cy);ctx.lineTo(cx,cy+sy*length);ctx.stroke()}}ctx.restore();
}
function drawStarPoints(g){
  const points=app.state.profile.archerStarPoints||[],inner=Math.min(g.cw,g.ch)*.07,outer=Math.min(g.cw,g.ch)*.18;
  ctx.save();ctx.strokeStyle='rgba(109,60,17,.7)';ctx.lineWidth=1.25;
  for(const point of points){const x=g.pad+point.col*g.cw,y=g.pad+point.row*g.ch;for(const [sx,sy] of [[-1,-1],[1,-1],[-1,1],[1,1]]){ctx.beginPath();ctx.moveTo(x+sx*inner,y+sy*inner);ctx.lineTo(x+sx*outer,y+sy*outer);ctx.stroke()}}
  ctx.restore();
}
// P1-7 射·星轨：经典档选中射 → 四斜向星位锚点的放射线 + 端点空心环。
// 星点集只认服务端下发的 profile.archerStarPoints；JS 只做纯几何求锚点，
// 不重判"哪些点是星位"。复盘中 legal 与显示局面错位、计分测验会替玩家答题、
// 观战无玩家选中 —— 三种场景一律不画。
function drawStarHints(g){
  if(!app.preferences.starHints||app.replayIndex!==null||app.puzzleSession||app.spectator)return;
  if(!app.options||app.options.archer_enhanced_mode!==false)return;
  if(g.rows!==13||!app.selected||app.selected.type!=='archer')return;
  const points=app.state.profile.archerStarPoints||[];
  const rays=globalThis.XHStarHints?.archerAnchorRays(points,app.selected,g.rows,g.cols)||[];
  if(!rays.length)return;
  const shown=displayPosition(g,app.selected),fx=g.pad+shown.col*g.cw,fy=g.pad+shown.row*g.ch;
  const cell=Math.min(g.cw,g.ch),radius=cell*.13*.5;
  ctx.save();ctx.strokeStyle=lastMoveInk(.20);ctx.lineWidth=Math.max(1,cell*.02);
  for(const anchor of rays){const to=displayPosition(g,anchor),x=g.pad+to.col*g.cw,y=g.pad+to.row*g.ch;ctx.beginPath();ctx.moveTo(fx,fy);ctx.lineTo(x,y);ctx.stroke();ctx.beginPath();ctx.arc(x,y,radius,0,Math.PI*2);ctx.stroke()}
  ctx.restore();
}
function drawAnimation(g){if(!app.animation)return;const age=performance.now()-app.animation.started;if(age>320){app.animation=null;return}const progress=Math.min(1,age/320),from=displayPosition(g,app.animation.source),to=displayPosition(g,app.animation.target),fx=g.pad+from.col*g.cw,fy=g.pad+from.row*g.ch,tx=g.pad+to.col*g.cw,ty=g.pad+to.row*g.ch;ctx.save();ctx.strokeStyle=app.animation.capture?'rgba(157,37,37,.9)':'rgba(49,92,72,.9)';ctx.lineWidth=Math.max(2,Math.min(g.cw,g.ch)*.06);ctx.globalAlpha=1-progress;ctx.beginPath();ctx.moveTo(fx,fy);ctx.lineTo(tx,ty);ctx.stroke();const angle=Math.atan2(ty-fy,tx-fx),head=Math.min(g.cw,g.ch)*.18;ctx.beginPath();ctx.moveTo(tx,ty);ctx.lineTo(tx-head*Math.cos(angle-.55),ty-head*Math.sin(angle-.55));ctx.lineTo(tx-head*Math.cos(angle+.55),ty-head*Math.sin(angle+.55));ctx.closePath();ctx.fill();const r=Math.min(g.cw,g.ch)*(.2+progress*.35);ctx.beginPath();ctx.arc(tx,ty,r,0,Math.PI*2);ctx.stroke();ctx.restore()}
function animate(){draw();if(app.animation)requestAnimationFrame(animate)}
function drawPalaces(g){const palaces=g.rows===10?[[0,3],[7,3]]:[[1,5],[9,5]];ctx.lineWidth=1.2;for(const [r,c] of palaces){line(g,r,c,r+2,c+2);line(g,r,c+2,r+2,c)}}
function line(g,r1,c1,r2,c2){ctx.beginPath();ctx.moveTo(g.pad+c1*g.cw,g.pad+r1*g.ch);ctx.lineTo(g.pad+c2*g.cw,g.pad+r2*g.ch);ctx.stroke()}
function lastMoveInk(alpha){const raw=(getComputedStyle(document.documentElement).getPropertyValue('--board-line').trim()||'#604326');const hex=raw.length===4?`#${raw[1]}${raw[1]}${raw[2]}${raw[2]}${raw[3]}${raw[3]}`:raw;const n=parseInt(hex.slice(1,7),16);return `rgba(${(n>>16)&255},${(n>>8)&255},${n&255},${alpha})`}
// D1 上一步起讫格：与桌面 board_widget.LAST_MOVE_* 同参数——**格内圆角方框**
// （内缩 5%、圆角 16% 格宽）、不透明度 .25、盘线色。方框而不是圆盘：圆和圆棋子
// 同心，棋子会遮掉中间，方框的四个角仍可见，两端点都读得出来。
// 画在**最前**，将军（.35 红环）、选择（.55 金环）、可走点依次压在上面。
function cellFrame(g,raw,color){const p=displayPosition(g,raw),ix=g.cw*.05,iy=g.ch*.05,x=g.pad+p.col*g.cw-g.cw/2+ix,y=g.pad+p.row*g.ch-g.ch/2+iy,w=g.cw-2*ix,h=g.ch-2*iy,r=Math.min(g.cw,g.ch)*.16;ctx.beginPath();ctx.roundRect?ctx.roundRect(x,y,w,h,r):ctx.rect(x,y,w,h);ctx.fillStyle=color;ctx.fill()}
// 回放时**不画**上一步：网页的 `app.state.history` 始终是实时对局的，
// 切到某个历史局面后末手会与所显示的局面错位。
// 桌面端相反 —— 它的复盘快照自带 history 前缀，画的是「走到这一手的那一步」，
// 与显示局面严格对应，所以那边照画。**两端语义一致（都显示当前局面的上一步），
// 实现必然不同，别为了"统一"把其中一边改成另一种做法，那会引入错位 bug。**
function currentBoardBg(){return getComputedStyle(document.documentElement).getPropertyValue('--board-bg').trim()||'#f9e8c4'}

function drawHighlights(g){const last=app.replayIndex===null?app.state.history?.at(-1):null;if(last){const ink=lastMoveInk(.25);cellFrame(g,last.move.from,ink);cellFrame(g,last.move.to,ink)}if(app.state.check){const king=app.state.pieces.find(p=>p.type==='king'&&p.color===app.state.turn);if(king)ring(g,king,'rgba(196,35,35,.35)',.47)}if(app.selected&&app.preferences.selection!==false)ring(g,app.selected,'rgba(215,167,55,.55)',.48);if(app.preferences.legalTargets!==false){const hc=app.preferences.highContrastPieces===true,bg=currentBoardBg(),captureFill=hc?deriveRgb([157,37,37],bg,CONTRAST_GRAPHIC_TARGET).color:'rgba(157,37,37,.28)',legalDot=hc?deriveRgb([49,92,72],bg,CONTRAST_GRAPHIC_TARGET).color:'rgba(49,92,72,.72)',legalRadius=hc?LEGAL_DOT_RATIO_HC:0.13;for(const raw of app.legal){const p=displayPosition(g,raw),occupied=app.state.pieces.some(x=>x.row===raw.row&&x.col===raw.col);ctx.beginPath();ctx.arc(g.pad+p.col*g.cw,g.pad+p.row*g.ch,occupied?Math.min(g.cw,g.ch)*.42:Math.min(g.cw,g.ch)*legalRadius,0,Math.PI*2);ctx.fillStyle=occupied?captureFill:legalDot;ctx.fill()}}}
// 两种吃子提示，两套视觉，别合并（桌面端 board_widget._draw_capture_hints 同构）：
// 实心叉 = 落点可吃（这枚子就站在某条合法着法的落点上，点过去必吃）；
// 空心圈 = 旁吃受害者（三连吃子从落点旁边的线上取子，这枚子不在任何落点上，
// 点它会被引擎拒绝）。合并成一个集合时，红叉会出现在棋子去不了的格子上，
// 玩家读成"落点可吃" —— 正是用户报的那个 bug。
function drawCaptureHints(g){if(app.preferences.captureHints===false)return;const cell=Math.min(g.cw,g.ch),size=cell*.3;const hc=app.preferences.highContrastPieces===true,bg=currentBoardBg(),hcRing=hc?deriveRgb([205,32,32],bg,CONTRAST_GRAPHIC_TARGET).color:null;ctx.save();ctx.strokeStyle=hcRing||'rgba(205,32,32,.9)';ctx.lineWidth=Math.max(2.5,cell*.055);for(const raw of app.capturable){const p=displayPosition(g,raw),x=g.pad+p.col*g.cw,y=g.pad+p.row*g.ch;ctx.beginPath();ctx.moveTo(x-size,y-size);ctx.lineTo(x+size,y+size);ctx.moveTo(x+size,y-size);ctx.lineTo(x-size,y+size);ctx.stroke()}ctx.strokeStyle=hcRing||'rgba(205,32,32,.66)';ctx.lineWidth=Math.max(2,cell*.04);for(const raw of app.victims){const p=displayPosition(g,raw),x=g.pad+p.col*g.cw,y=g.pad+p.row*g.ch;ctx.beginPath();ctx.arc(x,y,cell*.34,0,Math.PI*2);ctx.stroke()}ctx.restore()}
function ring(g,raw,color,size){const p=displayPosition(g,raw);ctx.beginPath();ctx.arc(g.pad+p.col*g.cw,g.pad+p.row*g.ch,Math.min(g.cw,g.ch)*size,0,Math.PI*2);ctx.fillStyle=color;ctx.fill()}
const pieceAssetTypes={king:'han',rook:'che',horse:'ma',elephant:'xiang',advisor:'shi',cannon:'pao',pawn:'bing',guard:'wei',archer:'she',thunder:'lei',patrol:'xun'};
function pieceImage(p){const suffix=pieceAssetTypes[p.type];if(!suffix)return null;const key=`${app.preferences.pieceStyle}:${p.color}:${suffix}`;if(app.pieceImages.has(key))return app.pieceImages.get(key);const image=new Image();image.onload=draw;image.onerror=()=>app.pieceImages.set(key,null);image.src=`/assets/pieces/${app.preferences.pieceStyle}/${p.color==='red'?'hong':'hei'}${suffix}.png`;app.pieceImages.set(key,image);return image}
const BADGE_ORBIT=0.86,BADGE_SIZE=0.26,BADGE_STROKE=0.055;function specialBadge(p,x,y,r,ink){if(app.preferences.pieceBadges!==true)return;const kind={guard:'slash',archer:'star',thunder:'bars',patrol:'square'}[p.type];if(!kind)return;const bx=x,by=y-r*BADGE_ORBIT,R=r*BADGE_SIZE;ctx.save();ctx.strokeStyle=ink;ctx.lineWidth=Math.max(1,r*BADGE_STROKE);ctx.lineCap='round';ctx.lineJoin='round';if(kind==='star'){const inner=R*.42,pts=[[0,-R],[inner,-inner],[R,0],[inner,inner],[0,R],[-inner,inner],[-R,0],[-inner,-inner]];ctx.beginPath();pts.forEach((q,i)=>i===0?ctx.moveTo(bx+q[0],by+q[1]):ctx.lineTo(bx+q[0],by+q[1]));ctx.closePath();ctx.stroke();ctx.beginPath();ctx.arc(bx,by,R*1.35,0,Math.PI*2);ctx.stroke()}else if(kind==='slash'){for(const off of[-R*.28,R*.28]){ctx.beginPath();ctx.moveTo(bx-R*.6+off,by-R*.6-off);ctx.lineTo(bx+R*.6+off,by+R*.6-off);ctx.stroke()}}else if(kind==='bars'){for(const dy of[-R*.5,0,R*.5]){ctx.beginPath();ctx.moveTo(bx-R*.6,by+dy);ctx.lineTo(bx+R*.6,by+dy);ctx.stroke()}}else{ctx.strokeRect(bx-R*.6,by-R*.6,R*1.2,R*1.2)}ctx.restore()}
function drawPiece(g,p){const shown=displayPosition(g,p),x=g.pad+shown.col*g.cw,y=g.pad+shown.row*g.ch,r=Math.min(g.cw,g.ch)*.39,img=pieceImage(p);const inkToken=p.color==='red'?'#a12424':'#292522';const boardBg=getComputedStyle(document.documentElement).getPropertyValue('--board-bg').trim()||'#f9e8c4';const ink=app.preferences.highContrastPieces===true?deriveForBackground(inkToken,boardBg).color:inkToken;if(img?.complete&&img.naturalWidth){const size=r*2.14;ctx.save();ctx.shadowColor='rgba(0,0,0,.28)';ctx.shadowBlur=5;ctx.shadowOffsetY=2;ctx.drawImage(img,x-size/2,y-size/2,size,size);specialBadge(p,x,y,r,ink);ctx.restore();return}ctx.save();ctx.shadowColor='rgba(0,0,0,.28)';ctx.shadowBlur=5;ctx.shadowOffsetY=2;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fillStyle='#f4d99f';ctx.fill();ctx.shadowColor='transparent';ctx.lineWidth=Math.max(2,r*.09);ctx.strokeStyle=ink;ctx.stroke();ctx.beginPath();ctx.arc(x,y,r*.82,0,Math.PI*2);ctx.lineWidth=1;ctx.stroke();ctx.fillStyle=ink;ctx.font=`bold ${r*1.15}px KaiTi`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(names[p.color][p.type],x,y+1);specialBadge(p,x,y,r,ink);ctx.restore()}

async function selectOrMove(pos){
  if(!app.state||app.state.finished||app.replayIndex!==null)return;const piece=app.state.pieces.find(p=>p.row===pos.row&&p.col===pos.col);
  if(app.selected&&app.legal.some(p=>p.row===pos.row&&p.col===pos.col)){const payload={from:{row:app.selected.row,col:app.selected.col},to:pos};if(app.selected.type==='pawn'&&app.options.pawn_promotion&&(pos.row===0||pos.row===app.state.profile.rows-1)){const choices=[...new Set((app.state.captured[app.selected.color]||[]).map(p=>p.type).filter(t=>!['pawn','king'].includes(t)))];if(choices.length){const answer=prompt(t('prompt.promotion',{choices:choices.join(' / ')}),choices[0]);if(!choices.includes(answer))return toast(t('toast.valid_promotion'),'warn');payload.promotion=answer}}send('move',payload);app.selected=null;app.legal=[];app.capturable=[],app.victims=[];draw();return}
  if(piece&&app.selected&&piece.row===app.selected.row&&piece.col===app.selected.col){draw();return}
  if(canControl(piece)){app.selected=piece;playSound('select');await loadLegal(piece)}else{app.selected=null;app.legal=[];app.capturable=[],app.victims=[];draw()}
}
async function loadLegal(piece){
  app.legalPromise=api(`/api/rooms/${app.roomId}/legal?row=${piece.row}&col=${piece.col}`);
  try{const data=await app.legalPromise;if(data.revision===app.revision){app.legal=data.moves;app.capturable=data.capturesOnLanding??data.captures??[];app.victims=data.capturesAway??[]}}catch(error){toast(error.message,'error');app.legal=[];app.capturable=[],app.victims=[]}finally{app.legalPromise=null}draw()
}

async function refreshAccount(){if(!app.authToken){app.account=null;$('#accountGuest').hidden=false;$('#accountProfile').hidden=true;return}try{const data=await api('/api/me');app.account=data.account;app.preferences={...app.preferences,...data.preferences};applyPreferences();$('#accountGuest').hidden=true;$('#accountProfile').hidden=false;$('#accountName').textContent=`${app.account.displayName} (@${app.account.username})`;$('#profileDisplayName').value=app.account.displayName;$('#profileAvatarUrl').value=app.account.avatarUrl?.startsWith('http')?app.account.avatarUrl:'';renderAvatarPicker(app.account.avatarUrl||'');await refreshCloudGames()}catch{app.authToken=null;app.account=null;localStorage.removeItem('xh-auth-token');$('#accountGuest').hidden=false;$('#accountProfile').hidden=true}}
async function saveProfile(){try{const selected=$('#profileAvatarPicker .selected')?.dataset.avatar||'',external=$('#profileAvatarUrl').value.trim(),data=await api('/api/me/profile',{method:'PUT',body:JSON.stringify({displayName:$('#profileDisplayName').value.trim(),avatarUrl:external||selected})});app.account=data.account;$('#accountName').textContent=`${app.account.displayName} (@${app.account.username})`;renderAvatarPicker(app.account.avatarUrl||'');toast('账号资料已更新','success')}catch(error){toast(error.message,'error')}}
async function authenticate(mode){const body={username:$('#accountUsername').value.trim(),password:$('#accountPassword').value,displayName:$('#accountDisplayName').value.trim()};try{const data=await api(`/api/auth/${mode}`,{method:'POST',body:JSON.stringify(body)});app.authToken=data.token;app.account=data.account;safeStorageSet('xh-auth-token',data.token);app.preferences={...app.preferences,...data.preferences};applyPreferences();await refreshAccount();toast(mode==='login'?'登录成功':'注册成功','success')}catch(error){toast(error.message,'error')}}
async function refreshCloudGames(){if(!app.account)return;const games=await api('/api/me/games');$('#cloudGameList').innerHTML=games.length?games.map(game=>`<div class="cloud-game"><div><strong>${game.favorite?'★ ':''}${game.title}</strong><span>${new Date(game.updatedAt*1000).toLocaleString(currentLocale())}</span></div><div><button data-cloud-open="${game.id}">打开</button><button data-cloud-favorite="${game.id}" data-favorite="${!game.favorite}">${game.favorite?'取消收藏':'收藏'}</button><button data-cloud-delete="${game.id}">删除</button></div></div>`).join(''):'<p>暂无云端棋谱</p>'}
async function saveCloudGame(){const document=currentGameDocument();if(!document)return toast('当前没有可上传的棋局','warn');try{await api('/api/me/games',{method:'POST',body:JSON.stringify({document,title:`${app.state.profile.title} · ${app.state.history.length} 手`})});await refreshCloudGames();toast('棋局已同步到云端','success')}catch(error){toast(error.message,'error')}}
async function runAnalysis(){const document=currentGameDocument();if(!document||!app.state.history.length)return toast('当前棋局还没有可分析的着法','warn');$('#analysisDialog').showModal();$('#analysisLoading').hidden=false;$('#analysisContent').hidden=true;try{const result=await api('/api/analysis',{method:'POST',body:JSON.stringify({document,difficulty:'beginner'})});renderAnalysis(result)}catch(error){$('#analysisDialog').close();toast(error.message,'error')}}
function renderAnalysis(result){$('#analysisLoading').hidden=true;$('#analysisContent').hidden=false;const labels={best:'最佳',good:'良好',inaccuracy:'欠准',mistake:'失误',blunder:'严重失误'};$('#analysisMoveList').innerHTML=result.moves.map(item=>`<button data-analysis-ply="${item.ply}" class="quality-${item.quality}"><span>${item.ply}. ${item.notation}</span><strong>${labels[item.quality]}</strong></button>`).join('')}
function customPuzzles(){try{const items=JSON.parse(localStorage.getItem('xh-custom-puzzles')||'[]');return Array.isArray(items)?items:[]}catch{return[]}}
function validPuzzle(item){return!!(item&&typeof item.id==='string'&&typeof item.title==='string'&&['beginner','advanced','master'].includes(item.difficulty)&&item.document&&item.document.formatVersion===1&&Array.isArray(item.solution)&&item.solution.length&&item.solution.every(move=>move?.from&&move?.to)&&Array.isArray(item.hints))}
async function openTraining(level='beginner'){try{const builtIn=await api(`/api/puzzles?difficulty=${level}`),puzzles=[...builtIn,...customPuzzles().filter(item=>item.difficulty===level)];// A2：按战役章节分组。分组标题是不可点的 div，用 CSS 让它看起来像小标题。
app.trainingPuzzles=puzzles;const order=TRAINING_ORDER;const groups=new Map();puzzles.forEach(item=>{const key=item.chapter||'';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(item)});const keys=[...groups.keys()].sort((a,b)=>{const ia=order.indexOf(a),ib=order.indexOf(b);return (ia<0?order.length:ia)-(ib<0?order.length:ib)});const tp=readTraining();const unlockedCh=unlockedChapters(tp.stars,puzzles);$('#puzzleList').innerHTML=keys.map(key=>{const items=groups.get(key);const isDrill=!key;const locked=!isDrill&&!unlockedCh.includes(key);const prevIdx=order.indexOf(key)-1;const prev=prevIdx>=0?order[prevIdx]:order[0];const earned=items.reduce((s,p)=>s+(tp.stars[p.id]||0),0);const maxStars=items.length*3;let title=key||t('training.drills');if(isDrill)title+=` · ${t('training.freeHint')}`;else if(!locked)title+=` · ${'★'.repeat(earned)}${'☆'.repeat(Math.max(0,maxStars-earned))}`;const rows=locked?`<button class="puzzle-locked" disabled><strong>🔒 ${t('training.locked',{chapter:prev})}</strong></button>`:items.map(item=>`<button data-puzzle-id="${item.id}" data-custom-puzzle="${item.document?'true':'false'}"><strong>${item.title}${(tp.stars[item.id]||0)>0?' '+'★'.repeat(tp.stars[item.id])+'☆'.repeat(3-tp.stars[item.id]):''}</strong><span>${item.description||''}</span><small>${(item.tags||[]).join(' · ')}</small></button>`).join('');return `<div class="puzzle-chapter">${title}</div>${rows}`}).join('');refreshStreakButton();$('#puzzleDetail').hidden=true;if(!$('#trainingDialog').open)$('#trainingDialog').showModal()}catch(error){toast(error.message,'error')}}
async function selectPuzzle(id){try{app.dailyDay=null;app.selectedPuzzle=customPuzzles().find(item=>item.id===id)||await api(`/api/puzzles/${id}?reveal=true`);$('#puzzleInfo').innerHTML=`<h3>${app.selectedPuzzle.title}</h3><p>${app.selectedPuzzle.description||''}</p><small>${(app.selectedPuzzle.tags||[]).join(' · ')}</small>`;$('#puzzleDetail').hidden=false}catch(error){toast(error.message,'error')}}
async function startPuzzle(){if(!app.selectedPuzzle)return;app.puzzleSession={...app.selectedPuzzle,step:0,misses:0,hints:0,hintStage:0,scored:false,streak:false};$('#trainingDialog').close();await importDocument(app.selectedPuzzle.document,'local');toast(t('toast.puzzle_started'))}
// --- 每日一题 ---------------------------------------------------------------
// 选题在服务端算（`/api/daily` → `core/daily.py`），前端只负责记「今天做没做」。
// 连续性规则与 `core/daily.py` **同构**：隔天做完 +1、同一天重解不涨、断档归零、
// 时间回拨不惩罚。改这里必须同步改那边，反之亦然。
const DAILY_KEY='xh-daily';
function dailyRecord(){try{const raw=JSON.parse(localStorage.getItem(DAILY_KEY)||'{}');return raw&&typeof raw==='object'?raw:{}}catch(error){return{}}}
function saveDailyRecord(record){safeStorageSet(DAILY_KEY,JSON.stringify(record))}
function dailyToday(){const now=new Date();return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`}
function dailyGap(from,to){return Math.round((Date.parse(to)-Date.parse(from))/86400000)}
// D4 首跑引导：只在**首次访问**出现，记在 localStorage（不采集、不上报）
function maybeShowOnboarding(){
  try{if(localStorage.getItem('xh-onboarded'))return}catch(error){return}
  ['1','2','3'].forEach((n,index)=>$('#onboardLine'+n).textContent=t('training.onboard_'+(index+1)));
  $('#onboardTitle').textContent=t('training.onboard_title');
  $('#onboardStartButton').textContent=t('training.onboard_cta');
  const dialog=$('#onboardDialog');if(!dialog)return;
  $('#onboardStartButton').onclick=()=>{try{localStorage.setItem('xh-onboarded','1')}catch(error){}dialog.close()};
  if(!dialog.open)dialog.showModal();
}
// 版本号从服务端取，页面里不再写死（桌面端的「关于」也做过同样的修正）
async function loadAppVersion(){
  try{const data=await api('/api/version');
    const label=$('#aboutVersion');if(label&&data?.version)label.textContent=`${t('common.version')||'版本'} ${data.version}`}
  catch(error){/* 拿不到就保持占位符，不影响游戏 */}
}

function refreshDailyButton(){const button=$('#dailyPuzzleButton');if(!button)return;const record=dailyRecord(),today=dailyToday();let label=t('training.daily');const gap=record.day?dailyGap(record.day,today):0;
  if(record.day===today&&record.done)label+=` · ${t('training.daily_done')}`;
  else if(record.streak&&gap<=1)label+=` · ${t('training.daily_streak',{count:record.streak+1})}`;
  button.textContent=label}
async function openDaily(){try{
  const data=await api('/api/daily');const today=data.day,record=dailyRecord(),gap=record.day?dailyGap(record.day,today):0;
  if(record.day===today&&record.done)return toast(t('training.daily_done'));
  // 惰性归零：昨天开了没做完、或断了两天以上 —— 与桌面端 `start_today` 同一口径
  if(record.day&&(gap>1||(gap===1&&!record.done))){record.streak=0;saveDailyRecord(record)}
  app.dailyDay=today;app.selectedPuzzle=data.puzzle;await startPuzzle();if(app.puzzleSession)app.puzzleSession.scored=true;refreshDailyButton();
}catch(error){toast(error.message,'error')}}
function recordDailySolved(session){if(!app.dailyDay)return;const today=app.dailyDay,record=dailyRecord(),gap=record.day?dailyGap(record.day,today):0;
  const streak=(record.day&&gap===1&&record.done)?(record.streak||0)+1:1;
  saveDailyRecord({day:today,id:session.id,done:true,streak,best:Math.max(streak,record.best||0)});
  app.dailyDay=null;toast(t('training.daily_solved',{count:streak}));refreshDailyButton()}
// A3 星级：只罚错着与提示（解法是唯一强制线，不存在「更短」的走法）
// D3：大子阈值与 Python `core.model.BIG_CAPTURE_VALUE`（450）同源，
// 两端必须同一个集合，否则同一步棋一边喊一边不响。
const BIG_CAPTURE_TYPES=['rook','cannon','horse','archer','thunder','guard','patrol'];
function isBigCapture(captured){return (captured||[]).some(piece=>BIG_CAPTURE_TYPES.includes(piece.type))}
function shakeBoard(){const shell=$('#boardShell');if(!shell)return;
  shell.classList.remove('board-shake');void shell.offsetWidth;shell.classList.add('board-shake');
  setTimeout(()=>shell.classList.remove('board-shake'),320)}
// ===== 批次 A：训练进度（章节化 + 连对挑战）================================
// 进度存独立键 xh-training，**不进 app.preferences**，因此绝不随
// persistPreferences 的 /api/me/preferences POST 上传（零采集）。坚持天数仍在 xh-daily。
const TRAINING_KEY='xh-training';
const TRAINING_ORDER=['揭竿','破釜','逐鹿','垓下','定鼎'];
function readTraining(){try{const t=JSON.parse(localStorage.getItem(TRAINING_KEY)||'{}');return {stars:t.stars||{},unlocked:Array.isArray(t.unlocked)?t.unlocked:['揭竿'],streak:{best:Number((t.streak||{}).best)||0}}}catch{return {stars:{},unlocked:['揭竿'],streak:{best:0}}}}
function writeTraining(t){safeStorageSet(TRAINING_KEY,JSON.stringify(t))}
function recordTrainingStar(id,stars){const t=readTraining();t.stars[id]=Math.max(t.stars[id]||0,stars);t.unlocked=unlockedChapters(t.stars,app.trainingPuzzles||[]);writeTraining(t)}
function unlockedChapters(stars,puzzles){const solved=stars||{};const out=[];for(let i=0;i<TRAINING_ORDER.length;i++){if(i===0){out.push(TRAINING_ORDER[i]);continue}if(!out.includes(TRAINING_ORDER[i-1]))continue;const prev=(puzzles||[]).filter(p=>p.chapter===TRAINING_ORDER[i-1]&&!((p.tags||[]).includes('drill')));if(prev.length>0&&prev.every(p=>(solved[p.id]||0)>=1))out.push(TRAINING_ORDER[i])}return out}
function poolForTraining(stars,unlocked,dailyId,puzzles){const solved=stars||{};const open=unlocked||[];const rank=p=>{const s=solved[p.id]||0;return s===0?0:(s<3?1:2)};return (puzzles||[]).filter(p=>p.chapter&&open.includes(p.chapter)&&!((p.tags||[]).includes('drill'))&&p.id!==dailyId).map((p,i)=>({p,i,r:rank(p)})).sort((a,b)=>a.r-b.r||TRAINING_ORDER.indexOf(a.p.chapter)-TRAINING_ORDER.indexOf(b.p.chapter)||a.i-b.i).map(x=>x.p)}
function softHintDue(n){return (n||0)>=5}
function puzzleStars(session){const penalty=(session.misses||0)+(session.hints||0);return penalty===0?3:(penalty<=2?2:1)}
// 连对挑战会话（一错即止）。scored=true 计分态屏蔽文字提示。
function refreshStreakButton(){const btn=$('#streakPuzzleButton');if(!btn)return;const meta=$('#streakPuzzleMeta');const best=readTraining().streak.best||0;if(meta)meta.textContent=best?t('training.streakBest',{count:best}):t('training.streakSub')}
async function startStreakRun(){try{const tp=readTraining();// 连对池必须覆盖全部难度，不能只用当前筛选档的 app.trainingPuzzles
  const all=[...(await api('/api/puzzles?difficulty=beginner')),...(await api('/api/puzzles?difficulty=advanced')),...(await api('/api/puzzles?difficulty=master'))];app.trainingPuzzles=all;const dailyPuzzle=await api('/api/daily');const dailyId=dailyPuzzle&&dailyPuzzle.puzzle?dailyPuzzle.puzzle.id:null;const pool=poolForTraining(tp.stars,tp.unlocked,dailyId,all);if(!pool.length){toast(t('training.streakEmpty'),'warn');return}$('#trainingDialog').close();hideStreakBanner();app.streakRun={correct:0,pool,used:new Set(),scored:true};nextStreakPuzzle()}catch(error){toast(error.message,'error')}}
function nextStreakPuzzle(){const run=app.streakRun;if(!run)return;const next=run.pool.find(p=>!run.used.has(p.id));if(!next){endStreakRun();return}run.used.add(next.id);startStreakPuzzle(next)}
async function startStreakPuzzle(summary){try{// 池里是 summary（无 document/solution），按 id 取完整题面再开局
  const data=await api(`/api/puzzles/${encodeURIComponent(summary.id)}?reveal=true`);app.dailyDay=null;app.selectedPuzzle=data;app.puzzleSession={...data,step:0,misses:0,hints:0,hintStage:0,scored:true,streak:true};$('#trainingDialog').close();await importDocument(data.document,'local');startStreakTimer();toast(t('toast.puzzle_started'))}catch(error){toast(error.message,'error')}}
let streakTimer=null;
function startStreakTimer(){stopStreakTimer();streekSkipHidden(true);streakTimer=setTimeout(()=>{streekSkipHidden(false);toast(t('training.streakSkipHint'))},60000)}
function streekSkipHidden(hidden){const b=$('#streakSkipButton');if(b)b.hidden=hidden}
function stopStreakTimer(){if(streakTimer)clearTimeout(streakTimer);streakTimer=null}
function skipStreakPuzzle(){endStreakRun()}
function endStreakRun(){const run=app.streakRun;if(!run)return;stopStreakTimer();const correct=run.correct;const tp=readTraining();const previousBest=tp.streak.best||0;const isRecord=correct>previousBest;if(isRecord){tp.streak.best=correct;writeTraining(tp)}app.streakRun=null;app.puzzleSession=null;streekSkipHidden(true);showStreakBanner(correct,previousBest,isRecord);refreshStreakButton()}
function showStreakBanner(correct,previousBest,isRecord){const banner=$('#streakBanner');if(!banner)return;const lines=[t('training.streakRound',{count:correct})];if(isRecord)lines.push(t('training.streakRecord',{count:correct-previousBest}));else{lines.push(t('training.streakNoRecord'));lines.push(t('training.streakGap',{count:Math.max(1,previousBest-correct+1)}))}lines.push(t('training.streakKept'));lines.push(t('training.streakPractice'));const body=$('#streakBannerBody');if(body)body.textContent=lines.join('\n');banner.hidden=false}
function hideStreakBanner(){const b=$('#streakBanner');if(b)b.hidden=true}
function puzzleMoveKey(move){return `${move.from.row},${move.from.col}-${move.to.row},${move.to.col}`}
function checkPuzzleProgress(){
  const session=app.puzzleSession;if(!session||!app.state?.history.length)return;
  const actual=app.state.history.at(-1)?.move;if(!actual)return;
  const key=puzzleMoveKey(actual);
  // 程序刚替对手落的那一着会再触发一次本函数，跳过判定（游标已在下面推进过）
  if(session.pendingAuto===key){session.pendingAuto=null;return}
  const expected=session.solution[session.step];if(!expected)return;
  if(puzzleMoveKey(expected)!==key){
    session.misses=(session.misses||0)+1;session.consecutiveMisses=(session.consecutiveMisses||0)+1;
    // 连对挑战：一错即止
    if(session.streak){stopStreakTimer();setTimeout(()=>endStreakRun(),380);return}
    toast(t('toast.puzzle_wrong'),'warn');
    if(!session.scored&&softHintDue(session.consecutiveMisses))setTimeout(()=>toast(t('training.hintDue')),420);
    return
  }
  session.consecutiveMisses=0;session.step++;session.hintStage=0;
  if(session.step>=session.solution.length){
    const stars=puzzleStars(session);
    if(session.streak&&app.streakRun){app.streakRun.correct+=1;stopStreakTimer();setTimeout(()=>nextStreakPuzzle(),500);return}
    if(!session.scored)recordTrainingStar(session.id,stars);
    toast(`${t('toast.puzzle_solved')} ${'★'.repeat(stars)}${'☆'.repeat(3-stars)}`,'success');recordDailySolved(session);app.puzzleSession=null;return
  }
  toast(t('toast.puzzle_continue'));
  // 交替序列：偶数下标归玩家、奇数下标是**对手的被迫应着**，由程序自动落。
  // 少了这一步，多步题第二步就会把对手的应着当成玩家的答案（必错）。
  if(session.step%2===1){const reply=session.solution[session.step];session.step++;session.hintStage=0;session.pendingAuto=puzzleMoveKey(reply);send('move',{from:reply.from,to:reply.to})}
}

board.addEventListener('pointerdown',async e=>{const pos=positionAt(e);if(pos){app.dragging={start:pos,x:e.clientX,y:e.clientY};const piece=app.state?.pieces.find(p=>p.row===pos.row&&p.col===pos.col);if(canControl(piece)&&(!app.selected||app.selected.row!==pos.row||app.selected.col!==pos.col)){app.selected=piece;playSound('select');await loadLegal(piece)}}});
board.addEventListener('pointerup',async e=>{const pos=positionAt(e),drag=app.dragging;app.dragging=null;if(!pos)return;if(app.legalPromise)await app.legalPromise.catch(()=>{});if(drag&&Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>8&&app.selected)selectOrMove(pos);else selectOrMove(pos)});board.addEventListener('pointercancel',()=>{app.dragging=null});
window.addEventListener('resize',resizeBoard);if(window.ResizeObserver)new ResizeObserver(resizeBoard).observe($('#boardShell'));$('#newGameButton').onclick=createGame;$('#joinButton').onclick=joinGame;$('#resignButton').onclick=()=>{const color=app.color||app.state?.turn;if(!confirm(t('dialog.confirm_resign',{color:t(`common.${color}`)})))return;send('resign')};$('#drawButton').onclick=()=>send('draw_offer');$('#undoButton').onclick=()=>send('undo_request');$('#pauseButton').onclick=()=>send('pause',{paused:!app.state?.paused});$('#restartButton').onclick=()=>{const playing=app.state&&!app.state.finished&&app.state.history.length>0;if(playing&&!confirm('对局尚未结束，确认重新开始？'))return;send(app.mode==='online'?'restart_request':'restart',{options:app.options});};$('#replayButton').onclick=()=>openReplay();
$('#resurrectButton').onclick=()=>{const cols=app.state?.profile?.cols||13;const value=prompt(t('prompt.resurrect_col',{cols}),'1'),col=Number(value)-1;if(!Number.isInteger(col)||col<0||col>=cols)return toast(t('toast.resurrect_col'),'warn');// The rank comes from the profile's own pawn slots instead of a hard coded
// 8/4 split, so `traditional` (10x9) aims at row 6 rather than row 8.
const home=(app.state?.profile?.pawnHomeSquares||[]).find(square=>square.col===col);if(!home)return toast(t('toast.resurrect_col'),'warn');send('resurrect',{row:home.row,col})};
$('#profileSelect').onchange=()=>{const profile=app.profiles.get($('#profileSelect').value);app.options={...(profile?.options||{})}};
$('#modeSelect').onchange=syncModeControls;
$('#moveList').onclick=e=>{const li=e.target.closest('li');if(!li)return;openReplay();setReplayIndex(Number(li.dataset.index)+1)};
$('#copyRoomButton').onclick=async()=>{if(app.roomId){await navigator.clipboard.writeText(app.roomId);toast(t('toast.room_copied'),'success')}};
$('#spectateButton').onclick=spectateGame;
$('#flipBoardButton').onclick=()=>{app.preferences.flipped=!app.preferences.flipped;persistPreferences();draw()};
$('#handicapButton').onclick=()=>{renderHandicap();$('#handicapDialog').showModal()};
$('#redPieceSlots').onchange=e=>{if(e.target.matches('[data-piece-slot]'))updateHandicapSelection(e.target)};$('#blackPieceSlots').onchange=$('#redPieceSlots').onchange;
$('#resetHandicapButton').onclick=()=>{const {profile,all}=profileSetup();app.setupSlots[profile.id]={red:all.filter(x=>x.color==='red').map(x=>x.id),black:all.filter(x=>x.color==='black').map(x=>x.id)};renderHandicap()};
$('#applyHandicapButton').onclick=()=>{const setup=selectedSetup();if(setup.red.length!==setup.black.length)return toast('双方登场棋子数量必须相同','warn');$('#handicapDialog').close();toast(`双方各 ${setup.red.length} 枚棋子登场`,'success')};
$('#accountButton').onclick=async()=>{await refreshAccount();$('#accountDialog').showModal()};$('#loginButton').onclick=()=>authenticate('login');$('#registerButton').onclick=()=>authenticate('register');$('#saveProfileButton').onclick=saveProfile;$('#cloudSaveButton').onclick=saveCloudGame;$('#syncPreferencesButton').onclick=()=>{persistPreferences();toast('偏好已同步','success')};$('#logoutButton').onclick=async()=>{try{await api('/api/auth/logout',{method:'POST'})}catch{}app.authToken=null;app.account=null;localStorage.removeItem('xh-auth-token');await refreshAccount()};
document.addEventListener('click',event=>{const button=event.target.closest('#profileAvatarPicker [data-avatar]');if(!button)return;document.querySelectorAll('#profileAvatarPicker [data-avatar]').forEach(item=>item.classList.toggle('selected',item===button));if(button.dataset.avatar)$('#profileAvatarUrl').value=''});
$('#cloudGameList').onclick=async e=>{const open=e.target.closest('[data-cloud-open]'),fav=e.target.closest('[data-cloud-favorite]'),del=e.target.closest('[data-cloud-delete]');try{if(open){const game=await api(`/api/me/games/${open.dataset.cloudOpen}`);$('#accountDialog').close();await importDocument(game.document)}if(fav){await api(`/api/me/games/${fav.dataset.cloudFavorite}/favorite`,{method:'PUT',body:JSON.stringify({favorite:fav.dataset.favorite==='true'})});await refreshCloudGames()}if(del&&confirm('确定删除这份云端棋谱？')){await api(`/api/me/games/${del.dataset.cloudDelete}`,{method:'DELETE'});await refreshCloudGames()}}catch(error){toast(error.message,'error')}};
$('#analyzeReplayButton').onclick=runAnalysis;$('#analysisMoveList').onclick=e=>{const item=e.target.closest('[data-analysis-ply]');if(item){$('#analysisDialog').close();if(!replayDialog.open)openReplay();setReplayIndex(Number(item.dataset.analysisPly))}};$('#analysisNoteToggle').onclick=()=>{const helper=$('#analysisNoteHelper');helper.hidden=!helper.hidden;$('#analysisNoteToggle').setAttribute('aria-expanded',String(!helper.hidden))};
$('#trainingButton').onclick=()=>openTraining();document.querySelector('.training-filters').onclick=e=>{const level=e.target.closest('[data-puzzle-level]');if(level){document.querySelectorAll('[data-puzzle-level]').forEach(button=>button.classList.toggle('active',button===level));openTraining(level.dataset.puzzleLevel)}};$('#puzzleList').onclick=e=>{const item=e.target.closest('[data-puzzle-id]');if(item)selectPuzzle(item.dataset.puzzleId)};$('#puzzleStartButton').onclick=startPuzzle;$('#dailyPuzzleButton').onclick=openDaily;const streakBtn=$('#streakPuzzleButton');if(streakBtn)streakBtn.onclick=startStreakRun;const skipBtn=$('#streakSkipButton');if(skipBtn)skipBtn.onclick=skipStreakPuzzle;const againBtn=$('#streakAgainButton');if(againBtn)againBtn.onclick=()=>{hideStreakBanner();startStreakRun()};refreshDailyButton();
loadAppVersion();// C2 两段式提示：先指子、再指招（与桌面 `PuzzleSession.staged_hint` 同构）
$('#puzzleHintButton').onclick=()=>{
  if(!app.selectedPuzzle)return;
  const session=app.puzzleSession;
  // 计分态（每日一题 / 连对挑战）屏蔽文字提示；星轨几何层守卫在别处，勿改。
  if(session&&session.scored)return;
  if(!session){toast(app.selectedPuzzle.hints[0]||'暂无更多提示');return}
  const move=session.solution[session.step];
  if(!move)return;
  session.hints=(session.hints||0)+1;
  if(!session.hintStage){
    session.hintStage=1;
    const pieces=app.selectedPuzzle.document?.state?.pieces||[];
    const piece=pieces.find(item=>item.row===move.from.row&&item.col===move.from.col);
    toast(`先看这一枚：${piece?t('piece_name.'+piece.type):''}`);return
  }
  const hand=Math.floor(session.step/2);
  toast(app.selectedPuzzle.hints[hand]||'暂无更多提示');
};$('#puzzleReviewButton').onclick=()=>{if(app.selectedPuzzle){$('#trainingDialog').close();openReplay(stateFromDocument(app.selectedPuzzle.document),app.selectedPuzzle.title)}};$('#importPuzzleButton').onclick=()=>$('#puzzleFileInput').click();$('#puzzleFileInput').onchange=async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;if(file.size>10*1024*1024)return toast(t('toast.file_too_large'),'warn');try{const imported=JSON.parse(await file.text()),items=Array.isArray(imported)?imported:[imported];if(!items.length||!items.every(validPuzzle))throw new Error(t('toast.invalid_puzzle'));const merged=new Map(customPuzzles().map(item=>[item.id,item]));items.forEach(item=>merged.set(item.id,item));if(safeStorageSet('xh-custom-puzzles',JSON.stringify([...merged.values()])))toast(`已导入 ${items.length} 道习题`,'success')}catch(error){toast(error.message,'error')}};
$('#showMovesButton').onclick=()=>showRecordView('moves');$('#showChatButton').onclick=()=>showRecordView('chat');$('#sendQuickChatButton').onclick=()=>sendChat(true);$('#sendChatButton').onclick=()=>sendChat(false);$('#chatInput').onkeydown=e=>{if(e.key==='Enter')sendChat(false)};
$('#soundButton').onclick=()=>{app.sound=!app.sound;$('#soundEnabled').checked=app.sound;$('#soundButton').textContent=app.sound?'♪':'♩';persistPreferences();if(app.music)startMusic();toast(app.sound?t('toast.sound_on'):t('toast.sound_off'))};
$('#closeReplayButton').onclick=closeReplay;replayDialog.addEventListener('close',()=>{stopReplay();app.replayIndex=null;app.replaySource=null;draw()});
$('#replayBegin').onclick=()=>setReplayIndex(0);$('#replayPrev').onclick=()=>setReplayIndex((app.replayIndex||0)-1);$('#replayPlay').onclick=toggleReplay;$('#replayNext').onclick=()=>setReplayIndex((app.replayIndex||0)+1);$('#replayEnd').onclick=()=>setReplayIndex(replayGame()?.history?.length||0);$('#replayProgress').oninput=e=>setReplayIndex(Number(e.target.value));$('#replayMoves').onclick=e=>{const li=e.target.closest('li');if(li)setReplayIndex(Number(li.dataset.index))};
$('#saveReplayButton').onclick=saveCurrentReplay;$('#savedReplayList').onclick=async e=>{const replay=e.target.closest('[data-replay-record]'),resume=e.target.closest('[data-continue-record]'),exportButton=e.target.closest('[data-export-record]'),del=e.target.closest('[data-delete-replay]'),records=replayRecords();if(replay)loadSavedReplay(Number(replay.dataset.replayRecord));if(resume){const record=records.find(r=>r.id===Number(resume.dataset.continueRecord));if(record)try{await importDocument(record.document)}catch(error){toast(error.message,'error')}}if(exportButton){const record=records.find(r=>r.id===Number(exportButton.dataset.exportRecord));if(record)downloadDocument(record.document)}if(del&&confirm(t('dialog.confirm_delete_replay'))){localStorage.setItem('xh-replays',JSON.stringify(records.filter(r=>r.id!==Number(del.dataset.deleteReplay))));renderSavedReplays()}};
$('#settingsButton').onclick=()=>{
  const root=$('#ruleOptions'),profile=app.profiles.get($('#profileSelect').value),available=new Set(profile?.pieceTypes||[]);
  const general=['enforce_self_check','threefold_draw'].map(key=>`<label><input type="checkbox" data-option="${key}" ${optionIsOn(key)?'checked':''}>${t(`rule.${key}`)}</label>`).join('')
    // no_progress_draw_plies is the only numeric RuleOption (default 120), so it gets a
    // select instead of a checkbox; the "" value means "off" (0 disables the check).
    +`<label>${t('rule.no_progress_draw_plies')} <select data-option-int="no_progress_draw_plies">${[0,60,120,180,240].map(plies=>`<option value="${plies}" ${Number(app.options.no_progress_draw_plies)===plies?'selected':''}>${plies||t('settings.no_progress_off')}</option>`).join('')}</select></label>`;
  const pieces=Object.entries(pieceLabels).map(([kind])=>{const key=`${kind}_appear`,enabled=available.has(kind),mandatory=kind==='king',rules=(pieceRuleKeys[kind]||[]).map(rule=>`<label><input type="checkbox" data-option="${rule}" ${optionIsOn(rule)?'checked':''}>${t(`rule.${rule}`)}</label>`).join('');return `<fieldset class="piece-rule-group ${enabled?'':'unavailable'}"><legend>${t(`piece.${kind}`)}</legend><p>${ruleText(kind)}</p><label><input type="checkbox" data-option="${key}" ${mandatory||app.options[key]!==false?'checked':''} ${!enabled||mandatory?'disabled':''}>${t('settings.piece_appear')}</label>${rules}</fieldset>`}).join('');
  root.innerHTML=`<fieldset><legend>${t('settings.general_rules')}</legend><div class="option-grid">${general}</div></fieldset><div class="piece-rule-list">${pieces}</div>`;applyPreferences();
  // 规则依赖：上游关掉时把"必然失效"的下游置灰（引擎里本来就被 and 住，置灰只是把真相显式化）。
  const syncDependencies=()=>{const deps=profile?.optionDependencies||{};for(const [child,parents] of Object.entries(deps)){const box=root.querySelector(`[data-option="${child}"]`);if(!box)continue;const enabled=parents.every(parent=>{const source=root.querySelector(`[data-option="${parent}"]`);return !source||source.checked});box.disabled=!enabled;box.title=enabled?'':t('rule.depends_disabled')}};
  syncDependencies();root.onchange=e=>{if(e.target.dataset?.option)syncDependencies()};
  $('#settingsDialog').showModal();startMusic()
};
$('#applySettings').onclick=()=>{app.options={...app.options};document.querySelectorAll('[data-option]').forEach(input=>{if(!input.disabled||input.dataset.option==='king_appear')app.options[input.dataset.option]=optionStored(input.dataset.option,input.checked)});document.querySelectorAll('[data-option-int]').forEach(input=>{app.options[input.dataset.optionInt]=Number(input.value)});app.options.king_appear=true;setTimeout(createGame)};
$('#resultRestart').onclick=()=>{$('#resultDialog').close();createGame()};

for(const [id,key] of [['systemThemeSelect','systemTheme'],['fontSelect','font'],['boardThemeSelect','boardTheme'],['pageBackgroundSelect','pageBackground'],['boardBackgroundSelect','boardBackground'],['musicStyleSelect','musicStyle']]){$(`#${id}`).onchange=e=>{app.preferences[key]=e.target.value;applyPreferences();persistPreferences();if(key==='musicStyle'){stopMusic();startMusic()}}}
$('#uploadBackgroundButton').onclick=()=>$('#backgroundFileInput').click();
$('#backgroundFileInput').onchange=async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;if(!file.type.startsWith('image/'))return toast('请选择图片文件','warn');if(file.size>12*1024*1024)return toast('图片不能超过 12 MB','warn');const id=globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;const name=file.name.replace(/\.[^.]+$/,'')||t('settings.custom_background');try{await putBackground({id,name,blob:file});await loadCustomBackgrounds();app.preferences.pageBackground=`custom:${id}`;applyPreferences();persistPreferences();$('#customBackgroundSelect').value=id;toast('自定义图片已上传','success')}catch(error){toast(error.message,'error')}};
$('#renameBackgroundButton').onclick=async()=>{const id=$('#customBackgroundSelect').value,record=app.customBackgrounds.get(id);if(!record)return;const name=prompt(t('settings.custom_background_name'),record.name)?.trim();if(!name)return;try{await putBackground({id,name,blob:record.blob});await loadCustomBackgrounds();$('#customBackgroundSelect').value=id;applyPreferences();toast('图片已重命名','success')}catch(error){toast(error.message,'error')}};
$('#deleteBackgroundButton').onclick=async()=>{const id=$('#customBackgroundSelect').value;if(!app.customBackgrounds.has(id)||!confirm('确定删除这张自定义图片？'))return;try{await removeBackground(id);for(const key of ['pageBackground','boardBackground'])if(app.preferences[key]===`custom:${id}`)app.preferences[key]='none';await loadCustomBackgrounds();applyPreferences();persistPreferences();toast('自定义图片已删除','success')}catch(error){toast(error.message,'error')}};
$('#languageSelect').onchange=async e=>{app.preferences.language=e.target.value;await setLanguage(e.target.value);applyPreferences();persistPreferences();renderSavedReplays();if(app.state){$('#turnRibbon').textContent=app.state.finished?t('status.game_over'):(app.state.paused?t('status.paused'):t('status.turn',{color:t(`common.${app.state.turn}`)}));$('#moveCount').textContent=t('common.rounds',{count:Math.ceil(app.state.history.length/2)});$('#pauseButton').textContent=app.state.paused?`▶ ${t('action.resume')}`:`Ⅱ ${t('action.pause')}`;}syncModeControls();draw()};
$('#pieceStyleSelect').onchange=e=>{app.preferences.pieceStyle=e.target.value;app.pieceImages.clear();persistPreferences();draw()};
$('#soundEnabled').onchange=e=>{app.sound=e.target.checked;$('#soundButton').textContent=app.sound?'♪':'♩';persistPreferences()};
$('#musicEnabled').onchange=e=>{app.music=e.target.checked;persistPreferences();app.music?startMusic():stopMusic()};
$('#volumeSlider').oninput=e=>{app.preferences.volume=Number(e.target.value);applyPreferences();persistPreferences()};
for(const [id,key] of [['animationEnabled','animation'],['selectionEnabled','selection'],['legalTargetsEnabled','legalTargets'],['captureHintsEnabled','captureHints'],['starHintsEnabled','starHints'],['highContrastEnabled','highContrastPieces'],['pieceBadgesEnabled','pieceBadges'],['tauntsEnabled','taunts'],['autosaveEnabled','autosave']]){$(`#${id}`).onchange=e=>{app.preferences[key]=e.target.checked;persistPreferences();draw()}}
for(const [id,key] of [['initialMinutesSelect','initialMinutes'],['countdownSecondsSelect','countdownSeconds']]){$(`#${id}`).onchange=e=>{app.preferences[key]=Number(e.target.value);persistPreferences();updateClockVisuals()}}

async function toggleFullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen()}catch(error){toast(error.message,'error')}}
async function runCommand(command){
  if(command==='new')return createGame();
  if(command==='save-local')return saveCurrentReplay();
  if(command==='history')return showStatistics();
  if(command==='export'){const gameDocument=currentGameDocument();return gameDocument?downloadDocument(gameDocument):toast(t('toast.no_export_game'),'warn')}
  if(command==='import'){return $('#gameFileInput').click()}
  if(command.startsWith('mode-')){$('#modeSelect').value=command.slice(5);syncModeControls();return createGame()}
  if(command==='undo')return send('undo_request');
  if(command==='pause')return send('pause',{paused:!app.state?.paused});
  if(command==='draw')return send('draw_offer');
  if(command==='resign')return send('resign');
  if(command==='restart')return send('restart',{options:app.options});
  if(command==='replay')return openReplay();
  if(command.startsWith('replay-')){if(!replayDialog.open)openReplay();const total=replayGame()?.history?.length||0;return setReplayIndex(command==='replay-begin'?0:command==='replay-prev'?(app.replayIndex||0)-1:command==='replay-next'?(app.replayIndex||0)+1:total)}
  if(command==='fullscreen')return toggleFullscreen();
  if(command==='toggle-panels'){document.querySelector('.workspace').classList.toggle('panels-hidden');return setTimeout(resizeBoard)}
  if(command==='settings')return $('#settingsButton').click();
  if(command==='sound')return $('#soundButton').click();
  if(command==='guide')return $('#helpDialog').showModal();
  if(command==='rules')return $('#rulesDialog').showModal();
  if(command==='about')return $('#aboutDialog').showModal();
}
document.querySelector('.menubar').onclick=e=>{const button=e.target.closest('[data-command]');if(!button)return;runCommand(button.dataset.command);document.querySelectorAll('.menu[open]').forEach(menu=>menu.removeAttribute('open'))};
document.addEventListener('click',e=>{if(!e.target.closest('.menu'))document.querySelectorAll('.menu[open]').forEach(menu=>menu.removeAttribute('open'))});
document.querySelectorAll('[data-close-dialog]').forEach(button=>button.onclick=()=>document.getElementById(button.dataset.closeDialog).close());
$('#newLocalButton').onclick=()=>runCommand('mode-local');$('#saveGameButton').onclick=saveCurrentReplay;$('#loadGameButton').onclick=()=>$('#gameFileInput').click();$('#replayButtonTop').onclick=()=>openReplay();$('#fullscreenButton').onclick=toggleFullscreen;$('#saveLocalButton').onclick=saveCurrentReplay;$('#exportButton').onclick=()=>runCommand('export');
$('#serverSettingsButton').onclick=()=>window.XionghanAndroid?.openServerSettings?.();
$('#openReplayLibraryButton').onclick=()=>{$('#statisticsDialog').close();openReplayLibrary()};$('#resetStatisticsButton').onclick=()=>{if(confirm(t('dialog.confirm_reset_stats'))){localStorage.removeItem('xh-statistics');localStorage.removeItem('xh-stat-keys');showStatistics()}};
$('#gameFileInput').onchange=async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;if(file.size>10*1024*1024)return toast(t('toast.file_too_large'),'warn');try{const text=await file.text();let gameDocument;try{gameDocument=JSON.parse(text)}catch{gameDocument={position:text}}await importDocument(gameDocument)}catch(error){toast(t('toast.read_failed',{message:error.message}),'error')}};
document.addEventListener('keydown',e=>{const key=e.key.toLowerCase(),command=e.key==='F1'?'guide':e.key==='F11'?'fullscreen':(e.ctrlKey&&key==='n'?'new':e.ctrlKey&&key==='s'?'export':e.ctrlKey&&key==='o'?'import':e.ctrlKey&&key==='z'?'undo':e.ctrlKey&&key==='r'?'replay':null);if(command){e.preventDefault();runCommand(command)}});

async function restore(){try{app.preferences={...app.preferences,...JSON.parse(localStorage.getItem('xh-preferences')||'{}')}}catch{}await setLanguage(app.preferences.language||localStorage.getItem('xh-language')||'zh-CN');maybeShowOnboarding();await loadPreferences();renderSavedReplays();syncModeControls();$('#soundButton').textContent=app.sound?'♪':'♩';if(window.XionghanAndroid){document.body.classList.add('android-client');$('#serverSettingsButton').hidden=false}try{const profiles=await api('/api/profiles');app.profiles=new Map(profiles.map(profile=>[profile.id,profile]));negatedOptions=new Set(profiles[0]?.negatedOptions||[]);app.ruleVersion=profiles[0]?.ruleVersion??app.ruleVersion;await refreshAccount();const saved=JSON.parse(localStorage.getItem('xh-session'));if(saved?.roomId){const snapshot=await api(`/api/rooms/${saved.roomId}`,{headers:{'X-Room-Token':saved.token}});app.roomId=saved.roomId;app.token=saved.token;app.color=saved.color;app.spectator=!!saved.spectator;receiveSnapshot(snapshot);connect();return}}catch{}await createGame()}
restore();

// 仅离屏证据脚本使用，生产路径不启用。
// 只有页面在本模块加载之前就把 window.__XH_DEBUG__ 置为 'offscreen'，
// 才把离屏拍摄需要的少量成员挂到 window.__xh；其余情况一行都不挂——
// 不新增全局、不改 DOM、不写 storage，也不进入任何 export / 公开 API 清单。
if (window.__XH_DEBUG__ === 'offscreen') {
  window.__xh = { app, draw, resizeBoard, geometry };
}
