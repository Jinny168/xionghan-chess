const $ = (selector) => document.querySelector(selector);
const board = $('#board');
const ctx = board.getContext('2d');
const app = {
  roomId: null, token: null, color: null, revision: 0, state: null, socket: null,
  selected: null, legal: [], capturable: [], dragging: null, replayIndex: null, replaySource: null, sound: true, music: true,
  preferences: {font:'system',boardTheme:'classic',background:'3',pieceStyle:'traditional',musicStyle:'fc',volume:70},
  options: {}, profiles: new Map(), pieceImages: new Map(), animation: null, legalPromise: null,
};
const sounds={select:new Audio('/assets/sounds/choose.wav'),move:new Audio('/assets/sounds/drop.wav'),capture:new Audio('/assets/sounds/eat.wav'),check:new Audio('/assets/sounds/warn.wav'),win:new Audio('/assets/sounds/fc_victory_sound.wav'),lose:new Audio('/assets/sounds/fc_defeat_sound.wav'),button:new Audio('/assets/sounds/button.wav')};
let backgroundMusic=null;
function persistPreferences(){localStorage.setItem('xh-preferences',JSON.stringify(app.preferences));localStorage.setItem('xh-sound',JSON.stringify({sound:app.sound,music:app.music}))}
function applyPreferences(){const p=app.preferences;document.body.dataset.font=p.font;document.body.dataset.boardTheme=p.boardTheme;document.body.style.backgroundImage=`url('/assets/backgrounds/${p.background}.jpg')`;document.documentElement.style.setProperty('--board-line',({classic:'#6d3c11',green:'#3a6b1e',blue:'#2471a3',purple:'#7d3c98',dark:'#aaa'})[p.boardTheme]||'#6d3c11');document.documentElement.style.setProperty('--board-text',({classic:'#8b4513',green:'#2d5016',blue:'#1a5276',purple:'#6c3483',dark:'#ddd'})[p.boardTheme]||'#8b4513');$('#fontSelect').value=p.font;$('#boardThemeSelect').value=p.boardTheme;$('#backgroundSelect').value=p.background;$('#pieceStyleSelect').value=p.pieceStyle;$('#musicStyleSelect').value=p.musicStyle;$('#volumeSlider').value=p.volume;$('#volumeValue').textContent=`${p.volume}%`;$('#soundEnabled').checked=app.sound;$('#musicEnabled').checked=app.music;Object.values(sounds).forEach(a=>{a.volume=p.volume/100});if(backgroundMusic)backgroundMusic.volume=p.volume/200;draw()}
function loadPreferences(){try{app.preferences={...app.preferences,...JSON.parse(localStorage.getItem('xh-preferences')||'{}')};const s=JSON.parse(localStorage.getItem('xh-sound')||'{}');if(typeof s.sound==='boolean')app.sound=s.sound;if(typeof s.music==='boolean')app.music=s.music}catch{}applyPreferences()}
function playSound(key){if(!app.sound)return;const audio=sounds[key];if(audio){audio.currentTime=0;audio.volume=app.preferences.volume/100;audio.play().catch(()=>{})}}
function startMusic(){if(!app.music)return;if(!backgroundMusic||backgroundMusic.dataset.style!==app.preferences.musicStyle){if(backgroundMusic)backgroundMusic.pause();backgroundMusic=new Audio(`/assets/sounds/${app.preferences.musicStyle==='qq'?'qq_background_sound.wav':'fc_background_sound.wav'}`);backgroundMusic.loop=true;backgroundMusic.dataset.style=app.preferences.musicStyle;backgroundMusic.volume=app.preferences.volume/200}backgroundMusic.play().catch(()=>{})}
function stopMusic(){if(backgroundMusic){backgroundMusic.pause();backgroundMusic.currentTime=0}}
function replayGame(){return app.replaySource||app.state}
function openReplay(){if(!app.state?.history?.length)return toast('当前对局暂无棋谱');if(app.replayIndex===null){app.replaySource=null;app.replayIndex=app.state.history.length}else{app.replayIndex=null;app.replaySource=null}$('#replaySidebar').classList.toggle('open',app.replayIndex!==null);updateReplayUI();renderSavedReplays();draw();toast(app.replayIndex===null?'已返回实时棋局':'已进入复盘')}
function setReplayIndex(step){const total=replayGame()?.history?.length||0;app.replayIndex=Math.max(0,Math.min(total,step));updateReplayUI();draw()}
function updateReplayUI(){const game=replayGame(),total=game?.history?.length||0,current=app.replayIndex===null?total:app.replayIndex;$('#replayProgress').max=total;$('#replayProgress').value=current;$('#replayStepInfo').textContent=`${current} / ${total}`;$('#replayMoves').innerHTML=(game?.history||[]).map((h,i)=>`<li data-index="${i+1}" class="${app.replayIndex===i+1?'active':''}">${i+1}. ${h.notation||''}</li>`).join('')}
function replayRecords(){try{return JSON.parse(localStorage.getItem('xh-replays')||'[]')}catch{return[]}}
function saveCurrentReplay(){if(!app.state?.history?.length)return toast('当前对局暂无棋谱');const records=replayRecords();records.unshift({id:Date.now(),savedAt:new Date().toISOString(),profile:app.state.profile,history:app.state.history,replay:app.state.replay,winner:app.state.winner,resultReason:app.state.resultReason});localStorage.setItem('xh-replays',JSON.stringify(records.slice(0,30)));renderSavedReplays();toast('棋谱已保存到本机')}
function renderSavedReplays(){const list=$('#savedReplayList');if(!list)return;const records=replayRecords();list.innerHTML=records.length?records.map(r=>`<div class="saved-replay"><div><strong>${r.winner?(r.winner==='red'?'红方胜':'黑方胜'):'对局棋谱'} · ${r.history.length} 步</strong><span>${new Date(r.savedAt).toLocaleString('zh-CN')}</span></div><div class="saved-replay-actions"><button data-load-replay="${r.id}">载入</button><button data-delete-replay="${r.id}">删</button></div></div>`).join(''):'<span>暂无已保存棋谱</span>'}
function loadSavedReplay(id){const record=replayRecords().find(r=>r.id===id);if(!record)return;app.replaySource=record;app.replayIndex=record.history.length;$('#replaySidebar').classList.add('open');updateReplayUI();draw();toast('已载入本地棋谱')}

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
    const data=await api('/api/rooms',{method:'POST',body:JSON.stringify({profileId:$('#profileSelect').value,mode:$('#modeSelect').value,playerName:'玩家',playerColor:$('#colorSelect').value,difficulty:$('#difficultySelect').value,options:app.options,initialMinutes:20})});
    acceptSession(data); toast(data.snapshot.mode==='online'?`房间 ${data.roomId} 已创建`:'人机对局已开始');
  }catch(error){toast(error.message)}
}
async function joinGame(){
  const code=$('#roomInput').value.trim().toUpperCase(); if(!code)return toast('请输入房间号');
  try{const data=await api(`/api/rooms/${code}/join`,{method:'POST',body:JSON.stringify({playerName:'玩家二'})});acceptSession(data);toast('已加入房间')}catch(error){toast(error.message)}
}
function acceptSession(data){app.roomId=data.roomId;app.token=data.token;app.color=data.color;receiveSnapshot(data.snapshot);localStorage.setItem('xh-session',JSON.stringify({roomId:app.roomId,token:app.token,color:app.color}));connect()}
function connect(){
  if(!app.roomId||!app.token)return; const protocol=location.protocol==='https:'?'wss':'ws'; app.socket=new WebSocket(`${protocol}://${location.host}/ws/${app.roomId}?token=${encodeURIComponent(app.token)}`);
  app.socket.onopen=()=>{$('#connectionText').textContent='已连接 · 状态同步正常'};
  app.socket.onmessage=e=>{const message=JSON.parse(e.data);if(message.type==='state')receiveSnapshot(message.payload);else if(message.type==='chat')appendChat(message.payload);else if(message.type==='error'){toast(message.payload.message);if(message.payload.state)receiveSnapshot(message.payload.state)}};
  app.socket.onclose=()=>{$('#connectionText').textContent='连接中断 · 正在重连';setTimeout(()=>{if(app.roomId)connect()},1800)};
}
function closeSocket(){if(app.socket){app.socket.onclose=null;app.socket.close()}app.socket=null}
function send(type,payload={}){if(!app.socket||app.socket.readyState!==WebSocket.OPEN)return toast('连接尚未就绪');app.socket.send(JSON.stringify({type,roomId:app.roomId,revision:app.revision,payload,protocolVersion:1}))}
function appendChat(payload){const list=$('#chatMessages'),item=document.createElement('div');item.className=`chat-message ${payload.color||''}`;const sender=document.createElement('strong');sender.textContent=`${payload.sender||'玩家'}：`;item.append(sender,document.createTextNode(payload.text||''));list.append(item);list.scrollTop=list.scrollHeight}
function sendChat(quick=false){const input=$('#chatInput'),text=(quick?$('#quickChatSelect').value:input.value).trim();if(!text)return;send('chat',{text,quick});if(!quick)input.value=''}
function showRecordView(view){const chat=view==='chat';$('#chatView').hidden=!chat;$('#moveList').hidden=chat;$('#moveCount').hidden=chat;$('#showMovesButton').classList.toggle('active',!chat);$('#showChatButton').classList.toggle('active',chat)}
function receiveSnapshot(snapshot){
  const previous=app.state;app.revision=snapshot.revision;app.state=snapshot.game;app.options=snapshot.game.profile.options;app.selected=null;app.legal=[];app.capturable=[];app.replayIndex=null;app.replaySource=null;$('#replaySidebar').classList.remove('open');
  $('#roomCode').textContent=snapshot.roomId;$('#roomInput').value=snapshot.roomId;$('#turnRibbon').textContent=app.state.finished?'对局结束':`${app.state.turn==='red'?'红方':'黑方'}行棋`;
  $('#thinking').hidden=!(snapshot.mode==='ai'&&app.state.turn!==app.color&&!app.state.finished);renderMeta(snapshot);resizeBoard();
  if(previous&&app.state.history.length>previous.history.length){const last=app.state.history.at(-1);playSound(last.captured?.length?'capture':app.state.check?'check':'move');app.animation={target:last.move.to,capture:!!last.captured?.length,started:performance.now()};requestAnimationFrame(animate)}
  if(app.state.finished)showResult();
  if(app.state.pendingDrawOffer&&app.state.pendingDrawOffer!==app.color&&confirm('对手请求和棋，是否接受？'))send('draw_response',{accept:true});
  else if(app.state.pendingDrawOffer&&app.state.pendingDrawOffer!==app.color)send('draw_response',{accept:false});
  if(app.state.pendingUndoOffer&&app.state.pendingUndoOffer!==app.color&&confirm('对手请求悔棋，是否接受？'))send('undo_response',{accept:true});
  else if(app.state.pendingUndoOffer&&app.state.pendingUndoOffer!==app.color)send('undo_response',{accept:false});
}
function renderMeta(snapshot){
  $('#redClock').textContent=formatClock(app.state.clocksMs.red);$('#blackClock').textContent=formatClock(app.state.clocksMs.black);
  for(const color of ['red','black']){const player=snapshot.players.find(p=>p.color===color);$(`#${color}Status`).textContent=player?(player.connected?'在线':'暂时离线'):'等待落座';$(`#${color}Captured`).innerHTML=(app.state.captured[color]||[]).map(p=>`<span>${names[color][p.type]}</span>`).join('')}
  $('#moveList').innerHTML=app.state.history.map((h,i)=>`<li data-index="${i}">${h.notation}</li>`).join('');$('#moveCount').textContent=`${Math.ceil(app.state.history.length/2)} 回合`;const list=$('#moveList');list.scrollTop=list.scrollHeight;
  const myTurn=app.state.turn===app.color&&!app.state.finished;$('#resignButton').disabled=app.state.finished;$('#drawButton').disabled=!myTurn;$('#undoButton').disabled=!app.state.history.length;
}
function showResult(){const winner=app.state.winner;$('#resultMark').textContent=winner?(winner==='red'?'漢':'汗'):'和';$('#resultTitle').textContent=winner?`${winner==='red'?'红方':'黑方'}胜利`:'和棋';$('#resultText').textContent=({checkmate:'将死',king_captured:'主帅被擒',palace_invasion:'主帅攻入敌方九宫',stalemate:'困毙',timeout:'超时判负',resignation:'认输',disconnect_timeout:'断线超时',draw_agreement:'双方议和',threefold_repetition:'三次重复局面',no_progress:'长时间无进展'})[app.state.resultReason]||'对局结束';playSound(winner===app.color?'win':'lose');if(!$('#resultDialog').open)$('#resultDialog').showModal()}

