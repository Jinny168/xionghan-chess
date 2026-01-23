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
    
    def start_replay(self):
        """开始复盘模式"""
        # 保存原始游戏状态
        self.original_state = copy.deepcopy(self.game_state)
        
        # 从当前状态开始构建历史记录
        self.history_states = [copy.deepcopy(self.game_state)]
        self.current_step = 0
        self.max_steps = 0
        
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
