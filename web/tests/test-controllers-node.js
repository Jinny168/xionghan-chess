/**
 * 控制器单元测试 - Node.js环境
 * 使用简单的断言库进行测试
 */

// 模拟浏览器环境
global.window = {
    location: {
        protocol: 'http:',
        host: 'localhost'
    },
    dialogManager: {
        showInfo: () => {},
        showError: () => {},
        showConfirm: () => {}
    },
    GameRules: {
        getRuleConfig: () => ({})
    }
};

global.document = {
    body: {
        classList: {
            add: () => {},
            remove: () => {},
            contains: () => false
        },
        appendChild: () => {},
        removeChild: () => {}
    },
    createElement: () => ({
        style: {},
        classList: {
            add: () => {},
            remove: () => {},
            toggle: () => {}
        },
        appendChild: () => {},
        remove: () => {},
        scrollTop: 0,
        scrollHeight: 0,
        innerHTML: '',
        textContent: '',
        value: '',
        addEventListener: () => {}
    }),
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => []
};

// 简单的断言库
class Assert {
    static equal(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(`${message}: 期望 ${expected}, 实际 ${actual}`);
        }
    }
    
    static notEqual(actual, expected, message) {
        if (actual === expected) {
            throw new Error(`${message}: 不应该相等`);
        }
    }
    
    static ok(value, message) {
        if (!value) {
            throw new Error(`${message}: 值为假`);
        }
    }
    
    static strictEqual(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(`${message}: 期望 ${expected} (${typeof expected}), 实际 ${actual} (${typeof actual})`);
        }
    }
    
    static deepEqual(actual, expected, message) {
        const actualStr = JSON.stringify(actual);
        const expectedStr = JSON.stringify(expected);
        if (actualStr !== expectedStr) {
            throw new Error(`${message}: 深度不相等`);
        }
    }
    
    static throws(fn, message) {
        try {
            fn();
            throw new Error(`${message}: 应该抛出异常`);
        } catch (e) {
            // 预期会抛出异常
        }
    }
}

// 测试结果统计
const results = {
    total: 0,
    passed: 0,
    failed: 0,
    tests: []
};

function test(name, fn) {
    results.total++;
    try {
        fn();
        results.passed++;
        results.tests.push({ name, status: 'PASS' });
        console.log(`✅ ${name}`);
    } catch (error) {
        results.failed++;
        results.tests.push({ name, status: 'FAIL', error: error.message });
        console.error(`❌ ${name}`);
        console.error(`   错误: ${error.message}`);
    }
}

// ==================== 测试开始 ====================

console.log('\n🧪 开始运行控制器单元测试...\n');

// 测试1: EventDispatcher
console.log('📋 测试模块: EventDispatcher');

test('EventDispatcher应该能够实例化', () => {
    const { EventDispatcher } = require('../js/controllers/event-dispatcher.js');
    const dispatcher = new EventDispatcher();
    Assert.ok(dispatcher instanceof EventDispatcher, 'EventDispatcher实例化');
});

test('EventDispatcher应该能够订阅和发布事件', () => {
    const { EventDispatcher } = require('../js/controllers/event-dispatcher.js');
    const dispatcher = new EventDispatcher();
    
    let triggered = false;
    let data = null;
    
    dispatcher.on('test:event', (d) => {
        triggered = true;
        data = d;
    });
    
    dispatcher.emit('test:event', { message: 'hello' });
    
    Assert.ok(triggered, '事件应该被触发');
    Assert.equal(data.message, 'hello', '事件数据应该正确传递');
});

test('EventDispatcher应该能够取消订阅', () => {
    const { EventDispatcher } = require('../js/controllers/event-dispatcher.js');
    const dispatcher = new EventDispatcher();
    
    let count = 0;
    const unsubscribe = dispatcher.on('test:event', () => {
        count++;
    });
    
    dispatcher.emit('test:event');
    Assert.equal(count, 1, '第一次触发应该计数');
    
    unsubscribe();
    dispatcher.emit('test:event');
    Assert.equal(count, 1, '取消订阅后不应该再触发');
});

test('EventDispatcher应该支持一次性事件', () => {
    const { EventDispatcher } = require('../js/controllers/event-dispatcher.js');
    const dispatcher = new EventDispatcher();
    
    let count = 0;
    dispatcher.once('once:event', () => {
        count++;
    });
    
    dispatcher.emit('once:event');
    dispatcher.emit('once:event');
    
    Assert.equal(count, 1, '一次性事件应该只触发一次');
});

test('GameEvents常量应该正确定义', () => {
    const { GameEvents } = require('../js/controllers/event-dispatcher.js');
    
    Assert.equal(GameEvents.PIECE_MOVED, 'piece:moved', 'PIECE_MOVED常量');
    Assert.equal(GameEvents.GAME_END, 'game:end', 'GAME_END常量');
    Assert.equal(GameEvents.CHECK_DETECTED, 'check:detected', 'CHECK_DETECTED常量');
});