function resizeBoard(){const rect=board.parentElement.getBoundingClientRect();const dpr=Math.min(devicePixelRatio||1,2);board.width=Math.floor(rect.width*dpr);board.height=Math.floor(rect.height*dpr);board.style.width=`${rect.width}px`;board.style.height=`${rect.height}px`;draw()}
function geometry(){const model=replayGame(),rows=model?.profile?.rows||13,cols=model?.profile?.cols||13,w=board.clientWidth,h=board.clientHeight,pad=Math.min(w,h)*.055;return{rows,cols,pad,cw:(w-pad*2)/(cols-1),ch:(h-pad*2)/(rows-1),w,h}}
function positionAt(event){const r=board.getBoundingClientRect(),g=geometry();const col=Math.round((event.clientX-r.left-g.pad)/g.cw),row=Math.round((event.clientY-r.top-g.pad)/g.ch);return row>=0&&row<g.rows&&col>=0&&col<g.cols?{row,col}:null}
function draw(){
  if(!app.state)return;const replay=replayGame(),shown=app.replayIndex===null?app.state:(replay.replay?.[app.replayIndex]||app.state);const originalPieces=app.state.pieces;app.state.pieces=shown.pieces;const g=geometry(),dpr=board.width/g.w,styles=getComputedStyle(document.documentElement);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,g.w,g.h);ctx.strokeStyle=styles.getPropertyValue('--board-line').trim()||'#604326';ctx.lineWidth=1.25;
  if(g.rows===13)drawXionghanGrid(g);else drawStandardGrid(g);
  drawPalaces(g);if(g.rows===13){drawInitialPositionMarks(g);drawStarPoints(g)}drawHighlights(g);for(const piece of app.state.pieces)drawPiece(g,piece);drawCaptureHints(g);drawAnimation(g);app.state.pieces=originalPieces;
}
function drawStandardGrid(g){for(let r=0;r<g.rows;r++)line(g,r,0,r,g.cols-1);for(let c=0;c<g.cols;c++)line(g,0,c,g.rows-1,c)}
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
function drawHighlights(g){if(app.state.check){const king=app.state.pieces.find(p=>p.type==='king'&&p.color===app.state.turn);if(king)ring(g,king,'rgba(196,35,35,.35)',.47)}if(app.selected)ring(g,app.selected,'rgba(215,167,55,.55)',.48);for(const p of app.legal){const occupied=app.state.pieces.some(x=>x.row===p.row&&x.col===p.col);ctx.beginPath();ctx.arc(g.pad+p.col*g.cw,g.pad+p.row*g.ch,occupied?Math.min(g.cw,g.ch)*.43:Math.min(g.cw,g.ch)*.1,0,Math.PI*2);ctx.fillStyle=occupied?'rgba(157,37,37,.28)':'rgba(49,92,72,.72)';ctx.fill()}}
function drawCaptureHints(g){const size=Math.min(g.cw,g.ch)*.3;ctx.save();ctx.strokeStyle='rgba(205,32,32,.9)';ctx.lineWidth=Math.max(2.5,Math.min(g.cw,g.ch)*.055);for(const p of app.capturable){const x=g.pad+p.col*g.cw,y=g.pad+p.row*g.ch;ctx.beginPath();ctx.moveTo(x-size,y-size);ctx.lineTo(x+size,y+size);ctx.moveTo(x+size,y-size);ctx.lineTo(x-size,y+size);ctx.stroke()}ctx.restore()}
function ring(g,p,color,size){ctx.beginPath();ctx.arc(g.pad+p.col*g.cw,g.pad+p.row*g.ch,Math.min(g.cw,g.ch)*size,0,Math.PI*2);ctx.fillStyle=color;ctx.fill()}
const pieceAssetTypes={king:'han',rook:'che',horse:'ma',elephant:'xiang',advisor:'shi',cannon:'pao',pawn:'bing',guard:'wei',archer:'she',thunder:'lei',patrol:'xun'};
function pieceImage(p){const suffix=pieceAssetTypes[p.type];if(!suffix)return null;const key=`${app.preferences.pieceStyle}:${p.color}:${suffix}`;if(app.pieceImages.has(key))return app.pieceImages.get(key);const image=new Image();image.onload=draw;image.onerror=()=>app.pieceImages.set(key,null);image.src=`/assets/pieces/${app.preferences.pieceStyle}/${p.color==='red'?'hong':'hei'}${suffix}.png`;app.pieceImages.set(key,image);return image}
function drawPiece(g,p){const x=g.pad+p.col*g.cw,y=g.pad+p.row*g.ch,r=Math.min(g.cw,g.ch)*.39,img=pieceImage(p);if(img?.complete&&img.naturalWidth){const size=r*2.14;ctx.save();ctx.shadowColor='rgba(0,0,0,.28)';ctx.shadowBlur=5;ctx.shadowOffsetY=2;ctx.drawImage(img,x-size/2,y-size/2,size,size);ctx.restore();return}ctx.save();ctx.shadowColor='rgba(0,0,0,.28)';ctx.shadowBlur=5;ctx.shadowOffsetY=2;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fillStyle='#f4d99f';ctx.fill();ctx.shadowColor='transparent';ctx.lineWidth=Math.max(2,r*.09);ctx.strokeStyle=p.color==='red'?'#a12424':'#292522';ctx.stroke();ctx.beginPath();ctx.arc(x,y,r*.82,0,Math.PI*2);ctx.lineWidth=1;ctx.stroke();ctx.fillStyle=p.color==='red'?'#a12424':'#292522';ctx.font=`bold ${r*1.18}px KaiTi`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(names[p.color][p.type],x,y+1);ctx.restore()}

