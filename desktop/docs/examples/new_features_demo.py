"""
新基础设施使用示例
展示如何使用事件总线、常量配置、异常体系和日志系统
"""

# ==================== 1. 事件总线使用示例 ====================
from desktopevents import event_bus, event_types


def example_event_bus():
    """事件总线使用示例"""
    
    # 订阅事件
    def on_game_over(event):
        print(f"游戏结束! 获胜方: {event.data.get('winner')}")
    
    event_bus.subscribe(event_types.GAME_OVER, on_game_over)
    
    # 发布事件
    event_bus.emit(event_types.GAME_OVER, {"winner": "red", "reason": "checkmate"})
    
    # 一次性订阅
    def on_first_move(event):
        print("第一次移动发生!")
    
    event_bus.subscribe_once(event_types.PIECE_MOVED, on_first_move)
    
    # 带优先级的订阅
    def high_priority_handler(event):
        print("高优先级处理器")
    
    def low_priority_handler(event):
        print("低优先级处理器")
    
    event_bus.subscribe(event_types.PIECE_MOVED, high_priority_handler, priority=10)
    event_bus.subscribe(event_types.PIECE_MOVED, low_priority_handler, priority=1)


# ==================== 2. 常量配置使用示例 ====================
from desktopconfig.constants import GameConstants


def example_constants():
    """常量配置使用示例"""
    
    # 直接使用常量
    window_width = GameConstants.DEFAULT_WINDOW_WIDTH
    fps = GameConstants.NORMAL_FPS
    
    # 使用方法获取动态值
    board_size = GameConstants.get_board_size(traditional_mode=False)  # 返回13
    current_fps = GameConstants.get_fps(ai_thinking=True)  # 返回15
    
    print(f"窗口宽度: {window_width}, FPS: {fps}")
    print(f"棋盘尺寸: {board_size}, AI思考时FPS: {current_fps}")


# ==================== 3. 异常体系使用示例 ====================
from desktopexceptions import (
    InvalidMoveError,
    PositionOutOfBoundsError,
    AITimeoutError,
    ChessGameError,
)


def example_exceptions():
    """异常体系使用示例"""
    
    # 抛出具体异常
    try:
        raise InvalidMoveError(
            from_pos=(0, 0),
            to_pos=(5, 5),
            reason="马不能这样移动"
        )
    except InvalidMoveError as e:
        print(f"捕获到非法移动异常: {e}")
        print(f"错误码: {e.error_code}")
    
    # 使用基类捕获
    try:
        raise PositionOutOfBoundsError(row=15, col=15, board_size=13)
    except ChessGameError as e:
        print(f"捕获到游戏异常: {e}")
    
    # AI超时异常
    try:
        raise AITimeoutError(timeout_ms=10000)
    except AITimeoutError as e:
        print(f"AI超时: {e.timeout_ms}ms")


# ==================== 4. 日志系统使用示例 ====================
from desktoputils.logger import get_module_logger, debug, info, warning, error


def example_logging():
    """日志系统使用示例"""
    
    # 获取模块专属logger
    logger = get_module_logger("game")
    
    # 使用不同级别记录日志
    logger.debug("这是调试信息")
    logger.info("游戏开始")
    logger.warning("AI思考时间较长")
    logger.error("加载资源失败")
    
    # 使用便捷函数
    info("玩家选择了红方")
    warning("检测到重复局面")
    error("网络连接断开")
    
    # 格式化消息
    player_name = "Player1"
    score = 100
    info("玩家 %s 得分: %d", player_name, score)


# ==================== 5. 综合使用示例 ====================
def example_integrated():
    """综合使用示例"""
    from desktopevents import event_bus, event_types
    from desktopconfig.constants import GameConstants
    from desktopexceptions import InvalidMoveError
    from desktoputils.logger import get_module_logger
    
    logger = get_module_logger("example")
    
    # 订阅棋子移动事件
    def on_piece_moved(event):
        logger.info("棋子从 %s 移动到 %s", event.data.get('from'), event.data.get('to'))
        
        # 检查是否超时
        if event.data.get('time_used', 0) > GameConstants.AI_THINK_TIMEOUT_MS:
            warning("移动超时!")
    
    event_bus.subscribe(event_types.PIECE_MOVED, on_piece_moved)
    
    # 模拟移动
    try:
        # 验证移动合法性
        from_pos = (0, 0)
        to_pos = (15, 15)
        
        if to_pos[0] >= GameConstants.BOARD_SIZE_XIONGHAN:
            raise PositionOutOfBoundsError(
                row=to_pos[0],
                col=to_pos[1],
                board_size=GameConstants.BOARD_SIZE_XIONGHAN
            )
        
        # 发布移动事件
        event_bus.emit(event_types.PIECE_MOVED, {
            'from': from_pos,
            'to': to_pos,
            'time_used': 5000
        })
        
    except ChessGameError as e:
        logger.error("移动失败: %s", e)
        # 发布错误事件
        event_bus.emit(event_types.ERROR_OCCURRED, {
            'error_type': type(e).__name__,
            'message': str(e)
        })


if __name__ == "__main__":
    print("=" * 60)
    print("事件总线示例:")
    print("=" * 60)
    example_event_bus()
    
    print("\n" + "=" * 60)
    print("常量配置示例:")
    print("=" * 60)
    example_constants()
    
    print("\n" + "=" * 60)
    print("异常体系示例:")
    print("=" * 60)
    example_exceptions()
    
    print("\n" + "=" * 60)
    print("日志系统示例:")
    print("=" * 60)
    example_logging()
    
    print("\n" + "=" * 60)
    print("综合使用示例:")
    print("=" * 60)
    example_integrated()



