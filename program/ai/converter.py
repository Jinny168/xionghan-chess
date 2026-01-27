# coding=utf-8
"""
匈汉象棋MCTS AI适配器
用于将MCTS AI系统的输入输出转换为游戏本体可用的格式
"""

from program.ai.mcts.mcts_game import Game
from program.core.chess_pieces import Ju, Ma, Xiang, Shi, King, Pao, Pawn, Lei, She, Xun, Wei, \
    Jia, Ci, Dun
from program.core.game_state import GameState

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


def _get_random_valid_move(game_state):
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


def convert_game_move_to_mcts_format(from_pos, to_pos):
    """将游戏本体的移动格式转换为MCTS格式

    Args:
        from_pos: 起始位置 (row, col)
        to_pos: 目标位置 (row, col)

    Returns:
        int: MCTS移动ID
    """
    from_y, from_x = from_pos
    to_y, to_x = to_pos
    move_str = f"{from_y:02d}{from_x:02d}{to_y:02d}{to_x:02d}"
    if move_str in move_action2move_id:
        return move_action2move_id[move_str]
    return None


def validate_move(game_state, from_pos, to_pos):
    """验证移动是否符合匈汉象棋的规则

    Args:
        game_state: 游戏状态
        from_pos: 起始位置 (row, col)
        to_pos: 目标位置 (row, col)

    Returns:
        bool: 移动是否合法
    """
    from_row, from_col = from_pos
    to_row, to_col = to_pos

    # 检查边界
    if not (0 <= from_row < 13 and 0 <= from_col < 13 and 0 <= to_row < 13 and 0 <= to_col < 13):
        return False

    # 获取棋子
    piece = game_state.get_piece_at(from_row, from_col)
    if not piece:
        return False

    # 检查是否是当前玩家的棋子
    if piece.color != game_state.player_turn:
        return False

    # 使用游戏规则验证移动
    from program.core.game_rules import GameRules
    return GameRules.is_valid_move(game_state.pieces, piece, from_row, from_col, to_row, to_col)


# 匈汉象棋规则适配器 - 适配MCTS与游戏本体的规则
def _convert_piece_name(game_piece_name, color):
    """将游戏本体的棋子名称转换为MCTS格式"""
    # 创建从游戏本体棋子名称到MCTS棋子名称的映射
    game_to_mcts_name_map = {
        # 红方棋子
        "漢": "红漢", "仕": "红仕", "相": "红相", "俥": "红俥",
        "傌": "红傌", "炮": "红炮", "兵": "红兵", "射": "红射",
        "檑": "红檑", "尉": "红尉", "甲": "红甲", "刺": "红刺", "楯": "红楯", "巡": "红巡",
        # 黑方棋子
        "汗": "黑汗", "士": "黑士", "象": "黑象", "車": "黑車",
        "砲": "黑砲", "卒": "黑卒", "䠶": "黑䠶", "衛": "黑衛", "胄": "黑胄", "伺": "黑伺", "碷": "黑碷",
        "礌": "黑礌", "廵": "黑廵",
    }

    # 首先尝试直接映射
    if game_piece_name in game_to_mcts_name_map:
        return game_to_mcts_name_map[game_piece_name]

    # 如果是红方，添加"红"前缀
    if color == "red":
        return f"红{game_piece_name}"
    # 如果是黑方，添加"黑"前缀
    elif color == "black":
        return f"黑{game_piece_name}"

    return f"红{game_piece_name}"  # 默认为红方


def get_piece_class_by_name(name):
    """根据棋子名称获取棋子类

    Args:
        name (str): 棋子名称

    Returns:
        class: 棋子类
    """
    piece_classes = {
        '車': Ju, '俥': Ju,
        '馬': Ma, '傌': Ma,
        '象': Xiang, '相': Xiang,
        '士': Shi, '仕': Shi,
        '汗': King, '漢': King,
        '砲': Pao, '炮': Pao,
        '卒': Pawn, '兵': Pawn,
        '礌': Lei, '檑': Lei,
        '䠶': She, '射': She,
        '廵': Xun, '巡': Xun,
        '衛': Wei, '尉': Wei,
        '胄': Jia, '甲': Jia,
        '刺': Ci, '伺': Ci,
        '楯': Dun, '碷': Dun
    }

    return piece_classes.get(name)


def convert_move_format(from_pos, to_pos):
    """将游戏本体的移动格式转换为MCTS格式

    Args:
        from_pos (tuple): 起始位置(row, col)
        to_pos (tuple): 目标位置(row, col)

    Returns:
        str: MCTS格式的移动字符串
    """
    from_row, from_col = from_pos
    to_row, to_col = to_pos

    # 生成MCTS格式的移动字符串
    move_action = f"{from_row:02d}{from_col:02d}{to_row:02d}{to_col:02d}"
    return move_action

