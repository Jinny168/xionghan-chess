"""将军/绝杀提示管理器
专门负责所有将军/绝杀字样的显示、隐藏、坐标更新逻辑
"""


import pygame
import math
from program.utils.utils import load_font


class CheckCheckmateTipManager:
    """将军/绝杀提示管理器类，专门负责处理将军/绝杀提示文字的显示逻辑"""
    
    def __init__(self):
        """初始化将军/绝杀提示管理器"""
        # 缓存表面以提高性能
        self.animation_surfaces = {}
        # 当前显示的提示信息
        self.current_tip_info = None
        # 上一次更新的时间
        self.last_update_time = 0
        
    def update_tip_position(self, game_state):
        """根据游戏状态更新提示位置信息
        
        Args:
            game_state: 游戏状态对象
        """
        # 检查是否应该显示将军/绝杀提示
        if game_state.should_show_check_animation():
            king_pos = game_state.get_checked_king_position()
            if king_pos:
                # 更新提示信息：位置、是否绝杀
                self.current_tip_info = {
                    'position': king_pos,
                    'is_checkmate': game_state.is_checkmate(),
                    'show': True
                }
            else:
                self.current_tip_info = None
        else:
            self.current_tip_info = None
    
    def draw_tip(self, screen, game_state, board):
        """在屏幕上绘制将军/绝杀提示
        
        Args:
            screen: pygame屏幕对象
            game_state: 游戏状态对象
            board: 棋盘对象
        """
        # 更新提示位置信息
        self.update_tip_position(game_state)
        
        # 如果没有提示信息，直接返回
        if not self.current_tip_info or not self.current_tip_info.get('show', False):
            return
            
        king_pos = self.current_tip_info['position']
        is_checkmate = self.current_tip_info['is_checkmate']
        
        # 获取王在屏幕上的坐标
        x, y = board.get_position_center(king_pos[0], king_pos[1])
        
        # 获取当前时间用于动画效果
        ticks = pygame.time.get_ticks()
        
        # 创建脉动效果 - 使用正弦函数产生0到1之间的值
        pulse = (math.sin(ticks * 0.015) + 1) * 0.5  # 0.0 到 1.0 之间变化，频率提高
        
        # 计算动态大小和透明度
        base_size = board.grid_size * 1.0  # 基础大小
        size_variation = board.grid_size * 0.3  # 大小变化范围
        current_size = base_size + size_variation * pulse
        
        # 透明度在220-255之间变化，更不透明
        alpha = int(220 + 35 * pulse)
        
        # 绘制脉动效果的圆圈
        self._draw_pulse_effect(screen, x, y, current_size, alpha)
        
        # 绘制"将军"/"绝杀"文字提示
        self._draw_tip_text(screen, x, y, is_checkmate, pulse, board.grid_size)
    
    @staticmethod
    def _draw_pulse_effect(screen, x, y, current_size, alpha):
        """绘制脉动效果的圆圈
        
        Args:
            screen: pygame屏幕对象
            x, y: 中心坐标
            current_size: 当前大小
            alpha: 透明度
        """
        # 计算表面大小
        total_size = int(current_size * 1.1 * 2)
        glow_surface = pygame.Surface((total_size, total_size), pygame.SRCALPHA)
        
        # 创建多层渐变效果
        for i in range(3):  # 创建3层效果
            layer_size = current_size * (1 - i * 0.2)  # 每层递减尺寸
            layer_alpha = alpha * (1 - i * 0.2)  # 每层递减透明度
            
            # 使用更鲜艳的红色
            red_color = (255, 20 + i * 20, 20, int(layer_alpha))
            
            # 绘制一个渐变的红色圆形
            pygame.draw.circle(
                glow_surface, 
                red_color, 
                (total_size // 2, total_size // 2), 
                int(layer_size)
            )
        
        # 绘制到屏幕上
        surface_size = glow_surface.get_width()
        screen.blit(glow_surface, (x - surface_size // 2, y - surface_size // 2))
        
        # 绘制边框
        border_size = current_size * 1.1  # 边框略大于内圆
        border_surface = pygame.Surface((int(border_size * 2), int(border_size * 2)), pygame.SRCALPHA)
        border_color = (255, 100, 100, alpha)
        # 只画边框
        pygame.draw.circle(
            border_surface, 
            border_color, 
            (int(border_size), int(border_size)), 
            int(border_size), 
            3
        )
        
        # 绘制到屏幕上
        border_size_cached = border_surface.get_width() // 2
        screen.blit(border_surface, (x - border_size_cached, y - border_size_cached))
    
    @staticmethod
    def _draw_tip_text(screen, x, y, is_checkmate, pulse, grid_size):
        """绘制将军/绝杀文字提示
        
        Args:
            screen: pygame屏幕对象
            x, y: 中心坐标
            is_checkmate: 是否为绝杀
            pulse: 脉动值 (0-1)
            grid_size: 棋盘格子大小
        """
        # 获取字体
        font = load_font(40, bold=True)
        
        # 根据是否为绝杀决定显示文字
        text = "绝杀!" if is_checkmate else "将军!"
        
        # 闪烁的文字颜色
        rendered_text = font.render(text, True, (255, 50, 50))
        
        # 文字位置 - 在棋子上方，稍稍上移
        text_pos = (x, y - grid_size * 1.5)  # 进一步上移文字
        text_rect = rendered_text.get_rect(center=text_pos)
        
        # 增大背景框，使文字更突出
        padding = 15  # 增大内边距
        bg_rect = pygame.Rect(
            text_rect.left - padding,
            text_rect.top - padding,
            text_rect.width + padding * 2,
            text_rect.height + padding * 2
        )
        
        # 加入闪烁效果背景
        bg_alpha = int(150 + 50 * pulse)  # 背景透明度
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, bg_alpha))  # 更深的半透明黑色背景
        screen.blit(bg_surface, (bg_rect.left, bg_rect.top))
        
        # 绘制文字边框，使文字更突出
        outline_rect = pygame.Rect(
            text_rect.left - 2,
            text_rect.top - 2,
            text_rect.width + 4,
            text_rect.height + 4
        )
        outline_surface = pygame.Surface((outline_rect.width, outline_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(
            outline_surface, 
            (255, 255, 255), 
            (0, 0, outline_rect.width, outline_rect.height), 
            2
        )
        screen.blit(outline_surface, (outline_rect.left, outline_rect.top))
        
        # 绘制文字
        screen.blit(rendered_text, text_rect)
    
    def hide_tip(self):
        """隐藏提示"""
        self.current_tip_info = None