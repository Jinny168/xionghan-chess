import math

import pygame

from program.utils.utils import load_font
from program.controllers.game_config_manager import get_piece_color, get_piece_text_color, theme_manager, THEME_CONFIG


class ChessBoard:
    def __init__(self, window_width, window_height, margin_left, margin_top):
        """初始化棋盘
        
        Args:
            window_width (int): 棋盘区域宽度
            window_height (int): 窗口高度
            margin_left (int): 左侧边距
            margin_top (int): 顶部边距
        """
        self.label_font = None
        self.label_font_size = None
        self.chess_font = None
        self.window_width = window_width
        self.window_height = window_height
        self.margin_left = margin_left
        self.margin_top = margin_top
        
        # 棋盘尺寸和格子大小 - 改为13x13
        self.board_width = window_width - 2 * 50  # 保持左右各留50px的边距
        self.board_height = self.board_width  # 13x13比例，正方形
        self.grid_size = self.board_width / 12
        
        # 确保棋盘高度不超过窗口高度
        max_height = window_height - margin_top - 100  # 保留底部至少100px空间
        if self.board_height > max_height:
            self.board_height = max_height
            self.board_width = self.board_height
            self.grid_size = self.board_width / 12
        
        # 高亮位置
        self.highlighted = None
        
        # 可能的落点
        self.possible_moves = []
        
        # 可吃棋子的位置
        self.capturable_positions = []
        
        # 加载飘逸字体 - 尝试加载几种可能的字体
        self.update_font()
        
        # 预创建用于绘制将军动画的表面
        self.check_animation_surfaces = {}
        
    def update_font(self):
        """根据当前棋盘尺寸更新字体"""
        font_size = int(self.grid_size * 0.5)
        
        # 使用统一的字体加载函数
        self.chess_font = load_font(font_size, bold=True)
        
    def draw(self, screen, pieces, game_state=None):
        """绘制棋盘和棋子"""
        # 获取当前主题
        current_theme = theme_manager.get_current_theme()
        theme_colors = theme_manager.get_theme_colors()
        
        # 绘制棋盘背景
        board_rect = pygame.Rect(
            self.margin_left, 
            self.margin_top, 
            self.board_width, 
            self.board_height
        )
        # 使用主题配置的棋盘底色
        pygame.draw.rect(screen, theme_colors["board"]["base_color"], board_rect)
        
        # 添加木纹效果（使用细线条模拟木纹）
        for i in range(0, int(self.board_width), 4):
            pygame.draw.line(
                screen,
                (theme_colors["board"]["base_color"][0]-20, 
                 theme_colors["board"]["base_color"][1]-20, 
                 theme_colors["board"]["base_color"][2]-10),  # 稍暗的颜色作为木纹
                (self.margin_left + i, self.margin_top),
                (self.margin_left + i, self.margin_top + self.board_height),
                1
            )
        
        # 绘制棋盘外边框
        pygame.draw.rect(screen, theme_colors["board"]["line_color"], board_rect, 3)
        
        # 绘制棋盘线条 (13x13)
        for i in range(13):  # 横线，但在楚河汉界区域不绘制
            y = self.margin_top + i * self.grid_size
            # 不在楚河汉界线上绘制横线（第6行，索引为6）
            if i != 6:
                pygame.draw.line(
                    screen, 
                    theme_colors["board"]["line_color"], 
                    (self.margin_left, y), 
                    (self.margin_left + self.board_width, y), 
                    2
                )
        
        # 绘制竖线，但在长城阴山区域不绘制
        for i in range(13):  # 竖线
            x = self.margin_left + i * self.grid_size
            # 上半部分（0-5行）
            pygame.draw.line(
                screen,
                theme_colors["board"]["line_color"],
                (x, self.margin_top),
                (x, self.margin_top + 5 * self.grid_size),
                2
            )
            # 下半部分（7-12行）
            pygame.draw.line(
                screen,
                theme_colors["board"]["line_color"],
                (x, self.margin_top + 7 * self.grid_size),
                (x, self.margin_top + 12 * self.grid_size),
                2
            )

        # 绘制第6行的特殊点位标记
        separator_y = self.margin_top + 6 * self.grid_size
        for col in range(13):  # 包含所有列
            x = self.margin_left + col * self.grid_size
            # 绘制四个方向的短线 - 增大长度
            line_length = 8
            # 上
            pygame.draw.line(screen, theme_colors["board"]["line_color"], (x - line_length, separator_y), (x + line_length, separator_y), 2)
            # 下
            pygame.draw.line(screen, theme_colors["board"]["line_color"], (x - line_length, separator_y), (x + line_length, separator_y), 2)
            # 左 - 只有非第一列才绘制
            if col > 0:
                pygame.draw.line(screen, theme_colors["board"]["line_color"], (x, separator_y - line_length), (x, separator_y + line_length), 2)
            # 右 - 只有非最后一列才绘制
            if col < 12:
                pygame.draw.line(screen, theme_colors["board"]["line_color"], (x, separator_y - line_length), (x, separator_y + line_length), 2)

        # 绘制列标识
        self.draw_column_labels(screen)
        
        # 绘制九宫格斜线
        # 上方九宫 (1-3行, 5-7列)
        pygame.draw.line(
            screen,
            theme_colors["board"]["line_color"],
            (self.margin_left + 5 * self.grid_size, self.margin_top + 1 * self.grid_size),
            (self.margin_left + 7 * self.grid_size, self.margin_top + 3 * self.grid_size),
            2
        )
        pygame.draw.line(
            screen,
            theme_colors["board"]["line_color"],
            (self.margin_left + 7 * self.grid_size, self.margin_top + 1 * self.grid_size),
            (self.margin_left + 5 * self.grid_size, self.margin_top + 3 * self.grid_size),
            2
        )
        
        # 下方九宫 (9-11行, 5-7列)
        pygame.draw.line(
            screen,
            theme_colors["board"]["line_color"],
            (self.margin_left + 5 * self.grid_size, self.margin_top + 9 * self.grid_size),
            (self.margin_left + 7 * self.grid_size, self.margin_top + 11 * self.grid_size),
            2
        )
        pygame.draw.line(
            screen,
            theme_colors["board"]["line_color"],
            (self.margin_left + 7 * self.grid_size, self.margin_top + 9 * self.grid_size),
            (self.margin_left + 5 * self.grid_size, self.margin_top + 11 * self.grid_size),
            2
        )
        

        # 绘制"长城阴山"
        font = load_font(36)
        chu_text = font.render("长 城", True, theme_colors["board"]["line_color"])
        han_text = font.render("阴 山", True, theme_colors["board"]["line_color"])
        
        # 绘制分隔线（只在两端绘制短线）
        separator_y = self.margin_top + 6 * self.grid_size


        # 绘制文字
        chu_rect = chu_text.get_rect(center=(self.margin_left + self.board_width/4, separator_y))
        han_rect = han_text.get_rect(center=(self.margin_left + 3*self.board_width/4, separator_y))
        screen.blit(chu_text, chu_rect)
        screen.blit(han_text, han_rect)
        
        # 绘制兵、炮位置标记
        # 根据当前棋子布局，标记兵和炮的初始位置
        positions = [
            # 黑方兵位置 (第4行)
            (4, 0), (4, 2), (4, 4), (4, 6), (4, 8), (4, 10), (4, 12),
            # 黑方炮位置 (第3行)
            (3, 1), (3, 11),
            # 红方兵位置 (第8行)
            (8, 0), (8, 2), (8, 4), (8, 6), (8, 8), (8, 10), (8, 12),
            # 红方炮位置 (第9行)
            (9, 1), (9, 11)
        ]
        
        for row, col in positions:
            x = self.margin_left + col * self.grid_size
            y = self.margin_top + row * self.grid_size
            self.draw_position_mark(screen, x, y)
        
        # 绘制可能的落点
        for row, col in self.possible_moves:
            # 如果这个位置不在可吃子位置列表中，才画绿点
            if (row, col) not in self.capturable_positions:
                x = self.margin_left + col * self.grid_size
                y = self.margin_top + row * self.grid_size
                pygame.draw.circle(
                    screen,
                    (50, 205, 50, 180),  # 绿色半透明
                    (x, y),
                    self.grid_size * 0.2,
                    0  # 填充圆形
                )
        
        # 绘制所有棋子
        for piece in pieces:
            self.draw_piece(screen, piece, current_theme)
            
        # 绘制可以吃子的位置（画红叉）- 移到棋子绘制之后，这样叉会显示在棋子上面
        for row, col in self.capturable_positions:
            x = self.margin_left + col * self.grid_size
            y = self.margin_top + row * self.grid_size
            
            # 绘制红叉
            cross_size = self.grid_size * 0.35  # 保持增大的红叉尺寸
            line_width = 4  # 保持增加的线宽
            red_color = (255, 0, 0)  # 亮红色
            
            # 绘制叉的两条线
            pygame.draw.line(
                screen, 
                red_color, 
                (x - cross_size, y - cross_size), 
                (x + cross_size, y + cross_size), 
                line_width
            )
            pygame.draw.line(
                screen, 
                red_color, 
                (x + cross_size, y - cross_size), 
                (x - cross_size, y + cross_size), 
                line_width
            )
        
        # 绘制兵/卒复活的小星星标记
        if game_state:
            self.draw_pawn_resurrection_stars(screen, game_state)
        
        # 绘制高亮位置
        if self.highlighted:
            row, col = self.highlighted
            x = self.margin_left + col * self.grid_size
            y = self.margin_top + row * self.grid_size
            pygame.draw.circle(
                screen,
                (255, 255, 0, 128),  # 黄色高亮
                (x, y),
                self.grid_size * 0.4,
                3
            )
    
    def draw_piece(self, screen, piece, current_theme):
        """绘制美化后的棋子，使用白玉渐变效果，并应用主题配色"""
        # 计算棋子中心位置
        center_x = self.margin_left + piece.col * self.grid_size
        center_y = self.margin_top + piece.row * self.grid_size
        
        # 棋子大小为格子的85%
        radius = int(self.grid_size * 0.42)
        
        # 确保radius为正数，避免Surface创建错误
        if radius <= 0:
            return  # 如果半径无效，直接返回，不绘制棋子
        
        # 绘制棋子底部阴影
        shadow_offset = 3
        shadow_radius = radius + 1
        # 确保shadow_radius为正数，避免Surface创建错误
        if shadow_radius > 0:
            # 使用缓存的阴影表面
            shadow_cache_key = shadow_radius
            if shadow_cache_key not in self.check_animation_surfaces:
                shadow_surface = pygame.Surface((shadow_radius*2, shadow_radius*2), pygame.SRCALPHA)
                pygame.draw.circle(shadow_surface, (20, 20, 20, 100), 
                                  (shadow_radius, shadow_radius), 
                                  shadow_radius)
                self.check_animation_surfaces[shadow_cache_key] = shadow_surface
            
            screen.blit(self.check_animation_surfaces[shadow_cache_key], 
                       (center_x - shadow_radius + shadow_offset, 
                        center_y - shadow_radius + shadow_offset))
        
        # 白玉颜色方案 - 两种棋子都使用相同的白玉颜色
        outer_color = (230, 230, 220)        # 外环略带米黄的白色
        inner_color = (255, 255, 250)        # 内部纯白微泛光
        highlight_color = (255, 255, 255)    # 高光点纯白
        edge_color = (180, 180, 170)         # 边缘颜色微灰
        
        # 根据棋子颜色确定阵营（side）
        side = "light_side" if piece.color == "black" else "dark_side"
        
        # 获取棋子配色 - 使用新的配色函数
        piece_color = get_piece_color(piece.name, current_theme, side)
        text_color = get_piece_text_color(current_theme, side)
        text_shadow_color = THEME_CONFIG[current_theme]["pieces"]["text_border"]  # 使用主题配置的描边色
        
        # 使用缓存的棋子表面
        piece_cache_key = (piece.color, piece.name, radius, current_theme)
        if piece_cache_key not in self.check_animation_surfaces:
            # 绘制主体
            piece_surface = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            
            # 创建白玉渐变效果 - 从外到内
            gradient_steps = 15  # 更细腻渐变
            for i in range(gradient_steps, 0, -1):
                current_radius = int(radius * (i / gradient_steps))
                # 计算当前渐变颜色
                ratio = i / gradient_steps
                # 使用棋子的配色进行渐变，从外部较暗到内部较亮
                r = int(piece_color[0] * ratio + min(255, piece_color[0] + 30) * (1-ratio))
                g = int(piece_color[1] * ratio + min(255, piece_color[1] + 30) * (1-ratio))
                b = int(piece_color[2] * ratio + min(255, piece_color[2] + 30) * (1-ratio))
                
                pygame.draw.circle(piece_surface, (r, g, b), (radius, radius), current_radius)
            
            # 绘制边缘 - 稍微更薄一些的边框
            pygame.draw.circle(piece_surface, edge_color, (radius, radius), radius, 1)
            
            # 添加多重高光效果 - 更真实的玉质感
            
            # 主高光点 - 左上方
            highlight_pos1 = (radius - int(radius*0.5), radius - int(radius*0.5))
            highlight_radius1 = int(radius * 0.2)
            for i in range(5):
                h_radius = highlight_radius1 - i
                if h_radius <= 0:
                    continue
                alpha = 180 - i * 35
                pygame.draw.circle(piece_surface, (*highlight_color, alpha), 
                                 highlight_pos1, h_radius)
            
            # 次高光点 - 右下方较弱
            highlight_pos2 = (radius + int(radius*0.3), radius + int(radius*0.3))
            highlight_radius2 = int(radius * 0.1)
            for i in range(3):
                h_radius = highlight_radius2 - i
                if h_radius <= 0:
                    continue
                alpha = 100 - i * 30
                pygame.draw.circle(piece_surface, (*highlight_color, alpha), 
                                 highlight_pos2, h_radius)
            
            self.check_animation_surfaces[piece_cache_key] = piece_surface
        
        # 从缓存中获取棋子表面
        cached_piece_surface = self.check_animation_surfaces[piece_cache_key]
        # 将棋子表面绘制到屏幕上
        screen.blit(cached_piece_surface, (center_x - radius, center_y - radius))
        
        # 绘制棋子文字 - 使用飘逸字体
        text = self.chess_font.render(piece.name, True, text_color)
        
        # 添加文字阴影，提高可读性
        shadow_offset = 1
        text_shadow = self.chess_font.render(piece.name, True, text_shadow_color)
        text_shadow_rect = text_shadow.get_rect(center=(center_x + shadow_offset, center_y + shadow_offset))
        screen.blit(text_shadow, text_shadow_rect)
        
        # 绘制主文字
        text_rect = text.get_rect(center=(center_x, center_y))
        screen.blit(text, text_rect)
    
    def draw_position_mark(self, screen, x, y):
        """绘制位置标记（兵、炮位置）"""
        # 标记大小参数
        offset = int(self.grid_size * 0.15)
        line_length = int(self.grid_size * 0.25)
        
        # 绘制四个角的标记
        # 左上
        pygame.draw.line(screen, (0, 0, 0), (x - offset, y - offset), (x - offset, y - offset - line_length), 2)
        pygame.draw.line(screen, (0, 0, 0), (x - offset, y - offset), (x - offset - line_length, y - offset), 2)
        
        # 右上
        pygame.draw.line(screen, (0, 0, 0), (x + offset, y - offset), (x + offset, y - offset - line_length), 2)
        pygame.draw.line(screen, (0, 0, 0), (x + offset, y - offset), (x + offset + line_length, y - offset), 2)
        
        # 左下
        pygame.draw.line(screen, (0, 0, 0), (x - offset, y + offset), (x - offset, y + offset + line_length), 2)
        pygame.draw.line(screen, (0, 0, 0), (x - offset, y + offset), (x - offset - line_length, y + offset), 2)
        
        # 右下
        pygame.draw.line(screen, (0, 0, 0), (x + offset, y + offset), (x + offset, y + offset + line_length), 2)
        pygame.draw.line(screen, (0, 0, 0), (x + offset, y + offset), (x + offset + line_length, y + offset), 2)
    
    def draw_pawn_resurrection_stars(self, screen, game_state):
        """绘制兵/卒复活的小星星标记"""
        # 从game_state获取预计算的复活位置
        resurrection_positions = game_state.get_resurrection_positions()
        
        # 绘制红方可复活位置的星星
        for row, col in resurrection_positions["red"]:
            x = self.margin_left + col * self.grid_size
            y = self.margin_top + row * self.grid_size
            self.draw_star_marker(screen, x, y, (255, 215, 0))  # 金色星星
        
        # 绘制黑方可复活位置的星星
        for row, col in resurrection_positions["black"]:
            x = self.margin_left + col * self.grid_size
            y = self.margin_top + row * self.grid_size
            self.draw_star_marker(screen, x, y, (255, 215, 0))  # 金色星星
    
    def draw_star_marker(self, screen, x, y, color):
        """绘制一个小星星标记"""
        # 计算星星的五个顶点
        star_size = self.grid_size * 0.2
        points = []
        for i in range(5):
            # 外圈顶点
            angle = math.pi/2 + i * 2*math.pi/5
            points.append((
                x + star_size * math.cos(angle),
                y - star_size * math.sin(angle)
            ))
            # 内圈顶点
            inner_angle = math.pi/2 + (i + 0.5) * 2*math.pi/5
            inner_size = star_size * 0.4
            points.append((
                x + inner_size * math.cos(inner_angle),
                y - inner_size * math.sin(inner_angle)
            ))
        
        # 绘制星星
        pygame.draw.polygon(screen, color, points)
        # 添加边框
        pygame.draw.polygon(screen, (0, 0, 0), points, 2)
    
    def get_grid_position(self, pos):
        """将屏幕坐标转换为棋盘格子坐标"""
        x, y = pos
        
        # 扩大检测范围，允许点击边缘区域也能识别
        expanded_margin = self.grid_size / 2  # 扩展半个格子的范围
        
        # 检查是否在扩大后的棋盘范围内
        if (x < self.margin_left - expanded_margin or x > self.margin_left + self.board_width + expanded_margin or
            y < self.margin_top - expanded_margin or y > self.margin_top + self.board_height + expanded_margin):
            return None
        
        # 转换为棋盘坐标
        col = round((x - self.margin_left) / self.grid_size)
        row = round((y - self.margin_top) / self.grid_size)
        
        # 确保坐标在有效范围内
        if 0 <= row <= 12 and 0 <= col <= 12:
            return row, col
        
        return None
    
    def highlight_position(self, row, col):
        """高亮显示选中的位置"""
        self.highlighted = (row, col)
    
    def clear_highlights(self):
        """清除高亮和可能的移动显示"""
        self.highlighted = None
        self.possible_moves = []
        self.capturable_positions = []
    
    def set_possible_moves(self, moves):
        """设置可能的移动位置"""
        self.possible_moves = moves
    
    def set_capturable_positions(self, positions):
        """设置可以吃子的位置"""
        self.capturable_positions = positions
    
    def highlight_last_move(self, screen, from_row, from_col, to_row, to_col):
        """高亮显示上一步的走法
        
        Args:
            screen: 屏幕surface
            from_row: 起点行
            from_col: 起点列
            to_row: 终点行
            to_col: 终点列
        """
        # 计算起点的像素坐标
        from_x, from_y = self.get_position_center(from_row, from_col)
        to_x, to_y = self.get_position_center(to_row, to_col)
        
        # 计算方格大小
        grid_size = self.board_width / 12
        
        # 绘制半透明的起点标记
        from_surface = pygame.Surface((grid_size, grid_size), pygame.SRCALPHA)
        from_surface.fill((0, 200, 80, 100))  # 绿色半透明
        screen.blit(from_surface, (from_x - grid_size/2, from_y - grid_size/2))
        
        # 绘制半透明的终点标记（更明显一些）
        to_surface = pygame.Surface((grid_size, grid_size), pygame.SRCALPHA)
        to_surface.fill((0, 200, 80, 150))  # 绿色半透明但更深
        screen.blit(to_surface, (to_x - grid_size/2, to_y - grid_size/2))
        
        # 绘制连接线
        pygame.draw.line(screen, (0, 180, 80, 200), (from_x, from_y), (to_x, to_y), 2) 

    def get_position_center(self, row, col):
        """获取格子中心的像素坐标
        
        Args:
            row: 行坐标
            col: 列坐标
            
        Returns:
            tuple: (x, y) 像素坐标
        """
        x = self.margin_left + col * self.grid_size
        y = self.margin_top + row * self.grid_size
        return x, y 

    def draw_column_labels(self, screen):
        """绘制列标识"""
        # 获取当前主题
        current_theme = theme_manager.get_current_theme()
        theme_colors = theme_manager.get_theme_colors()
        
        # 定义标识
        red_labels = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三"]
        black_labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
        
        # 设置字体大小
        label_font_size = int(self.grid_size * 0.4)  # 增大字体
        
        # 预先尝试加载字体，避免每次都重复加载
        if not hasattr(self, 'label_font') or self.label_font_size != label_font_size:
            fonts_to_try = [
                'fonts/simhei.ttf',
                'fonts/simkai.ttf',
                'fonts/fangsong.ttf',
                'fonts/xingkai.ttf',
                'fonts/msyh.ttc',
                'fonts/kaiti.ttf',
                'fonts/fangsong.ttf'
            ]
            label_font = None
            
            for font_path in fonts_to_try:
                try:
                    label_font = pygame.font.Font(font_path, label_font_size)
                    break
                except FileNotFoundError:
                    continue
            
            if label_font is None:
                label_font = load_font(label_font_size, bold=True)
            
            self.label_font = label_font
            self.label_font_size = label_font_size
        else:
            label_font = self.label_font
        
        # 绘制红方（下方）列标识
        for i in range(13):
            # 计算位置 - 从右到左
            col_index = 12 - i  # 将棋盘列索引转换为从右到左的列标识索引
            x = self.margin_left + i * self.grid_size
            y = self.margin_top + self.board_height + 5
            
            # 渲染文本
            text = label_font.render(red_labels[col_index], True, (180, 30, 30))  # 红色标识
            text_rect = text.get_rect(center=(x, y + label_font_size))
            screen.blit(text, text_rect)
        
        # 绘制黑方（上方）列标识 - 调整位置使其更明显
        for i in range(13):
            # 计算位置 - 从右到左
            col_index = 12 - i  # 将棋盘列索引转换为从右到左的列标识索引
            x = self.margin_left + i * self.grid_size
            y = self.margin_top - 15  # 增加与棋盘的距离
            
            # 先绘制背景以增强可见性
            text = label_font.render(black_labels[col_index], True, (0, 0, 0))  # 黑色标识
            text_rect = text.get_rect(center=(x, y))
            
            # 绘制白色背景框增强可见性
            bg_rect = text_rect.inflate(6, 6)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surface.fill((255, 255, 255, 180))  # 半透明白色背景
            screen.blit(bg_surface, (bg_rect.left, bg_rect.top))
            
            # 绘制文本
            screen.blit(text, text_rect)

    def handle_click(self, pos, game_state, game_instance):
        """处理棋盘点击事件"""
        # 获取点击的棋盘位置
        grid_pos = self.get_grid_position(pos)
        if not grid_pos:
            return

        row, col = grid_pos

        # 如果正在等待升变选择，不处理棋盘点击
        if game_instance.promotion_dialog:
            return

        # 检查是否点击了空闲的兵/卒起始位置，触发复活对话框
        # 首先检查当前玩家是否有兵/卒在局数量不足7个，且点击位置是初始兵/卒位置且为空
        current_player = game_state.player_turn
        if game_instance.selected_piece is None:  # 如果没有选中任何棋子
            # 检查是否点击了兵/卒初始位置且该位置为空
            if ((current_player == "red" and row == 8) or (current_player == "black" and row == 4)) and \
               game_state.get_piece_at(row, col) is None:
                # 检查当前玩家在局的兵/卒数量是否小于7
                if game_state.get_pawn_count(current_player) < 7:
                    # 检查是否满足复活条件
                    resurrection_positions = game_state.get_resurrection_positions()
                    if (row, col) in resurrection_positions[current_player]:
                        # 弹出复活确认对话框
                        from program.ui.dialogs import PawnResurrectionDialog
                        game_instance.pawn_resurrection_dialog = PawnResurrectionDialog(
                            500, 200, current_player, (row, col)
                        )
                        return

        # 选择棋子或移动棋子
        if game_instance.selected_piece is None:
            # 尝试选择棋子
            piece = game_state.get_piece_at(row, col)
            if piece and piece.color == game_state.player_turn:
                game_instance.selected_piece = (row, col)
                self.highlight_position(row, col)

                # 计算可能的移动位置
                possible_moves, capturable = game_state.calculate_possible_moves(row, col)
                self.set_possible_moves(possible_moves)
                self.set_capturable_positions(capturable)
        else:
            sel_row, sel_col = game_instance.selected_piece

            # 检查是否点击了同一个棋子（取消选择）
            if sel_row == row and sel_col == col:
                game_instance.selected_piece = None
                self.clear_highlights()
                return

            # 检查是否选择了另一个己方棋子（更换选择）
            new_piece = game_state.get_piece_at(row, col)
            if new_piece and new_piece.color == game_state.player_turn:
                game_instance.selected_piece = (row, col)
                self.highlight_position(row, col)

                # 计算新选择棋子的可能移动
                possible_moves, capturable = game_state.calculate_possible_moves(row, col)
                self.set_possible_moves(possible_moves)
                self.set_capturable_positions(capturable)
                return

            # 已选择棋子，尝试移动
            captured_piece = game_state.get_piece_at(row, col)
            move_successful = game_state.move_piece(sel_row, sel_col, row, col)

            if move_successful:
                print(f"[DEBUG] 移动成功: {sel_row},{sel_col} -> {row},{col}")
                # 检查是否需要升变（兵/卒到达对方底线）
                if game_state.needs_promotion:
                    # 获取兵的颜色
                    pawn_color = game_state.promotion_pawn.color if game_state.promotion_pawn else game_state.player_turn
                    print(f"[DEBUG] 需要升变: {pawn_color}方兵到达底线")
                    # 自动弹出升变选择对话框
                    from program.ui.dialogs import PromotionDialog
                    game_instance.promotion_dialog = PromotionDialog(
                        500, 400, pawn_color, (row, col), game_state.available_promotion_pieces
                    )

                # 记录上一步走法
                game_instance.last_move = (sel_row, sel_col, row, col)

                # 生成上一步走法的中文表示
                from program.utils import tools
                piece = game_state.get_piece_at(row, col)
                if piece:
                    game_instance.last_move_notation = tools.generate_move_notation(piece, sel_row, sel_col, row, col)

                # 播放选子音效（当选择棋子时）
                if game_instance.selected_piece and not captured_piece:
                    try:
                        from program.controllers.sound_manager import sound_manager
                        sound_manager.play_sound('choose')  # 使用chess-master的选子音效
                    except (pygame.error, KeyError, FileNotFoundError):
                        pass
                
                # 播放移动音效
                if captured_piece:
                    try:
                        from program.controllers.sound_manager import sound_manager
                        sound_manager.play_sound('eat')  # 使用chess-master的吃子音效
                    except (pygame.error, KeyError, FileNotFoundError):
                        pass
                else:
                    try:
                        from program.controllers.sound_manager import sound_manager
                        sound_manager.play_sound('drop')  # 使用chess-master的落子音效
                    except (pygame.error, KeyError, FileNotFoundError):
                        pass

                # 更新头像状态
                game_instance.game_screen.update_avatars(game_state)

                # 播放将军/绝杀音效 - 优先处理绝杀情况，避免重复播放
                from program.controllers.sound_manager import sound_manager
                sound_manager.check_and_play_game_sound(game_state)

                # 移动完成后清除所有高亮显示
                self.clear_highlights()
                game_instance.selected_piece = None