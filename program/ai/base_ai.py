import threading


class BaseAI:
    """匈汉象棋AI基类，定义统一的AI接口"""

    def __init__(self, ai_color="black"):
        """初始化AI

        Args:
            ai_color (str): AI执子颜色 'red' 或 'black'
        """
        self.ai_color = ai_color
        self.computed_move = None
        self.computation_finished = False
        self.best_move_so_far = None
        self.best_value_so_far = float('-inf')

        # 多线程相关
        self.ai_thread = None
        self.lock = threading.Lock()

    def get_move_async(self, game_state):
        """异步获取AI的最佳走法，启动多线程计算

        Args:
            game_state: GameState对象，表示当前棋盘状态
        """
        raise NotImplementedError("Subclasses must implement get_move_async")

    def is_computation_finished(self):
        """检查计算是否完成"""
        raise NotImplementedError("Subclasses must implement is_computation_finished")

    def get_computed_move(self):
        """获取计算完成的走法，如果计算未完成则返回当前最佳走法"""
        raise NotImplementedError("Subclasses must implement get_computed_move")

    def get_best_move(self, game_state):
        """获取AI的最佳走法（同步方法，用于兼容性）"""
        raise NotImplementedError("Subclasses must implement get_best_move")
