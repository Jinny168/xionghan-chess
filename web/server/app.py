"""
雄汉象棋网页版 - Flask后端服务器
遵循设计文档架构，参考桌面版实现
"""

import datetime
import time
import uuid
import logging
import json

from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from socketio import RedisManager
import redis

# 创建Flask应用，启用静态文件缓存
app = Flask(__name__, static_folder='..', static_url_path='')
CORS(app)

# Redis 连接配置
# 支持从环境变量读取配置（Docker 部署）
import os
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = int(os.environ.get('REDIS_PORT', '6379'))
redis_password = os.environ.get('REDIS_PASSWORD', '')
redis_db = int(os.environ.get('REDIS_DB', '0'))

try:
    redis_kwargs = {
        'host': redis_host,
        'port': redis_port,
        'db': redis_db,
        'decode_responses': True,
        'socket_connect_timeout': 5,
        'socket_timeout': 5
    }
    
    if redis_password:
        redis_kwargs['password'] = redis_password
    
    redis_client = redis.Redis(**redis_kwargs)
    redis_client.ping()
    print(f'✅ Redis 连接成功 ({redis_host}:{redis_port})')
    if redis_password:
        print('🔒 已启用密码认证')
    USE_REDIS = True
except (redis.ConnectionError, redis.AuthenticationError) as e:
    print(f'⚠️ Redis 连接失败: {e}')
    print('⚠️ 回退到内存模式（数据将在重启后丢失）')
    redis_client = None
    USE_REDIS = False

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

# Socket.IO Redis 适配器（如果 Redis 可用）
socketio_kwargs = {
    'cors_allowed_origins': "*",
    'async_mode': async_mode,
    'ping_timeout': 60,
    'ping_interval': 25,
    'max_http_buffer_size': 1e6,
    'logger': False,  # 禁用Socket.IO日志
    'engineio_logger': False  # 禁用Engine.IO日志
}

if USE_REDIS:
    # Socket.IO Redis 管理器连接字符串
    if redis_password:
        redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}'
    else:
        redis_url = f'redis://{redis_host}:{redis_port}/{redis_db}'
    socketio_kwargs['client_manager'] = RedisManager(redis_url)

socketio = SocketIO(app, **socketio_kwargs)

# ==================== 配置 ====================
ROOM_TIMEOUT = 3600  # 房间超时时间（秒）
MAX_CONNECTIONS_PER_IP = 5  # 每个IP最大连接数
MOVE_RATE_LIMIT = 100  # 移动频率限制（毫秒）
STATIC_CACHE_TIMEOUT = 31536000  # 静态文件缓存时间（1年，秒）

# Redis 键前缀
REDIS_PREFIX = 'xionghan_chess:'
ROOM_KEY_PREFIX = f'{REDIS_PREFIX}room:'
PLAYER_ROOM_KEY_PREFIX = f'{REDIS_PREFIX}player_room:'
IP_CONN_KEY = f'{REDIS_PREFIX}ip_connections'
MOVE_TIME_KEY = f'{REDIS_PREFIX}move_times'

# 配置日志级别
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

# 抑制BrokenPipeError日志（客户端断开连接时的正常现象）
class IgnoreBrokenPipeFilter(logging.Filter):
    """过滤掉BrokenPipeError警告"""
    def filter(self, record):
        msg = record.getMessage()
        # 忽略客户端断开连接相关的错误
        if 'BrokenPipeError' in msg or 'Errno 32' in msg or 'Connection reset by peer' in msg:
            return False
        return True

# 应用到werkzeug日志
log.addFilter(IgnoreBrokenPipeFilter())

# 应用到eventlet日志
import eventlet
eventlet_log = logging.getLogger('eventlet')
eventlet_log.addFilter(IgnoreBrokenPipeFilter())

# ==================== 存储层 ====================
# 房间存储（内存/Redis 混合模式）
rooms = {}  # 内存缓存
connection_count = {}  # IP连接计数
last_move_time = {}  # 玩家最后移动时间


def redis_get(key):
    """从 Redis 获取数据"""
    if USE_REDIS and redis_client:
        try:
            data = redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f'⚠️ Redis GET 错误: {e}')
    return None


def redis_set(key, value, expire=None):
    """向 Redis 存储数据"""
    if USE_REDIS and redis_client:
        try:
            redis_client.set(key, json.dumps(value), ex=expire)
            return True
        except Exception as e:
            print(f'⚠️ Redis SET 错误: {e}')
    return False


def redis_delete(key):
    """从 Redis 删除数据"""
    if USE_REDIS and redis_client:
        try:
            redis_client.delete(key)
            return True
        except Exception as e:
            print(f'️ Redis DELETE 错误: {e}')
    return False


