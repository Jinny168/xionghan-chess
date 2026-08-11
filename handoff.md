# 项目交接快照
## 1. 项目基础信息
项目名称：`xionghan-chess-next` 匈汉象棋三端统一版本。  
技术栈：Python 3.11 + FastAPI/uvicorn + Pydantic + pytest；桌面端 PySide6；Web 端原生 HTML/CSS/JS；Android 端 .NET 9 for Android + WebView；打包侧包含 PyInstaller、Windows PowerShell、Android APK 构建脚本。  
目录结构：`src/xionghan_chess` 为共享核心与桌面/服务端实现，`web` 为网页前端，`android` 为安卓壳，`tests` 为测试，`docs` 为方案与说明，`packaging` 为发布脚本，`release` 为产物。  
启动方式：`xionghan-server` 启动服务端，`xionghan-desktop` 启动桌面端，Web 由服务端挂载静态资源访问，Android 直接打开 WebView 并在本地/联网模式间切换。  
环境依赖：Python 3.11、Node.js、.NET 9 SDK/Android workload、Android SDK、PySide6、FastAPI、uvicorn、pytest、httpx、PyInstaller、Pillow。  

## 2. 初始目标 & 需求范围
原始需求：三端（安卓、桌面、网页）功能完全对齐，统一 UI/交互/弹窗/菜单/按钮风格，并重点修复安卓棋盘不渲染问题。  
交付标准：统一公共功能清单、统一 UI 规范、分端专项修复、三端发布包、可验证测试结果。  
约定规则：一端新增/修复功能，其余两端必须同步实现，不允许功能分叉；安卓必须保持全屏沉浸式；所有端共享同一套规则/协议/棋谱格式。  
编码规范：共享核心逻辑放在 `src/xionghan_chess/core`，协议通过 `Envelope`/`MessageType` 统一，Web/桌面/安卓都围绕共享状态渲染，不在客户端私自改规则语义。  

## 3. 已完成工作清单
已完成统一 1.1.0 的跨端对齐，新增暂停/继续、冻结计时、读秒、自动保存棋谱、历史对局、统计、导入导出、提示走棋、可行落点、吃子提示、棋子样式切换、棋盘主题切换、背景/音效/音量等能力。  
已完成安卓沉浸式全屏和棋盘空白渲染修复，核心处理是把 Canvas 尺寸同步与命中测试解耦，并在 `resize`/`resume`/`focus`/`visibilitychange` 上补重绘。  
已完成 Web/桌面与服务端协议对齐，`pause`、`state`、`undo`、`draw_offer`、`resign`、`restart`、`resurrect` 等消息保持统一。  
已完成发布文档与说明：`docs/UNIFIED_UI_OPTIMIZATION_1.1.md`、`docs/RELEASE_NOTES_1.1.0.md`。  
已完成发布包：`release/匈漢象棋-1.1.0-安卓版.apk`、`release/匈漢象棋-1.1.0-网页版.zip`、`release/匈漢象棋-1.1.0-桌面版.exe`。  
关键决策：安卓保留 WebView 作为统一渲染层，减少三端分叉；共享 `Game`/`RulesEngine`/`protocol` 作为唯一真相源；桌面端继续原生壳层，但功能语义和 Web 完全一致。  

## 4. 当前进度 & 半成品代码位置
当前主线功能已可交付，未见明确“写一半”的核心函数；剩余主要是收尾、回归和整理。  
正在重点关注的文件：`xionghan-chess-next/android/MainActivity.cs`、`xionghan-chess-next/web/js/app.js`、`xionghan-chess-next/src/xionghan_chess/service/app.py`、`xionghan-chess-next/src/xionghan_chess/core/game.py`、`xionghan-chess-next/src/xionghan_chess/core/protocol.py`。  
当前存在的主要风险不是业务缺口，而是仓库里混有大量构建产物与历史变更，需要后续按交接节奏清理/分层管理。  
待调试逻辑主要集中在跨端回归时的窗口缩放、安卓 WebView 重绘、以及本地棋谱导入导出后的状态一致性。  

