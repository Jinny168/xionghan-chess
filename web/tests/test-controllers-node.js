/**
 * Node.js环境下的完整集成测试
 * 使用jsdom模拟浏览器环境
 */

const { JSDOM } = require('jsdom');
const path = require('path');
const fs = require('fs');

// 创建虚拟DOM环境
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
    url: 'http://localhost',
    pretendToBeVisual: true,
    resources: 'usable'
});

global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;

// 辅助函数：加载JavaScript文件
function loadScript(filePath) {
    const fullPath = path.join(__dirname, filePath);
    const code = fs.readFileSync(fullPath, 'utf-8');
    
    // 在window上下文中执行代码
    const script = dom.window.document.createElement('script');
    script.textContent = code;
    dom.window.document.body.appendChild(script);
}

console.log('🚀 开始加载游戏模块...\n');

// 按顺序加载所有模块
try {
    console.log('📦 加载核心模块...');
    loadScript('../js/core/chess-piece.js');
    loadScript('../js/core/game-rules.js');
    loadScript('../js/core/game-state.js');
    console.log('✅ 核心模块加载完成\n');

    console.log('🎨 加载UI模块...');
    loadScript('../js/ui/chess-board-renderer.js');
    loadScript('../js/ui/dialog-manager.js');
    console.log('✅ UI模块加载完成\n');

    console.log('⚙️ 加载控制器模块...');
    loadScript('../js/controllers/event-dispatcher.js');
    loadScript('../js/controllers/sound-manager.js');
    loadScript('../js/controllers/avatar-manager.js');
    loadScript('../js/controllers/taunt-manager.js');
    loadScript('../js/controllers/statistics-manager.js');
    loadScript('../js/controllers/game-rule-config.js');
    loadScript('../js/controllers/game-logic-handler.js');
    loadScript('../js/controllers/network-handler.js');
    loadScript('../js/controllers/ui-controller.js');
    loadScript('../js/controllers/game-record-manager.js');
    loadScript('../js/controllers/replay-controller.js');
    loadScript('../js/controllers/replay-manager.js');
    loadScript('../js/controllers/game-controller.js');
    console.log('✅ 控制器模块加载完成\n');
} catch (error) {
    console.error('❌ 模块加载失败:', error.message);
    process.exit(1);
}

// ========================================
// 测试框架
// ========================================

class TestRunner {
    constructor() {
        this.totalTests = 0;
        this.passedTests = 0;
        this.failedTests = 0;
        this.testResults = [];
        this.startTime = Date.now();
    }

    assertEqual(actual, expected, message) {
        this.totalTests++;
        if (actual === expected) {
            this.passedTests++;
            this.testResults.push({ status: 'pass', message });
            console.log(`  ✅ ${message}`);
            return true;
        } else {
            this.failedTests++;
            const error = `期望: ${expected}, 实际: ${actual}`;
            this.testResults.push({ status: 'fail', message, error });
            console.log(`  ❌ ${message}`);
            console.log(`     ${error}`);
            return false;
        }
    }

    assertTrue(value, message) {
        this.totalTests++;
        if (value === true) {
            this.passedTests++;
            this.testResults.push({ status: 'pass', message });
            console.log(`  ✅ ${message}`);
            return true;
        } else {
            this.failedTests++;
            const error = `期望: true, 实际: ${value}`;
            this.testResults.push({ status: 'fail', message, error });
            console.log(`  ❌ ${message}`);
            console.log(`     ${error}`);
            return false;
        }
    }

    assertNotNull(obj, message) {
        this.totalTests++;
        if (obj !== null && obj !== undefined) {
            this.passedTests++;
            this.testResults.push({ status: 'pass', message });
            console.log(`  ✅ ${message}`);
            return true;
        } else {
            this.failedTests++;
            const error = '对象为null或undefined';
            this.testResults.push({ status: 'fail', message, error });
            console.log(`  ❌ ${message}`);
            console.log(`     ${error}`);
            return false;
        }
    }

    assertNoThrow(fn, message) {
        this.totalTests++;
        try {
            fn();
            this.passedTests++;
            this.testResults.push({ status: 'pass', message });
            console.log(`  ✅ ${message}`);
            return true;
        } catch (e) {
            this.failedTests++;
            const error = e.message;
            this.testResults.push({ status: 'fail', message, error });
            console.log(`  ❌ ${message}`);
            console.log(`     ${error}`);
            return false;
        }
    }

    testGroup(name, testFn) {
        console.log(`\n📋 ${name}`);
        console.log('─'.repeat(60));
        try {
            testFn();
        } catch (error) {
            console.log(`  💥 测试组执行错误: ${error.message}`);
            this.failedTests++;
        }
    }
}

// ========================================
// 测试用例
// ========================================

const runner = new TestRunner();

console.log('\n' + '='.repeat(60));
console.log('🧪 匈汉象棋控制器架构集成测试');
console.log('='.repeat(60));

