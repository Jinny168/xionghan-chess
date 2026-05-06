"""
雄汉象棋网页版 - Flask后端服务器
遵循设计文档架构，参考桌面版实现
"""

import datetime
import time
import uuid
import logging

from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room

# 创建Flask应用，启用静态文件缓存
app = Flask(__name__, static_folder='..', static_url_path='')
CORS(app)

# SocketIO配置优化：使用gevent或eventlet提升性能（如果已安装）
try:
    import gevent
    async_mode = 'gevent'
except ImportError:
    try:
        import eventlet
        async_mode = 'eventlet'
    except ImportError:
        async_mode = 'threading'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode=async_mode,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6
)

# ==================== 配置 ====================
ROOM_TIMEOUT = 3600  # 房间超时时间（秒）
MAX_CONNECTIONS_PER_IP = 5  # 每个IP最大连接数
MOVE_RATE_LIMIT = 100  # 移动频率限制（毫秒）
STATIC_CACHE_TIMEOUT = 31536000  # 静态文件缓存时间（1年，秒）

# 配置日志级别
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

# ==================== 全局状态 ====================
rooms = {}
connection_count = {}  # IP连接计数
last_move_time = {}  # 玩家最后移动时间


# ==================== 游戏房间模型 ====================
class GameRoom:
    """游戏房间类 - 参考桌面版network_game.py实现"""
    
    def __init__(self, room_id, mode='xionghan'):
        self.room_id = room_id
        self.mode = mode  # 'xionghan' 或 'traditional'
        self.players = []  # [{'sid': xxx, 'camp': 'red/black', 'ready': False}]
        self.created_at = datetime.datetime.now()
        self.last_activity = time.time()
        self.game_started = False
        self.game_state = None  # 服务端游戏状态（用于验证）
        self.move_history = []  # 移动历史
        
    def add_player(self, sid):
        """添加玩家到房间"""
        if len(self.players) >= 2:
            return False, '房间已满'
        
        camp = 'red' if len(self.players) == 0 else 'black'
        self.players.append({'sid': sid, 'camp': camp, 'ready': False})
        self.update_activity()
        return True, camp
    
    def remove_player(self, sid):
        """移除玩家"""
        self.players = [p for p in self.players if p['sid'] != sid]
        self.update_activity()
        
    def get_player_camp(self, sid):
        """获取玩家阵营"""
        for player in self.players:
            if player['sid'] == sid:
                return player['camp']
        return None
        
    def get_opponent(self, sid):
        """获取对手信息"""
        for player in self.players:
            if player['sid'] != sid:
                return player
        return None
    
    def is_full(self):
        """房间是否已满"""
        return len(self.players) >= 2
    
    def is_timeout(self):
        """检查房间是否超时"""
        return (time.time() - self.last_activity) > ROOM_TIMEOUT
    
    def update_activity(self):
        """更新活动时间"""
        self.last_activity = time.time()
    
    def validate_move(self, from_row, from_col, to_row, to_col, player_camp):
        """
        验证移动合法性 - 参考桌面版game_rules.py
        TODO: 集成完整的游戏规则验证
        目前做基础验证，后续可扩展
        """
        # 基础验证：坐标在范围内
        if self.mode == 'traditional':
            if not (0 <= to_row <= 9 and 0 <= to_col <= 8):
                return False, '目标位置超出棋盘'
        else:  # xionghan
            if not (0 <= to_row <= 12 and 0 <= to_col <= 12):
                return False, '目标位置超出棋盘'
        
        # 记录移动历史
        self.move_history.append({
            'from': (from_row, from_col),
            'to': (to_row, to_col),
            'camp': player_camp,
            'timestamp': time.time()
        })
        
        return True, None


# ==================== 辅助函数 ====================
def get_player_room(sid):
    """获取玩家所在的房间ID"""
    for room_id, room in rooms.items():
        if any(p['sid'] == sid for p in room.players):
            return room_id
    return None


def get_player_camp(sid):
    """获取玩家的阵营"""
    for room in rooms.values():
        for player in room.players:
            if player['sid'] == sid:
                return player['camp']
    return None


def cleanup_timeout_rooms():
    """清理超时房间"""
    timeout_rooms = [rid for rid, room in rooms.items() if room.is_timeout()]
    for rid in timeout_rooms:
        del rooms[rid]
    return len(timeout_rooms)


def rate_limit_check(sid, interval_ms=MOVE_RATE_LIMIT):
    """频率限制检查"""
    current_time = time.time() * 1000  # 毫秒
    if sid in last_move_time:
        if current_time - last_move_time[sid] < interval_ms:
            return False
    last_move_time[sid] = current_time
    return True