## 5. 待办任务列表（优先级排序）
P0：继续回归三端暂停/继续、计时冻结、断线重连、撤销/求和/认输的消息闭环，确保状态在 Web、桌面、安卓完全一致。  
P0：再跑一轮安卓真机或模拟器验证，确认棋盘在首屏、切后台、回前台、旋转/缩放后都能稳定重绘。  
P1：整理并拆分当前工作树中的构建产物，避免后续提交把 `bin/obj/build-onefile/release` 的大量二进制变更混进业务代码。  
P1：补充/复核桌面端窗口缩放、Web 移动端窄屏布局，以及棋谱库/统计页的边界文案。  
P2：如果后续还有版本迭代，再按同一套规则扩展新棋谱或新 UI 皮肤，但必须同步三端。  

## 6. 重要约束 & 踩坑记录
安卓硬约束：必须沉浸式全屏，不能保留系统状态栏/导航栏；这次最终以全屏为准。  
最关键踩坑：安卓棋盘空白不是规则错，而是 Canvas 尺寸更新与渲染命中测试耦合导致的，修复方向是分离 `syncCanvasSize()` 和点击命中逻辑，并在窗口生命周期上补重绘。  
协议约束：客户端不能各自扩展自己的状态语义，所有新能力要落到共享 `MessageType`、`GameState`、`RuleOptions` 或服务端房间逻辑上。  
打包约束：Android APK 体积控制要优先考虑离线资源；Windows 打包曾通过收窄 PyInstaller 收集范围降低体积。  
注意事项：当前仓库有较多未清理的生成文件和历史变更，继续开发时不要误删非本次任务内容。  

## 7. 相关代码片段引用
```python
# xionghan-chess-next/src/xionghan_chess/service/app.py
app = FastAPI(title="鍖堟眽璞℃ API", version="1.1.0", lifespan=lifespan)

@app.get("/api/rooms/{room_id}/legal")
async def legal_moves(room_id: str, token: str, row: int, col: int) -> dict:
    room = manager.require(room_id)
    seat = manager.seat_for(room, token)
    source = Position(row, col)
    piece = room.game.state.piece_at(source)
    controlled_color = room.game.state.turn if room.mode == "local" else seat.color
```
```python
# xionghan-chess-next/src/xionghan_chess/core/protocol.py
class MessageType(StrEnum):
    HELLO = "hello"
    JOIN = "join"
    STATE = "state"
    MOVE = "move"
    PAUSE = "pause"
    ERROR = "error"
```
```python
# xionghan-chess-next/src/xionghan_chess/core/game.py
def set_paused(self, paused: bool, color: Color | None = None) -> None:
    if paused:
        self.tick()
        self.state.paused = True
        self.state.paused_by = color
    else:
        self.state.paused = False
        self.state.paused_by = None
        self.state.turn_started_at = time.monotonic()
```
```csharp
// xionghan-chess-next/android/MainActivity.cs
void RequestGameRedraw() => webView?.EvaluateJavascript(
    "requestAnimationFrame(function(){document.body.classList.add('android-client');window.dispatchEvent(new Event('resize'));if(window.redrawBoard)window.redrawBoard();});",
    null);
```
```javascript
// xionghan-chess-next/web/js/app.js
window.addEventListener('resize', resizeBoard);
if (window.ResizeObserver) new ResizeObserver(resizeBoard).observe($('#boardShell'));
$('#pauseButton').onclick = () => send('pause', { paused: !app.state?.paused });
```

## 8. 后续接续指令
先读：`xionghan-chess-next/docs/UNIFIED_UI_OPTIMIZATION_1.1.md`、`xionghan-chess-next/docs/RELEASE_NOTES_1.1.0.md`、`xionghan-chess-next/src/xionghan_chess/service/app.py`、`xionghan-chess-next/src/xionghan_chess/core/game.py`、`xionghan-chess-next/android/MainActivity.cs`、`xionghan-chess-next/web/js/app.js`。  
第一步：先跑一次三端回归检查，确认暂停、计时、断线重连、棋盘重绘、导入导出和历史回放都能通。  
第二步：如果还要继续开发，就优先把生成产物和业务改动分离，再按 P0/P1 顺序推进。  