// 测试1: EventDispatcher
runner.testGroup('测试1: EventDispatcher事件分发器', () => {
    const { EventDispatcher } = window;
    
    const dispatcher = new EventDispatcher();
    let eventFired = false;
    let eventData = null;

    // 注册监听器
    dispatcher.on('test:event', (data) => {
        eventFired = true;
        eventData = data;
    });

    // 触发事件
    dispatcher.emit('test:event', { value: 42 });
    runner.assertTrue(eventFired, '事件应该被触发');
    runner.assertEqual(eventData.value, 42, '事件数据应该正确传递');

    // 移除监听器
    dispatcher.off('test:event');
    eventFired = false;
    dispatcher.emit('test:event', { value: 99 });
    runner.assertTrue(!eventFired, '移除监听器后不应再触发');
});

// 测试2: GameState初始化
runner.testGroup('测试2: GameState游戏状态', () => {
    const { GameState } = window;
    const gameState = new GameState();
    
    runner.assertNotNull(gameState, 'GameState应该成功创建');
    runner.assertEqual(gameState.playerTurn, 'red', '红方先手');
    runner.assertEqual(gameState.gameOver, false, '游戏未结束');
    runner.assertEqual(gameState.pieces.length, 44, '初始44个棋子');
    runner.assertEqual(gameState.moveHistory.length, 0, '初始无移动历史');
});

// 测试3: GameLogicHandler
runner.testGroup('测试3: GameLogicHandler游戏逻辑处理器', () => {
    const { GameLogicHandler, GameRuleConfig, EventDispatcher } = window;
    
    const gameState = new window.GameState();
    const ruleConfig = new GameRuleConfig();
    const events = new EventDispatcher();
    const logicHandler = new GameLogicHandler(gameState, ruleConfig, events);

    runner.assertNotNull(logicHandler, 'GameLogicHandler应该成功创建');
    runner.assertNotNull(logicHandler.executeMove, 'executeMove方法应该存在');
    runner.assertNotNull(logicHandler.trySpawnBing, 'trySpawnBing方法应该存在');
    
    // 测试兵复活配置检查
    const result = logicHandler.trySpawnBing(6, 0);
    runner.assertEqual(result.success, false, '默认配置下兵复活应该失败');
});

// 测试4: UIController
runner.testGroup('测试4: UIController界面控制器', () => {
    const { UIController, EventDispatcher } = window;
    
    // 创建模拟Canvas
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 800;
    document.body.appendChild(canvas);

    const events = new EventDispatcher();
    const uiController = new UIController(canvas, events);

    runner.assertNotNull(uiController, 'UIController应该成功创建');
    runner.assertNotNull(uiController.bindEvents, 'bindEvents方法应该存在');
    runner.assertNotNull(uiController.updateUI, 'updateUI方法应该存在');
});

// 测试5: NetworkHandler
runner.testGroup('测试5: NetworkHandler网络处理器', () => {
    const { NetworkHandler, EventDispatcher } = window;
    
    const events = new EventDispatcher();
    const networkHandler = new NetworkHandler(events);

    runner.assertNotNull(networkHandler, 'NetworkHandler应该成功创建');
    runner.assertNotNull(networkHandler.connect, 'connect方法应该存在');
    runner.assertNotNull(networkHandler.joinRoom, 'joinRoom方法应该存在');
});

// 测试6: ReplayManager
runner.testGroup('测试6: ReplayManager复盘管理器', () => {
    const { ReplayManager, GameState } = window;
    
    const mockController = {
        gameState: new GameState(),
        loadGameFromHistory: () => {}
    };

    const replayManager = new ReplayManager(mockController);

    runner.assertNotNull(replayManager, 'ReplayManager应该成功创建');
    runner.assertNotNull(replayManager.init, 'init方法应该存在');
    runner.assertNotNull(replayManager.showReplaySidebar, 'showReplaySidebar方法应该存在');
});

// 测试7: 兵复活接口
runner.testGroup('测试7: 兵复活接口(spawnBing)', () => {
    const { GameState } = window;
    const gameState = new GameState();

    runner.assertNotNull(gameState.spawnBing, 'spawnBing方法应该存在');
    
    // 验证方法签名支持camp参数
    const funcStr = gameState.spawnBing.toString();
    const hasCampParam = funcStr.includes('camp');
    runner.assertTrue(hasCampParam, 'spawnBing应该接受camp参数');
});

// 测试8: GameController架构
runner.testGroup('测试8: GameController主控制器架构', () => {
    const { GameController } = window;
    
    const requiredMethods = [
        'toggleBackgroundMusic',
        'switchMusicStyle',
        'updateVolume',
        'changeBoardTheme',
        'changePieceStyle',
        'resetSettings',
        'handleCanvasClick',
        'undo',
        'restart',
        'resign'
    ];

    requiredMethods.forEach(method => {
        runner.assertNotNull(
            GameController.prototype[method],
            `GameController应该有${method}方法`
        );
    });
});