# ==================== HTTP路由 ====================
@app.after_request
def add_cache_headers(response):
    """为静态资源添加缓存头"""
    if request.path.startswith(('/images/', '/sounds/', '/css/', '/js/')):
        response.headers['Cache-Control'] = f'public, max-age={STATIC_CACHE_TIMEOUT}'
        # 使用时区感知的时间对象，避免弃用警告
        response.headers['Expires'] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=STATIC_CACHE_TIMEOUT)
    return response


@app.route('/')
def index():
    """主页 - 模式选择页面"""
    response = make_response(send_from_directory(app.static_folder, 'index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/game.html')
def game_page():
    """游戏页面"""
    response = make_response(send_from_directory(app.static_folder, 'game.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/create_room', methods=['POST'])
def create_room():
    """创建游戏房间"""
    data = request.json
    mode = data.get('mode', 'xionghan')
    
    if mode not in ['xionghan', 'traditional']:
        return jsonify({'success': False, 'error': '无效的游戏模式'}), 400
    
    room_id = str(uuid.uuid4())[:8]
    rooms[room_id] = GameRoom(room_id, mode)
    
    return jsonify({
        'success': True,
        'roomId': room_id,
        'mode': mode,
        'message': '房间创建成功'
    })


@app.route('/api/join_room/<room_id>', methods=['POST'])
def join_room_api(room_id):
    """加入游戏房间"""
    if room_id not in rooms:
        return jsonify({
            'success': False,
            'error': '房间不存在'
        }), 404
    
    room = rooms[room_id]
    if room.is_full():
        return jsonify({
            'success': False,
            'error': '房间已满'
        }), 400
    
    success, result = room.add_player(request.sid if hasattr(request, 'sid') else 'temp')
    
    if success:
        return jsonify({
            'success': True,
            'camp': result
        })
    else:
        return jsonify({
            'success': False,
            'error': result
        }), 400


@app.route('/api/room_status/<room_id>', methods=['GET'])
def room_status(room_id):
    """获取房间状态"""
    if room_id not in rooms:
        return jsonify({'success': False, 'error': '房间不存在'}), 404
    
    room = rooms[room_id]
    return jsonify({
        'success': True,
        'roomId': room_id,
        'mode': room.mode,
        'players': len(room.players),
        'started': room.game_started,
        'moveHistory': len(room.move_history)
    })


# ==================== WebSocket事件 ====================
@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    client_ip = request.remote_addr
    
    # IP限流
    connection_count[client_ip] = connection_count.get(client_ip, 0) + 1
    if connection_count[client_ip] > MAX_CONNECTIONS_PER_IP:
        emit('error', {'message': '连接数过多'})
        return False
    
    # 只在debug模式打印连接信息
    if app.debug:
        print(f'客户端连接: {request.sid} (IP: {client_ip})')
    emit('connected', {'sid': request.sid})


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    if app.debug:
        print(f'客户端断开: {request.sid}')
    
    client_ip = request.remote_addr
    if client_ip in connection_count:
        connection_count[client_ip] -= 1
    
    # 从房间中移除玩家
    for room_id, room in list(rooms.items()):
        opponent = room.get_opponent(request.sid)
        if opponent:
            room.remove_player(request.sid)
            
            # 通知对手玩家离开
            emit('player_disconnected', {
                'reason': 'player_left'
            }, room=room_id)
            
            # 如果房间为空,删除房间
            if not room.players:
                del rooms[room_id]
            break


@socketio.on('join_game_room')
def handle_join_game_room(data):
    """加入游戏房间(SocketIO)"""
    room_id = data.get('roomId')
    
    if room_id not in rooms:
        emit('error', {'message': '房间不存在'})
        return
    
    room = rooms[room_id]
    success, result = room.add_player(request.sid)
    
    if success:
        join_room(room_id)
        emit('joined', {
            'roomId': room_id,
            'camp': result,
            'opponentConnected': room.is_full()
        })
        
        # 如果房间已满,通知两个玩家开始游戏
        if room.is_full():
            room.game_started = True
            room.update_activity()
            
            # 通知红方
            red_player = room.players[0]
            emit('game_start', {
                'opponentCamp': 'black',
                'mode': room.mode
            }, room=room_id)
            
            print(f'游戏开始: 房间 {room_id}, 模式: {room.mode}')
    else:
        emit('error', {'message': result})


@socketio.on('move')
def handle_move(data):
    """
    处理棋子移动
    参考桌面版：需要服务端验证移动合法性
    """
    # 频率限制
    if not rate_limit_check(request.sid):
        emit('error', {'message': '操作过于频繁'})
        return
    
    room_id = get_player_room(request.sid)
    if not room_id:
        emit('error', {'message': '不在房间中'})
        return
    
    room = rooms[room_id]
    if not room.game_started:
        emit('error', {'message': '游戏未开始'})
        return
    
    # 验证是否是当前玩家的回合
    player_camp = get_player_camp(request.sid)
    # TODO: 添加回合验证逻辑
    
    # 提取移动数据
    from_row = data.get('fromRow')
    from_col = data.get('fromCol')
    to_row = data.get('toRow')
    to_col = data.get('toCol')
    
    if None in [from_row, from_col, to_row, to_col]:
        emit('error', {'message': '移动数据不完整'})
        return
    
    # 服务端验证移动合法性
    valid, error_msg = room.validate_move(from_row, from_col, to_row, to_col, player_camp)
    if not valid:
        emit('error', {'message': error_msg})
        return
    
    room.update_activity()
    
    # 广播给对手
    emit('opponent_move', data, room=room_id, include_self=False)
    
    # TODO: 检查是否将军/将死


@socketio.on('undo_request')
def handle_undo_request():
    """悔棋请求"""
    room_id = get_player_room(request.sid)
    if room_id:
        emit('undo_request', {
            'requester': get_player_camp(request.sid)
        }, room=room_id, include_self=False)


@socketio.on('undo_response')
def handle_undo_response(data):
    """悔棋响应"""
    room_id = get_player_room(request.sid)
    if room_id:
        emit('undo_response', {
            'accepted': data.get('accepted', False),
            'responder': get_player_camp(request.sid)
        }, room=room_id)


@socketio.on('restart_request')
def handle_restart_request():
    """重新开始请求"""
    room_id = get_player_room(request.sid)
    if room_id:
        emit('restart_request', {
            'requester': get_player_camp(request.sid)
        }, room=room_id, include_self=False)


@socketio.on('restart_response')
def handle_restart_response(data):
    """重新开始响应"""
    room_id = get_player_room(request.sid)
    if room_id and data.get('accepted'):
        room = rooms[room_id]
        room.move_history = []
        room.update_activity()
        
        emit('game_restart', {}, room=room_id)


@socketio.on('resign')
def handle_resign():
    """认输"""
    room_id = get_player_room(request.sid)
    if room_id:
        room = rooms[room_id]
        winner_camp = 'black' if get_player_camp(request.sid) == 'red' else 'red'
        
        emit('game_over', {
            'winner': winner_camp,
            'reason': 'resign',
            'moveCount': len(room.move_history)
        }, room=room_id)


@socketio.on('chat')
def handle_chat(data):
    """聊天消息"""
    room_id = get_player_room(request.sid)
    if room_id:
        camp = get_player_camp(request.sid)
        message = data.get('message', '')
        
        # 过滤敏感词（简单实现）
        if len(message) > 200:
            emit('error', {'message': '消息过长'})
            return
        
        emit('chat_message', {
            'player': camp,
            'message': message,
            'timestamp': datetime.datetime.now().isoformat()
        }, room=room_id)


# ==================== 定时任务 ====================
@socketio.on('ping')
def handle_ping():
    """心跳检测"""
    room_id = get_player_room(request.sid)
    if room_id:
        rooms[room_id].update_activity()
    emit('pong')


def cleanup_loop():
    """定期清理超时房间"""
    while True:
        socketio.sleep(300)  # 每5分钟清理一次
        cleaned = cleanup_timeout_rooms()
        if cleaned > 0:
            print(f'清理了 {cleaned} 个超时房间')


# ==================== 启动服务器 ====================
if __name__ == '__main__':
    print('=' * 50)
    print('Xionghan Chess Web Server Started')
    print(f'URL: http://localhost:5000')
    print(f'Async Mode: {async_mode}')
    print(f'Room Timeout: {ROOM_TIMEOUT}s')
    print(f'IP Rate Limit: {MAX_CONNECTIONS_PER_IP} connections')
    print(f'Static Cache: {STATIC_CACHE_TIMEOUT}s')
    print('=' * 50)
    
    # 启动后台清理任务
    socketio.start_background_task(cleanup_loop)
    
    # 生产环境建议关闭debug模式
    debug_mode = True  # 开发时设为True，生产环境设为False
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=debug_mode,
        allow_unsafe_werkzeug=True,
        log_output=debug_mode  # 只在debug模式输出日志
    )
