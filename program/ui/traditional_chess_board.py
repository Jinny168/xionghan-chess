import pygame
from program.ui.chess_board import ChessBoard
from program.utils.utils import load_font
from program.controllers.game_config_manager import theme_manager, get_piece_color, get_piece_text_color


class TraditionalChessBoard(ChessBoard):
    def __init__(self, window_width, window_height, margin_left, margin_top):
        """初始化传统中国象棋棋盘
        
        Args:
            window_width (int): 棋盘区域宽度
            window_height (int): 窗口高度
            margin_left (int): 左侧边距
            margin_top (int): 顶部边距
        """
        # 调用父类构造函数
        super().__init__(window_width, window_height, margin_left, margin_top)

        # 重新设置中国象棋的尺寸（9x10）
        self.board_width = window_width - 2 * 50  # 保持左右各留50px的边距
        self.board_height = self.board_width * 10 / 9  # 保持9x10的比例
        self.grid_size = self.board_width / 8  # 8个间隔，形成9条竖线

        # 确保棋盘高度不超过窗口高度
        max_height = window_height - margin_top - 100  # 保留底部至少100px空间
        if self.board_height > max_height:
            self.board_height = max_height
            self.board_width = self.board_height * 9 / 10
            self.grid_size = self.board_width / 8

        # 高亮位置
        self.highlighted = None

        # 可能的落点
        self.possible_moves = []

        # 可吃棋子的位置
        self.capturable_positions = []

        # 加载字体
        self.update_font()

        # 预创建用于绘制的表面
        self.cached_surfaces = {}

    def draw(self, screen, pieces, game_state=None):
        """绘制传统象棋棋盘和棋子"""
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
                (theme_colors["board"]["base_color"][0] - 20,
                 theme_colors["board"]["base_color"][1] - 20,
                 theme_colors["board"]["base_color"][2] - 10),  # 稍暗的颜色作为木纹
                (self.margin_left + i, self.margin_top),
                (self.margin_left + i, self.margin_top + self.board_height),
                1
            )

        # 绘制棋盘外边框
        pygame.draw.rect(screen, theme_colors["board"]["line_color"], board_rect, 3)

        # 绘制棋盘线条 (9x10)
        # 绘制横线（10条）
        for i in range(10):
            y = self.margin_top + i * (self.board_height / 9)
            line_width = 3 if i in [0, 9] else 2  # 边框线更粗
            pygame.draw.line(
                screen,
                theme_colors["board"]["line_color"],  # 使用主题颜色
                (self.margin_left, y),
                (self.margin_left + self.board_width, y),
                line_width
            )

        # 绘制竖线（9条），但在楚河汉界区域不绘制
        for i in range(9):
            x = self.margin_left + i * (self.board_width / 8)
            # 上半部分（0-4行）
            if i != 0 and i != 8:  # 边缘线是连续的
                pygame.draw.line(
                    screen,
                    theme_colors["board"]["line_color"],  # 使用主题颜色
                    (x, self.margin_top),
                    (x, self.margin_top + 4 * (self.board_height / 9)),
                    2
                )
            # 下半部分（5-9行）
            if i != 0 and i != 8:  # 边缘线是连续的
                pygame.draw.line(
                    screen,
                    theme_colors["board"]["line_color"],  # 使用主题颜色
                    (x, self.margin_top + 5 * (self.board_height / 9)),
                    (x, self.margin_top + self.board_height),
                    2
                )
            # 边缘线是连续的
            if i == 0 or i == 8:
                pygame.draw.line(
                    screen,
                    theme_colors["board"]["line_color"],  # 使用主题颜色
                    (x, self.margin_top),
                    (x, self.margin_top + self.board_height),
                    3  # 边框线更粗
                )

        # 绘制九宫格斜线
        # 上方九宫 (0-2行, 3-5列)
        mid_x = self.margin_left + 4 * (self.board_width / 8)
        top_3_y = self.margin_top + 0 * (self.board_height / 9)
        top_2_y = self.margin_top + 2 * (self.board_height / 9)
        bottom_7_y = self.margin_top + 7 * (self.board_height / 9)
        bottom_9_y = self.margin_top + 9 * (self.board_height / 9)

        # 黑方九宫
        pygame.draw.line(
            screen,
            theme_colors["board"]["line_color"],  # 使用主题颜色
            (self.margin_left + 3 * (self.board_width / 8), top_3_y),
            (self.margin_left + 5 * (self.board_width / 8), top_2_y),
            2
        )
        pygame.draw.line(
            screen,
            theme_colors["board"]["line_color"],  # 使用主题颜色
            (self.margin_left + 5 * (self.board_width / 8), top_3_y),
            (self.margin_left + 3 * (self.board_width / 8), top_2_y),
            2
        )

        # 红方九宫
        pygame.draw.line(
            screen,
            theme_colors["board"]["line_color"],  # 使用主题颜色
            (self.margin_left + 3 * (self.board_width / 8), bottom_7_y),
            (self.margin_left + 5 * (self.board_width / 8), bottom_9_y),
            2
        )
        pygame.draw.line(
            screen,
            theme_colors["board"]["line_color"],  # 使用主题颜色
            (self.margin_left + 5 * (self.board_width / 8), bottom_7_y),
            (self.margin_left + 3 * (self.board_width / 8), bottom_9_y),
            2
        )

        # 绘制"楚河汉界"
        font = load_font(36, bold=True)
        chu_text = font.render("楚  河", True, theme_colors["board"]["line_color"])  # 使用主题颜色
        han_text = font.render("汉  界", True, theme_colors["board"]["line_color"])  # 使用主题颜色

        # 计算分隔线和文字位置
        separator_y = self.margin_top + 4.5 * (self.board_height / 9)
        chu_rect = chu_text.get_rect(center=(self.margin_left + self.board_width / 4, separator_y))
        han_rect = han_text.get_rect(center=(self.margin_left + 3 * self.board_width / 4, separator_y))
        screen.blit(chu_text, chu_rect)
        screen.blit(han_text, han_rect)

        # 绘制可能的落点
        for row, col in self.possible_moves:
            # 如果这个位置不在可吃子位置列表中，才画绿点
            if (row, col) not in self.capturable_positions:
                x = self.margin_left + col * (self.board_width / 8)
                y = self.margin_top + row * (self.board_height / 9)
                pygame.draw.circle(
                    screen,
                    (50, 205, 50, 180),  # 绿色半透明
                    (x, y),
                    (self.board_width / 8) * 0.2,
                    0  # 填充圆形
                )

        # 绘制所有棋子
        for piece in pieces:
            self.draw_piece(screen, piece, current_theme)

        # 绘制可以吃子的位置（画红叉）- 移到棋子绘制之后，这样叉会显示在棋子上面
        for row, col in self.capturable_positions:
            x = self.margin_left + col * (self.board_width / 8)
            y = self.margin_top + row * (self.board_height / 9)

            # 绘制红叉
            cross_size = (self.board_width / 8) * 0.35
            line_width = 4
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

        # 绘制高亮位置
        if self.highlighted:
            row, col = self.highlighted
            x = self.margin_left + col * (self.board_width / 8)
            y = self.margin_top + row * (self.board_height / 9)

            # 绘制双重高亮圆圈，增强视觉效果
            # 外圈
            pygame.draw.circle(
                screen,
                (255, 215, 0, 180),  # 金色高亮
                (x, y),
                (self.board_width / 8) * 0.45,
                4
            )
            # 内圈
            pygame.draw.circle(
                screen,
                (255, 255, 0, 220),  # 黄色高亮
                (x, y),
                (self.board_width / 8) * 0.35,
                2
            )

    def draw_piece(self, screen, piece, current_theme):
        """绘制传统象棋棋子，使用主题配色"""
        # 计算棋子中心位置
        center_x = self.margin_left + piece.col * (self.board_width / 8)
        center_y = self.margin_top + piece.row * (self.board_height / 9)

        # 棋子大小为格子的85%
        radius = int(min(self.board_width / 8, self.board_height / 9) * 0.42)

        # 确保radius为正数，避免Surface创建错误
        if radius <= 0:
            return  # 如果半径无效，直接返回，不绘制棋子

        # 绘制棋子底部阴影
        shadow_offset = 4
        shadow_radius = radius + 2
        # 确保shadow_radius为正数，避免Surface创建错误
        if shadow_radius > 0:
            # 使用缓存的阴影表面
            shadow_cache_key = shadow_radius
            if shadow_cache_key not in self.cached_surfaces:
                shadow_surface = pygame.Surface((shadow_radius * 2, shadow_radius * 2), pygame.SRCALPHA)
                # 绘制模糊阴影
                for r in range(shadow_radius, 0, -1):
                    alpha = max(0, 100 - (shadow_radius - r) * 3)  # 从中心向外渐变
                    pygame.draw.circle(shadow_surface, (0, 0, 0, alpha),
                                       (shadow_radius, shadow_radius),
                                       r)
                self.cached_surfaces[shadow_cache_key] = shadow_surface

            screen.blit(self.cached_surfaces[shadow_cache_key],
                        (center_x - shadow_radius + shadow_offset,
                         center_y - shadow_radius + shadow_offset))

        # 根据棋子颜色确定阵营（side）
        side = "light_side" if piece.color == "black" else "dark_side"

        # 获取棋子配色 - 使用新的配色函数
        piece_color = get_piece_color(piece.name, current_theme, side)
        text_color = get_piece_text_color(current_theme, side)
        text_shadow_color = (0, 0, 0)  # 默认文字描边色

        # 检查是否是选中的棋子
        is_selected = (self.highlighted and
                       self.highlighted[0] == piece.row and
                       self.highlighted[1] == piece.col)

        highlight_color = (255, 255, 255)  # 白色高光
        border_color = (180, 180, 170)  # 边缘颜色微灰
        highlight_border_color = (255, 215, 0)  # 金色高亮边框（当棋子被选中时）

        # 使用缓存的棋子表面
        piece_cache_key = (piece.color, piece.name, radius, current_theme, is_selected)
        if piece_cache_key not in self.cached_surfaces:
            # 绘制主体
            piece_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)

            # 创建白玉渐变效果 - 从外到内
            gradient_steps = 15  # 更细腻渐变
            for i in range(gradient_steps, 0, -1):
                current_radius = int(radius * (i / gradient_steps))
                # 计算当前渐变颜色
                ratio = i / gradient_steps
                # 使用棋子的配色进行渐变，从外部较暗到内部较亮
                r = int(piece_color[0] * ratio + min(255, piece_color[0] + 30) * (1 - ratio))
                g = int(piece_color[1] * ratio + min(255, piece_color[1] + 30) * (1 - ratio))
                b = int(piece_color[2] * ratio + min(255, piece_color[2] + 30) * (1 - ratio))

                pygame.draw.circle(piece_surface, (r, g, b), (radius, radius), current_radius)

            # 绘制边缘 - 稍微更薄一些的边框
            pygame.draw.circle(piece_surface, border_color, (radius, radius), radius, 1)

            # 添加多重高光效果 - 更真实的玉质感

            # 主高光点 - 左上方
            highlight_pos1 = (radius - int(radius * 0.5), radius - int(radius * 0.5))
            highlight_radius1 = int(radius * 0.2)
            for i in range(5):
                h_radius = highlight_radius1 - i
                if h_radius <= 0:
                    continue
                alpha = 180 - i * 35
                pygame.draw.circle(piece_surface, (*highlight_color, alpha),
                                   highlight_pos1, h_radius)

            # 次高光点 - 右下方较弱
            highlight_pos2 = (radius + int(radius * 0.3), radius + int(radius * 0.3))
            highlight_radius2 = int(radius * 0.1)
            for i in range(3):
                h_radius = highlight_radius2 - i
                if h_radius <= 0:
                    continue
                alpha = 100 - i * 30
                pygame.draw.circle(piece_surface, (*highlight_color, alpha),
                                   highlight_pos2, h_radius)

            # 如果是选中的棋子，添加额外的高亮效果
            if is_selected:
                # 添加发光效果
                glow_radius = radius + 5
                for r in range(glow_radius, radius, -1):
                    alpha = max(0, 100 - (glow_radius - r) * 20)  # 从外向内渐变
                    pygame.draw.circle(piece_surface, (*highlight_border_color[:3], alpha),
                                       (radius, radius),
                                       r, 1)

            self.cached_surfaces[piece_cache_key] = piece_surface

        # 从缓存中获取棋子表面
        cached_piece_surface = self.cached_surfaces[piece_cache_key]
        # 将棋子表面绘制到屏幕上
        screen.blit(cached_piece_surface, (center_x - radius, center_y - radius))

        # 绘制棋子文字
        text = self.chess_font.render(piece.name, True, text_color)

        # 添加文字阴影，提高可读性
        shadow_offset = 1
        text_shadow = self.chess_font.render(piece.name, True, text_shadow_color)
        text_shadow_rect = text_shadow.get_rect(center=(center_x + shadow_offset, center_y + shadow_offset))
        screen.blit(text_shadow, text_shadow_rect)

        # 绘制主文字
        text_rect = text.get_rect(center=(center_x, center_y))
        screen.blit(text, text_rect)

    def get_grid_position(self, pos):
        """将屏幕坐标转换为棋盘格子坐标"""
        x, y = pos

        # 定义一个小的容错边界（半个网格大小的一半）
        tolerance = min(self.board_width / 16, self.board_height / 18)  # 大约半个网格大小

        # 检查是否在棋盘范围内（增加容错边界）
        if (x < self.margin_left - tolerance or x > self.margin_left + self.board_width + tolerance or
                y < self.margin_top - tolerance or y > self.margin_top + self.board_height + tolerance):
            return None

        # 转换为棋盘坐标
        raw_col = (x - self.margin_left) / (self.board_width / 8)
        raw_row = (y - self.margin_top) / (self.board_height / 9)

        # 确保坐标在有效范围内（9列，10行）
        col = round(raw_col)
        row = round(raw_row)

        if 0 <= row <= 9 and 0 <= col <= 8:
            return row, col

        # 检查是否是边缘位置，稍微超出边界但仍应识别
        # 如果原始坐标在合理范围内，即使四舍五入后超出了边界，也尝试调整回边界内
        if -0.5 <= raw_row <= 9.5 and -0.5 <= raw_col <= 8.5:
            # 将坐标限制在有效范围内
            clamped_row = max(0, min(9, round(raw_row)))
            clamped_col = max(0, min(8, round(raw_col)))
            return clamped_row, clamped_col

        return None

    def get_position_center(self, row, col):
        """获取格子中心的像素坐标
        
        Args:
            row: 行坐标
            col: 列坐标
            
        Returns:
            tuple: (x, y) 像素坐标
        """
        x = self.margin_left + col * (self.board_width / 8)
        y = self.margin_top + row * (self.board_height / 9)
        return x, y