# ==================== 游戏房间模型 ====================
class GameRoom:
    """游戏房间类 - 支持 Redis 持久化"""
    
    def __init__(self, room_id, mode='xionghan'):
        self.room_id = room_id
        self.mode = mode  # 'xionghan' 或 'traditional'
        self.players = []  # [{'sid': xxx, 'camp': 'red/black', 'ready': False}]
        self.created_at = datetime.datetime.now().isoformat()
        self.last_activity = time.time()
        self.game_started = False
        self.game_state = None  # 服务端游戏状态（用于验证）
        self.move_history = []  # 移动历史
        self.current_turn = 'red'  # 当前回合，红方先手
        self.save_to_redis()
        
    def save_to_redis(self):
        """将房间状态保存到 Redis"""
        data = {
            'room_id': self.room_id,
            'mode': self.mode,
            'players': self.players,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'game_started': self.game_started,
            'move_history': self.move_history,
            'current_turn': self.current_turn
        }
        redis_set(f'{ROOM_KEY_PREFIX}{self.room_id}', data, expire=ROOM_TIMEOUT * 2)
        
        # 保存玩家到房间的映射
        for player in self.players:
            redis_set(f'{PLAYER_ROOM_KEY_PREFIX}{player["sid"]}', self.room_id, expire=ROOM_TIMEOUT * 2)
        
    def load_from_redis(room_id):
        """从 Redis 加载房间状态"""
        data = redis_get(f'{ROOM_KEY_PREFIX}{room_id}')
        if not data:
            return None
        
        room = GameRoom.__new__(GameRoom)
        room.room_id = data['room_id']
        room.mode = data['mode']
        room.players = data['players']
        room.created_at = data['created_at']
        room.last_activity = data['last_activity']
        room.game_started = data['game_started']
        room.move_history = data['move_history']
        room.current_turn = data['current_turn']
        return room
        
    def add_player(self, sid):
        """添加玩家到房间"""
        if len(self.players) >= 2:
            return False, '房间已满'
        
        camp = 'red' if len(self.players) == 0 else 'black'
        self.players.append({'sid': sid, 'camp': camp, 'ready': False})
        self.update_activity()
        self.save_to_redis()
        return True, camp
    
    def remove_player(self, sid):
        """移除玩家"""
        self.players = [p for p in self.players if p['sid'] != sid]
        self.update_activity()
        self.save_to_redis()
        # 删除玩家到房间的映射
        redis_delete(f'{PLAYER_ROOM_KEY_PREFIX}{sid}')
        
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
        self.save_to_redis()
    
    def validate_move(self, from_row, from_col, to_row, to_col, player_camp):
        """
        验证移动合法性 - 参考桌面版game_rules.py
        TODO: 集成完整的游戏规则验证
        目前做基础验证，后续可扩展
        """
        # 验证是否是该玩家的回合
        if player_camp != self.current_turn:
            return False, '不是你的回合'
        
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
        
        # 切换回合
        self.current_turn = 'black' if self.current_turn == 'red' else 'red'
        
        self.save_to_redis()
        return True, None


# ==================== 辅助函数 ====================
def get_player_room(sid):
    """获取玩家所在的房间ID"""
    # 优先从 Redis 查询
    if USE_REDIS:
        room_id = redis_get(f'{PLAYER_ROOM_KEY_PREFIX}{sid}')
        if room_id:
            return room_id
    
    # 回退到内存查询
    for room_id, room in rooms.items():
        if any(p['sid'] == sid for p in room.players):
            return room_id
    return None


def get_room(room_id):
    """获取房间对象（优先从内存，其次从 Redis）"""
    # 优先从内存获取
    if room_id in rooms:
        return rooms[room_id]
    
    # 从 Redis 加载
    if USE_REDIS:
        room = GameRoom.load_from_redis(room_id)
        if room:
            rooms[room_id] = room  # 缓存到内存
            return room
    
    return None


def get_player_camp(sid):
    """获取玩家的阵营"""
    room_id = get_player_room(sid)
    if room_id:
        room = get_room(room_id)
        if room:
            return room.get_player_camp(sid)
    return None


def cleanup_timeout_rooms():
    """清理超时房间"""
    cleaned = 0
    
    if USE_REDIS:
        # 从 Redis 扫描所有房间
        for key in redis_client.scan_iter(f'{ROOM_KEY_PREFIX}*'):
            room_id = key.replace(ROOM_KEY_PREFIX, '')
            data = redis_get(key)
            if data and (time.time() - data.get('last_activity', 0)) > ROOM_TIMEOUT:
                redis_delete(key)
                # 清理玩家映射
                for player in data.get('players', []):
                    redis_delete(f'{PLAYER_ROOM_KEY_PREFIX}{player["sid"]}')
                cleaned += 1
                if room_id in rooms:
                    del rooms[room_id]
    else:
        # 内存模式
        timeout_rooms = [rid for rid, room in rooms.items() if room.is_timeout()]
        for rid in timeout_rooms:
            del rooms[rid]
            cleaned += 1
    
    return cleaned