async function selectOrMove(pos){
  if(!app.state||app.state.finished||app.replayIndex!==null)return;const piece=app.state.pieces.find(p=>p.row===pos.row&&p.col===pos.col);
  if(app.selected&&app.legal.some(p=>p.row===pos.row&&p.col===pos.col)){const payload={from:{row:app.selected.row,col:app.selected.col},to:pos};if(app.selected.type==='pawn'&&app.options.pawn_promotion&&(pos.row===0||pos.row===app.state.profile.rows-1)){const choices=[...new Set((app.state.captured[app.color]||[]).map(p=>p.type).filter(t=>!['pawn','king'].includes(t)))];if(choices.length){const answer=prompt(`选择升变棋子：${choices.join(' / ')}`,choices[0]);if(!choices.includes(answer))return toast('请选择有效的升变棋子');payload.promotion=answer}}send('move',payload);app.selected=null;app.legal=[];app.capturable=[];draw();return}
  if(piece&&app.selected&&piece.row===app.selected.row&&piece.col===app.selected.col){draw();return}
  if(piece&&piece.color===app.color&&piece.color===app.state.turn){app.selected=piece;playSound('select');await loadLegal(piece)}else{app.selected=null;app.legal=[];app.capturable=[];draw()}
}
async function loadLegal(piece){
  app.legalPromise=api(`/api/rooms/${app.roomId}/legal?token=${encodeURIComponent(app.token)}&row=${piece.row}&col=${piece.col}`);
  try{const data=await app.legalPromise;if(data.revision===app.revision){app.legal=data.moves;app.capturable=data.captures||[]}}catch(error){toast(error.message);app.legal=[];app.capturable=[]}finally{app.legalPromise=null}draw()
}

