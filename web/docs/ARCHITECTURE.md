# 控制器架构说明

## 📋 架构概览

本项目采用**模块化控制器架构**，将游戏逻辑拆分为多个职责清晰的子控制器，通过事件分发器进行通信。

## 🏗️ 核心组件

### 1. GameController (主控制器)
**文件**: `game-controller.js`  
**职责**: 
- 协调所有子控制器
- 管理游戏生命周期
- 处理高层业务逻辑

**依赖的子控制器**:
- GameLogicHandler - 游戏逻辑
- NetworkHandler - 网络通信
- UIController - 用户界面
- ReplayManager - 复盘管理

### 2. EventDispatcher (事件分发器)
**文件**: `event-dispatcher.js`  
**职责**:
- 统一管理事件发布/订阅
- 解耦各模块间的通信
- 提供事件常量定义

**主要事件**:
```javascript
// 游戏状态
GAME_INIT, GAME_START, GAME_END, GAME_RESET

// 棋子事件
PIECE_SELECTED, PIECE_MOVED, PIECE_CAPTURED, PIECE_SPAWNED

// 回合事件
TURN_CHANGED, CHECK_DETECTED, CHECKMATE_DETECTED

// UI事件
UI_UPDATED, MOVE_HISTORY_UPDATED

// 网络事件
NETWORK_CONNECTED, OPPONENT_MOVE, OPPONENT_JOINED

// 复盘事件
REPLAY_STARTED, REPLAY_STOPPED, REPLAY_STEP
```

### 3. GameLogicHandler (游戏逻辑处理器)
**文件**: `game-logic-handler.js`  
**职责**:
- 棋子移动验证和执行
- 规则检查（将军、绝杀）
- 兵复活逻辑
- 悔棋处理
- 棋谱生成

**核心方法**:
```javascript
executeMove(fromPos, toPos)  // 执行移动
trySpawnBing(row, col)       // 尝试复活兵
undo()                       // 悔棋
restart()                    // 重新开始
resign(camp)                 // 认输
```

### 4. NetworkHandler (网络处理器)
**文件**: `network-handler.js`  
**职责**:
- WebSocket连接管理
- 消息收发
- 断线重连
- 房间管理

**核心方法**:
```javascript
initialize(roomId)           // 初始化连接
sendMove(moveData)           // 发送移动
sendChatMessage(message)     // 发送聊天
requestUndo()                // 请求悔棋
requestRestart()             // 请求重新开始
resign()                     // 认输
```

### 5. UIController (UI控制器)
**文件**: `ui-controller.js`  
**职责**:
- DOM元素管理
- 事件绑定
- UI更新
- Canvas交互
- 暗黑模式

**核心方法**:
```javascript
initElements()               // 初始化DOM引用
bindEvents(handlers)         // 绑定事件
updateUI(gameState, stats)   // 更新UI显示
toggleDarkMode(enabled)      // 切换暗黑模式
addChatMessage(...)          // 添加聊天消息
```

### 6. ReplayManager (复盘管理器)
**文件**: `replay-manager.js`  
**职责**:
- 复盘侧边栏管理
- 对局记录列表
- 加载/删除记录

**依赖**:
- ReplayController - 复盘控制核心
- GameRecordManager - 记录存储

### 7. 辅助管理器

#### SoundManager
音效管理（移动、吃子、将军等）

#### AvatarManager
头像渲染和管理

#### TauntManager
嘲讽语句管理

#### StatisticsManager
游戏统计（胜场、步数、时长等）

#### GameRecordManager
对局记录的保存和加载

#### GameRuleConfig
游戏规则配置

## 🔄 数据流

```
用户操作
   ↓
UIController (捕获事件)
   ↓
GameController (协调)
   ↓
GameLogicHandler (处理逻辑)
   ↓
EventDispatcher (发布事件)
   ↓
各监听器响应
   ├→ SoundManager (播放音效)
   ├→ UIController (更新界面)
   ├→ StatisticsManager (更新统计)
   └→ NetworkHandler (同步对手)
```

## 💡 优势

1. **职责清晰**: 每个控制器只负责一个领域
2. **易于测试**: 可以单独测试每个控制器
3. **易于维护**: 修改某个功能不影响其他模块
4. **可扩展**: 新增功能只需添加新的事件监听器
5. **低耦合**: 通过事件系统解耦，模块间不直接依赖

## 📝 使用示例

### 初始化游戏
```javascript
const game = new GameController();
game.init({
    mode: 'local',  // 或 'online'
    roomId: 'room123'  // 仅在线模式需要
});
```

### 监听事件
```javascript
game.events.on('piece:moved', (data) => {
    console.log('棋子移动:', data);
});

game.events.on('checkmate:detected', (data) => {
    console.log('绝杀！获胜方:', data.winner);
});
```

### 触发动作
```javascript
// 通过UI交互自动触发，无需手动调用
// 用户点击棋盘 → UIController → GameController → GameLogicHandler
```

## 🎯 关键设计原则

1. **单一职责**: 每个类只做一件事
2. **依赖注入**: 通过构造函数传递依赖
3. **事件驱动**: 模块间通过事件通信
4. **开闭原则**: 对扩展开放，对修改关闭
5. **接口隔离**: 暴露最小化的公共API

## 🔧 扩展指南

### 添加新功能

1. **创建新的处理器**（如需要）
```javascript
class NewFeatureHandler {
    constructor(events) {
        this.events = events;
    }
    
    doSomething() {
        // 实现逻辑
        this.events.emit('feature:done', data);
    }
}
```

2. **在GameController中集成**
```javascript
initializeControllers() {
    // ...
    this.newFeatureHandler = new NewFeatureHandler(this.events);
}
```

3. **绑定事件**
```javascript
bindEventHandlers() {
    this.events.on('feature:done', (data) => {
        // 处理结果
    });
}
```

## 📊 文件清单

```
web/js/controllers/
├── game-controller.js        # 主控制器 (588行)
├── event-dispatcher.js       # 事件分发器 (142行)
├── game-logic-handler.js     # 游戏逻辑 (339行)
├── network-handler.js        # 网络处理 (326行)
├── ui-controller.js          # UI控制 (372行)
├── replay-manager.js         # 复盘管理 (368行)
├── replay-controller.js      # 复盘控制 (268行)
├── game-record-manager.js    # 记录管理 (207行)
├── sound-manager.js          # 音效管理
├── avatar-manager.js         # 头像管理
├── taunt-manager.js          # 嘲讽管理
├── statistics-manager.js     # 统计管理
└── game-rule-config.js       # 规则配置

web/docs/
└── ARCHITECTURE.md           # 架构说明文档 📖
```

## ⚠️ 注意事项

1. **不要直接访问其他控制器的内部状态**，应通过事件通信
2. **事件命名要规范**，使用 `模块:动作` 格式
3. **及时清理事件监听器**，避免内存泄漏
4. **异步操作要考虑错误处理**
5. **保持控制器的无状态性**，状态应存储在GameState中

## 🚀 性能优化建议

1. 使用事件节流/防抖处理高频事件
2. 避免在事件处理器中进行DOM操作
3. 使用requestAnimationFrame进行UI更新
4. 合理管理WebSocket连接，避免重复连接
5. 缓存常用的DOM引用

---

**版本**: 1.0  
**更新日期**: 2026-05-22  
**作者**: AI Assistant