def rate_limit_check(sid, interval_ms=MOVE_RATE_LIMIT):
    """频率限制检查"""
    current_time = time.time() * 1000  # 毫秒
    
    if USE_REDIS:
        last_time = redis_client.hget(MOVE_TIME_KEY, sid)
        if last_time and (current_time - float(last_time)) < interval_ms:
            return False
        redis_client.hset(MOVE_TIME_KEY, sid, current_time)
        redis_client.expire(MOVE_TIME_KEY, 3600)  # 1小时过期
    else:
        if sid in last_move_time:
            if current_time - last_move_time[sid] < interval_ms:
                return False
        last_move_time[sid] = current_time
    
    return True


# ==================== HTTP路由 ====================
@app.after_request
def add_cache_headers(response):
    """为静态资源添加缓存头"""
    # HTML页面不缓存
    if request.path.endswith('.html') or request.path == '/':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    # 静态资源长期缓存
    elif request.path.startswith(('/images/', '/sounds/', '/css/', '/js/')):
        response.headers['Cache-Control'] = f'public, max-age={STATIC_CACHE_TIMEOUT}, immutable'
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


@app.route('/socket.io.min.js')
def socket_io_client():
    """提供Socket.IO客户端库（本地备用）"""
    # 尝试从多个CDN下载并缓存，或者直接返回错误让浏览器使用备用CDN
    from flask import redirect
    # 重定向到可靠的CDN
    return redirect('https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js', code=302)


@app.route('/api/create_room', methods=['POST'])
def create_room():
    """创建游戏房间"""
    data = request.json
    mode = data.get('mode', 'xionghan')
    
    if mode not in ['xionghan', 'traditional']:
        return jsonify({'success': False, 'error': '无效的游戏模式'}), 400
    
    room_id = str(uuid.uuid4())[:8]
    room = GameRoom(room_id, mode)
    rooms[room_id] = room  # 缓存到内存
    
    return jsonify({
        'success': True,
        'roomId': room_id,
        'mode': mode,
        'message': '房间创建成功'
    })