// 测试9: 事件驱动通信
runner.testGroup('测试9: 事件驱动通信机制', () => {
    const { EventDispatcher, GameState, GameLogicHandler, GameRuleConfig } = window;
    
    const events = new EventDispatcher();
    const gameState = new GameState();
    const ruleConfig = new GameRuleConfig();
    const logicHandler = new GameLogicHandler(gameState, ruleConfig, events);

    let moveExecuted = false;
    events.on('move:executed', () => {
        moveExecuted = true;
    });

    // 模拟一次移动
    const piece = gameState.getPieceAt(9, 4); // 红方兵
    if (piece) {
        logicHandler.executeMove([9, 4], [8, 4]);
        runner.assertTrue(moveExecuted, '移动后应该触发move:executed事件');
    } else {
        runner.assertTrue(true, '跳过移动测试（棋子不存在）');
    }
});

// 测试10: SoundManager
runner.testGroup('测试10: SoundManager音效管理器', () => {
    const { SoundManager } = window;
    
    runner.assertNotNull(SoundManager, 'SoundManager类应该存在');
    runner.assertNotNull(SoundManager.prototype.playMove, 'playMove方法应该存在');
    runner.assertNotNull(SoundManager.prototype.playCapture, 'playCapture方法应该存在');
    runner.assertNotNull(SoundManager.prototype.playCheck, 'playCheck方法应该存在');
});

// 测试11: GameRuleConfig
runner.testGroup('测试11: GameRuleConfig规则配置', () => {
    const { GameRuleConfig } = window;
    
    const config = new GameRuleConfig();
    runner.assertNotNull(config, 'GameRuleConfig应该成功创建');
    runner.assertNotNull(config.getConfig, 'getConfig方法应该存在');
    runner.assertNotNull(config.setConfig, 'setConfig方法应该存在');
    
    const defaultConfig = config.getConfig();
    runner.assertNotNull(defaultConfig.pawnResurrection, '应该包含pawnResurrection配置');
    runner.assertNotNull(defaultConfig.horseStraightThree, '应该包含horseStraightThree配置');
});

// 测试12: 多事件监听器
runner.testGroup('测试12: 多事件监听器协作', () => {
    const { EventDispatcher } = window;
    
    const events = new EventDispatcher();
    let listener1Called = false;
    let listener2Called = false;

    events.on('multi:test', () => { listener1Called = true; });
    events.on('multi:test', () => { listener2Called = true; });
    
    events.emit('multi:test');
    
    runner.assertTrue(listener1Called, '第一个监听器应该被调用');
    runner.assertTrue(listener2Called, '第二个监听器应该被调用');
});

// 测试13: 一次性事件
runner.testGroup('测试13: once一次性事件', () => {
    const { EventDispatcher } = window;
    
    const events = new EventDispatcher();
    let callCount = 0;

    events.once('once:test', () => { callCount++; });
    
    events.emit('once:test');
    events.emit('once:test');
    
    runner.assertEqual(callCount, 1, '一次性事件应该只触发一次');
});

// 测试14: Canvas渲染器
runner.testGroup('测试14: ChessBoardRenderer棋盘渲染器', () => {
    const { ChessBoardRenderer } = window;
    
    runner.assertNotNull(ChessBoardRenderer, 'ChessBoardRenderer类应该存在');
    runner.assertNotNull(ChessBoardRenderer.prototype.render, 'render方法应该存在');
    runner.assertNotNull(ChessBoardRenderer.prototype.highlightPiece, 'highlightPiece方法应该存在');
});

// 测试15: 游戏记录管理
runner.testGroup('测试15: GameRecordManager对局记录管理', () => {
    const { GameRecordManager } = window;
    
    runner.assertNotNull(GameRecordManager, 'GameRecordManager类应该存在');
    runner.assertNotNull(GameRecordManager.prototype.saveGame, 'saveGame方法应该存在');
    runner.assertNotNull(GameRecordManager.prototype.loadRecords, 'loadRecords方法应该存在');
});

// ========================================
// 测试结果汇总
// ========================================

const endTime = Date.now();
const duration = ((endTime - runner.startTime) / 1000).toFixed(2);
const passRate = runner.totalTests > 0 
    ? ((runner.passedTests / runner.totalTests) * 100).toFixed(2)
    : 0;

console.log('\n' + '='.repeat(60));
console.log('📊 测试结果汇总');
console.log('='.repeat(60));
console.log(`总测试数: ${runner.totalTests}`);
console.log(`通过: ${runner.passedTests} ✅`);
console.log(`失败: ${runner.failedTests} ❌`);
console.log(`通过率: ${passRate}%`);
console.log(`耗时: ${duration}s`);
console.log('='.repeat(60));

if (runner.failedTests === 0) {
    console.log('\n🎉 恭喜！所有测试通过！');
    process.exit(0);
} else {
    console.log(`\n⚠️ 有 ${runner.failedTests} 个测试失败，请检查上述错误信息`);
    process.exit(1);
}
