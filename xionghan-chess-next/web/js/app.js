const $ = (selector) => document.querySelector(selector);
const board = $('#board');
const ctx = board.getContext('2d');
const replayDialog = $('#replayDialog');
const replayBoard = $('#replayBoard');
const replayCtx = replayBoard.getContext('2d');
const app = {
  roomId: null, token: null, color: null, revision: 0, state: null, socket: null,
  mode: 'ai', selected: null, legal: [], capturable: [], dragging: null,
  replayIndex: null, replaySource: null, replayTimer: null, sound: true, music: true,
  preferences: {font:'system',boardTheme:'classic',background:'none',pieceStyle:'traditional',musicStyle:'fc',volume:70,animation:true,selection:true,legalTargets:true,captureHints:true,autosave:true,initialMinutes:20,countdownSeconds:30},
  options: {}, profiles: new Map(), pieceImages: new Map(), animation: null, legalPromise: null, resultKey: null, reconnectTimer: null,
};
const sounds={select:new Audio('/assets/sounds/choose.wav'),move:new Audio('/assets/sounds/drop.wav'),capture:new Audio('/assets/sounds/eat.wav'),check:new Audio('/assets/sounds/warn.wav'),win:new Audio('/assets/sounds/fc_victory_sound.wav'),lose:new Audio('/assets/sounds/fc_defeat_sound.wav'),button:new Audio('/assets/sounds/button.wav')};
let backgroundMusic=null;
function persistPreferences(){localStorage.setItem('xh-preferences',JSON.stringify(app.preferences));localStorage.setItem('xh-sound',JSON.stringify({sound:app.sound,music:app.music}))}
function applyPreferences(){const p=app.preferences;document.body.dataset.font=p.font;document.body.dataset.boardTheme=p.boardTheme;document.body.dataset.background=p.background;document.documentElement.style.setProperty('--scene-image',p.background==='none'?'none':`url('/assets/backgrounds/${p.background}.jpg')`);document.documentElement.style.setProperty('--board-line',({classic:'#6d3c11',green:'#3a6b1e',blue:'#2471a3',purple:'#7d3c98',dark:'#aaa'})[p.boardTheme]||'#6d3c11');document.documentElement.style.setProperty('--board-text',({classic:'#8b4513',green:'#2d5016',blue:'#1a5276',purple:'#6c3483',dark:'#ddd'})[p.boardTheme]||'#8b4513');$('#fontSelect').value=p.font;$('#boardThemeSelect').value=p.boardTheme;$('#backgroundSelect').value=p.background;$('#pieceStyleSelect').value=p.pieceStyle;$('#musicStyleSelect').value=p.musicStyle;$('#volumeSlider').value=p.volume;$('#volumeValue').textContent=`${p.volume}%`;$('#soundEnabled').checked=app.sound;$('#musicEnabled').checked=app.music;$('#animationEnabled').checked=p.animation!==false;$('#selectionEnabled').checked=p.selection!==false;$('#legalTargetsEnabled').checked=p.legalTargets!==false;$('#captureHintsEnabled').checked=p.captureHints!==false;$('#autosaveEnabled').checked=p.autosave!==false;$('#initialMinutesSelect').value=String(p.initialMinutes||20);$('#countdownSecondsSelect').value=String(p.countdownSeconds??30);Object.values(sounds).forEach(a=>{a.volume=p.volume/100});if(backgroundMusic)backgroundMusic.volume=p.volume/200;draw()}
function loadPreferences(){try{app.preferences={...app.preferences,...JSON.parse(localStorage.getItem('xh-preferences')||'{}')};const s=JSON.parse(localStorage.getItem('xh-sound')||'{}');if(typeof s.sound==='boolean')app.sound=s.sound;if(typeof s.music==='boolean')app.music=s.music}catch{}applyPreferences()}
function playSound(key){if(!app.sound)return;const audio=sounds[key];if(audio){audio.currentTime=0;audio.volume=app.preferences.volume/100;audio.play().catch(()=>{})}}
function startMusic(){if(!app.music)return;if(!backgroundMusic||backgroundMusic.dataset.style!==app.preferences.musicStyle){if(backgroundMusic)backgroundMusic.pause();backgroundMusic=new Audio(`/assets/sounds/${app.preferences.musicStyle==='qq'?'qq_background_sound.wav':'fc_background_sound.wav'}`);backgroundMusic.loop=true;backgroundMusic.dataset.style=app.preferences.musicStyle;backgroundMusic.volume=app.preferences.volume/200}backgroundMusic.play().catch(()=>{})}
function stopMusic(){if(backgroundMusic){backgroundMusic.pause();backgroundMusic.currentTime=0}}
function replayGame(){return app.replaySource||app.state}
function openReplay(source=null,title='当前对局'){const game=source||app.state;if(!game?.history?.length)return toast('当前对局暂无棋谱');stopReplay();app.replaySource=source;app.replayIndex=game.history.length;$('#replayTitle').textContent=title;updateReplayUI();renderSavedReplays();if(!replayDialog.open)replayDialog.showModal();requestAnimationFrame(draw)}
function closeReplay(){stopReplay();app.replayIndex=null;app.replaySource=null;if(replayDialog.open)replayDialog.close();draw()}
function stopReplay(){if(app.replayTimer){clearInterval(app.replayTimer);app.replayTimer=null}$('#replayPlay').textContent='▶';$('#replayPlay').title='播放'}
function toggleReplay(){if(app.replayTimer){stopReplay();return}const total=replayGame()?.history?.length||0;if((app.replayIndex??total)>=total)setReplayIndex(0);app.replayTimer=setInterval(()=>{const current=app.replayIndex??0;if(current>=total){stopReplay();return}setReplayIndex(current+1)},850);$('#replayPlay').textContent='Ⅱ';$('#replayPlay').title='暂停'}
function setReplayIndex(step){const total=replayGame()?.history?.length||0;app.replayIndex=Math.max(0,Math.min(total,step));updateReplayUI();draw()}
function updateReplayUI(){const game=replayGame(),total=game?.history?.length||0,current=app.replayIndex===null?total:app.replayIndex;$('#replayProgress').max=total;$('#replayProgress').value=current;$('#replayStepInfo').textContent=`${current} / ${total}`;$('#replayMoves').innerHTML=(game?.history||[]).map((h,i)=>`<li data-index="${i+1}" class="${app.replayIndex===i+1?'active':''}">${i+1}. ${h.notation||''}</li>`).join('')}
function currentGameDocument(){if(!app.state)return null;const state=JSON.parse(JSON.stringify(app.state));delete state.profile;delete state.check;delete state.replay;return{formatVersion:1,profileId:app.state.profile.id,options:app.state.profile.options,state,snapshots:(app.state.replay||[]).slice(0,-1),savedAt:new Date().toISOString()}}
function normalizeRecord(record){if(record?.document)return record;if(!record?.profile?.id||!record?.replay?.length)return null;const state=record.replay.at(-1);return{id:record.id||Date.now(),savedAt:record.savedAt||new Date().toISOString(),document:{formatVersion:1,profileId:record.profile.id,options:record.profile.options||{},state,snapshots:record.replay.slice(0,-1),savedAt:record.savedAt||new Date().toISOString()}}}
function replayRecords(){try{return JSON.parse(localStorage.getItem('xh-replays')||'[]').map(normalizeRecord).filter(Boolean)}catch{return[]}}
function stateFromDocument(document){const profile=app.profiles.get(document.profileId)||app.state?.profile||{id:document.profileId,title:document.profileId,rows:13,cols:13,archerStarPoints:[]};return{...JSON.parse(JSON.stringify(document.state)),profile:{...profile,options:document.options||profile.options||{}},check:false,replay:[...(document.snapshots||[]),document.state]}}
function storeReplay(document,{silent=false,autoKey=null}={}){const records=replayRecords();if(autoKey&&records.some(record=>record.autoKey===autoKey))return;records.unshift({id:Date.now(),savedAt:document.savedAt,document,autoKey});localStorage.setItem('xh-replays',JSON.stringify(records.slice(0,50)));renderSavedReplays();if(!silent)toast('棋局已保存到本机棋谱库')}
function saveCurrentReplay(){const document=currentGameDocument();if(!document)return toast('当前没有可保存的棋局');storeReplay(document)}
function renderSavedReplays(){const list=$('#savedReplayList');if(!list)return;const records=replayRecords();list.innerHTML=records.length?records.map(r=>{const state=r.document.state,total=state.history?.length||0,result=state.winner?(state.winner==='red'?'红方胜':'黑方胜'):(state.draw?'和棋':'未结束');return `<div class="saved-replay"><div><strong>${result} · ${total} 步</strong><span>${new Date(r.savedAt).toLocaleString('zh-CN')}</span></div><div class="saved-replay-actions"><button data-replay-record="${r.id}">复盘</button><button data-continue-record="${r.id}">继续</button><button data-export-record="${r.id}">导出</button><button data-delete-replay="${r.id}">删除</button></div></div>`}).join(''):'<span>暂无已保存棋谱</span>'}
function loadSavedReplay(id){const record=replayRecords().find(r=>r.id===id);if(!record)return;openReplay(stateFromDocument(record.document),new Date(record.savedAt).toLocaleString('zh-CN'))}
function openReplayLibrary(){if(app.state?.history?.length)return openReplay();const record=replayRecords()[0];if(record)return loadSavedReplay(record.id);toast('本地棋谱库暂无记录')}
function loadStatistics(){try{return{games:0,redWins:0,blackWins:0,draws:0,moves:0,...JSON.parse(localStorage.getItem('xh-statistics')||'{}')}}catch{return{games:0,redWins:0,blackWins:0,draws:0,moves:0}}}
function recordFinishedGame(key){let recorded=[];try{recorded=JSON.parse(localStorage.getItem('xh-stat-keys')||'[]');if(!Array.isArray(recorded))recorded=[]}catch{}if(recorded.includes(key))return;const stats=loadStatistics();stats.games++;stats.moves+=app.state.history.length;if(app.state.draw)stats.draws++;else if(app.state.winner==='red')stats.redWins++;else if(app.state.winner==='black')stats.blackWins++;localStorage.setItem('xh-statistics',JSON.stringify(stats));localStorage.setItem('xh-stat-keys',JSON.stringify([key,...recorded].slice(0,200)));if(app.preferences.autosave!==false){const document=currentGameDocument();if(document)storeReplay(document,{silent:true,autoKey:key})}}
function showStatistics(){const stats=loadStatistics(),decided=Math.max(1,stats.games-stats.draws),redRate=stats.games?stats.redWins*100/decided:0;$('#statisticsSummary').innerHTML=`<strong>${stats.games}</strong><span>总对局</span><strong>${stats.redWins}</strong><span>红方胜</span><strong>${stats.blackWins}</strong><span>黑方胜</span><strong>${stats.draws}</strong><span>和棋</span><strong>${stats.moves}</strong><span>累计走子</span><strong>${redRate.toFixed(1)}%</strong><span>红方胜率</span>`;if(!$('#statisticsDialog').open)$('#statisticsDialog').showModal()}
function downloadDocument(gameDocument){const filename=`xionghan_${new Date().toISOString().replace(/[:.]/g,'-')}.xhgame`,content=JSON.stringify(gameDocument,null,2);if(window.XionghanAndroid?.saveGame){window.XionghanAndroid.saveGame(filename,content);toast('请选择棋谱保存位置');return}const url=URL.createObjectURL(new Blob([content],{type:'application/json'})),link=documentNode('a',{href:url,download:filename});document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('棋局文件已导出')}
function documentNode(tag,attrs){const node=document.createElement(tag);Object.assign(node,attrs);return node}
async function importDocument(document,mode){const targetMode=mode||(app.mode==='online'?'local':app.mode||'local');const data=await api('/api/rooms/import',{method:'POST',body:JSON.stringify({document,mode:targetMode,playerName:'玩家',playerColor:$('#colorSelect').value,difficulty:$('#difficultySelect').value})});closeReplay();acceptSession(data);$('#modeSelect').value=targetMode;syncModeControls();toast(targetMode==='local'?'已载入为双人同机对局':'已载入人机对局')}

