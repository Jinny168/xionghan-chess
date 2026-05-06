/**
 * WebSocket客户端 - 处理网络通信
 */

class WebSocketClient {
    constructor(serverUrl) {
        this.serverUrl = serverUrl;
        this.ws = null;
        this.callbacks = {};
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000; // 2秒
    }
    
    /**
     * 连接服务器
     */
    connect() {
        try {
            this.ws = new WebSocket(this.serverUrl);
            this.setupEventHandlers();
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.scheduleReconnect();
        }
    }
    
    /**
     * 设置事件处理器
     */
    setupEventHandlers() {
        this.ws.onopen = () => {
            console.log('WebSocket连接成功');
            this.connected = true;
            this.reconnectAttempts = 0;
            
            // 发送握手消息
            this.send({ type: 'handshake', data: { version: '1.0' } });
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('解析消息失败:', error);
            }
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket连接关闭');
            this.connected = false;
            this.scheduleReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };
    }
    
    /**
     * 处理接收到的消息
     */
    handleMessage(data) {
        console.log('收到消息:', data.type);
        
        switch (data.type) {
            case 'opponent_move':
                this.trigger('opponent_move', data.data);
                break;
            case 'game_over':
                this.trigger('game_over', data.data);
                break;
            case 'chat_message':
                this.trigger('chat_message', data.data);
                break;
            case 'undo_request':
                this.trigger('undo_request', data.data);
                break;
            case 'undo_response':
                this.trigger('undo_response', data.data);
                break;
            case 'restart_request':
                this.trigger('restart_request', data.data);
                break;
            case 'player_disconnected':
                this.trigger('player_disconnected', data.data);
                alert('对手已断开连接');
                break;
            default:
                console.log('未知消息类型:', data.type);
        }
    }
    
    /**
     * 发送消息
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket未连接,无法发送消息');
        }
    }
    
    /**
     * 发送移动
     */
    sendMove(fromRow, fromCol, toRow, toCol) {
        this.send({
            type: 'move',
            data: { fromRow, fromCol, toRow, toCol },
            timestamp: Date.now()
        });
    }
    
    /**
     * 发送悔棋请求
     */
    sendUndoRequest() {
        this.send({ type: 'undo_request' });
    }
    
    /**
     * 发送悔棋响应
     */
    sendUndoResponse(accepted) {
        this.send({
            type: 'undo_response',
            data: { accepted }
        });
    }
    
    /**
     * 发送重新开始请求
     */
    sendRestartRequest() {
        this.send({ type: 'restart_request' });
    }
    
    /**
     * 发送认输
     */
    sendResign() {
        this.send({ type: 'resign' });
    }
    
    /**
     * 发送聊天消息
     */
    sendChat(message) {
        this.send({
            type: 'chat',
            data: { message },
            timestamp: Date.now()
        });
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
     * 计划重连
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('达到最大重连次数,放弃重连');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`将在${delay}ms后尝试第${this.reconnectAttempts}次重连...`);
        
        setTimeout(() => {
            console.log('尝试重连...');
            this.connect();
        }, delay);
    }
    
    /**
     * 断开连接
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
    
    /**
     * 检查是否已连接
     */
    isConnected() {
        return this.connected && this.ws && this.ws.readyState === WebSocket.OPEN;
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
