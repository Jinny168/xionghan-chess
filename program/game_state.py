import time

from chess_pieces import create_initial_pieces, King, Jia, Ci, Dun
from game_rules import GameRules


class GameState:
    """游戏状态管理类，负责维护当前棋局、历史记录和状态判断"""
    
    def __init__(self):
        """初始化游戏状态"""
        # 初始化棋子
        self.is_game_over = None
        self.pieces = create_initial_pieces()

        # 游戏状态
        self.player_turn = "red"  # 红方先行
        self.game_over = False
        self.winner = None
        
        # 将军状态
        self.is_check = False  # 当前是否有一方被将军
        self.check_animation_time = 0  # 将军动画开始的时间戳
        self.check_animation_duration = 4.0  # 将军动画持续时间（秒），延长为4秒
        
        # 历史记录 - 用于悔棋功能
        self.move_history = []  # 存储 (piece, from_row, from_col, to_row, to_col, captured_piece)
        
        # 阵亡棋子记录
        self.captured_pieces = {"red": [], "black": []}  # 记录双方阵亡的棋子
        
        # 时间跟踪
        self.start_time = time.time()  # 游戏开始时间
        self.total_time = 0  # 游戏总时长（秒）
        self.red_time = 0  # 红方已用时间（秒）
        self.black_time = 0  # 黑方已用时间（秒）
        self.current_turn_start_time = time.time()  # 当前回合开始时间
    
    def get_piece_at(self, row, col):
        """获取指定位置的棋子"""
        return GameRules.get_piece_at(self.pieces, row, col)
    
    def move_piece(self, from_row, from_col, to_row, to_col):
        """移动棋子
        
        Args:
            from_row (int): 起始行
            from_col (int): 起始列
            to_row (int): 目标行
            to_col (int): 目标列
            
        Returns:
            bool: 移动是否成功
        """
        # 获取要移动的棋子
        piece = self.get_piece_at(from_row, from_col)
        if not piece or piece.color != self.player_turn:
            return False
        
        # 检查移动是否合法
        if not GameRules.is_valid_move(self.pieces, piece, from_row, from_col, to_row, to_col):
            return False
        
        # 检查移动后是否会导致自己被将军（送将）
        if GameRules.would_be_in_check_after_move(self.pieces, piece, from_row, from_col, to_row, to_col):
            return False
        
        # 获取目标位置的棋子（如果有）
        captured_piece = self.get_piece_at(to_row, to_col)
        
        # 记录移动历史
        self.move_history.append((
            piece,
            from_row,
            from_col,
            to_row,
            to_col,
            captured_piece
        ))
        
        # 更新当前玩家的用时
        current_time = time.time()
        elapsed = current_time - self.current_turn_start_time
        if self.player_turn == "red":
            self.red_time += elapsed
        else:
            self.black_time += elapsed
        
        # 如果有棋子被吃掉，移除它并记录到阵亡列表
        if captured_piece:
            self.pieces.remove(captured_piece)
            self.captured_pieces[captured_piece.color].append(captured_piece)
            
            # 如果吃掉的是对方将/帅/汉/汗，游戏结束
            if isinstance(captured_piece, King):
                self.game_over = True
                self.winner = piece.color
                # 更新游戏总时长
                self.total_time = current_time - self.start_time
                return True
        
        # 执行移动
        piece.move_to(to_row, to_col)

        # 处理甲/胄的特殊吃子规则（移动后检查）
        if isinstance(piece, Jia):
            # 查找所有被吃掉的敌方棋子
            captured_pieces = GameRules.find_jia_capture_moves(self.pieces, piece)
            
            # 实际移除被吃掉的棋子
            for captured in captured_pieces:
                if captured in self.pieces:
                    self.pieces.remove(captured)
                    self.captured_pieces[captured.color].append(captured)
                    
                    # 如果吃掉的是对方将/帅/汉/汗，游戏结束
                    if isinstance(captured, King):
                        self.game_over = True
                        self.winner = piece.color
                        # 更新游戏总时长
                        current_time = time.time()
                        self.total_time = current_time - self.start_time
                        # 切换玩家
                        opponent_color = "black" if self.player_turn == "red" else "red"
                        return True
        
        # 处理刺的兑子规则
        if isinstance(piece, Ci):
            # 检查移动前起始位置的反方向一格是否有敌棋（兑子条件）
            row_diff = to_row - from_row
            col_diff = to_col - from_col
            
            # 计算起始位置的反方向
            reverse_row = from_row - row_diff
            reverse_col = from_col - col_diff
            
            # 检查反方向位置是否在棋盘范围内
            if 0 <= reverse_row < 13 and 0 <= reverse_col < 13:
                reverse_piece = GameRules.get_piece_at(self.pieces, reverse_row, reverse_col)
                # 如果反方向有敌方棋子，则进行兑子（双方都阵亡）
                if reverse_piece and reverse_piece.color != piece.color:
                    # 移除刺棋子
                    if piece in self.pieces:
                        self.pieces.remove(piece)
                        self.captured_pieces[piece.color].append(piece)
                    # 移除反方向的敌方棋子
                    if reverse_piece in self.pieces:
                        self.pieces.remove(reverse_piece)
                        self.captured_pieces[reverse_piece.color].append(reverse_piece)
                        
                        # 如果吃掉的是对方将/帅/汉/汗，游戏结束
                        if isinstance(reverse_piece, King):
                            self.game_over = True
                            self.winner = piece.color
                            # 更新游戏总时长
                            current_time = time.time()
                            self.total_time = current_time - self.start_time
                            # 切换玩家
                            opponent_color = "black" if self.player_turn == "red" else "red"
                            return True
                    
                    # 由于刺和敌棋都被移除了，无需继续处理
                    # 切换玩家
                    opponent_color = "black" if self.player_turn == "red" else "red"
                    
                    # 检查是否将军
                    self.is_check = GameRules.is_check(self.pieces, opponent_color)
                    if self.is_check:
                        # 设置将军动画计时器
                        self.check_animation_time = current_time
                    
                    # 检查是否将死或获胜
                    game_over, winner = GameRules.is_game_over(self.pieces, self.player_turn)
                    
                    if game_over:
                        self.game_over = True
                        self.winner = winner
                        # 更新游戏总时长
                        self.total_time = current_time - self.start_time
                    else:
                        # 切换玩家回合
                        self.player_turn = opponent_color
                        # 重置当前回合开始时间
                        self.current_turn_start_time = current_time
                    
                    return True

        # 切换玩家
        opponent_color = "black" if self.player_turn == "red" else "red"
        
        # 检查是否将军
        self.is_check = GameRules.is_check(self.pieces, opponent_color)
        if self.is_check:
            # 设置将军动画计时器
            self.check_animation_time = current_time
        
        # 检查是否将死或获胜
        game_over, winner = GameRules.is_game_over(self.pieces, self.player_turn)
        
        if game_over:
            self.game_over = True
            self.winner = winner
            # 更新游戏总时长
            self.total_time = current_time - self.start_time
        else:
            # 切换玩家回合
            self.player_turn = opponent_color
            # 重置当前回合开始时间
            self.current_turn_start_time = current_time
        
        return True
    
    def undo_move(self):
        """撤销上一步移动
        
        Returns:
            bool: 是否成功撤销
        """
        if not self.move_history:
            return False
        
        # 获取上一步移动记录
        piece, from_row, from_col, to_row, to_col, captured_piece = self.move_history.pop()
        
        # 将棋子移回原位置
        piece.move_to(from_row, from_col)
        
        # 恢复被吃掉的棋子
        if captured_piece:
            self.pieces.append(captured_piece)
            # 从阵亡列表中移除
            if captured_piece in self.captured_pieces[captured_piece.color]:
                self.captured_pieces[captured_piece.color].remove(captured_piece)
        
        # 切换玩家回合
        self.player_turn = "black" if self.player_turn == "red" else "red"
        
        # 重置游戏状态
        self.game_over = False
        self.winner = None
        
        # 重置将军状态
        self.is_check = False
        
        # 重置当前回合开始时间
        self.current_turn_start_time = time.time()
        
        return True
    
    def update_times(self):
        """更新当前时间计数，但不切换回合"""
        if not self.game_over:
            current_time = time.time()
            elapsed = current_time - self.current_turn_start_time
            # 更新总游戏时长
            self.total_time = current_time - self.start_time
            
            # 这里我们只计算临时的当前回合时间，不更新累计时间
            # 因为累计时间只在移动棋子时更新
            if self.player_turn == "red":
                return self.red_time + elapsed, self.black_time
            else:
                return self.red_time, self.black_time + elapsed
        return self.red_time, self.black_time
    
    def should_show_check_animation(self):
        """检查是否应该显示将军动画"""
        if not self.is_check:
            return False
            
        # 检查动画是否在有效时间内
        current_time = time.time()
        elapsed = current_time - self.check_animation_time
        return elapsed < self.check_animation_duration
    
    def get_checked_king_position(self):
        """获取被将军的将/帅的位置"""
        if not self.is_check:
            return None
            
        # 被将军的是当前player_turn的玩家（因为player_turn在move_piece末尾已经切换）
        # 例如，如果红方将军了黑方，move_piece后player_turn是"black"，所以要返回黑方的将/帅位置
        for piece in self.pieces:
            if isinstance(piece, King) and piece.color == self.player_turn:
                return (piece.row, piece.col)
        
        return None
    
    def calculate_possible_moves(self, row, col):
        """计算指定位置棋子的所有可能移动
        
        Args:
            row (int): 棋子的行坐标
            col (int): 棋子的列坐标
            
        Returns:
            tuple: (可移动位置列表, 可吃子位置列表)
        """
        piece = self.get_piece_at(row, col)
        if not piece:
            return [], []
        
        moves, capturable = GameRules.calculate_possible_moves(self.pieces, piece)
        
        # 过滤掉会导致被将军的移动（送将）
        safe_moves = []
        for to_row, to_col in moves:
            if not GameRules.would_be_in_check_after_move(self.pieces, piece, row, col, to_row, to_col):
                # 如果目标位置有盾，且不是己方的盾，则不能吃（盾不可被吃）
                target_piece = self.get_piece_at(to_row, to_col)
                if target_piece and isinstance(target_piece, Dun) and target_piece.color != piece.color:
                    continue  # 不能吃盾
                safe_moves.append((to_row, to_col))
        
        # 过滤掉会导致被将军的吃子移动
        safe_capturable = []
        for to_row, to_col in capturable:
            if not GameRules.would_be_in_check_after_move(self.pieces, piece, row, col, to_row, to_col):
                # 如果目标位置有盾，且不是己方的盾，则不能吃（盾不可被吃）
                target_piece = self.get_piece_at(to_row, to_col)
                if target_piece and isinstance(target_piece, Dun) and target_piece.color != piece.color:
                    continue  # 不能吃盾
                safe_capturable.append((to_row, to_col))
        
        return safe_moves, safe_capturable
    
    def get_winner_text(self):
        """获取胜利方文本
        
        Returns:
            str: 胜利信息文本
        """
        if not self.game_over or not self.winner:
            return ""
        
        return f"{'红方' if self.winner == 'red' else '黑方'}胜利!"
    
    def reset(self):
        """重置游戏状态"""
        self.__init__()
        
        # 重置棋谱滚动位置
        if hasattr(self, 'history_scroll_y'):
            self.history_scroll_y = 0