const labels = {
  king_can_leave_palace:'汉/汗允许出九宫', king_diagonal_in_palace:'汉/汗在九宫内可斜走',
  king_lose_diagonal_outside_palace:'汉/汗出九宫后失去斜走',
  invasion_victory:'进入敌方九宫获胜', advisor_can_leave_palace:'仕/士允许出宫',
  advisor_gain_straight_outside_palace:'仕/士出九宫后可直走',
  elephant_can_cross_river:'相/象允许过长城阴山',
  elephant_gain_jump_two_enemy_territory:'相/象进入敌境后可横竖两格',
  horse_straight_three:'马允许直走三格',
  archer_enhanced_mode:'加强射/䠶（自由斜走三格）',
  pawn_fast_move_before_enemy_territory:'兵卒进入敌境前可快速行军',
  pawn_backward_at_base:'兵卒到底线可后退', pawn_full_movement_at_base:'兵卒到底线四向移动',
  pawn_resurrection:'兵卒复活', pawn_promotion:'兵卒升变', enforce_self_check:'禁止送将',
  threefold_draw:'三次重复和棋'
};
const pieceLabels = {
  king:'汉/汗登场',rook:'车登场',horse:'马登场',elephant:'相/象登场',advisor:'仕/士登场',
  cannon:'炮登场',pawn:'兵/卒登场',guard:'尉/卫登场',archer:'射登场',thunder:'檑登场',
  armor:'甲/胄登场',assassin:'刺/伺登场',shield:'楯/碷登场',patrol:'巡/廵登场'
};
const pieceRuleKeys={
  king:['king_can_leave_palace','king_diagonal_in_palace','king_lose_diagonal_outside_palace','invasion_victory'],
  horse:['horse_straight_three'],elephant:['elephant_can_cross_river','elephant_gain_jump_two_enemy_territory'],
  advisor:['advisor_can_leave_palace','advisor_gain_straight_outside_palace'],
  pawn:['pawn_fast_move_before_enemy_territory','pawn_backward_at_base','pawn_full_movement_at_base','pawn_resurrection','pawn_promotion'],
  archer:['archer_enhanced_mode']
};
const pieceDescriptions={king:'主帅；可配置出九宫与攻入敌宫获胜',rook:'横竖直行，路径不可有子',horse:'日字走法，受蹩马腿限制',elephant:'斜走两格，受象眼与过界规则限制',advisor:'基础为九宫内斜走一格',cannon:'直线移动，隔一子吃子',pawn:'向前推进，进入敌境后可横走',guard:'沿直线或斜线隔一子跳',archer:'弱化沿有效星轨，强化可脱离轨道',thunder:'八方向移动，近身攻击落单敌子',armor:'直行并通过三子连线夹击',assassin:'直行至空位并反向兑子',shield:'隔一子跳，自身不可被吃',patrol:'在指定边界线上横移'};
const names = {red:{king:'漢',rook:'俥',horse:'傌',elephant:'相',advisor:'仕',cannon:'炮',pawn:'兵',guard:'尉',archer:'射',thunder:'檑',armor:'甲',assassin:'刺',shield:'楯',patrol:'巡'},black:{king:'汗',rook:'車',horse:'馬',elephant:'象',advisor:'士',cannon:'砲',pawn:'卒',guard:'衛',archer:'䠶',thunder:'礌',armor:'胄',assassin:'伺',shield:'碷',patrol:'廵'}};