console.log('');

// 测试2: GameLogicHandler
console.log('📋 测试模块: GameLogicHandler');

test('GameLogicHandler应该能够实例化', () => {
    // 需要加载依赖
    require('../js/core/game-state.js');
    require('../js/controllers/game-rule-config.js');
    require('../js/controllers/event-dispatcher.js');
    const { GameLogicHandler } = require('../js/controllers/game-logic-handler.js');
    
    const gameState = new GameState();
    const ruleConfig = new GameRuleConfig();
    const events = new EventDispatcher();
    
    const handler = new GameLogicHandler(gameState, ruleConfig, events);
    Assert.ok(handler instanceof GameLogicHandler, 'GameLogicHandler实例化');
});

test('GameLogicHandler应该返回空的移动历史', () => {
    require('../js/core/game-state.js');
    require('../js/controllers/game-rule-config.js');
    require('../js/controllers/event-dispatcher.js');
    const { GameLogicHandler } = require('../js/controllers/game-logic-handler.js');
    
    const gameState = new GameState();
    const ruleConfig = new GameRuleConfig();
    const events = new EventDispatcher();
    
    const handler = new GameLogicHandler(gameState, ruleConfig, events);
    const history = handler.getMoveHistory();
    
    Assert.ok(Array.isArray(history), '移动历史应该是数组');
    Assert.equal(history.length, 0, '初始移动历史应该为空');
});

test('GameLogicHandler应该能够清空历史', () => {
    require('../js/core/game-state.js');
    require('../js/controllers/game-rule-config.js');
    require('../js/controllers/event-dispatcher.js');
    const { GameLogicHandler } = require('../js/controllers/game-logic-handler.js');
    
    const gameState = new GameState();
    const ruleConfig = new GameRuleConfig();
    const events = new EventDispatcher();
    
    const handler = new GameLogicHandler(gameState, ruleConfig, events);
    handler.clearHistory();
    
    Assert.equal(handler.getMoveHistory().length, 0, '清空后历史应该为空');
});

console.log('');

// 测试3: NetworkHandler
console.log('📋 测试模块: NetworkHandler');

test('NetworkHandler应该能够实例化', () => {
    require('../js/controllers/event-dispatcher.js');
    const { NetworkHandler } = require('../js/controllers/network-handler.js');
    
    const events = new EventDispatcher();
    const handler = new NetworkHandler(events);
    
    Assert.ok(handler instanceof NetworkHandler, 'NetworkHandler实例化');
});

test('NetworkHandler初始状态应该正确', () => {
    require('../js/controllers/event-dispatcher.js');
    const { NetworkHandler } = require('../js/controllers/network-handler.js');
    
    const events = new EventDispatcher();
    const handler = new NetworkHandler(events);
    
    const status = handler.getStatus();
    
    Assert.equal(status.isConnected, false, '初始应该未连接');
    Assert.equal(status.roomId, null, '初始应该无房间ID');
    Assert.equal(status.playerCamp, null, '初始应该无阵营');
});

console.log('');

// 测试4: UIController
console.log('📋 测试模块: UIController');

test('UIController应该能够实例化', () => {
    require('../js/controllers/event-dispatcher.js');
    const { UIController } = require('../js/controllers/ui-controller.js');
    
    const canvas = document.createElement('canvas');
    const events = new EventDispatcher();
    
    const controller = new UIController(canvas, events);
    Assert.ok(controller instanceof UIController, 'UIController实例化');
});

test('UIController应该能够切换暗黑模式', () => {
    require('../js/controllers/event-dispatcher.js');
    const { UIController } = require('../js/controllers/ui-controller.js');
    
    const canvas = document.createElement('canvas');
    const events = new EventDispatcher();
    
    const controller = new UIController(canvas, events);
    
    controller.toggleDarkMode(false);
    Assert.equal(controller.isDarkMode, false, '暗黑模式应该关闭');
    
    controller.toggleDarkMode(true);
    Assert.equal(controller.isDarkMode, true, '暗黑模式应该开启');
});

console.log('');

// 输出测试结果
console.log('\n' + '='.repeat(60));
console.log('📊 测试结果汇总');
console.log('='.repeat(60));
console.log(`总测试数: ${results.total}`);
console.log(`通过: ${results.passed} ✅`);
console.log(`失败: ${results.failed} ❌`);
console.log(`通过率: ${((results.passed / results.total) * 100).toFixed(2)}%`);
console.log('='.repeat(60));

if (results.failed > 0) {
    console.log('\n❌ 失败的测试:');
    results.tests
        .filter(t => t.status === 'FAIL')
        .forEach(t => {
            console.log(`  - ${t.name}`);
            console.log(`    错误: ${t.error}`);
        });
    process.exit(1);
} else {
    console.log('\n🎉 所有测试通过！');
    process.exit(0);
}
