"""传统象棋AI对手"""

import random

from program.core.game_rules import GameRules
from program.controllers.game_config_manager import game_config


class TraditionalAI:
    """传统象棋AI类"""
    
    def __init__(self, difficulty="medium"):
        """
        初始化AI
        :param difficulty: 难度级别 ("easy", "medium", "hard")
        """
        self.difficulty = difficulty
        self.rules = GameRules()
        # 棋子价值表，参考标准象棋评估
        self.piece_values = {
            '將': 1000, '帥': 1000,  # 将/帅
            '士': 4, '仕': 4,        # 士/仕
            '象': 4, '相': 4,        # 象/相
            '馬': 8, '傌': 8,        # 马/傌
            '車': 18, '俥': 18,      # 車/俥
            '砲': 9, '炮': 9,        # 炮/砲
            '卒': 3, '兵': 3         # 卒/兵
        }
        
    def get_best_move(self, pieces, current_player):
        """
        获取最佳移动
        :param pieces: 当前棋盘上的所有棋子
        :param current_player: 当前玩家颜色
        :return: (棋子, 目标行, 目标列) 或 None
        """
        # 根据难度选择不同的策略
        if self.difficulty == "easy":
            return self._get_random_move(pieces, current_player)
        elif self.difficulty == "medium":
            return self._get_medium_move(pieces, current_player)
        else:  # hard
            return self._get_hard_move(pieces, current_player)
    
    def _get_random_move(self, pieces, current_player):
        """随机移动策略"""
        # 获取所有可能的移动
        possible_moves = []
        for piece in pieces:
            if piece.color == current_player:
                moves, capturable = self._get_piece_possible_moves(pieces, piece)
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
                moves, capturable = self._get_piece_possible_moves(pieces, piece)
                
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
    
    def _get_piece_possible_moves(self, pieces, piece):
        """获取棋子的所有可能移动"""
        # 临时保存当前的传统模式设置
        original_traditional_mode = game_config.get_setting("traditional_mode", False)
        # 临时设置为传统模式以获取移动
        game_config.set_setting("traditional_mode", True)
        
        # 获取可能的移动
        moves, capturable = self.rules.calculate_possible_moves(pieces, piece)
        
        # 恢复原始模式设置
        game_config.set_setting("traditional_mode", original_traditional_mode)
        
        return moves, capturable
    
    def _get_piece_at(self, pieces, row, col):
        """获取指定位置的棋子"""
        for piece in pieces:
            if piece.row == row and piece.col == col:
                return piece
        return None
    
    def _evaluate_move(self, pieces, piece, to_row, to_col, current_player):
        """评估移动的价值"""
        value = 0
        
        # 基础位置价值：控制中心更有价值
        center_bonus = 0
        if 3 <= to_row <= 6 and 3 <= to_col <= 5:  # 接近中心
            center_bonus = 2
        elif 2 <= to_row <= 7 and 2 <= to_col <= 6:  # 中心附近
            center_bonus = 1
        value += center_bonus
        
        # 棋子安全性：避免被吃
        original_row, original_col = piece.row, piece.col
        piece.row, piece.col = to_row, to_col
        
        # 检查移动后是否会被吃
        if self._would_be_attacked(pieces, piece, current_player):
            value -= 5  # 避免被吃
        
        # 恢复位置
        piece.row, piece.col = original_row, original_col
        
        # 检查是否能攻击对方棋子
        attacked_pieces = self._get_attacked_pieces(pieces, piece, to_row, to_col)
        for attacked_piece in attacked_pieces:
            value += self.piece_values.get(attacked_piece.name, 0) * 0.1
        
        return value
    
    def _would_be_attacked(self, pieces, piece, current_player):
        """检查移动后棋子是否会被攻击"""
        enemy_color = "black" if current_player == "red" else "red"
        
        # 检查是否有敌方棋子能攻击到这个位置
        for enemy_piece in pieces:
            if enemy_piece.color == enemy_color:
                # 使用规则检查敌方棋子是否能攻击到这个位置
                moves, capturable = self._get_piece_possible_moves(pieces, enemy_piece)
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