async function api(path, options={}) { const response=await fetch(path,{headers:{'Content-Type':'application/json'},...options}); const data=await response.json(); if(!response.ok) throw new Error(data.detail||'请求失败'); return data; }
function toast(message){const el=$('#toast');el.textContent=message;el.classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove('show'),2200)}
function formatClock(ms=0){const total=Math.max(0,Math.ceil(ms/1000));return `${String(Math.floor(total/60)).padStart(2,'0')}:${String(total%60).padStart(2,'0')}`}

async function createGame(){
  closeSocket();
  try{
    app.preferences.initialMinutes=Number($('#initialMinutesSelect').value);app.preferences.countdownSeconds=Number($('#countdownSecondsSelect').value);persistPreferences();
    const data=await api('/api/rooms',{method:'POST',body:JSON.stringify({profileId:$('#profileSelect').value,mode:$('#modeSelect').value,playerName:'玩家',playerColor:$('#colorSelect').value,difficulty:$('#difficultySelect').value,options:app.options,initialMinutes:app.preferences.initialMinutes})});
    acceptSession(data);toast(data.snapshot.mode==='online'?`房间 ${data.roomId} 已创建`:(data.snapshot.mode==='local'?'双人同机对局已开始':'人机对局已开始'));
  }catch(error){toast(error.message)}
}
async function joinGame(){
  const code=$('#roomInput').value.trim().toUpperCase(); if(!code)return toast('请输入房间号');
  try{const data=await api(`/api/rooms/${code}/join`,{method:'POST',body:JSON.stringify({playerName:'玩家二'})});acceptSession(data);toast('已加入房间')}catch(error){toast(error.message)}
}
function acceptSession(data){app.roomId=data.roomId;app.token=data.token;app.color=data.color;app.resultKey=null;receiveSnapshot(data.snapshot);localStorage.setItem('xh-session',JSON.stringify({roomId:app.roomId,token:app.token,color:app.color,mode:app.mode}));connect()}
function connect(){
  if(!app.roomId||!app.token||app.socket?.readyState===WebSocket.CONNECTING)return;clearTimeout(app.reconnectTimer);const protocol=location.protocol==='https:'?'wss':'ws'; app.socket=new WebSocket(`${protocol}://${location.host}/ws/${app.roomId}?token=${encodeURIComponent(app.token)}`);
  app.socket.onopen=()=>{$('#connectionText').textContent=app.mode==='local'?'双人同机 · 本地对弈':'已连接 · 状态同步正常'};
  app.socket.onmessage=e=>{const message=JSON.parse(e.data);if(message.type==='state')receiveSnapshot(message.payload);else if(message.type==='chat')appendChat(message.payload);else if(message.type==='error'){toast(message.payload.message);if(message.payload.state)receiveSnapshot(message.payload.state)}};
  app.socket.onclose=()=>{$('#connectionText').textContent='连接中断 · 正在重连';app.socket=null;clearTimeout(app.reconnectTimer);app.reconnectTimer=setTimeout(()=>{if(app.roomId)connect()},1800)};
}
function closeSocket(){clearTimeout(app.reconnectTimer);if(app.socket){app.socket.onclose=null;app.socket.close()}app.socket=null}
function send(type,payload={}){if(!app.socket||app.socket.readyState!==WebSocket.OPEN)return toast('连接尚未就绪');app.socket.send(JSON.stringify({type,roomId:app.roomId,revision:app.revision,payload,protocolVersion:1}))}
function appendChat(payload){const list=$('#chatMessages'),item=document.createElement('div');item.className=`chat-message ${payload.color||''}`;const sender=document.createElement('strong');sender.textContent=`${payload.sender||'玩家'}：`;item.append(sender,document.createTextNode(payload.text||''));list.append(item);list.scrollTop=list.scrollHeight}
function sendChat(quick=false){const input=$('#chatInput'),text=(quick?$('#quickChatSelect').value:input.value).trim();if(!text)return;send('chat',{text,quick});if(!quick)input.value=''}
function showRecordView(view){const chat=view==='chat';$('#chatView').hidden=!chat;$('#moveList').hidden=chat;$('#moveCount').hidden=chat;$('#showMovesButton').classList.toggle('active',!chat);$('#showChatButton').classList.toggle('active',chat)}
function receiveSnapshot(snapshot){
  const previous=app.state,revisionChanged=snapshot.revision!==app.revision;app.revision=snapshot.revision;app.state=snapshot.game;app.mode=snapshot.mode;app.options=snapshot.game.profile.options;$('#modeSelect').value=app.mode;syncModeControls();if(revisionChanged){app.selected=null;app.legal=[];app.capturable=[]}
  $('#roomCode').textContent=snapshot.roomId;$('#roomInput').value=snapshot.roomId;$('#turnRibbon').textContent=app.state.finished?'对局结束':(app.state.paused?'对局已暂停':`${app.state.turn==='red'?'红方':'黑方'}行棋`);
  $('#thinking').hidden=!(snapshot.mode==='ai'&&app.state.turn!==app.color&&!app.state.finished&&!app.state.paused);$('#pauseOverlay').hidden=!app.state.paused;renderMeta(snapshot);resizeBoard();
  if(previous&&app.state.history.length>previous.history.length){const last=app.state.history.at(-1);playSound(last.captured?.length?'capture':app.state.check?'check':'move');if(app.preferences.animation!==false){app.animation={target:last.move.to,capture:!!last.captured?.length,started:performance.now()};requestAnimationFrame(animate)}}
  if(app.state.finished)showResult();
  if(app.state.pendingDrawOffer&&app.state.pendingDrawOffer!==app.color&&confirm('对手请求和棋，是否接受？'))send('draw_response',{accept:true});
  else if(app.state.pendingDrawOffer&&app.state.pendingDrawOffer!==app.color)send('draw_response',{accept:false});
  if(app.state.pendingUndoOffer&&app.state.pendingUndoOffer!==app.color&&confirm('对手请求悔棋，是否接受？'))send('undo_response',{accept:true});
  else if(app.state.pendingUndoOffer&&app.state.pendingUndoOffer!==app.color)send('undo_response',{accept:false});
}
function updateClockVisuals(){if(!app.state)return;for(const color of ['red','black']){const clock=$(`#${color}Clock`);clock.textContent=formatClock(app.state.clocksMs[color]);clock.classList.toggle('countdown',!app.state.paused&&app.preferences.countdownSeconds>0&&app.state.clocksMs[color]<=app.preferences.countdownSeconds*1000)}}
function renderMeta(snapshot){
  updateClockVisuals();
  for(const color of ['red','black']){const player=snapshot.players.find(p=>p.color===color);$(`#${color}Status`).textContent=snapshot.mode==='local'?(color==='red'?'本机玩家一':'本机玩家二'):(player?(player.connected?'在线':'暂时离线'):'等待落座');$(`#${color}Captured`).innerHTML=(app.state.captured[color]||[]).map(p=>`<span>${names[color][p.type]}</span>`).join('')}
  $('#moveList').innerHTML=app.state.history.map((h,i)=>`<li data-index="${i}">${h.notation}</li>`).join('');$('#moveCount').textContent=`${Math.ceil(app.state.history.length/2)} 回合`;const list=$('#moveList');list.scrollTop=list.scrollHeight;
  const myTurn=(app.mode==='local'||app.state.turn===app.color)&&!app.state.finished&&!app.state.paused;$('#resignButton').disabled=app.state.finished;$('#drawButton').disabled=!myTurn;$('#undoButton').disabled=!app.state.history.length||app.state.paused;$('#resurrectButton').disabled=!myTurn;$('#pauseButton').disabled=app.state.finished;$('#pauseButton').textContent=app.state.paused?'▶ 继续':'Ⅱ 暂停';
}
function showResult(){const winner=app.state.winner,key=`${app.roomId}:${winner||'draw'}:${app.state.resultReason}:${app.state.history.length}`;$('#resultMark').textContent=winner?(winner==='red'?'漢':'汗'):'和';$('#resultTitle').textContent=winner?`${winner==='red'?'红方':'黑方'}胜利`:'和棋';$('#resultText').textContent=({checkmate:'将死',king_captured:'主帅被擒',palace_invasion:'主帅攻入敌方九宫',stalemate:'困毙',timeout:'超时判负',resignation:'认输',disconnect_timeout:'断线超时',draw_agreement:'双方议和',threefold_repetition:'三次重复局面',no_progress:'长时间无进展'})[app.state.resultReason]||'对局结束';if(app.resultKey!==key){playSound(app.mode==='local'||winner===app.color?'win':'lose');recordFinishedGame(key);app.resultKey=key}if(!$('#resultDialog').open)$('#resultDialog').showModal()}
function syncModeControls(){const mode=$('#modeSelect').value;$('#difficultyRow').hidden=mode!=='ai';$('#colorRow').hidden=mode==='local';$('#joinRow').hidden=mode!=='online';$('#connectionText').textContent=mode==='local'?'双人同机 · 本地对弈':(mode==='ai'?'人机对战':'网络对战')}
function canControl(piece){return piece&&!app.state.paused&&piece.color===app.state.turn&&(app.mode==='local'||piece.color===app.color)}

