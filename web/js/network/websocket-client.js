/**
 * WebSocket客户端 - 使用Socket.IO处理网络通信
 * 优化版本：支持单台电脑多窗口测试
 */

class WebSocketClient {
    constructor(serverUrl) {
        this.serverUrl = serverUrl;
        this.socket = null;
        this.callbacks = {};
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10; // 增加重连次数
        this.reconnectDelay = 1000; // 减少初始重连延迟
        this.roomId = null;
        this.playerCamp = null;
    }
    
    /**
     * 连接服务器 - 使用Socket.IO
     */
    connect() {
        return new Promise((resolve, reject) => {
            try {
                // 检查Socket.IO是否已加载
                if (typeof io === 'undefined') {
                    console.error('Socket.IO库未加载，尝试动态加载...');
                    this.loadSocketIO().then(() => {
                        this.initializeSocket(resolve, reject);
                    }).catch(reject);
                } else {
                    this.initializeSocket(resolve, reject);
                }
            } catch (error) {
                console.error('WebSocket连接失败:', error);
                reject(error);
                this.scheduleReconnect();
            }
        });
    }
    
    /**
     * 动态加载Socket.IO库
     */
    loadSocketIO() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = '/socket.io/socket.io.js';
            script.onload = () => {
                console.log('Socket.IO库加载成功');
                resolve();
            };
            script.onerror = () => {
                console.error('Socket.IO库加载失败');
                reject(new Error('无法加载Socket.IO库'));
            };
            document.head.appendChild(script);
        });
    }
    
    /**
     * 初始化Socket连接
     */
    initializeSocket(resolve, reject) {
        // Socket.IO配置 - 优化本地测试
        this.socket = io(this.serverUrl, {
            transports: ['websocket', 'polling'], // 优先使用websocket，降级到polling
            reconnection: true,
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: this.reconnectDelay,
            timeout: 10000,
            forceNew: true // 强制创建新连接，避免多窗口冲突
        });
        
        this.setupEventHandlers(resolve, reject);
    }
    
    /**
     * 设置事件处理器 - Socket.IO版本
     */
    setupEventHandlers(resolve, reject) {
        // 连接成功
        this.socket.on('connect', () => {
            console.log('✅ Socket.IO连接成功, ID:', this.socket.id);
            this.connected = true;
            this.reconnectAttempts = 0;
            
            if (resolve) {
                resolve();
            }
        });
        
        // 连接错误
        this.socket.on('connect_error', (error) => {
            console.error('❌ Socket.IO连接错误:', error.message);
            this.connected = false;
            
            if (reject) {
                reject(error);
            }
        });
        
        // 断开连接
        this.socket.on('disconnect', (reason) => {
            console.log('⚠️ Socket.IO断开连接:', reason);
            this.connected = false;
            
            if (reason === 'io server disconnect') {
                // 服务端主动断开，需要手动重连
                this.socket.connect();
            }
        });
        
        // 重连中
        this.socket.on('reconnecting', (attemptNumber) => {
            console.log(`🔄 正在重连... 第${attemptNumber}次尝试`);
        });
        
        // 重连成功
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`✅ 重连成功！共尝试${attemptNumber}次`);
            this.connected = true;
        });
        
        // 重连失败
        this.socket.on('reconnect_failed', () => {
            console.error('❌ 重连失败，已达到最大重试次数');
        });
        
        // 监听游戏事件
        this.setupGameEvents();
    }
    
    /**
     * 设置游戏相关事件监听
     */
    setupGameEvents() {
        // 对手移动
        this.socket.on('opponent_move', (data) => {
            console.log('📥 收到对手移动:', data);
            this.trigger('opponent_move', data);
        });
        
        // 游戏结束
        this.socket.on('game_over', (data) => {
            console.log('🏁 游戏结束:', data);
            this.trigger('game_over', data);
        });
        
        // 聊天消息
        this.socket.on('chat_message', (data) => {
            console.log('💬 收到聊天消息:', data);
            this.trigger('chat_message', data);
        });
        
        // 悔棋请求
        this.socket.on('undo_request', (data) => {
            console.log('↩️ 收到悔棋请求:', data);
            this.trigger('undo_request', data);
        });
        
        // 悔棋响应
        this.socket.on('undo_response', (data) => {
            console.log('↩️ 收到悔棋响应:', data);
            this.trigger('undo_response', data);
        });
        
        // 重新开始请求
        this.socket.on('restart_request', (data) => {
            console.log('🔄 收到重新开始请求:', data);
            this.trigger('restart_request', data);
        });
        
        // 游戏重新开始
        this.socket.on('game_restart', (data) => {
            console.log('🔄 游戏重新开始');
            this.trigger('game_restart', data);
        });
        
        // 玩家断开
        this.socket.on('player_disconnected', (data) => {
            console.log('⚠️ 对手断开连接:', data);
            this.trigger('player_disconnected', data);
        });
        
        // 加入房间成功
        this.socket.on('joined', (data) => {
            console.log('✅ 加入房间成功:', data);
            this.roomId = data.roomId;
            this.playerCamp = data.camp;
            this.trigger('joined', data);
        });
        
        // 游戏开始
        this.socket.on('game_start', (data) => {
            console.log('🎮 游戏开始:', data);
            this.trigger('game_start', data);
        });
        
        // 错误消息
        this.socket.on('error', (data) => {
            console.error('❌ 收到错误:', data);
            this.trigger('error', data);
        });
    }
    

    
    /**
     * 发送消息 - Socket.IO版本
     */
    send(eventName, data) {
        if (this.socket && this.connected) {
            console.log('📤 发送消息:', eventName, data);
            this.socket.emit(eventName, data || {});
        } else {
            console.warn('⚠️ Socket未连接，无法发送消息');
        }
    }
    
    /**
     * 发送移动
     */
    sendMove(fromRow, fromCol, toRow, toCol) {
        this.send('move', {
            fromRow,
            fromCol,
            toRow,
            toCol,
            timestamp: Date.now()
        });
    }
    
    /**
     * 加入游戏房间
     */
    joinGameRoom(roomId) {
        console.log(`🚪 加入房间: ${roomId}`);
        this.send('join_game_room', { roomId });
    }
    
    /**
     * 发送悔棋请求
     */
    sendUndoRequest() {
        this.send('undo_request');
    }
    
    /**
     * 发送悔棋响应
     */
    sendUndoResponse(accepted) {
        this.send('undo_response', { accepted });
    }
    
    /**
     * 发送重新开始请求
     */
    sendRestartRequest() {
        this.send('restart_request');
    }
    
    /**
     * 发送认输
     */
    sendResign() {
        this.send('resign');
    }
    
    /**
     * 发送聊天消息
     */
    sendChat(message) {
        this.send('chat', { message });
    }
    
    /**
     * 注册事件回调
     */
    on(event, callback) {
        this.callbacks[event] = callback;
    }
    
    /**
     * 触发事件
     */
    trigger(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event](data);
        }
    }
    
    /**
     * 计划重连 - Socket.IO自动处理重连
     */
    scheduleReconnect() {
        // Socket.IO会自动处理重连，这里只记录日志
        console.log('Socket.IO将自动尝试重连...');
    }
    
    /**
     * 断开连接
     */
    disconnect() {
        if (this.socket) {
            console.log('🔌 主动断开连接');
            this.socket.disconnect();
            this.connected = false;
        }
    }
    
    /**
     * 检查是否已连接
     */
    isConnected() {
        return this.connected && this.socket && this.socket.connected;
    }
    
    /**
     * 获取当前房间ID
     */
    getRoomId() {
        return this.roomId;
    }
    
    /**
     * 获取当前玩家阵营
     */
    getPlayerCamp() {
        return this.playerCamp;
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketClient;
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.WebSocketClient = WebSocketClient;
}
