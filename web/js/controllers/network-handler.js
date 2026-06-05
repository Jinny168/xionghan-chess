/**
 * 网络处理器 - 管理所有网络通信
 * 职责：WebSocket连接、消息收发、断线重连、房间管理
 */

class NetworkHandler {
    constructor(eventDispatcher) {
        this.events = eventDispatcher;
        this.network = null;
        
        // 网络状态
        this.isConnected = false;
        this.roomId = null;
        this.playerCamp = null;
        this.isHost = false;
        this.opponentConnected = false;
        
        // 重连配置
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000; // 2秒
    }

    /**
     * 初始化网络连接
     * @param {string} roomId - 房间ID
     */
    initialize(roomId) {
        if (!roomId) {
            console.warn('⚠️ 房间ID为空，无法初始化网络连接');
            return;
        }
        
        this.roomId = roomId;
        
        console.log(`🚀 正在连接房间: ${roomId}`);
        
        // 创建Socket.IO客户端
        const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
        const host = window.location.host;
        const serverUrl = `${protocol}//${host}`;
        
        // 检查WebSocketClient是否已加载
        if (typeof WebSocketClient === 'undefined') {
            console.error('❌ WebSocketClient类未加载，请检查HTML中是否包含websocket-client.js');
            return;
        }
        
        this.network = new WebSocketClient(serverUrl);
        
        // 检查网络连接是否创建成功
        if (!this.network) {
            console.error('❌ 网络客户端创建失败');
            return;
        }
        
        // 注册事件回调
        this.registerEventHandlers();
        
        // 先连接服务器，再加入房间
        this.network.connect().then(() => {
            console.log('✅ 服务器连接成功，加入房间');
            this.joinRoom(roomId);
        }).catch((error) => {
            console.error('❌ 服务器连接失败:', error);
        });
    }

    /**
     * 注册网络事件处理器
     * @private
     */
    registerEventHandlers() {
        // 连接成功
        this.network.on('connected', () => {
            console.log('✅ WebSocket连接成功');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            
            this.events.emit('network:connected');
        });

        // 断开连接
        this.network.on('disconnected', () => {
            console.log('❌ WebSocket断开连接');
            this.isConnected = false;
            
            this.events.emit('network:disconnected');
            
            // 尝试重连
            this.attemptReconnect();
        });

        // 加入房间成功
        this.network.on('joined', (data) => {
            console.log(`✅ 成功加入房间，阵营: ${data.camp}`);
            this.playerCamp = data.camp;
            this.isHost = data.isHost || false;
            this.opponentConnected = data.opponentConnected || false;
            
            this.events.emit('opponent:joined', {
                camp: this.playerCamp,
                isHost: this.isHost,
                opponentConnected: this.opponentConnected
            });
            
            if (this.opponentConnected) {
                console.log('👥 对手已连接，准备开始游戏');
                if (window.dialogManager) {
                    window.dialogManager.showInfo('提示', '对手已连接，游戏即将开始！');
                }
            } else {
                console.log('⏳ 等待对手连接...');
                if (window.dialogManager) {
                    window.dialogManager.showInfo('提示', '等待对手连接...', 3000);
                }
            }
        });

        // 游戏开始
        this.network.on('game_start', (data) => {
            console.log('🎮 游戏开始！', data);
            this.opponentConnected = true;
            
            const campText = this.playerCamp === 'red' ? '红' : '黑';
            const hostText = this.isHost ? '（房主）' : '（客人）';
            
            if (window.dialogManager) {
                window.dialogManager.showInfo('游戏开始', `您执${campText}棋${hostText}`);
            }
        });

        // 收到对手移动
        this.network.on('opponent_move', (data) => {
            console.log('📥 收到对手移动:', data);
            this.events.emit('opponent:move', data);
        });

        // 游戏结束
        this.network.on('game_over', (data) => {
            console.log('🏁 游戏结束:', data);
            this.handleGameOver(data);
        });

        // 聊天消息
        this.network.on('chat_message', (data) => {
            console.log('💬 收到聊天消息:', data);
            this.events.emit('chat:message', data);
        });

        // 悔棋请求
        this.network.on('undo_request', (data) => {
            console.log('↩️ 收到悔棋请求:', data);
            this.events.emit('undo:request', data);
        });

        // 重新开始请求
        this.network.on('restart_request', (data) => {
            console.log('🔄 收到重新开始请求:', data);
            this.events.emit('restart:request', data);
        });
    }

    /**
     * 加入房间
     * @param {string} roomId
     */
    joinRoom(roomId) {
        if (!this.network) {
            console.warn('⚠️ 网络客户端未初始化，无法加入房间');
            return;
        }
        
        if (typeof this.network.joinGameRoom !== 'function') {
            console.error('❌ 网络客户端没有joinGameRoom方法');
            return;
        }
        
        this.network.joinGameRoom(roomId);
    }

    /**
     * 发送移动
     * @param {Object} moveData - 移动数据
     */
    sendMove(moveData) {
        if (!this.isConnected) {
            console.warn('⚠️ 网络未连接，无法发送移动');
            return false;
        }
        
        // 注意：服务端监听的是move事件，不是player_move
        // eslint-disable-next-line spellcheck/spell-checker
        this.network.send('move', moveData);
        return true;
    }

    /**
     * 发送聊天消息
     * @param {string} message
     */
    sendChatMessage(message) {
        if (!this.isConnected) return;
        
        this.network.send('chat_message', {
            message: message,
            timestamp: Date.now()
        });
    }

    /**
     * 发送悔棋请求
     */
    requestUndo() {
        if (!this.isConnected) return;
        
        this.network.send('undo_request');
    }

    /**
     * 响应悔棋请求
     * @param {boolean} accepted
     */
    respondUndo(accepted) {
        if (!this.isConnected) return;
        
        this.network.send('undo_response', { accepted });
    }

    /**
     * 发送重新开始请求
     */
    requestRestart() {
        if (!this.isConnected) return;
        
        this.network.send('restart_request');
    }

    /**
     * 响应重新开始请求
     * @param {boolean} accepted
     */
    respondRestart(accepted) {
        if (!this.isConnected) return;
        
        this.network.send('restart_response', { accepted });
    }

    /**
     * 认输
     */
    resign() {
        if (!this.isConnected) return;
        
        this.network.send('resign');
    }

    /**
     * 处理游戏结束
     * @private
     */
    handleGameOver(data) {
        const winnerText = data.winner === this.playerCamp ? '你赢了！' : '你输了！';
        
        if (window.dialogManager) {
            window.dialogManager.showInfo('游戏结束', winnerText);
        }
    }

    /**
     * 尝试重连
     * @private
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ 达到最大重连次数，放弃重连');
            
            if (window.dialogManager) {
                window.dialogManager.showError('连接失败', '无法重新连接到服务器，请刷新页面重试');
            }
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`🔄 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，${delay}ms后...`);
        
        setTimeout(() => {
            if (this.roomId) {
                this.joinRoom(this.roomId);
            }
        }, delay);
    }

    /**
     * 断开连接
     */
    disconnect() {
        if (this.network) {
            this.network.disconnect();
            this.isConnected = false;
        }
    }
}

// 浏览器全局导出
if (typeof window !== 'undefined') {
    window.NetworkHandler = NetworkHandler;
}
