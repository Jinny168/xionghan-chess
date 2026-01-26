# coding=utf-8
"""
匈汉象棋MCTS AI适配器
用于将MCTS AI系统的输入输出转换为游戏本体可用的格式
"""

from program.ai.mcts.mcts_game import Board, Game, move_id2move_action
from program.core.chess_pieces import Ju, Ma, Xiang, Shi, King, Pao, Pawn, Lei, She, Xun, Wei, \
    Jia, Ci, Dun
from program.core.game_state import GameState


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
                    piece_class = self.get_piece_class_by_name(game_piece_name)
                    if piece_class:
                        new_piece = piece_class(color, row, col)
                        new_game_state.pieces.append(new_piece)
        
        # 设置当前玩家
        new_game_state.player_turn = 'red' if self.mcts_board.current_player == 1 else 'black'
        
        return new_game_state
    
    def get_piece_class_by_name(self, name):
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
    
    def convert_move_format(self, from_pos, to_pos):
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
    
    def convert_mcts_move_to_game_format(self, mcts_move_id):
        """将MCTS的移动ID转换为游戏本体可用的格式
        
        Args:
            mcts_move_id: MCTS移动ID
            
        Returns:
            tuple: (from_pos, to_pos) 游戏本体格式的位置元组
        """
        # 将移动ID转换为移动动作字符串
        if mcts_move_id in move_id2move_action:
            move_action = move_id2move_action[mcts_move_id]
            
            # 解析移动动作字符串
            from_row = int(move_action[0:2])
            from_col = int(move_action[2:4])
            to_row = int(move_action[4:6])
            to_col = int(move_action[6:8])
            
            return (from_row, from_col), (to_row, to_col)
        else:
            # 如果移动ID无效，返回无效值
            return None, None
    
    def get_mcts_player(self, policy_value_function, c_puct=5, n_playout=2000, is_selfplay=0):
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