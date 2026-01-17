"""匈汉象棋统计数据展示对话框"""

import pygame
from program.config.statistics import statistics_manager
from program.utils.utils import load_font
from program.ui.button import Button


class StatisticsDialog:
    """统计数据展示对话框"""
    
    def __init__(self):
        # 字体
        self.title_font = load_font(24, bold=True)
        self.section_font = load_font(18, bold=True)
        self.normal_font = load_font(16)
        self.small_font = load_font(14)
        
        # 滚动相关
        self.scroll_y = 0
        self.max_scroll = 0
        self.dragging = False
        
        # 加载统计数据
        self.stats = statistics_manager.get_statistics()
        
        # 创建关闭按钮和重置按钮 - 位置会在draw方法中动态计算
        self.close_button = None
        self.reset_button = None
        
        # 字体
        self.title_font = load_font(24, bold=True)
        self.section_font = load_font(18, bold=True)
        self.normal_font = load_font(16)
        self.small_font = load_font(14)
        
        # 滚动相关
        self.scroll_y = 0
        self.max_scroll = 0
        self.dragging = False
        
        # 加载统计数据
        self.stats = statistics_manager.get_statistics()
    
    def handle_event(self, event, mouse_pos):
        """处理事件"""
        # 需要在绘制后才能获取到按钮实例，所以在这里动态检查按钮点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.close_button and self.close_button.is_clicked(mouse_pos, event):
                return "close"
            
            if self.reset_button and self.reset_button.is_clicked(mouse_pos, event):
                return "reset"
        
        return None
    
    def draw(self, screen):
        """绘制统计页面"""
        screen_width, screen_height = screen.get_size()
        
        # 绘制背景
        from program.utils.utils import draw_background
        draw_background(screen)
        
        # 绘制标题
        title_text = self.title_font.render("游戏统计数据", True, (0, 0, 0))
        title_rect = title_text.get_rect(center=(screen_width // 2, 60))
        screen.blit(title_text, title_rect)
        
        # 绘制装饰线
        pygame.draw.line(screen, (218, 165, 32), (screen_width//4, 100), (screen_width*3//4, 100), 3)
        
        # 获取统计数据
        stats = statistics_manager.get_statistics()
        
        # 设置滚动偏移
        y_pos = 130 - self.scroll_y
        line_height = 35  # 增加行高，让界面更舒适
        
        # 总体统计数据
        section_title = self.section_font.render("总体数据:", True, (0, 0, 0))
        screen.blit(section_title, (50, y_pos))
        y_pos += line_height + 10
        
        # 总游戏数
        games_played_text = self.normal_font.render(f"总游戏数: {stats['games_played']}", True, (0, 0, 0))
        screen.blit(games_played_text, (70, y_pos))
        y_pos += line_height
        
        # 各方胜利次数
        red_wins_text = self.normal_font.render(f"红方胜利: {stats['games_won']['red']}", True, (180, 30, 30))  # 红色
        black_wins_text = self.normal_font.render(f"黑方胜利: {stats['games_won']['black']}", True, (0, 0, 0))
        draw_text = self.normal_font.render(f"平局: {stats['games_won']['draw']}", True, (0, 0, 0))
        screen.blit(red_wins_text, (70, y_pos))
        screen.blit(black_wins_text, (250, y_pos))
        screen.blit(draw_text, (430, y_pos))
        y_pos += line_height
        
        # 总游戏时长
        total_time_hours = stats['total_time_played'] // 3600
        total_time_minutes = (stats['total_time_played'] % 3600) // 60
        total_time_text = self.normal_font.render(f"总游戏时长: {int(total_time_hours)}小时 {int(total_time_minutes)}分钟", True, (0, 0, 0))
        screen.blit(total_time_text, (70, y_pos))
        y_pos += line_height + 15
        
        # 胜率
        if stats['games_played'] > 0:
            red_win_rate = (stats['games_won']['red'] / stats['games_played']) * 100
            black_win_rate = (stats['games_won']['black'] / stats['games_played']) * 100
            draw_rate = (stats['games_won']['draw'] / stats['games_played']) * 100
        else:
            red_win_rate = black_win_rate = draw_rate = 0
            
        win_rate_text = self.normal_font.render(f"胜率 - 红方: {red_win_rate:.1f}% | 黑方: {black_win_rate:.1f}% | 平局: {draw_rate:.1f}%", True, (0, 0, 0))
        screen.blit(win_rate_text, (70, y_pos))
        y_pos += line_height + 15
        
        # 被吃棋子统计
        section_title = self.section_font.render("被吃棋子统计:", True, (0, 0, 0))
        screen.blit(section_title, (50, y_pos))
        y_pos += line_height + 10
        
        # 棋子类型映射
        piece_names = {
            'ju': '車',
            'ma': '馬', 
            'xiang': '相/象',
            'shi': '士/仕',
            'king': '将/帅',
            'pao': '炮/砲',
            'pawn': '兵/卒',
            'wei': '尉/衛',
            'she': '射/䠶',
            'lei': '檑/礌',
            'jia': '甲/胄',
            'ci': '刺',
            'dun': '盾',
            'xun': '巡/廵'
        }
        
        # 分两列显示棋子统计
        captured_stats = stats['pieces_captured']
        items = list(captured_stats.items())
        half = len(items) // 2 + len(items) % 2
        
        for i, (piece_type, count) in enumerate(items):
            piece_name = piece_names.get(piece_type, piece_type)
            text = self.normal_font.render(f"{piece_name}: {count}", True, (0, 0, 0))
            
            if i < half:
                # 第一列
                screen.blit(text, (70, y_pos + i * line_height))
            else:
                # 第二列
                screen.blit(text, (screen_width // 2 + 50, y_pos + (i - half) * line_height))
        
        # 计算最后一行的位置
        last_row = max(half, len(items) - half)
        y_pos += last_row * line_height + 20
        
        # 最快胜利记录
        section_title = self.section_font.render("最快胜利记录:", True, (0, 0, 0))
        screen.blit(section_title, (50, y_pos))
        y_pos += line_height + 10
        
        fastest_red = stats['fastest_win']['red']
        fastest_black = stats['fastest_win']['black']
        
        if fastest_red != float('inf'):
            fastest_red_text = self.normal_font.render(f"红方最快胜利: {fastest_red:.1f}秒 ({int(fastest_red//60)}:{int(fastest_red%60):02d})", True, (180, 30, 30))  # 红色
        else:
            fastest_red_text = self.normal_font.render("红方最快胜利: 无", True, (180, 30, 30))  # 红色
        
        if fastest_black != float('inf'):
            fastest_black_text = self.normal_font.render(f"黑方最快胜利: {fastest_black:.1f}秒 ({int(fastest_black//60)}:{int(fastest_black%60):02d})", True, (0, 0, 0))
        else:
            fastest_black_text = self.normal_font.render("黑方最快胜利: 无", True, (0, 0, 0))
        
        screen.blit(fastest_red_text, (70, y_pos))
        y_pos += line_height
        screen.blit(fastest_black_text, (70, y_pos))
        y_pos += line_height + 15
        
        # 最长游戏记录
        longest_game = stats['longest_game']
        longest_game_text = self.normal_font.render(f"最长单局时长: {longest_game:.1f}秒 ({int(longest_game//60)}:{int(longest_game%60):02d})", True, (0, 0, 0))
        screen.blit(longest_game_text, (70, y_pos))
        y_pos += line_height + 15
        
        # 连胜记录
        section_title = self.section_font.render("连胜记录:", True, (0, 0, 0))
        screen.blit(section_title, (50, y_pos))
        y_pos += line_height + 10
        
        red_streak = stats['win_streak']['red']
        black_streak = stats['win_streak']['black']
        current_red_streak = stats['win_streak']['current_streak']['red']
        current_black_streak = stats['win_streak']['current_streak']['black']
        
        red_streak_text = self.normal_font.render(f"红方最高连胜: {red_streak} | 当前连胜: {current_red_streak}", True, (180, 30, 30))  # 红色
        black_streak_text = self.normal_font.render(f"黑方最高连胜: {black_streak} | 当前连胜: {current_black_streak}", True, (0, 0, 0))
        
        screen.blit(red_streak_text, (70, y_pos))
        y_pos += line_height
        screen.blit(black_streak_text, (70, y_pos))
        y_pos += line_height + 15
        
        # 总走子数
        moves_text = self.normal_font.render(f"总走子数: {stats['total_moves_made']}", True, (0, 0, 0))
        screen.blit(moves_text, (70, y_pos))
        y_pos += line_height + 15
        
        # 动态创建按钮（每次绘制时都重新创建，以适应当前屏幕尺寸）
        button_width, button_height = 100, 40
        margin = 20
        
        # 关闭按钮（右上角）
        self.close_button = Button(
            screen_width - button_width - margin,
            margin,
            button_width,
            button_height,
            "返回",
            18
        )
        
        # 重置按钮（右下角）
        self.reset_button = Button(
            screen_width - button_width - margin,
            screen_height - button_height - margin,
            button_width,
            button_height,
            "重置",
            18
        )
        
        # 绘制按钮
        self.close_button.draw(screen)
        self.reset_button.draw(screen)