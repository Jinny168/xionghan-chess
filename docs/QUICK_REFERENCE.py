"""
快速参考卡片 - 新基础设施速查
"""

# ==================== 事件总线速查 ====================
"""
from program.events import event_bus, event_types

# 订阅
event_bus.subscribe(event_types.GAME_OVER, handler)
event_bus.subscribe(event_types.PIECE_MOVED, handler, priority=10)
event_bus.subscribe_once(event_types.FIRST_MOVE, handler)

# 发布
event_bus.emit(event_types.GAME_OVER, {"winner": "red"})

# 取消订阅
event_bus.unsubscribe(event_types.GAME_OVER, handler)

# 查询
event_bus.has_subscribers(event_types.GAME_OVER)
stats = event_bus.get_stats()
history = event_bus.get_event_history(limit=10)

# 清除
event_bus.clear("GAME_OVER")  # 清除特定事件
event_bus.clear()  # 清除所有
"""

# ==================== 常量配置速查 ====================
"""
from program.config.constants import GameConstants

# 棋盘
board_size = GameConstants.BOARD_SIZE_XIONGHAN  # 13
size = GameConstants.get_board_size(traditional_mode=False)

# 窗口
width = GameConstants.DEFAULT_WINDOW_WIDTH  # 1200
height = GameConstants.DEFAULT_WINDOW_HEIGHT  # 900

# FPS
fps = GameConstants.NORMAL_FPS  # 60
fps = GameConstants.get_fps(ai_thinking=True)  # 15
fps = GameConstants.get_fps(dialog_showing=True)  # 30

# 时间
timeout = GameConstants.AI_THINK_TIMEOUT_MS  # 10000
delay = GameConstants.AI_MOVE_DELAY_MS  # 800

# 颜色
black = GameConstants.BLACK  # (0, 0, 0)
red = GameConstants.RED  # (180, 30, 30)

# 模式
pvp = GameConstants.MODE_PVP  # "pvp"
pvc = GameConstants.MODE_PVC  # "pvc"
"""

# ==================== 异常体系速查 ====================
"""
from program.exceptions import (
    InvalidMoveError,
    PositionOutOfBoundsError,
    AITimeoutError,
    ChessGameError,
)

# 抛出异常
raise InvalidMoveError(
    from_pos=(0, 0),
    to_pos=(1, 1),
    reason="路径被阻挡"
)

raise PositionOutOfBoundsError(row=15, col=15, board_size=13)

raise AITimeoutError(timeout_ms=10000)

# 捕获异常
try:
    # 可能出错的代码
    pass
except InvalidMoveError as e:
    print(f"错误码: {e.error_code}")
    print(f"消息: {e.message}")
    print(f"位置: {e.from_pos} -> {e.to_pos}")

# 使用基类捕获
try:
    pass
except ChessGameError as e:
    # 可以捕获所有游戏相关异常
    logger.error(f"[{e.error_code}] {e}")
"""

# ==================== 日志系统速查 ====================
"""
from program.utils.logger import get_module_logger, debug, info, warning, error

# 获取模块logger
logger = get_module_logger("game")
logger = get_module_logger("ai_manager")

# 记录日志
logger.debug("调试信息")
logger.info("游戏开始")
logger.warning("AI思考超时")
logger.error("加载失败")
logger.critical("严重错误")

# 格式化
player = "Player1"
score = 100
logger.info("玩家 %s 得分: %d", player, score)

# 便捷函数（使用默认logger）
info("这是一条信息")
warning("警告")
error("错误")

# 启用文件日志
from program.utils.logger import setup_logger
logger = setup_logger(
    name="my_logger",
    level="DEBUG",
    log_to_file=True,
    log_file_path="logs/my.log"
)
"""

# ==================== 综合示例 ====================
"""
from program.events import event_bus, event_types
from program.config.constants import GameConstants
from program.exceptions import InvalidMoveError, ChessGameError
from program.utils.logger import get_module_logger

logger = get_module_logger("game_logic")

def handle_move(from_pos, to_pos):
    '''处理棋子移动'''
    try:
        # 验证移动合法性
        if to_pos[0] >= GameConstants.BOARD_SIZE_XIONGHAN:
            raise InvalidMoveError(
                from_pos=from_pos,
                to_pos=to_pos,
                reason="目标位置超出棋盘"
            )
        
        # 执行移动...
        
        # 发布事件
        event_bus.emit(event_types.PIECE_MOVED, {
            'from': from_pos,
            'to': to_pos,
            'time': pygame.time.get_ticks()
        })
        
        logger.info("棋子从 %s 移动到 %s", from_pos, to_pos)
        
    except ChessGameError as e:
        logger.error("移动失败 [%s]: %s", e.error_code, e)
        event_bus.emit(event_types.ERROR_OCCURRED, {
            'error': str(e),
            'code': e.error_code
        })
        return False
    
    return True
"""

# ==================== 测试运行 ====================
"""
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_event_bus.py -v

# 运行特定测试类
python -m pytest tests/test_event_bus.py::TestEventBus -v

# 运行特定测试方法
python -m pytest tests/test_event_bus.py::TestEventBus::test_singleton -v

# 查看详细输出
python -m pytest tests/ -v --tb=long

# 生成覆盖率报告
pip install pytest-cov
python -m pytest tests/ --cov=program --cov-report=html
"""

# ==================== 常见模式 ====================
"""
模式1: 事件驱动的状态更新
-----------------------------------
class GameManager:
    def __init__(self):
        event_bus.subscribe(event_types.PIECE_MOVED, self.on_piece_moved)
    
    def on_piece_moved(self, event):
        # 响应棋子移动事件
        self.update_score()
        self.check_game_over()

模式2: 统一的错误处理
-----------------------------------
def safe_execute(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ChessGameError as e:
        logger.error("[%s] %s", e.error_code, e)
        event_bus.emit(event_types.ERROR_OCCURRED, {'error': e})
        return None

模式3: 条件日志
-----------------------------------
if GameConstants.DEBUG_MODE:
    logger.debug("详细调试信息: %s", complex_data)

模式4: 资源清理
-----------------------------------
try:
    game.run()
except KeyboardInterrupt:
    logger.info("用户中断游戏")
finally:
    event_bus.clear()
    logger.info("资源已清理")
"""

print("快速参考卡片已加载！")
print("取消注释相应的部分查看示例代码")