def get_mcts_player(policy_value_function, c_puct=5, n_playout=2000, is_selfplay=0):
    """获取MCTS玩家实例

    Args:
        policy_value_function: 策略价值函数
        c_puct: UCT公式中的探索参数
        n_playout: 模拟次数
        is_selfplay: 是否为自我对弈模式

    Returns:
        MCTSPlayer: MCTS玩家实例
    """
    from program.ai.mcts.mcts import MCTSPlayer
    return MCTSPlayer(policy_value_function, c_puct, n_playout, is_selfplay)

def adapt_move_to_game_format(mcts_move, game_state):
    """将MCTS的移动适配为游戏本体的格式

    Args:
        mcts_move: MCTS返回的移动ID
        game_state: 当前游戏状态用于验证

    Returns:
        tuple: ((from_row, from_col), (to_row, to_col))
    """
    if mcts_move not in move_id2move_action:
        print(f"Invalid MCTS move ID: {mcts_move}")
        return _get_random_valid_move(game_state)

    move_str = move_id2move_action[mcts_move]

    # 解析移动字符串 '00000101' -> (from_y, from_x, to_y, to_x)
    from_y = int(move_str[0:2])
    from_x = int(move_str[2:4])
    to_y = int(move_str[4:6])
    to_x = int(move_str[6:8])

    return ((from_y, from_x), (to_y, to_x))

def convert_mcts_move_to_game_format(mcts_move, game_state):
    """将MCTS的移动转换为游戏本体的格式

    Args:
        mcts_move: MCTS返回的移动ID
        game_state: 当前游戏状态用于验证

    Returns:
        tuple: ((from_row, from_col), (to_row, to_col))
    """
    if mcts_move not in move_id2move_action:
        print(f"Invalid MCTS move ID: {mcts_move}")
        return _get_random_valid_move(game_state)

    move_str = move_id2move_action[mcts_move]

    # 解析移动字符串 '00000101' -> (from_y, from_x, to_y, to_x)
    from_y = int(move_str[0:2])
    from_x = int(move_str[2:4])
    to_y = int(move_str[4:6])
    to_x = int(move_str[6:8])

    return ((from_y, from_x), (to_y, to_x))

def adapt_state_to_mcts(game_state):
    """将游戏本体的GameState适配为MCTS的Board状态

    Args:
        game_state: 游戏本体的GameState对象

    Returns:
        Board: MCTS的Board对象
    """
    # 创建MCTS Board实例
    mcts_board = Board()

    # 将游戏状态复制到MCTS Board
    # 首先清空MCTS Board的初始状态
    mcts_board.state_list = [['一一' for _ in range(13)] for _ in range(13)]

    # 将游戏本体的棋子复制到MCTS棋盘
    for piece in game_state.pieces:
        # 转换棋子名称
        mcts_name = _convert_piece_name(piece.name, piece.color)
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
    from collections import deque
    mcts_board.state_deque = deque(maxlen=4)
    for _ in range(4):
        # 添加当前状态的副本
        current_state_copy = [['一一' for _ in range(13)] for _ in range(13)]
        for piece in game_state.pieces:
            mcts_name = _convert_piece_name(piece.name, piece.color)
            current_state_copy[piece.row][piece.col] = mcts_name
        mcts_board.state_deque.append(current_state_copy)

    return mcts_board


class XiangHanChessRuleAdapter:
    """匈汉象棋规则适配器，用于将游戏本体的规则适配到MCTS中"""

    def __init__(self):
        """初始化规则适配器"""
        # 特殊规则设置，从游戏配置中获取
        from program.config.config import game_config
        self.king_can_leave_palace = game_config.get_setting("king_can_leave_palace", True)  # 汉/汗是否可以出九宫
        self.king_lose_diagonal_outside_palace = game_config.get_setting("king_lose_diagonal_outside_palace",
                                                                         True)  # 汉/汗出九宫后是否失去斜走能力
        self.king_can_diagonal_in_palace = game_config.get_setting("king_can_diagonal_in_palace", True)  # 汉/汗在九宫内是否可以斜走
        self.shi_can_leave_palace = game_config.get_setting("shi_can_leave_palace", True)  # 士是否可以出九宫
        self.shi_gain_straight_outside_palace = game_config.get_setting("shi_gain_straight_outside_palace",
                                                                        True)  # 士出九宫后是否获得直走能力
        self.xiang_can_cross_river = game_config.get_setting("xiang_can_cross_river", True)  # 相是否可以过河
        self.xiang_gain_jump_two_outside_river = game_config.get_setting("xiang_gain_jump_two_outside_river",
                                                                         True)  # 相过河后是否获得隔两格吃子能力
        self.ma_can_straight_three = game_config.get_setting("ma_can_straight_three", True)  # 马是否可以获得直走三格的能力


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




