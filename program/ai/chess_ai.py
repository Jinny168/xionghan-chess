# 添加MCTS和神经网络相关导入
from program.ai.xionghan_chess_mcts_ai import XionghanChessMctsAI

# 导入传统AI和传统中国象棋AI
from program.ai.xionghan_chess_search_ai import XionghanChessSearchAI
from program.ai.chinese_chess_search_ai import ChineseChessSearchAI

try:
    from program.ai.mcts.mcts import MCTSPlayer
    from program.ai.mcts.pytorch_net import PolicyValueNet
    from program.ai.mcts.mcts_config import CONFIG as MCTS_CONFIG
    from program.ai.mcts.mcts_game import Board, move_id2move_action, move_action2move_id
    MCTS_AVAILABLE = True
except ImportError:
    MCTS_AVAILABLE = False
    print("Warning: MCTS modules not available. Only traditional algorithms will be supported.")

from program.controllers.game_config_manager import game_config


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

        # 检查是否为传统象棋模式
        is_traditional_mode = game_config.get_setting("traditional_mode", False)
        
        # 根据游戏模式和算法类型创建相应的AI实例
        if self.algorithm in ['negamax', 'minimax', 'alpha-beta']:
            if is_traditional_mode:
                # 传统象棋模式下使用专门的传统中国象棋AI
                self.ai_impl = ChineseChessSearchAI(algorithm, difficulty, ai_color)
            else:
                # 匈汉象棋模式下使用通用的传统AI
                self.ai_impl = XionghanChessSearchAI(algorithm, difficulty, ai_color)
        elif self.algorithm == 'mcts':
            if MCTS_AVAILABLE and not is_traditional_mode:
                # MCTS仅在匈汉象棋模式下可用
                self.ai_impl = XionghanChessMctsAI(ai_color, model_file, n_playout=1000)
            else:
                if is_traditional_mode:
                    print("Warning: MCTS not supported in traditional chess mode, falling back to traditional Chinese chess AI")
                    self.ai_impl = ChineseChessSearchAI("negamax", difficulty, ai_color)
                else:
                    print("Warning: MCTS not available, falling back to traditional Hungarian-Chinese chess AI")
                    self.ai_impl = XionghanChessSearchAI("negamax", difficulty, ai_color)
        else:
            if is_traditional_mode:
                print(f"Unknown algorithm {algorithm}, defaulting to traditional Chinese chess AI")
                self.ai_impl = ChineseChessSearchAI("negamax", difficulty, ai_color)
            else:
                print(f"Unknown algorithm {algorithm}, defaulting to traditional Hungarian-Chinese chess AI")
                self.ai_impl = XionghanChessSearchAI("negamax", difficulty, ai_color)

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