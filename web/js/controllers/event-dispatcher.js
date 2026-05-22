/**
 * 事件分发器 - 统一管理游戏事件
 * 职责：事件的发布与订阅，解耦各模块间的通信
 */

class EventDispatcher {
    constructor() {
        this.listeners = new Map();
    }

    /**
     * 注册事件监听器
     * @param {string} eventName - 事件名称
     * @param {Function} callback - 回调函数
     * @param {Object} context - 上下文对象
     */
    on(eventName, callback, context = null) {
        if (!this.listeners.has(eventName)) {
            this.listeners.set(eventName, []);
        }
        
        const listener = { callback, context };
        this.listeners.get(eventName).push(listener);
        
        return () => this.off(eventName, callback); // 返回取消订阅函数
    }

    /**
     * 移除事件监听器
     * @param {string} eventName - 事件名称
     * @param {Function} callback - 回调函数（可选，不传则移除该事件的所有监听器）
     */
    off(eventName, callback = null) {
        if (!this.listeners.has(eventName)) return;
        
        if (callback === null) {
            // 如果没有提供callback，移除该事件的所有监听器
            this.listeners.delete(eventName);
        } else {
            // 否则只移除匹配的监听器
            const listeners = this.listeners.get(eventName);
            const index = listeners.findIndex(l => l.callback === callback);
            
            if (index !== -1) {
                listeners.splice(index, 1);
            }
        }
    }

    /**
     * 触发事件
     * @param {string} eventName - 事件名称
     * @param {*} data - 事件数据
     */
    emit(eventName, data = null) {
        if (!this.listeners.has(eventName)) return;
        
        const listeners = this.listeners.get(eventName);
        listeners.forEach(({ callback, context }) => {
            try {
                callback.call(context, data);
            } catch (error) {
                console.error(`事件 ${eventName} 处理出错:`, error);
            }
        });
    }

    /**
     * 一次性事件监听
     * @param {string} eventName - 事件名称
     * @param {Function} callback - 回调函数
     * @param {Object} context - 上下文对象
     */
    once(eventName, callback, context = null) {
        const wrapper = (data) => {
            this.off(eventName, wrapper);
            callback.call(context, data);
        };
        
        this.on(eventName, wrapper);
    }

    /**
     * 清除所有监听器
     */
    clearAll() {
        this.listeners.clear();
    }

    /**
     * 获取某个事件的监听器数量
     * @param {string} eventName - 事件名称
     * @returns {number}
     */
    listenerCount(eventName) {
        if (!this.listeners.has(eventName)) return 0;
        return this.listeners.get(eventName).length;
    }
}

// 定义游戏事件常量
const GameEvents = {
    // 游戏状态事件
    GAME_INIT: 'game:init',
    GAME_START: 'game:start',
    GAME_END: 'game:end',
    GAME_RESET: 'game:reset',
    
    // 棋子事件
    PIECE_SELECTED: 'piece:selected',
    PIECE_MOVED: 'piece:moved',
    PIECE_CAPTURED: 'piece:captured',
    PIECE_SPAWNED: 'piece:spawned',
    
    // 回合事件
    TURN_CHANGED: 'turn:changed',
    CHECK_DETECTED: 'check:detected',
    CHECKMATE_DETECTED: 'checkmate:detected',
    
    // UI事件
    UI_UPDATED: 'ui:updated',
    MOVE_HISTORY_UPDATED: 'history:updated',
    TIMER_UPDATED: 'timer:updated',
    
    // 网络事件
    NETWORK_CONNECTED: 'network:connected',
    NETWORK_DISCONNECTED: 'network:disconnected',
    OPPONENT_MOVE: 'opponent:move',
    OPPONENT_JOINED: 'opponent:joined',
    
    // 复盘事件
    REPLAY_STARTED: 'replay:started',
    REPLAY_STOPPED: 'replay:stopped',
    REPLAY_STEP: 'replay:step',
    
    // 音效事件
    SOUND_PLAY: 'sound:play',
    
    // 统计事件
    STATISTICS_UPDATED: 'statistics:updated'
};

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.EventDispatcher = EventDispatcher;
    window.GameEvents = GameEvents;
}
