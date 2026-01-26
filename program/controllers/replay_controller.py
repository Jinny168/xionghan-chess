"""
复盘控制器模块

此模块负责处理复盘相关的所有逻辑，包括进度控制、状态回溯等
"""

import copy


class ReplayController:
    """复盘控制器类，独立实现复盘功能"""
    
    def __init__(self, game_state):
        """初始化复盘控制器
        
        Args:
            game_state: 游戏状态对象
        """
        # 保留对游戏状态的直接引用
        self.game_state = game_state
        
        # 存储历史状态的列表
        self.history_states = []
        
        # 当前步骤索引
        self.current_step = 0
        
        # 最大步骤数
        self.max_steps = 0
        
        # 复盘模式标志
        self.is_replay_mode = False
        
        # 原始游戏状态（用于恢复）
        self.original_state = None
    
    @classmethod
    def enter_replay_mode(cls, game_state):
        """进入复盘模式的工厂方法
        
        Args:
            game_state: 游戏状态对象
            
        Returns:
            ReplayController: 复盘控制器实例
        """
        controller = cls(game_state)
        controller.start_replay()
        return controller
    
    def start_replay(self):
        """开始复盘模式"""
        # 保存原始游戏状态
        self.original_state = copy.deepcopy(self.game_state)
        
        # 如果游戏状态中已经有move_history，我们应该从初始状态逐步重建整个复盘历史
        # 创建一个临时游戏状态来从初始位置开始重现每一步
        temp_game_state = copy.deepcopy(self.game_state)
        
        # 重置临时状态的历史，以便从初始状态开始
        initial_pieces = temp_game_state.pieces[:]  # 保存当前棋子
        temp_game_state.pieces = []  # 清空棋子
        # 重新初始化初始棋子
        from program.core.chess_pieces import create_initial_pieces
        temp_game_state.pieces = create_initial_pieces()
        temp_game_state.player_turn = "red"  # 从红方开始
        temp_game_state.move_history = []  # 清空历史
        
        # 重建历史状态列表
        self.history_states = [copy.deepcopy(temp_game_state)]
        
        # 逐步执行历史中的每一步
        for move_record in self.game_state.move_history:
            # 执行移动
            if len(move_record) >= 8:  # 包含甲/胄吃子信息和刺兑子信息
                piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces, ci_captured_pieces = move_record
                temp_game_state.move_piece(from_row, from_col, to_row, to_col)
                # 由于move_piece会自动添加到历史，我们需要确保历史状态正确
                # 我们只需要继续执行下一步
            elif len(move_record) >= 7:  # 包含甲/胄吃子信息
                piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces = move_record
                temp_game_state.move_piece(from_row, from_col, to_row, to_col)
            else:  # 旧格式
                piece, from_row, from_col, to_row, to_col, captured_piece = move_record
                temp_game_state.move_piece(from_row, from_col, to_row, to_col)
            
            # 将执行完这步后的状态添加到历史
            self.history_states.append(copy.deepcopy(temp_game_state))
        
        # 如果没有历史记录，至少保存初始状态
        if not self.history_states:
            self.history_states = [copy.deepcopy(temp_game_state)]
        
        self.current_step = len(self.history_states) - 1  # 默认跳转到最后一步
        self.max_steps = len(self.history_states) - 1
        
        self.is_replay_mode = True
    
    def go_to_beginning(self):
        """跳转到开局"""
        if self.history_states:
            self.current_step = 0
            self._apply_state(self.history_states[self.current_step])
            return True
        return False
    
    def go_to_end(self):
        """跳转到终局"""
        if self.history_states:
            self.current_step = len(self.history_states) - 1
            self._apply_state(self.history_states[self.current_step])
            return True
        return False
    
    def go_to_previous(self):
        """上一步"""
        if self.current_step > 0:
            self.current_step -= 1
            self._apply_state(self.history_states[self.current_step])
            return True
        return False
    
    def go_to_next(self):
        """下一步"""
        if self.current_step < len(self.history_states) - 1:
            self.current_step += 1
            self._apply_state(self.history_states[self.current_step])
            return True
        return False
    
    def get_progress_percentage(self):
        """获取复盘进度百分比"""
        if not self.history_states:
            return 0
        if len(self.history_states) <= 1:
            return 100 if self.history_states else 0
        return int((self.current_step / (len(self.history_states) - 1)) * 100) if len(self.history_states) > 1 else 0
    
    def set_progress(self, percentage):
        """设置复盘进度"""
        if not self.history_states:
            return False
        
        # 根据百分比计算目标步骤
        target_step = int((percentage / 100.0) * (len(self.history_states) - 1))
        target_step = max(0, min(target_step, len(self.history_states) - 1))
        
        self.current_step = target_step
        self._apply_state(self.history_states[self.current_step])
        return True
    
    def jump_to_step(self, step):
        """跳转到指定步骤"""
        if 0 <= step < len(self.history_states):
            self.current_step = step
            self._apply_state(self.history_states[self.current_step])
            return True
        return False
    
    def restore_original_state(self):
        """恢复原始游戏状态"""
        if self.original_state:
            # 恢复原始状态
            self.game_state.__dict__ = copy.deepcopy(self.original_state.__dict__)
            self.is_replay_mode = False
            return True
        return False
    
    def _apply_state(self, state):
        """应用指定的状态到当前游戏状态"""
        if state:
            self.game_state.__dict__ = copy.deepcopy(state.__dict__)
    
    def add_current_state(self):
        """添加当前游戏状态到历史记录"""
        if self.is_replay_mode:
            # 截断当前步骤之后的历史
            self.history_states = self.history_states[:self.current_step + 1]
            # 添加新的状态
            self.history_states.append(copy.deepcopy(self.game_state))
            self.current_step = len(self.history_states) - 1
            self.max_steps = len(self.history_states) - 1


# 为了兼容旧代码，保留原始的导入方式
try:
    import pygame
except ImportError:
    # 如果pygame未导入，则在使用时再检查
    pygame = None