board.addEventListener('pointerdown',async e=>{const pos=positionAt(e);if(pos){app.dragging={start:pos,x:e.clientX,y:e.clientY};const piece=app.state?.pieces.find(p=>p.row===pos.row&&p.col===pos.col);if(piece&&piece.color===app.color&&piece.color===app.state.turn&&(!app.selected||app.selected.row!==pos.row||app.selected.col!==pos.col)){app.selected=piece;playSound('select');await loadLegal(piece)}}});
board.addEventListener('pointerup',async e=>{const pos=positionAt(e),drag=app.dragging;app.dragging=null;if(!pos)return;if(app.legalPromise)await app.legalPromise.catch(()=>{});if(drag&&Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>8&&app.selected)selectOrMove(pos);else selectOrMove(pos)});
window.addEventListener('resize',resizeBoard);$('#newGameButton').onclick=createGame;$('#joinButton').onclick=joinGame;$('#resignButton').onclick=()=>send('resign');$('#drawButton').onclick=()=>send('draw_offer');$('#undoButton').onclick=()=>send('undo_request');$('#replayButton').onclick=openReplay;
$('#profileSelect').onchange=()=>{const profile=app.profiles.get($('#profileSelect').value);app.options={...(profile?.options||{})}};
$('#moveList').onclick=e=>{const li=e.target.closest('li');if(!li)return;app.replaySource=null;app.replayIndex=Number(li.dataset.index)+1;$('#replaySidebar').classList.add('open');updateReplayUI();draw();toast(`复盘至第 ${app.replayIndex} 步`)};
$('#copyRoomButton').onclick=async()=>{if(app.roomId){await navigator.clipboard.writeText(app.roomId);toast('房间号已复制')}};
$('#showMovesButton').onclick=()=>showRecordView('moves');$('#showChatButton').onclick=()=>showRecordView('chat');$('#sendQuickChatButton').onclick=()=>sendChat(true);$('#sendChatButton').onclick=()=>sendChat(false);$('#chatInput').onkeydown=e=>{if(e.key==='Enter')sendChat(false)};
$('#soundButton').onclick=()=>{app.sound=!app.sound;$('#soundEnabled').checked=app.sound;$('#soundButton').textContent=app.sound?'♪':'♩';persistPreferences();if(app.music)startMusic();toast(app.sound?'音效已开启':'音效已关闭')};
$('#closeReplayButton').onclick=()=>{app.replayIndex=null;app.replaySource=null;$('#replaySidebar').classList.remove('open');draw()};
$('#replayBegin').onclick=()=>setReplayIndex(0);$('#replayPrev').onclick=()=>setReplayIndex((app.replayIndex||0)-1);$('#replayNext').onclick=()=>setReplayIndex((app.replayIndex||0)+1);$('#replayEnd').onclick=()=>setReplayIndex(replayGame()?.history?.length||0);$('#replayProgress').oninput=e=>setReplayIndex(Number(e.target.value));$('#replayMoves').onclick=e=>{const li=e.target.closest('li');if(li)setReplayIndex(Number(li.dataset.index))};
$('#saveReplayButton').onclick=saveCurrentReplay;$('#savedReplayList').onclick=e=>{const load=e.target.closest('[data-load-replay]'),del=e.target.closest('[data-delete-replay]');if(load)loadSavedReplay(Number(load.dataset.loadReplay));if(del){localStorage.setItem('xh-replays',JSON.stringify(replayRecords().filter(r=>r.id!==Number(del.dataset.deleteReplay))));renderSavedReplays()}};
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

async function restore(){loadPreferences();renderSavedReplays();$('#soundButton').textContent=app.sound?'♪':'♩';try{const profiles=await api('/api/profiles');app.profiles=new Map(profiles.map(profile=>[profile.id,profile]));const saved=JSON.parse(localStorage.getItem('xh-session'));if(saved?.roomId){const snapshot=await api(`/api/rooms/${saved.roomId}?token=${encodeURIComponent(saved.token)}`);app.roomId=saved.roomId;app.token=saved.token;app.color=saved.color;receiveSnapshot(snapshot);connect();return}}catch{}await createGame()}
restore();