@app.route('/api/join_room/<room_id>', methods=['POST'])
def join_room_api(room_id):
    """加入游戏房间"""
    # 大小写不敏感查找
    room_id_lower = room_id.lower()
    matched_room_id = None
    
    # 优先从 Redis 查找
    if USE_REDIS:
        for key in redis_client.scan_iter(f'{ROOM_KEY_PREFIX}*'):
            rid = key.replace(ROOM_KEY_PREFIX, '')
            if rid.lower() == room_id_lower:
                matched_room_id = rid
                break
    else:
        for rid in rooms.keys():
            if rid.lower() == room_id_lower:
                matched_room_id = rid
                break
    
    if not matched_room_id:
        return jsonify({
            'success': False,
            'error': '房间不存在'
        }), 404
    
    room = get_room(matched_room_id)
    if not room:
        return jsonify({
            'success': False,
            'error': '房间不存在'
        }), 404
    
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
    # 大小写不敏感查找
    room_id_lower = room_id.lower()
    matched_room_id = None
    
    for rid in rooms.keys():
        if rid.lower() == room_id_lower:
            matched_room_id = rid
            break
    
    if not matched_room_id:
        return jsonify({'success': False, 'error': '房间不存在'}), 404
    
    room = rooms[matched_room_id]
    return jsonify({
        'success': True,
        'roomId': matched_room_id,
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
        print(f'🔴 客户端断开: {request.sid} (IP: {request.remote_addr})')
    
    client_ip = request.remote_addr
    if client_ip in connection_count:
        connection_count[client_ip] -= 1
    
    # 从所有房间中移除该玩家
    for room_id, room in list(rooms.items()):
        # 检查该玩家是否在这个房间
        player_in_room = any(p['sid'] == request.sid for p in room.players)
        
        if player_in_room:
            room.remove_player(request.sid)
            
            # 通知对手玩家离开
            emit('player_disconnected', {
                'reason': 'player_left'
            }, room=room_id)
            
            # 如果房间为空,删除房间
            if not room.players:
                del rooms[room_id]
                if app.debug:
                    print(f'️ 房间 {room_id} 已删除（空房间）')
            break


@socketio.on('join_game_room')
def handle_join_game_room(data):
    """加入游戏房间(SocketIO)"""
    room_id = data.get('roomId')
    
    # 大小写不敏感查找
    room_id_lower = room_id.lower()
    matched_room_id = None
    
    # 优先从 Redis 查找
    if USE_REDIS:
        for key in redis_client.scan_iter(f'{ROOM_KEY_PREFIX}*'):
            rid = key.replace(ROOM_KEY_PREFIX, '')
            if rid.lower() == room_id_lower:
                matched_room_id = rid
                break
    else:
        for rid in rooms.keys():
            if rid.lower() == room_id_lower:
                matched_room_id = rid
                break
    
    if not matched_room_id:
        emit('error', {'message': '房间不存在'})
        return
    
    room = get_room(matched_room_id)
    if not room:
        emit('error', {'message': '房间不存在'})
        return
    
    success, result = room.add_player(request.sid)
    
    if success:
        # 使用匹配到的房间 ID（保持原始大小写）
        join_room(matched_room_id)
        
        # 判断是否是房主（第一个加入的玩家）
        is_host = len(room.players) == 1
        
        emit('joined', {
            'roomId': matched_room_id,
            'camp': result,
            'isHost': is_host,
            'opponentConnected': room.is_full()
        })
        
        # 如果房间已满，通知两个玩家开始游戏
        if room.is_full():
            room.game_started = True
            room.update_activity()
            
            # 通知两个玩家游戏开始
            emit('game_start', {
                'mode': room.mode
            }, room=matched_room_id)
            
            print(f'🎮 游戏开始: 房间 {matched_room_id}, 模式: {room.mode}')
    else:
        emit('error', {'message': result})


@socketio.on('move')
def handle_move(data):
    """
    处理棋子移动
    参考桌面版：需要服务端验证移动合法性
    """
    # 只在debug模式打印移动日志
    if app.debug:
        print(f'📥 收到移动请求: {data} from {request.sid}')
    
    # 频率限制
    if not rate_limit_check(request.sid):
        if app.debug:
            print(f'❌ 频率限制: {request.sid}')
        emit('error', {'message': '操作过于频繁'})
        return
    
    room_id = get_player_room(request.sid)
    if not room_id:
        if app.debug:
            print(f'❌ 不在房间中: {request.sid}')
        emit('error', {'message': '不在房间中'})
        return
    
    room = get_room(room_id)
    if not room:
        if app.debug:
            print(f'⚠️ 房间不存在: {room_id}')
        emit('error', {'message': '房间不存在'})
        return
    
    if not room.game_started:
        if app.debug:
            print(f'❌ 游戏未开始: {room_id}')
        emit('error', {'message': '游戏未开始'})
        return
    
    # 验证是否是当前玩家的回合
    player_camp = get_player_camp(request.sid)
    if app.debug:
        print(f'🎯 玩家阵营: {player_camp}, 当前回合: {room.current_turn}')
    # TODO: 添加回合验证逻辑
    
    # 提取移动数据
    from_row = data.get('fromRow')
    from_col = data.get('fromCol')
    to_row = data.get('toRow')
    to_col = data.get('toCol')
    
    if None in [from_row, from_col, to_row, to_col]:
        if app.debug:
            print(f'❌ 移动数据不完整: {data}')
        emit('error', {'message': '移动数据不完整'})
        return
    
    # 服务端验证移动合法性
    valid, error_msg = room.validate_move(from_row, from_col, to_row, to_col, player_camp)
    if not valid:
        if app.debug:
            print(f'❌ 移动验证失败: {error_msg}')
        emit('error', {'message': error_msg})
        return
    
    if app.debug:
        print(f'✅ 移动验证通过，广播给对手')
    room.update_activity()
    
    # 广播给对手
    emit('opponent_move', data, room=room_id, include_self=False)
    if app.debug:
        print(f'📤 已广播 opponent_move 到房间 {room_id}')
    
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
    if room_id:
        room = get_room(room_id)
        if room and data.get('accepted'):
            room.move_history = []
            room.current_turn = 'red'  # 重置回合为红方
            room.update_activity()
            
            emit('game_restart', {}, room=room_id)


@socketio.on('resign')
def handle_resign():
    """认输"""
    room_id = get_player_room(request.sid)
    if room_id:
        room = get_room(room_id)
        if room:
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
        room = get_room(room_id)
        if room:
            room.update_activity()
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
    # 只在非重载器进程中打印启动信息
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
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
    
    # 生产环境关闭debug模式
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=debug_mode,
        allow_unsafe_werkzeug=True,
        log_output=debug_mode,  # 只在debug模式输出日志
        use_reloader=False  # 生产环境禁用重载器
    )
