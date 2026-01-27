# 添加MCTS和神经网络相关导入
from program.ai.mcts_ai import MCTSAI
from program.ai.traditional_ai import TraditionalAI

try:
    from program.ai.mcts.mcts import MCTSPlayer
    from program.ai.mcts.pytorch_net import PolicyValueNet
    from program.ai.mcts.mcts_config import CONFIG as MCTS_CONFIG
    from program.ai.mcts.mcts_game import Board, move_id2move_action, move_action2move_id
    MCTS_AVAILABLE = True
except ImportError:
    MCTS_AVAILABLE = False
    print("Warning: MCTS modules not available. Only traditional algorithms will be supported.")

class ChessAI:
    """匈汉象棋AI类，支持多种算法，包括传统搜索算法和MCTS+神经网络"""

    def __init__(self, algorithm="negamax", difficulty="hard", ai_color="black", model_file=None):
        """初始化AI

        Args:
            algorithm (str): 算法类型 'negamax', 'minimax', 'alpha-beta', 'mcts'
            difficulty (str): 难度级别 'easy', 'medium', 'hard'
            ai_color (str): AI执子颜色 'red' 或 'black'
            model_file (str): 模型文件路径（仅用于MCTS算法）
        """
        self.algorithm = algorithm.lower()
        self.ai_color = ai_color

        # 根据算法类型创建相应的AI实例
        if self.algorithm in ['negamax', 'minimax', 'alpha-beta']:
            self.ai_impl = TraditionalAI(algorithm, difficulty, ai_color)
        elif self.algorithm == 'mcts':
            if MCTS_AVAILABLE:
                self.ai_impl = MCTSAI(ai_color, model_file, n_playout=1000)
            else:
                print("Warning: MCTS not available, falling back to negamax")
                self.ai_impl = TraditionalAI("negamax", difficulty, ai_color)
        else:
            print(f"Unknown algorithm {algorithm}, defaulting to negamax")
            self.ai_impl = TraditionalAI("negamax", difficulty, ai_color)

    def get_move_async(self, game_state):
        """异步获取AI的最佳走法，启动多线程计算

        Args:
            game_state: GameState对象，表示当前棋盘状态
        """
        return self.ai_impl.get_move_async(game_state)

    def is_computation_finished(self):
        """检查计算是否完成"""
        return self.ai_impl.is_computation_finished()

    def get_computed_move(self):
        """获取计算完成的走法，如果计算未完成则返回当前最佳走法"""
        return self.ai_impl.get_computed_move()

    def get_best_move(self, game_state):
        """获取AI的最佳走法（同步方法，用于兼容性）"""
        return self.ai_impl.get_best_move(game_state)