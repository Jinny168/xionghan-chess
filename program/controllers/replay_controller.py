"""
复盘控制器模块

此模块负责处理复盘相关的所有逻辑，包括进度控制、状态回溯等
"""
from program.utils.tools import ReplayController as BaseReplayController


class ReplayController:
    """复盘控制器类，继承自工具模块中的基础复盘控制器"""
    
    def __init__(self, game_state):
        """初始化复盘控制器
        
        Args:
            game_state: 游戏状态对象
        """
        # 使用工具模块中的基础复盘控制器
        self.base_controller = BaseReplayController(game_state)
        
        # 保留对游戏状态的直接引用
        self.game_state = game_state
        
        # 复盘模式标志
        self.is_replay_mode = False
    
    def start_replay(self):
        """开始复盘模式"""
        self.base_controller.start_replay()
        self.is_replay_mode = True
    
    def go_to_beginning(self):
        """跳转到开局"""
        return self.base_controller.go_to_beginning()
    
    def go_to_end(self):
        """跳转到终局"""
        return self.base_controller.go_to_end()
    
    def go_to_previous(self):
        """上一步"""
        return self.base_controller.go_to_previous()
    
    def go_to_next(self):
        """下一步"""
        return self.base_controller.go_to_next()
    
    def get_progress_percentage(self):
        """获取复盘进度百分比"""
        return self.base_controller.get_progress_percentage()
    
    def set_progress(self, percentage):
        """设置复盘进度"""
        return self.base_controller.set_progress(percentage)
    
    def jump_to_step(self, step):
        """跳转到指定步骤"""
        return self.base_controller.jump_to_step(step)
    
    def restore_original_state(self):
        """恢复原始游戏状态"""
        return self.base_controller.restore_original_state()
    
    @property
    def current_step(self):
        """当前复盘步骤"""
        return self.base_controller.current_step
    
    @property
    def max_steps(self):
        """最大步骤数"""
        return self.base_controller.max_steps
    
    def handle_replay_event(self, event, mouse_pos, buttons):
        """处理复盘相关的事件
        
        Args:
            event: pygame事件
            mouse_pos: 鼠标位置
            buttons: 按钮字典，包含'beginning', 'previous', 'next', 'end', 'return'等键
            
        Returns:
            str: 事件处理结果，可能是'action_performed', 'exit_replay', 'none'
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # 左键点击
            # 检查各个按钮是否被点击
            if 'beginning' in buttons and buttons['beginning'].is_clicked(mouse_pos, event):
                self.go_to_beginning()
                return 'action_performed'
            
            elif 'previous' in buttons and buttons['previous'].is_clicked(mouse_pos, event):
                self.go_to_previous()
                return 'action_performed'
            
            elif 'next' in buttons and buttons['next'].is_clicked(mouse_pos, event):
                self.go_to_next()
                return 'action_performed'
            
            elif 'end' in buttons and buttons['end'].is_clicked(mouse_pos, event):
                self.go_to_end()
                return 'action_performed'
            
            elif 'return' in buttons and buttons['return'].is_clicked(mouse_pos, event):
                return 'exit_replay'  # 特殊返回值表示退出复盘
            
            # 检查进度条点击
            elif self._is_progress_bar_clicked(mouse_pos, buttons.get('progress_bar_coords')):
                self._handle_progress_bar_click(mouse_pos, buttons.get('progress_bar_coords'))
                return 'action_performed'
        
        # 处理进度条拖拽
        elif event.type == pygame.MOUSEMOTION and hasattr(self, '_dragging_progress') and self._dragging_progress:
            if self._is_mouse_in_progress_area(mouse_pos, buttons.get('progress_bar_coords')):
                self._handle_progress_bar_drag(mouse_pos, buttons.get('progress_bar_coords'))
                return 'action_performed'
        
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # 停止拖拽
            if hasattr(self, '_dragging_progress'):
                self._dragging_progress = False
        
        return 'none'
    
    def _is_progress_bar_clicked(self, mouse_pos, coords):
        """检查是否点击了进度条"""
        if not coords:
            return False
        
        x, y, width, height = coords
        mx, my = mouse_pos
        return x <= mx <= x + width and y <= my <= y + height
    
    def _is_mouse_in_progress_area(self, mouse_pos, coords):
        """检查鼠标是否在进度条区域内"""
        if not coords:
            return False
        
        x, y, width, height = coords
        mx, my = mouse_pos
        return x <= mx <= x + width and y <= my <= y + height
    
    def _handle_progress_bar_click(self, mouse_pos, coords):
        """处理进度条点击"""
        if not coords:
            return
        
        x, y, width, _ = coords
        mx, _ = mouse_pos
        
        # 计算点击位置对应的进度百分比
        click_percentage = max(0, min(100, 
            int(((mx - x) / width) * 100)))
        self.set_progress(click_percentage)
        
        # 开始拖拽模式
        self._dragging_progress = True
    
    def _handle_progress_bar_drag(self, mouse_pos, coords):
        """处理进度条拖拽"""
        if not coords:
            return
        
        x, _, width, _ = coords
        mx, _ = mouse_pos
        
        # 计算拖拽位置对应的进度百分比
        drag_percentage = max(0, min(100,
            int(((mx - x) / width) * 100)))
        self.set_progress(drag_percentage)


# 为了兼容旧代码，保留原始的导入方式
try:
    import pygame
except ImportError:
    # 如果pygame未导入，则在使用时再检查
    pygame = None