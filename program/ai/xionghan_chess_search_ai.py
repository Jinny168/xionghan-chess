"""传统象棋AI对手"""

import random

from program.core.game_rules import GameRules
from program.controllers.game_config_manager import game_config


class XionghanChessSearchAI:
    """传统象棋AI类"""
    
    def __init__(self, algorithm="negamax", difficulty="medium", ai_color="black"):
        """
        初始化AI
        :param algorithm: 算法类型 ('negamax', 'minimax', 'alpha-beta')
        :param difficulty: 难度级别 ("easy", "medium", "hard")
        :param ai_color: AI执子颜色 ('red', 'black')
        """
        self.algorithm = algorithm.lower()
        self.difficulty = difficulty
        self.ai_color = ai_color
        self.rules = GameRules()
        
        # 根据游戏模式设置不同的棋子价值表
        is_traditional_mode = game_config.get_setting("traditional_mode", False)
        if is_traditional_mode:
            # 传统象棋棋子价值表
            self.piece_values = {
                '將': 1000, '帥': 1000,  # 将/帅
                '士': 4, '仕': 4,        # 士/仕
                '象': 4, '相': 4,        # 象/相
                '馬': 8, '傌': 8,        # 马/傌
                '車': 18, '俥': 18,      # 車/俥
                '砲': 9, '炮': 9,        # 炮/砲
                '卒': 3, '兵': 3         # 卒/兵
            }
        else:
            # 匈汉象棋棋子价值表（包含更多种类的棋子）
            self.piece_values = {
                '汗': 1000, '漢': 1000,  # 将/帅 (King)
                '車': 18, '俥': 18,      # 車/俥 (Ju)
                '馬': 8, '傌': 8,        # 馬/傌 (Ma)
                '象': 4, '相': 4,        # 象/相 (Xiang)
                '士': 4, '仕': 4,        # 士/仕 (Shi)
                '砲': 9, '炮': 9,        # 炮/砲 (Pao)
                '卒': 3, '兵': 3,        # 卒/兵 (Pawn)
                '衛': 6, '尉': 6,        # 卫/尉 (Wei)
                '䠶': 5, '射': 5,        # 䠶/射 (She)
                '礌': 7, '檑': 7,        # 碌/檑 (Lei)
                '胄': 5, '甲': 5,        # 胄/甲 (Jia)
                '伺': 6, '刺': 6,        # 伺/刺 (Ci)
                '碷': 4, '楯': 4,        # 碷/楯 (Dun)
                '廵': 5, '巡': 5         # 廵/巡 (Xun)
            }
        
        # 根据难度设置搜索深度
        if difficulty == "easy":
            self.search_depth = 2
        elif difficulty == "medium":
            self.search_depth = 3
        else:  # hard
            self.search_depth = 4
    
    def get_best_move(self, game_state):
        """
        获取最佳移动
        :param game_state: 游戏状态对象
        :return: (棋子, 目标行, 目标列) 或 None
        """
        pieces = game_state.pieces
        current_player = game_state.player_turn
        
        # 根据算法类型选择不同的策略
        if self.algorithm == "minimax":
            return self._minimax_search(game_state, current_player)
        elif self.algorithm == "negamax":
            return self._negamax_search(game_state, current_player)
        elif self.algorithm == "alpha-beta":
            return self._alpha_beta_search(game_state, current_player)
        else:
            # 默认使用中等难度策略
            if self.difficulty == "easy":
                return self._get_random_move(pieces, current_player)
            elif self.difficulty == "medium":
                return self._get_medium_move(pieces, current_player)
            else:  # hard
                return self._get_hard_move(pieces, current_player)
    
    def get_move_async(self, game_state):
        """异步获取AI的最佳走法，启动多线程计算

        Args:
            game_state: GameState对象，表示当前棋盘状态
        """
        # 对于传统AI，直接返回同步结果
        return self.get_best_move(game_state)
    
    def is_computation_finished(self):
        """检查计算是否完成"""
        return True
    
    def get_computed_move(self):
        """获取计算完成的走法，如果计算未完成则返回当前最佳走法"""
        return None

    def _get_random_move(self, pieces, current_player):
        """随机移动策略"""
        # 获取所有可能的移动
        possible_moves = []
        for piece in pieces:
            if piece.color == current_player:
                moves, capturable = self._get_piece_possible_moves(pieces, piece, current_player)
                all_moves = moves + capturable
                for to_row, to_col in all_moves:
                    possible_moves.append((piece, to_row, to_col))
        
        if possible_moves:
            return random.choice(possible_moves)
        return None
    
    def _get_medium_move(self, pieces, current_player):
        """中等难度策略：优先吃子，其次保护自己，然后随机移动"""
        # 获取所有可能的移动
        possible_moves = []
        capture_moves = []  # 吃子移动
        normal_moves = []   # 普通移动
        
        for piece in pieces:
            if piece.color == current_player:
                moves, capturable = self._get_piece_possible_moves(pieces, piece, current_player)
                
                # 检查能否吃子
                for to_row, to_col in capturable:
                    target_piece = self._get_piece_at(pieces, to_row, to_col)
                    if target_piece:
                        capture_moves.append((piece, to_row, to_col, target_piece))
                
                # 普通移动
                for to_row, to_col in moves:
                    normal_moves.append((piece, to_row, to_col))
        
        # 优先选择吃子移动
        if capture_moves:
            # 按照被吃棋子的价值排序，优先吃价值高的棋子
            capture_moves.sort(key=lambda x: self.piece_values.get(x[3].name, 0), reverse=True)
            best_capture = capture_moves[0]
            return best_capture[0], best_capture[1], best_capture[2]
        
        # 如果没有吃子机会，选择普通移动
        if normal_moves:
            # 评估每个移动的价值
            evaluated_moves = []
            for piece, to_row, to_col in normal_moves:
                value = self._evaluate_move(pieces, piece, to_row, to_col, current_player)
                evaluated_moves.append((piece, to_row, to_col, value))
            
            # 选择价值最高的移动
            evaluated_moves.sort(key=lambda x: x[3], reverse=True)
            best_move = evaluated_moves[0]
            return best_move[0], best_move[1], best_move[2]
        
        return None
    
    def _get_hard_move(self, pieces, current_player):
        """高级策略：使用简单的评估函数"""
        # 这里可以实现更复杂的AI算法，比如minimax或alpha-beta剪枝
        # 为简化，我们使用改进的中等难度策略
        return self._get_medium_move(pieces, current_player)
    
    # Minimax算法实现
    def _minimax_search(self, game_state, current_player):
        """Minimax搜索算法"""
        _, best_move = self._minimax(game_state, self.search_depth, current_player == self.ai_color)
        return best_move
    
    def _minimax(self, game_state, depth, maximizing_player):
        """Minimax核心算法"""
        if depth == 0 or game_state.game_over:
            return self._evaluate_state(game_state), None
        
        best_move = None
        if maximizing_player:
            max_eval = float('-inf')
            moves = self._get_all_possible_moves(game_state, self.ai_color)
            for move in moves:
                # 执行移动
                original_pieces = self._copy_pieces(game_state.pieces)
                game_state.move_piece(move[0], move[1], move[2], move[3])
                
                eval_score, _ = self._minimax(game_state, depth - 1, False)
                
                # 撤销移动
                game_state.pieces = original_pieces
                game_state.update_pieces_positions(original_pieces)
                
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
            return max_eval, best_move
        else:
            min_eval = float('inf')
            opponent_color = "black" if self.ai_color == "red" else "red"
            moves = self._get_all_possible_moves(game_state, opponent_color)
            for move in moves:
                # 执行移动
                original_pieces = self._copy_pieces(game_state.pieces)
                game_state.move_piece(move[0], move[1], move[2], move[3])
                
                eval_score, _ = self._minimax(game_state, depth - 1, True)
                
                # 撤销移动
                game_state.pieces = original_pieces
                game_state.update_pieces_positions(original_pieces)
                
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
            return min_eval, best_move

    # Negamax算法实现
    def _negamax_search(self, game_state, current_player):
        """Negamax搜索算法"""
        _, best_move = self._negamax(game_state, self.search_depth, 1 if current_player == self.ai_color else -1)
        return best_move
    
    def _negamax(self, game_state, depth, color):
        """Negamax核心算法"""
        if depth == 0 or game_state.game_over:
            return color * self._evaluate_state(game_state), None
        
        best_move = None
        max_value = float('-inf')
        
        # 获取当前玩家的移动
        player_color = self.ai_color if color == 1 else ("black" if self.ai_color == "red" else "red")
        moves = self._get_all_possible_moves(game_state, player_color)
        
        for move in moves:
            # 执行移动
            original_pieces = self._copy_pieces(game_state.pieces)
            game_state.move_piece(move[0], move[1], move[2], move[3])
            
            value, _ = self._negamax(game_state, depth - 1, -color)
            value = -value  # Negamax的关键：翻转值
            
            # 撤销移动
            game_state.pieces = original_pieces
            game_state.update_pieces_positions(original_pieces)
            
            if value > max_value:
                max_value = value
                best_move = move
        
        return max_value, best_move

    # Alpha-Beta剪枝算法实现
    def _alpha_beta_search(self, game_state, current_player):
        """Alpha-Beta剪枝搜索算法"""
        _, best_move = self._alpha_beta(game_state, self.search_depth, float('-inf'), float('inf'), 
                                        current_player == self.ai_color)
        return best_move
    
    def _alpha_beta(self, game_state, depth, alpha, beta, maximizing_player):
        """Alpha-Beta剪枝核心算法"""
        if depth == 0 or game_state.game_over:
            return self._evaluate_state(game_state), None
        
        best_move = None
        if maximizing_player:
            max_eval = float('-inf')
            moves = self._get_all_possible_moves(game_state, self.ai_color)
            for move in moves:
                # 执行移动
                original_pieces = self._copy_pieces(game_state.pieces)
                game_state.move_piece(move[0], move[1], move[2], move[3])
                
                eval_score, _ = self._alpha_beta(game_state, depth - 1, alpha, beta, False)
                
                # 撤销移动
                game_state.pieces = original_pieces
                game_state.update_pieces_positions(original_pieces)
                
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                
                alpha = max(alpha, eval_score)
                if beta <= alpha:  # 剪枝
                    break
            return max_eval, best_move
        else:
            min_eval = float('inf')
            opponent_color = "black" if self.ai_color == "red" else "red"
            moves = self._get_all_possible_moves(game_state, opponent_color)
            for move in moves:
                # 执行移动
                original_pieces = self._copy_pieces(game_state.pieces)
                game_state.move_piece(move[0], move[1], move[2], move[3])
                
                eval_score, _ = self._alpha_beta(game_state, depth - 1, alpha, beta, True)
                
                # 撤销移动
                game_state.pieces = original_pieces
                game_state.update_pieces_positions(original_pieces)
                
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                
                beta = min(beta, eval_score)
                if beta <= alpha:  # 剪枝
                    break
            return min_eval, best_move

    def _get_all_possible_moves(self, game_state, player_color):
        """获取玩家的所有可能移动"""
        moves = []
        for piece in game_state.pieces:
            if piece.color == player_color:
                possible_moves, capturable = self._get_piece_possible_moves(game_state.pieces, piece, player_color)
                
                # 添加所有可能的移动
                for to_row, to_col in possible_moves + capturable:
                    moves.append((piece.row, piece.col, to_row, to_col))
        return moves
    
    def _evaluate_state(self, game_state):
        """评估游戏状态"""
        score = 0
        for piece in game_state.pieces:
            value = self.piece_values.get(piece.name, 0)
            piece_score = value
            
            if piece.color == self.ai_color:
                score += piece_score
            else:
                score -= piece_score
        return score

    def _copy_pieces(self, pieces):
        """复制棋子列表"""
        copied_pieces = []
        for piece in pieces:
            # 创建新棋子实例，保持相同的位置和属性
            import copy
            new_piece = copy.copy(piece)
            copied_pieces.append(new_piece)
        return copied_pieces

    def _get_piece_possible_moves(self, pieces, piece, current_player):
        """获取棋子的所有可能移动"""
        # 根据当前的游戏模式来确定使用哪种规则
        is_traditional_mode = game_config.get_setting("traditional_mode", False)
        
        # 临时保存当前的传统模式设置
        original_traditional_mode = game_config.get_setting("traditional_mode", False)
        # 设置为当前游戏模式以获取正确的移动规则
        game_config.set_setting("traditional_mode", is_traditional_mode)
        
        # 获取可能的移动
        moves, capturable = self.rules.calculate_possible_moves(piece.row, piece.col, pieces)
        
        # 恢复原始模式设置
        game_config.set_setting("traditional_mode", original_traditional_mode)
        
        return moves, capturable
    
    def _evaluate_move(self, pieces, piece, to_row, to_col, current_player):
        """评估移动的价值"""
        # 根据游戏模式选择不同的评估逻辑
        is_traditional_mode = game_config.get_setting("traditional_mode", False)
        
        value = 0
        
        # 基础位置价值：控制中心更有价值
        if is_traditional_mode:
            # 传统象棋评估：更注重防守和河界控制
            center_bonus = 0
            # 传统象棋中，接近河界和九宫格的位置更有价值
            if 4 <= to_row <= 5 and 3 <= to_col <= 5:  # 河界附近
                center_bonus = 3
            elif 3 <= to_row <= 6 and 2 <= to_col <= 6:  # 中心区域
                center_bonus = 2
            elif 2 <= to_row <= 7 and 1 <= to_col <= 7:  # 边缘中心
                center_bonus = 1
            value += center_bonus
        else:
            # 匈汉象棋评估：更大的棋盘，控制更广泛区域
            center_bonus = 0
            if 5 <= to_row <= 7 and 5 <= to_col <= 7:  # 接近中心
                center_bonus = 2
            elif 4 <= to_row <= 8 and 4 <= to_col <= 8:  # 中心附近
                center_bonus = 1
            value += center_bonus
        
        # 棋子安全性：避免被吃
        original_row, original_col = piece.row, piece.col
        piece.row, piece.col = to_row, to_col
        
        # 检查移动后是否会被吃
        if self._would_be_attacked(pieces, piece, current_player):
            value -= self.piece_values.get(piece.name, 1) * 0.5  # 避免损失
        
        # 恢复位置
        piece.row, piece.col = original_row, original_col
        
        # 检查是否能攻击对方棋子
        attacked_pieces = self._get_attacked_pieces(pieces, piece, to_row, to_col)
        for attacked_piece in attacked_pieces:
            value += self.piece_values.get(attacked_piece.name, 0) * 0.8  # 攻击奖励
        
        return value
    
    def _get_piece_at(self, pieces, row, col):
        """获取指定位置的棋子"""
        for piece in pieces:
            if piece.row == row and piece.col == col:
                return piece
        return None
    
    def _would_be_attacked(self, pieces, piece, current_player):
        """检查移动后棋子是否会被攻击"""
        enemy_color = "black" if current_player == "red" else "red"
        
        # 检查是否有敌方棋子能攻击到这个位置
        for enemy_piece in pieces:
            if enemy_piece.color == enemy_color:
                # 使用规则检查敌方棋子是否能攻击到这个位置
                # 根据当前模式获取正确的移动规则
                is_traditional_mode = game_config.get_setting("traditional_mode", False)
                
                # 临时保存当前的传统模式设置
                original_traditional_mode = game_config.get_setting("traditional_mode", False)
                # 设置为当前游戏模式以获取正确的移动规则
                game_config.set_setting("traditional_mode", is_traditional_mode)
                
                moves, capturable = self.rules.calculate_possible_moves(enemy_piece.row, enemy_piece.col, pieces)
                
                # 恢复原始模式设置
                game_config.set_setting("traditional_mode", original_traditional_mode)
                
                all_moves = moves + capturable
                for move_row, move_col in all_moves:
                    if move_row == piece.row and move_col == piece.col:
                        return True
        return False
    
    def _get_attacked_pieces(self, pieces, piece, to_row, to_col):
        """获取移动后能攻击的敌方棋子"""
        attacked = []
        enemy_color = "black" if piece.color == "red" else "red"
        
        # 检查这个位置是否能攻击敌方棋子
        for target_piece in pieces:
            if target_piece.color == enemy_color and target_piece.row == to_row and target_piece.col == to_col:
                attacked.append(target_piece)
        return attacked