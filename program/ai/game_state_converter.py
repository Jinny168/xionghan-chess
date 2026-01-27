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




class GameStateConverter:
    """游戏状态转换器，用于在游戏本体状态和MCTS状态之间转换"""

    def __init__(self):
        # 创建从游戏本体棋子名称到MCTS棋子名称的映射
        self.game_to_mcts_name_map = {
            # 红方棋子
            "漢": "红漢", "仕": "红仕", "相": "红相", "俥": "红俥",
            "傌": "红傌", "炮": "红炮", "兵": "红兵", "射": "红射",
            "檑": "红檑", "尉": "红尉", "甲": "红甲", "刺": "红刺", "楯": "红楯",
            # 黑方棋子
            "汗": "黑汗", "士": "黑士", "象": "黑象", "車": "黑車",
            "馬": "黑馬", "砲": "黑砲", "卒": "黑卒", "䠶": "黑䠶",
            "礌": "黑礌", "衛": "黑衛", "胄": "黑胄", "伺": "黑伺", "碷": "黑碷",
        }

        # 反向映射
        self.mcts_to_game_name_map = {v: k for k, v in self.game_to_mcts_name_map.items()}

    def convert_to_mcts_board(self, game_state):
        """将游戏本体的GameState转换为MCTS的Board

        Args:
            game_state: GameState对象

        Returns:
            Board: MCTS的Board对象
        """
        from collections import deque

        # 创建MCTS Board实例
        mcts_board = Board()

        # 将游戏状态复制到MCTS Board
        # 首先清空MCTS Board的初始状态
        mcts_board.state_list = [['一一' for _ in range(13)] for _ in range(13)]

        # 将游戏本体的棋子复制到MCTS棋盘
        for piece in game_state.pieces:
            # 转换棋子名称
            mcts_name = self._convert_piece_name(piece.name, piece.color)
            mcts_board.state_list[piece.row][piece.col] = mcts_name

        # 设置当前玩家颜色
        mcts_board.current_player_color = '红' if game_state.player_turn == 'red' else '黑'

        # 设置玩家ID
        mcts_board.current_player_id = 1 if game_state.player_turn == 'red' else 2

        # 设置游戏状态
        mcts_board.game_start = True
        mcts_board.winner = None
        mcts_board.action_count = getattr(game_state, 'moves_count', 0)

        # 更新state_deque
        mcts_board.state_deque = deque(maxlen=4)
        for _ in range(4):
            # 添加当前状态的副本
            current_state_copy = [['一一' for _ in range(13)] for _ in range(13)]
            for piece in game_state.pieces:
                mcts_name = self._convert_piece_name(piece.name, piece.color)
                current_state_copy[piece.row][piece.col] = mcts_name
            mcts_board.state_deque.append(current_state_copy)

        return mcts_board

    def _convert_piece_name(self, game_piece_name, color):
        """将游戏本体的棋子名称转换为MCTS格式"""
        # 首先尝试直接映射
        if game_piece_name in self.game_to_mcts_name_map:
            return self.game_to_mcts_name_map[game_piece_name]

        # 如果是红方，添加"红"前缀
        if color == "red":
            return f"红{game_piece_name}"
        # 如果是黑方，添加"黑"前缀
        elif color == "black":
            return f"黑{game_piece_name}"

        return f"红{game_piece_name}"  # 默认为红方

    def convert_mcts_move_to_game_format(self, mcts_move, game_state):
        """将MCTS的移动转换为游戏本体的格式

        Args:
            mcts_move: MCTS返回的移动ID
            game_state: 当前游戏状态用于验证

        Returns:
            tuple: ((from_row, from_col), (to_row, to_col))
        """
        if mcts_move not in move_id2move_action:
            print(f"Invalid MCTS move ID: {mcts_move}")
            return self._get_random_valid_move(game_state)

        move_str = move_id2move_action[mcts_move]

        # 解析移动字符串 '00000101' -> (from_y, from_x, to_y, to_x)
        from_y = int(move_str[0:2])
        from_x = int(move_str[2:4])
        to_y = int(move_str[4:6])
        to_x = int(move_str[6:8])

        return ((from_y, from_x), (to_y, to_x))

    def _get_random_valid_move(self, game_state):
        """获取一个随机的有效移动

        Args:
            game_state: GameState对象，表示当前棋盘状态

        Returns:
            tuple: ((from_row, from_col), (to_row, to_col)) 表示移动的起点和终点
        """
        import random
        # 获取所有有效移动
        valid_moves = tools.get_valid_moves(game_state, game_state.player_turn)
        if valid_moves:
            return random.choice(valid_moves)
        return None