function resizeBoard(){const rect=board.parentElement.getBoundingClientRect();if(rect.width<2||rect.height<2)return;const dpr=Math.min(devicePixelRatio||1,2),width=Math.max(1,Math.floor(rect.width*dpr)),height=Math.max(1,Math.floor(rect.height*dpr));if(board.width!==width)board.width=width;if(board.height!==height)board.height=height;board.style.width=`${rect.width}px`;board.style.height=`${rect.height}px`;draw()}
function geometry(){const model=replayGame(),rows=model?.profile?.rows||13,cols=model?.profile?.cols||13,w=board.clientWidth,h=board.clientHeight,pad=Math.min(w,h)*.055;return{rows,cols,pad,cw:(w-pad*2)/(cols-1),ch:(h-pad*2)/(rows-1),w,h}}
function positionAt(event){const r=board.getBoundingClientRect(),g=geometry();const col=Math.round((event.clientX-r.left-g.pad)/g.cw),row=Math.round((event.clientY-r.top-g.pad)/g.ch);return row>=0&&row<g.rows&&col>=0&&col<g.cols?{row,col}:null}
function draw(){
  if(!app.state)return;const replay=replayGame(),shown=app.replayIndex===null?app.state:(replay.replay?.[app.replayIndex]||app.state);const originalPieces=app.state.pieces;app.state.pieces=shown.pieces;const g=geometry(),dpr=board.width/g.w,styles=getComputedStyle(document.documentElement);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,g.w,g.h);ctx.strokeStyle=styles.getPropertyValue('--board-line').trim()||'#604326';ctx.lineWidth=1.25;
  if(g.rows===13)drawXionghanGrid(g);else drawStandardGrid(g);
  drawPalaces(g);if(g.rows===13){drawInitialPositionMarks(g);drawStarPoints(g)}drawHighlights(g);for(const piece of app.state.pieces)drawPiece(g,piece);drawCaptureHints(g);drawAnimation(g);app.state.pieces=originalPieces;mirrorReplayBoard();
}
function mirrorReplayBoard(){if(!replayDialog.open)return;const rect=replayBoard.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2),width=Math.max(1,Math.floor(rect.width*dpr)),height=Math.max(1,Math.floor(rect.height*dpr));if(replayBoard.width!==width)replayBoard.width=width;if(replayBoard.height!==height)replayBoard.height=height;replayCtx.setTransform(1,0,0,1,0,0);replayCtx.clearRect(0,0,width,height);const scale=Math.min(width/board.width,height/board.height),drawWidth=board.width*scale,drawHeight=board.height*scale;replayCtx.drawImage(board,(width-drawWidth)/2,(height-drawHeight)/2,drawWidth,drawHeight)}
function drawStandardGrid(g){
  for(let r=0;r<10;r++)line(g,r,0,r,8);
  for(let c=0;c<9;c++){if(c===0||c===8)line(g,0,c,9,c);else{line(g,0,c,4,c);line(g,5,c,9,c)}}
  const y=g.pad+4.5*g.ch;
  ctx.save();ctx.font=`${Math.max(16,g.cw*.38)}px KaiTi`;ctx.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--board-text').trim()||'#604326';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('楚  河',g.pad+2*g.cw,y);ctx.fillText('汉  界',g.pad+6*g.cw,y);ctx.restore();
}
function drawXionghanGrid(g){
  for(let r=0;r<13;r++)if(r!==6)line(g,r,0,r,12);
  for(let c=0;c<13;c++){line(g,0,c,5,c);line(g,7,c,12,c)}
  const y=g.pad+6*g.ch,m=Math.min(g.cw,g.ch)*.16;
  for(let c=0;c<13;c++){const x=g.pad+c*g.cw;ctx.beginPath();ctx.moveTo(x-m,y);ctx.lineTo(x+m,y);if(c>0&&c<12){ctx.moveTo(x,y-m);ctx.lineTo(x,y+m)}ctx.stroke()}
  ctx.save();ctx.font=`${Math.max(17,g.cw*.38)}px KaiTi`;ctx.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--board-text').trim()||'#604326';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('长 城',g.pad+3*g.cw,y);ctx.fillText('阴 山',g.pad+9*g.cw,y);ctx.restore();
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
function drawAnimation(g){if(!app.animation)return;const age=performance.now()-app.animation.started;if(age>360){app.animation=null;return}const progress=age/360,r=Math.min(g.cw,g.ch)*(.25+progress*.35);ctx.beginPath();ctx.arc(g.pad+app.animation.target.col*g.cw,g.pad+app.animation.target.row*g.ch,r,0,Math.PI*2);ctx.strokeStyle=app.animation.capture?`rgba(157,37,37,${1-progress})`:`rgba(49,92,72,${1-progress})`;ctx.lineWidth=5*(1-progress)+1;ctx.stroke()}
function animate(){draw();if(app.animation)requestAnimationFrame(animate)}
function drawPalaces(g){const palaces=g.rows===10?[[0,3],[7,3]]:[[1,5],[9,5]];ctx.lineWidth=1.2;for(const [r,c] of palaces){line(g,r,c,r+2,c+2);line(g,r,c+2,r+2,c)}}
function line(g,r1,c1,r2,c2){ctx.beginPath();ctx.moveTo(g.pad+c1*g.cw,g.pad+r1*g.ch);ctx.lineTo(g.pad+c2*g.cw,g.pad+r2*g.ch);ctx.stroke()}
function drawHighlights(g){if(app.state.check){const king=app.state.pieces.find(p=>p.type==='king'&&p.color===app.state.turn);if(king)ring(g,king,'rgba(196,35,35,.35)',.47)}if(app.selected&&app.preferences.selection!==false)ring(g,app.selected,'rgba(215,167,55,.55)',.48);if(app.preferences.legalTargets!==false)for(const p of app.legal){const occupied=app.state.pieces.some(x=>x.row===p.row&&x.col===p.col);ctx.beginPath();ctx.arc(g.pad+p.col*g.cw,g.pad+p.row*g.ch,occupied?Math.min(g.cw,g.ch)*.43:Math.min(g.cw,g.ch)*.1,0,Math.PI*2);ctx.fillStyle=occupied?'rgba(157,37,37,.28)':'rgba(49,92,72,.72)';ctx.fill()}}
function drawCaptureHints(g){if(app.preferences.captureHints===false)return;const size=Math.min(g.cw,g.ch)*.3;ctx.save();ctx.strokeStyle='rgba(205,32,32,.9)';ctx.lineWidth=Math.max(2.5,Math.min(g.cw,g.ch)*.055);for(const p of app.capturable){const x=g.pad+p.col*g.cw,y=g.pad+p.row*g.ch;ctx.beginPath();ctx.moveTo(x-size,y-size);ctx.lineTo(x+size,y+size);ctx.moveTo(x+size,y-size);ctx.lineTo(x-size,y+size);ctx.stroke()}ctx.restore()}
function ring(g,p,color,size){ctx.beginPath();ctx.arc(g.pad+p.col*g.cw,g.pad+p.row*g.ch,Math.min(g.cw,g.ch)*size,0,Math.PI*2);ctx.fillStyle=color;ctx.fill()}
const pieceAssetTypes={king:'han',rook:'che',horse:'ma',elephant:'xiang',advisor:'shi',cannon:'pao',pawn:'bing',guard:'wei',archer:'she',thunder:'lei',patrol:'xun'};
function pieceImage(p){const suffix=pieceAssetTypes[p.type];if(!suffix)return null;const key=`${app.preferences.pieceStyle}:${p.color}:${suffix}`;if(app.pieceImages.has(key))return app.pieceImages.get(key);const image=new Image();image.onload=draw;image.onerror=()=>app.pieceImages.set(key,null);image.src=`/assets/pieces/${app.preferences.pieceStyle}/${p.color==='red'?'hong':'hei'}${suffix}.png`;app.pieceImages.set(key,image);return image}
function drawPiece(g,p){const x=g.pad+p.col*g.cw,y=g.pad+p.row*g.ch,r=Math.min(g.cw,g.ch)*.39,img=pieceImage(p);if(img?.complete&&img.naturalWidth){const size=r*2.14;ctx.save();ctx.shadowColor='rgba(0,0,0,.28)';ctx.shadowBlur=5;ctx.shadowOffsetY=2;ctx.drawImage(img,x-size/2,y-size/2,size,size);ctx.restore();return}ctx.save();ctx.shadowColor='rgba(0,0,0,.28)';ctx.shadowBlur=5;ctx.shadowOffsetY=2;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fillStyle='#f4d99f';ctx.fill();ctx.shadowColor='transparent';ctx.lineWidth=Math.max(2,r*.09);ctx.strokeStyle=p.color==='red'?'#a12424':'#292522';ctx.stroke();ctx.beginPath();ctx.arc(x,y,r*.82,0,Math.PI*2);ctx.lineWidth=1;ctx.stroke();ctx.fillStyle=p.color==='red'?'#a12424':'#292522';ctx.font=`bold ${r*1.18}px KaiTi`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(names[p.color][p.type],x,y+1);ctx.restore()}

async function selectOrMove(pos){
  if(!app.state||app.state.finished||app.replayIndex!==null)return;const piece=app.state.pieces.find(p=>p.row===pos.row&&p.col===pos.col);
  if(app.selected&&app.legal.some(p=>p.row===pos.row&&p.col===pos.col)){const payload={from:{row:app.selected.row,col:app.selected.col},to:pos};if(app.selected.type==='pawn'&&app.options.pawn_promotion&&(pos.row===0||pos.row===app.state.profile.rows-1)){const choices=[...new Set((app.state.captured[app.selected.color]||[]).map(p=>p.type).filter(t=>!['pawn','king'].includes(t)))];if(choices.length){const answer=prompt(`选择升变棋子：${choices.join(' / ')}`,choices[0]);if(!choices.includes(answer))return toast('请选择有效的升变棋子');payload.promotion=answer}}send('move',payload);app.selected=null;app.legal=[];app.capturable=[];draw();return}
  if(piece&&app.selected&&piece.row===app.selected.row&&piece.col===app.selected.col){draw();return}
  if(canControl(piece)){app.selected=piece;playSound('select');await loadLegal(piece)}else{app.selected=null;app.legal=[];app.capturable=[];draw()}
}
async function loadLegal(piece){
  app.legalPromise=api(`/api/rooms/${app.roomId}/legal?token=${encodeURIComponent(app.token)}&row=${piece.row}&col=${piece.col}`);
  try{const data=await app.legalPromise;if(data.revision===app.revision){app.legal=data.moves;app.capturable=data.captures||[]}}catch(error){toast(error.message);app.legal=[];app.capturable=[]}finally{app.legalPromise=null}draw()
}

board.addEventListener('pointerdown',async e=>{const pos=positionAt(e);if(pos){app.dragging={start:pos,x:e.clientX,y:e.clientY};const piece=app.state?.pieces.find(p=>p.row===pos.row&&p.col===pos.col);if(canControl(piece)&&(!app.selected||app.selected.row!==pos.row||app.selected.col!==pos.col)){app.selected=piece;playSound('select');await loadLegal(piece)}}});
board.addEventListener('pointerup',async e=>{const pos=positionAt(e),drag=app.dragging;app.dragging=null;if(!pos)return;if(app.legalPromise)await app.legalPromise.catch(()=>{});if(drag&&Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>8&&app.selected)selectOrMove(pos);else selectOrMove(pos)});board.addEventListener('pointercancel',()=>{app.dragging=null});
window.addEventListener('resize',resizeBoard);if(window.ResizeObserver)new ResizeObserver(resizeBoard).observe($('#boardShell'));$('#newGameButton').onclick=createGame;$('#joinButton').onclick=joinGame;$('#resignButton').onclick=()=>send('resign');$('#drawButton').onclick=()=>send('draw_offer');$('#undoButton').onclick=()=>send('undo_request');$('#pauseButton').onclick=()=>send('pause',{paused:!app.state?.paused});$('#restartButton').onclick=()=>send('restart',{options:app.options});$('#replayButton').onclick=()=>openReplay();
$('#resurrectButton').onclick=()=>{const value=prompt(`输入复活列（1-${app.state?.profile?.cols||13}）`,'1'),col=Number(value)-1;if(!Number.isInteger(col)||col<0||col>=(app.state?.profile?.cols||13))return toast('请输入有效列号');send('resurrect',{row:app.state.turn==='red'?8:4,col})};
$('#profileSelect').onchange=()=>{const profile=app.profiles.get($('#profileSelect').value);app.options={...(profile?.options||{})}};
$('#modeSelect').onchange=syncModeControls;
$('#moveList').onclick=e=>{const li=e.target.closest('li');if(!li)return;openReplay();setReplayIndex(Number(li.dataset.index)+1)};
$('#copyRoomButton').onclick=async()=>{if(app.roomId){await navigator.clipboard.writeText(app.roomId);toast('房间号已复制')}};
$('#showMovesButton').onclick=()=>showRecordView('moves');$('#showChatButton').onclick=()=>showRecordView('chat');$('#sendQuickChatButton').onclick=()=>sendChat(true);$('#sendChatButton').onclick=()=>sendChat(false);$('#chatInput').onkeydown=e=>{if(e.key==='Enter')sendChat(false)};
$('#soundButton').onclick=()=>{app.sound=!app.sound;$('#soundEnabled').checked=app.sound;$('#soundButton').textContent=app.sound?'♪':'♩';persistPreferences();if(app.music)startMusic();toast(app.sound?'音效已开启':'音效已关闭')};
$('#closeReplayButton').onclick=closeReplay;replayDialog.addEventListener('close',()=>{stopReplay();app.replayIndex=null;app.replaySource=null;draw()});
$('#replayBegin').onclick=()=>setReplayIndex(0);$('#replayPrev').onclick=()=>setReplayIndex((app.replayIndex||0)-1);$('#replayPlay').onclick=toggleReplay;$('#replayNext').onclick=()=>setReplayIndex((app.replayIndex||0)+1);$('#replayEnd').onclick=()=>setReplayIndex(replayGame()?.history?.length||0);$('#replayProgress').oninput=e=>setReplayIndex(Number(e.target.value));$('#replayMoves').onclick=e=>{const li=e.target.closest('li');if(li)setReplayIndex(Number(li.dataset.index))};
$('#saveReplayButton').onclick=saveCurrentReplay;$('#savedReplayList').onclick=async e=>{const replay=e.target.closest('[data-replay-record]'),resume=e.target.closest('[data-continue-record]'),exportButton=e.target.closest('[data-export-record]'),del=e.target.closest('[data-delete-replay]'),records=replayRecords();if(replay)loadSavedReplay(Number(replay.dataset.replayRecord));if(resume){const record=records.find(r=>r.id===Number(resume.dataset.continueRecord));if(record)try{await importDocument(record.document)}catch(error){toast(error.message)}}if(exportButton){const record=records.find(r=>r.id===Number(exportButton.dataset.exportRecord));if(record)downloadDocument(record.document)}if(del&&confirm('确定删除这份本地棋谱？')){localStorage.setItem('xh-replays',JSON.stringify(records.filter(r=>r.id!==Number(del.dataset.deleteReplay))));renderSavedReplays()}};
$('#settingsButton').onclick=()=>{
  const root=$('#ruleOptions'),profile=app.profiles.get($('#profileSelect').value),available=new Set(profile?.pieceTypes||[]);
  const general=['enforce_self_check','threefold_draw'].map(key=>`<label><input type="checkbox" data-option="${key}" ${app.options[key]!==false?'checked':''}>${labels[key]}</label>`).join('');
  const pieces=Object.entries(pieceLabels).map(([kind,label])=>{const key=`${kind}_appear`,enabled=available.has(kind),mandatory=kind==='king',rules=(pieceRuleKeys[kind]||[]).map(rule=>`<label><input type="checkbox" data-option="${rule}" ${app.options[rule]!==false?'checked':''}>${labels[rule]}</label>`).join('');return `<fieldset class="piece-rule-group ${enabled?'':'unavailable'}"><legend>${label.replace('登场','')}</legend><p>${pieceDescriptions[kind]}</p><label><input type="checkbox" data-option="${key}" ${mandatory||app.options[key]!==false?'checked':''} ${!enabled||mandatory?'disabled':''}>本局登场</label>${rules}</fieldset>`}).join('');
  root.innerHTML=`<fieldset><legend>通用裁定</legend><div class="option-grid">${general}</div></fieldset><div class="piece-rule-list">${pieces}</div>`;applyPreferences();$('#settingsDialog').showModal();startMusic()
};
$('#applySettings').onclick=()=>{app.options={...app.options};document.querySelectorAll('[data-option]').forEach(input=>{if(!input.disabled||input.dataset.option==='king_appear')app.options[input.dataset.option]=input.checked});app.options.king_appear=true;setTimeout(createGame)};
$('#resultRestart').onclick=()=>{$('#resultDialog').close();createGame()};

for(const [id,key] of [['fontSelect','font'],['boardThemeSelect','boardTheme'],['backgroundSelect','background'],['musicStyleSelect','musicStyle']]){$(`#${id}`).onchange=e=>{app.preferences[key]=e.target.value;applyPreferences();persistPreferences();if(key==='musicStyle'){stopMusic();startMusic()}}}
$('#pieceStyleSelect').onchange=e=>{app.preferences.pieceStyle=e.target.value;app.pieceImages.clear();persistPreferences();draw()};
$('#soundEnabled').onchange=e=>{app.sound=e.target.checked;$('#soundButton').textContent=app.sound?'♪':'♩';persistPreferences()};
$('#musicEnabled').onchange=e=>{app.music=e.target.checked;persistPreferences();app.music?startMusic():stopMusic()};
$('#volumeSlider').oninput=e=>{app.preferences.volume=Number(e.target.value);applyPreferences();persistPreferences()};
for(const [id,key] of [['animationEnabled','animation'],['selectionEnabled','selection'],['legalTargetsEnabled','legalTargets'],['captureHintsEnabled','captureHints'],['autosaveEnabled','autosave']]){$(`#${id}`).onchange=e=>{app.preferences[key]=e.target.checked;persistPreferences();draw()}}
for(const [id,key] of [['initialMinutesSelect','initialMinutes'],['countdownSecondsSelect','countdownSeconds']]){$(`#${id}`).onchange=e=>{app.preferences[key]=Number(e.target.value);persistPreferences();updateClockVisuals()}}

async function toggleFullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen()}catch(error){toast(error.message)}}
async function runCommand(command){
  if(command==='new')return createGame();
  if(command==='save-local')return saveCurrentReplay();
  if(command==='history')return showStatistics();
  if(command==='export'){const gameDocument=currentGameDocument();return gameDocument?downloadDocument(gameDocument):toast('当前没有可导出的棋局')}
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
$('#openReplayLibraryButton').onclick=()=>{$('#statisticsDialog').close();openReplayLibrary()};$('#resetStatisticsButton').onclick=()=>{if(confirm('确定清空历史统计？')){localStorage.removeItem('xh-statistics');localStorage.removeItem('xh-stat-keys');showStatistics()}};
$('#gameFileInput').onchange=async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;try{const gameDocument=JSON.parse(await file.text());await importDocument(gameDocument)}catch(error){toast(`读取失败：${error.message}`)}};
document.addEventListener('keydown',e=>{const key=e.key.toLowerCase(),command=e.key==='F1'?'guide':e.key==='F11'?'fullscreen':(e.ctrlKey&&key==='n'?'new':e.ctrlKey&&key==='s'?'export':e.ctrlKey&&key==='o'?'import':e.ctrlKey&&key==='z'?'undo':e.ctrlKey&&key==='r'?'replay':null);if(command){e.preventDefault();runCommand(command)}});

async function restore(){loadPreferences();renderSavedReplays();syncModeControls();$('#soundButton').textContent=app.sound?'♪':'♩';if(window.XionghanAndroid){document.body.classList.add('android-client');$('#serverSettingsButton').hidden=false}try{const profiles=await api('/api/profiles');app.profiles=new Map(profiles.map(profile=>[profile.id,profile]));const saved=JSON.parse(localStorage.getItem('xh-session'));if(saved?.roomId){const snapshot=await api(`/api/rooms/${saved.roomId}?token=${encodeURIComponent(saved.token)}`);app.roomId=saved.roomId;app.token=saved.token;app.color=saved.color;receiveSnapshot(snapshot);connect();return}}catch{}await createGame()}
restore();
