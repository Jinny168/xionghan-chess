"""
游戏事件类型定义
"""

# ==================== 游戏流程事件 ====================
GAME_STARTED = "game_started"           # 游戏开始
GAME_PAUSED = "game_paused"             # 游戏暂停
GAME_RESUMED = "game_resumed"           # 游戏恢复
GAME_OVER = "game_over"                 # 游戏结束
GAME_RESTARTED = "game_restarted"       # 游戏重新开始

# ==================== 棋子相关事件 ====================
PIECE_SELECTED = "piece_selected"       # 棋子被选中
PIECE_MOVED = "piece_moved"             # 棋子移动
PIECE_CAPTURED = "piece_captured"       # 棋子被吃
PIECE_PROMOTED = "piece_promoted"       # 棋子升变
PIECE_RESURRECTED = "piece_resurrected" # 棋子复活

# ==================== 游戏状态事件 ====================
TURN_CHANGED = "turn_changed"           # 回合切换
CHECK_DETECTED = "check_detected"       # 将军检测
CHECKMATE_DETECTED = "checkmate_detected"  # 绝杀检测
STALEMATE_DETECTED = "stalemate_detected"  # 和棋检测

# ==================== AI相关事件 ====================
AI_THINKING_STARTED = "ai_thinking_started"    # AI开始思考
AI_THINKING_COMPLETED = "ai_thinking_completed" # AI思考完成
AI_MOVE_MADE = "ai_move_made"           # AI执行移动
AI_TIMEOUT = "ai_timeout"               # AI超时

# ==================== UI相关事件 ====================
UI_THEME_CHANGED = "ui_theme_changed"   # UI主题切换
UI_FULLSCREEN_TOGGLED = "ui_fullscreen_toggled"  # 全屏切换
UI_SETTINGS_CHANGED = "ui_settings_changed"  # 设置变更
UI_DIALOG_OPENED = "ui_dialog_opened"   # 对话框打开
UI_DIALOG_CLOSED = "ui_dialog_closed"   # 对话框关闭

# ==================== 音效相关事件 ====================
SOUND_PLAYED = "sound_played"           # 音效播放
MUSIC_TOGGLED = "music_toggled"         # 背景音乐切换
VOLUME_CHANGED = "volume_changed"       # 音量变化

# ==================== 网络相关事件 ====================
NETWORK_CONNECTED = "network_connected"     # 网络连接成功
NETWORK_DISCONNECTED = "network_disconnected" # 网络断开
NETWORK_ERROR = "network_error"             # 网络错误
NETWORK_MESSAGE_RECEIVED = "network_message_received"  # 收到网络消息

# ==================== 数据管理事件 ====================
GAME_SAVED = "game_saved"               # 游戏保存
GAME_LOADED = "game_loaded"             # 游戏加载
STATISTICS_UPDATED = "statistics_updated"  # 统计数据更新
REPLAY_STARTED = "replay_started"       # 复盘开始
REPLAY_ENDED = "replay_ended"           # 复盘结束

# ==================== 错误事件 ====================
ERROR_OCCURRED = "error_occurred"       # 发生错误
INVALID_MOVE = "invalid_move"           # 非法移动