class MCTSAdapter:
    """MCTS AI与游戏本体之间的适配器"""

    def __init__(self):
        """初始化适配器"""
        # MCTS相关的对象
        self.mcts_board = Board()
        self.mcts_game = Game(self.mcts_board)

        # 游戏本体的对象
        self.game_state = GameState()

        # 建立棋子映射关系
        self.piece_name_mapping = {
            # 从游戏本体到MCTS
            '俥': '红車', '傌': '红馬', '相': '红象', '仕': '红士', '漢': '红漢',
            '炮': '红砲', '兵': '红卒', '檑': '红礌', '射': '红射', '巡': '红巡',
            '尉': '红衛', '甲': '红甲', '刺': '红刺', '楯': '红楯',
            '車': '黑車', '馬': '黑馬', '象': '黑象', '士': '黑士', '汗': '黑汗',
            '砲': '黑砲', '卒': '黑卒', '礌': '黑礌', '䠶': '黑䠶', '廵': '黑廵',
            '衛': '黑衛', '胄': '黑胄', '伺': '黑伺', '碷': '黑碷'
        }

        # 反向映射
        self.reverse_piece_name_mapping = {v: k for k, v in self.piece_name_mapping.items()}

    def sync_game_state_to_mcts(self, game_state_obj):
        """将游戏本体的状态同步到MCTS棋盘

        Args:
            game_state_obj: 游戏本体的GameState对象
        """
        # 从游戏本体获取当前棋盘状态
        # 将棋子列表转换为MCTS棋盘所需的格式
        board_state = [['一一' for _ in range(13)] for _ in range(13)]

        for piece in game_state_obj.pieces:
            # 将游戏本体的棋子名称转换为MCTS格式
            piece_name = piece.name
            mcts_name = self.piece_name_mapping.get(piece_name, piece_name)

            # 根据玩家颜色确定MCTS棋子名称前缀
            if piece.color == 'red':
                mcts_name = '红' + mcts_name[1:]
            elif piece.color == 'black':
                mcts_name = '黑' + mcts_name[1:]

            board_state[piece.row][piece.col] = mcts_name

        # 更新MCTS棋盘状态
        self.mcts_board.state_list = board_state
        self.mcts_board.state_deque[-1] = board_state

        # 设置当前玩家
        self.mcts_board.current_player = 1 if game_state_obj.player_turn == 'red' else 2
        self.mcts_board.current_player_color = '红' if game_state_obj.player_turn == 'red' else '黑'
        self.mcts_board.id2color = {1: '红', 2: '黑'}
        self.mcts_board.color2id = {'红': 1, '黑': 2}

        # 重新计算合法走子
        # 由于availables是只读属性，我们不需要显式赋值，只需确保状态已更新
        # Board类会在访问availables属性时自动计算合法走子

    def sync_mcts_to_game_state(self):
        """将MCTS棋盘状态同步回游戏本体

        Returns:
            GameState: 同步后的游戏本体状态
        """
        # 创建新的GameState对象
        new_game_state = GameState()

        # 清空现有棋子
        new_game_state.pieces = []

        # 将MCTS棋盘状态转换为游戏本体格式
        for row in range(13):
            for col in range(13):
                mcts_piece = self.mcts_board.state_list[row][col]
                if mcts_piece != '一一':
                    # 将MCTS棋子名称转换为游戏本体格式
                    if mcts_piece.startswith('红'):
                        color = 'red'
                        piece_type = mcts_piece[1:]
                    elif mcts_piece.startswith('黑'):
                        color = 'black'
                        piece_type = mcts_piece[1:]
                    else:
                        continue  # 无效棋子名称

                    # 查找游戏本体的棋子名称
                    game_piece_name = self.reverse_piece_name_mapping.get(mcts_piece, piece_type)

                    # 根据棋子名称创建对应类型的棋子对象
                    from program.core.chess_pieces import (
                        Ju, Ma, Xiang, Shi, King, Pao, Pawn,
                        She, Lei, Xun, Wei, Jia, Ci, Dun
                    )

                    # 根据棋子名称创建对应的棋子类
                    piece_class = get_piece_class_by_name(game_piece_name)
                    if piece_class:
                        new_piece = piece_class(color, row, col)
                        new_game_state.pieces.append(new_piece)

        # 设置当前玩家
        new_game_state.player_turn = 'red' if self.mcts_board.current_player == 1 else 'black'

        return new_game_state

    def get_current_player_color(self):
        """获取当前玩家颜色

        Returns:
            str: 当前玩家颜色 ('red' 或 'black')
        """
        return 'red' if self.mcts_board.current_player == 1 else 'black'

    def make_move(self, mcts_move_id):
        """执行移动

        Args:
            mcts_move_id: MCTS移动ID

        Returns:
            bool: 移动是否成功
        """
        try:
            # 执行移动
            self.mcts_board.do_move(mcts_move_id)
            return True
        except Exception as e:
            print(f"执行移动失败: {e}")
            return False
