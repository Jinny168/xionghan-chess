import threading

import pygame

from program.ai.base_ai import BaseAI
from program.ai.game_state_converter import GameStateConverter

from program.utils import tools

# 添加MCTS和神经网络相关导入
try:
    from program.ai.mcts.mcts import MCTSPlayer
    from program.ai.mcts.pytorch_net import PolicyValueNet
    from program.ai.mcts.mcts_config import CONFIG as MCTS_CONFIG
    from program.ai.mcts.mcts_game import Board, move_id2move_action, move_action2move_id
    MCTS_AVAILABLE = True
except ImportError:
    MCTS_AVAILABLE = False
    print("Warning: MCTS modules not available. Only traditional algorithms will be supported.")




class MCTSAI(BaseAI):
    """MCTS+神经网络AI类"""

    def __init__(self, ai_color="black", model_file=None, n_playout=1000):
        """初始化MCTS+神经网络AI

        Args:
            ai_color (str): AI执子颜色 'red' 或 'black'
            model_file (str): 模型文件路径，如果为None则使用默认路径
            n_playout (int): MCTS模拟次数
        """
        if not MCTS_AVAILABLE:
            raise RuntimeError("MCTS modules are not available. Cannot initialize MCTSAI.")

        super().__init__(ai_color)

        self.n_playout = n_playout
        self.ai_color = ai_color

        # 加载神经网络模型
        if model_file is None:
            if MCTS_CONFIG['use_frame'] == 'pytorch':
                model_file = MCTS_CONFIG.get('pytorch_model_path', 'current_policy.pkl')
            else:
                model_file = MCTS_CONFIG.get('paddle_model_path', 'current_policy.model')

        try:
            self.policy_value_net = PolicyValueNet(model_file=model_file)
            print(f"MCTS AI initialized with model: {model_file}")
        except Exception as e:
            print(f"Failed to load model {model_file}: {e}")
            print("Initializing MCTS AI with random model...")
            self.policy_value_net = PolicyValueNet()  # 初始化随机模型

        # 创建MCTS玩家
        self.mcts_player = MCTSPlayer(
            self.policy_value_net.policy_value_fn,
            c_puct=5,
            n_playout=self.n_playout,
            is_selfplay=0
        )

        # 游戏状态转换器
        self.game_converter = GameStateConverter()

    def get_move_async(self, game_state):
        """异步获取AI的最佳走法，启动多线程计算

        Args:
            game_state: GameState对象，表示当前棋盘状态
        """
        # 重置状态
        self.computed_move = None
        self.computation_finished = False
        self.best_move_so_far = None
        self.best_value_so_far = float('-inf')

        # 启动一个线程来执行AI计算
        self.ai_thread = threading.Thread(target=self._compute_move, args=(game_state,))
        self.ai_thread.daemon = True  # 设置为守护线程
        self.ai_thread.start()

    def is_computation_finished(self):
        """检查计算是否完成"""
        return self.computation_finished

    def get_computed_move(self):
        """获取计算完成的走法，如果计算未完成则返回当前最佳走法"""
        with self.lock:  # 线程安全
            if self.computation_finished:
                return self.computed_move
            else:
                # 如果计算未完成，返回当前已知的最佳走法
                return self.best_move_so_far if self.best_move_so_far is not None else self.computed_move

    def _compute_move(self, game_state):
        """在单独线程中计算最佳走法"""
        try:
            # 执行实际的AI计算
            self.computed_move = self._get_best_move(game_state)
        except Exception as e:
            print(f"Error computing MCTS move: {e}")
            # 在出错的情况下返回一个有效的移动
            self.computed_move = self._get_random_valid_move(game_state)
        finally:
            # 标记计算完成
            with self.lock:  # 线程安全
                self.computation_finished = True
            # 通过pygame事件通知主线程
            pygame.event.post(pygame.event.Event(pygame.USEREVENT + 2))  # 使用不同的事件ID

    def _get_best_move(self, game_state):
        """获取AI的最佳走法（实际计算逻辑）

        Args:
            game_state: GameState对象，表示当前棋盘状态

        Returns:
            tuple: ((from_row, from_col), (to_row, to_col)) 表示移动的起点和终点
        """
        # 将游戏状态转换为MCTS所需的格式
        mcts_board = self.game_converter.convert_to_mcts_board(game_state)

        # 使用MCTS获取动作
        move = self.mcts_player.get_action(mcts_board, temp=1e-3)

        # 将MCTS动作转换回游戏状态格式
        return self.game_converter.convert_mcts_move_to_game_format(move, game_state)

    def _get_random_valid_move(self, game_state):
        """获取一个随机的有效移动作为备选

        Args:
            game_state: GameState对象，表示当前棋盘状态

        Returns:
            tuple: ((from_row, from_col), (to_row, to_col)) 表示移动的起点和终点
        """
        # 获取所有有效移动
        valid_moves = tools.get_valid_moves(game_state, self.ai_color)
        if valid_moves:
            import random
            return random.choice(valid_moves)
        return None

    def get_best_move(self, game_state):
        """获取AI的最佳走法（同步方法，用于兼容性）"""
        # 使用同步方式获取最佳走法
        return self._get_best_move(game_state)

