import pygame
from program.utils.utils import load_font


# 模拟缺失的模块（保证代码可独立运行，实际使用时替换为你的真实模块）
class GameConfig:
    def __init__(self):
        self.settings = {}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def update_settings(self, settings):
        self.settings.update(settings)


game_config = GameConfig()
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BACKGROUND_COLOR = (245, 245, 245)


class Button:
    """模拟按钮类，实际使用时替换为你的真实实现"""

    def __init__(self, x, y, width, height, text, font_size):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.font = load_font(font_size)
        self.hover = False

    def draw(self, screen):
        color = (200, 200, 200) if self.hover else (180, 180, 180)
        pygame.draw.rect(screen, color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 2)
        text_surf = self.font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
        screen.blit(text_surf, text_rect)

    def is_clicked(self, mouse_pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.x <= mouse_pos[0] <= self.x + self.width and self.y <= mouse_pos[1] <= self.y + self.height
        return False

    def check_hover(self, mouse_pos):
        self.hover = self.x <= mouse_pos[0] <= self.x + self.width and self.y <= mouse_pos[1] <= self.y + self.height


class SettingsScreen:
    """自定义设置界面"""
    # 棋子图标缓存
    _piece_icon_cache = {}

    # 常量定义
    PIECE_RADIUS = 12
    PIECE_BG_COLOR = (255, 255, 240)
    PIECE_BORDER_COLOR = (0, 0, 0)
    PIECE_FONT_SIZE = 16
    CHECKBOX_SIZE = 20

    # 界面布局常量
    Y_START = 120
    SECTION_SPACING = 40
    OPTION_SPACING = 60
    BUTTON_WIDTH = 120
    BUTTON_HEIGHT = 50
    BUTTON_SPACING = 20

    def __init__(self):
        self.xiang_jump_checkbox = None
        self.xiang_cross_label = None
        self.xiang_cross_checkbox = None
        self.xiang_jump_label = None
        self.shi_palace_label = None
        self.shi_straight_checkbox = None
        self.ma_straight_checkbox = None
        self.back_button = None
        self.shi_straight_label = None
        self.xiang_section_title = None
        self.shi_palace_checkbox = None
        self.shi_section_title = None
        self.king_diagonal_in_palace_checkbox = None
        self.ma_section_title = None
        self.confirm_button = None
        self.ma_straight_label = None
        self.king_diagonal_in_palace_label = None
        self.king_diagonal_label = None
        self.king_diagonal_checkbox = None
        self.king_palace_label = None
        self.king_palace_checkbox = None
        self.king_section_title = None
        self.desc_font = None
        self.option_font = None
        self.title_font = None
        self.ma_can_straight_three = None
        self.xiang_gain_jump_two_outside_river = None
        self.xiang_can_cross_river = None
        self.shi_gain_straight_outside_palace = None
        self.shi_can_leave_palace = None
        self.king_can_diagonal_in_palace = None
        self.king_lose_diagonal_outside_palace = None
        self.king_can_leave_palace = None

        # 新增：修复问题1 - 补充king_appear_checkbox初始化
        self.king_appear_checkbox = None

        # 棋子登场设置
        self.ju_appear = None
        self.ma_appear = None
        self.xiang_appear = None
        self.shi_appear = None
        self.pao_appear = None
        self.pawn_appear = None
        self.wei_appear = None
        self.she_appear = None
        self.lei_appear = None
        self.jia_appear = None
        self.ci_appear = None
        self.dun_appear = None

        # 棋子登场复选框和标签（删除重复定义，保留核心）
        self.ju_appear_checkbox = None
        self.ju_appear_label = None
        self.ma_appear_checkbox = None
        self.ma_appear_label = None
        self.xiang_appear_checkbox = None
        self.xiang_appear_label = None
        self.shi_appear_checkbox = None
        self.shi_appear_label = None
        self.pao_appear_checkbox = None
        self.pao_appear_label = None
        self.pawn_appear_checkbox = None
        self.pawn_appear_label = None
        self.wei_appear_checkbox = None
        self.wei_appear_label = None
        self.she_appear_checkbox = None
        self.she_appear_label = None
        self.lei_appear_checkbox = None
        self.lei_appear_label = None
        self.jia_appear_checkbox = None
        self.jia_appear_label = None
        self.ci_appear_checkbox = None
        self.ci_appear_label = None
        self.dun_appear_checkbox = None
        self.dun_appear_label = None

        self.window_width = 1200  # 增加宽度以容纳横向布局
        self.window_height = 900
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 自定义设置")

        # 从全局配置中加载设置
        self.load_settings()

        # 创建界面元素
        self.create_ui_elements()

    def load_settings(self):
        """从全局配置加载设置"""
        self.king_can_leave_palace = game_config.get_setting("king_can_leave_palace", True)
        self.king_lose_diagonal_outside_palace = game_config.get_setting("king_lose_diagonal_outside_palace", True)
        self.king_can_diagonal_in_palace = game_config.get_setting("king_can_diagonal_in_palace", True)
        self.shi_can_leave_palace = game_config.get_setting("shi_can_leave_palace", True)
        self.shi_gain_straight_outside_palace = game_config.get_setting("shi_gain_straight_outside_palace", True)
        self.xiang_can_cross_river = game_config.get_setting("xiang_can_cross_river", True)
        self.xiang_gain_jump_two_outside_river = game_config.get_setting("xiang_gain_jump_two_outside_river", True)
        self.ma_can_straight_three = game_config.get_setting("ma_can_straight_three", True)

        # 加载棋子登场设置
        self.ju_appear = game_config.get_setting("ju_appear", True)
        self.ma_appear = game_config.get_setting("ma_appear", True)
        self.xiang_appear = game_config.get_setting("xiang_appear", True)
        self.shi_appear = game_config.get_setting("shi_appear", True)
        self.pao_appear = game_config.get_setting("pao_appear", True)
        self.pawn_appear = game_config.get_setting("pawn_appear", True)
        self.wei_appear = game_config.get_setting("wei_appear", True)
        self.she_appear = game_config.get_setting("she_appear", True)
        self.lei_appear = game_config.get_setting("lei_appear", True)
        self.jia_appear = game_config.get_setting("jia_appear", True)
        self.ci_appear = game_config.get_setting("ci_appear", True)
        self.dun_appear = game_config.get_setting("dun_appear", True)

    def create_ui_elements(self):
        """创建界面元素（修复问题2、4：删除重复定义+相对坐标适配）"""
        # 标题字体
        self.title_font = load_font(48)
        self.option_font = load_font(18)  # 减小字体
        self.desc_font = load_font(14)  # 减小描述字体

        # 重新组织元素，使用更紧凑的布局
        y_pos = self.Y_START
        section_spacing = 25  # 减少间距
        option_spacing = 30  # 减少选项间距

        # 汉/汗设置区域（相对坐标：x基于窗口宽度比例）
        left_col_x = self.window_width * 0.08  # 左侧列x坐标（8%窗口宽度）
        checkbox_x = self.window_width * 0.15  # 复选框x坐标（15%窗口宽度）
        label_x = self.window_width * 0.18  # 标签x坐标（18%窗口宽度）

        self.king_section_title = (left_col_x, y_pos - 10)
        self.king_palace_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.king_palace_label = (label_x, y_pos)
        y_pos += option_spacing

        self.king_diagonal_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.king_diagonal_label = (label_x, y_pos)
        y_pos += option_spacing

        self.king_diagonal_in_palace_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.king_diagonal_in_palace_label = (label_x, y_pos)
        y_pos += option_spacing

        # 将/帅登场设置
        self.king_appear_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.king_appear_label = (label_x, y_pos)
        y_pos += option_spacing + section_spacing  # 增加段间距

        # 士设置区域
        self.shi_section_title = (left_col_x, y_pos - 10)
        self.shi_palace_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.shi_palace_label = (label_x, y_pos)
        y_pos += option_spacing

        self.shi_straight_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.shi_straight_label = (label_x, y_pos)
        y_pos += option_spacing

        # 士登场设置（仅保留此处，删除网格布局中的重复定义）
        self.shi_appear_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.shi_appear_label = (label_x, y_pos)
        y_pos += option_spacing + section_spacing

        # 相设置区域
        self.xiang_section_title = (left_col_x, y_pos - 10)
        self.xiang_cross_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.xiang_cross_label = (label_x, y_pos)
        y_pos += option_spacing

        self.xiang_jump_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.xiang_jump_label = (label_x, y_pos)
        y_pos += option_spacing

        # 相登场设置（仅保留此处，删除网格布局中的重复定义）
        self.xiang_appear_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.xiang_appear_label = (label_x, y_pos)
        y_pos += option_spacing + section_spacing

        # 马设置区域
        self.ma_section_title = (left_col_x, y_pos - 10)
        self.ma_straight_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.ma_straight_label = (label_x, y_pos)
        y_pos += option_spacing

        # 马登场设置（仅保留此处，删除网格布局中的重复定义）
        self.ma_appear_checkbox = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.ma_appear_label = (label_x, y_pos)
        y_pos += option_spacing + section_spacing

        # 棋子登场设置 - 使用3列网格布局（修复问题4：相对坐标适配窗口宽度）
        # 添加标题和图标
        self.piece_appear_title = (left_col_x, y_pos - 10)  # 棋子登场区域标题
        y_pos += option_spacing  # 为标题留出空间
        
        col1_x = self.window_width * 0.15  # 第1列x坐标
        col2_x = self.window_width * 0.40  # 第2列x坐标
        col3_x = self.window_width * 0.65  # 第3列x坐标
        col_label_offset = 30  # 标签与复选框的偏移量

        # 第1行: 車、炮、兵/卒
        self.ju_appear_checkbox = pygame.Rect(col1_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.ju_appear_label = (col1_x + col_label_offset, y_pos)
        self.pao_appear_checkbox = pygame.Rect(col2_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.pao_appear_label = (col2_x + col_label_offset, y_pos)
        self.pawn_appear_checkbox = pygame.Rect(col3_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.pawn_appear_label = (col3_x + col_label_offset, y_pos)
        y_pos += option_spacing

        # 第2行: 尉、射、檑（删除重复的马，补充未重复的棋子）
        self.wei_appear_checkbox = pygame.Rect(col1_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.wei_appear_label = (col1_x + col_label_offset, y_pos)
        self.she_appear_checkbox = pygame.Rect(col2_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.she_appear_label = (col2_x + col_label_offset, y_pos)
        self.lei_appear_checkbox = pygame.Rect(col3_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.lei_appear_label = (col3_x + col_label_offset, y_pos)
        y_pos += option_spacing

        # 第3行: 甲、刺、盾（删除重复的相，补充未重复的棋子）
        self.jia_appear_checkbox = pygame.Rect(col1_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.jia_appear_label = (col1_x + col_label_offset, y_pos)
        self.ci_appear_checkbox = pygame.Rect(col2_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.ci_appear_label = (col2_x + col_label_offset, y_pos)
        self.dun_appear_checkbox = pygame.Rect(col3_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.dun_appear_label = (col3_x + col_label_offset, y_pos)
        y_pos += option_spacing + section_spacing

        # 确认按钮 & 返回按钮（修复问题4：相对坐标居中适配）
        confirm_y = self.window_height - 80
        confirm_x = (self.window_width // 2) - self.BUTTON_WIDTH - (self.BUTTON_SPACING // 2)
        back_x = (self.window_width // 2) + (self.BUTTON_SPACING // 2)

        self.confirm_button = Button(
            confirm_x,
            confirm_y,
            self.BUTTON_WIDTH,
            self.BUTTON_HEIGHT,
            "确认",
            20
        )

        self.back_button = Button(
            back_x,
            confirm_y,
            self.BUTTON_WIDTH,
            self.BUTTON_HEIGHT,
            "返回",
            20
        )

    def draw(self):
        """绘制设置界面（修复重复绘制问题）"""
        # 绘制背景
        self.screen.fill(BACKGROUND_COLOR)

        # 绘制标题
        title_surface = self.title_font.render("自定义设置", True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width // 2, 80))
        self.screen.blit(title_surface, title_rect)

        # 绘制汉/汗区域标题图标
        self.draw_piece_icon("汉", self.king_section_title[0], self.king_section_title[1])

        # 汉/汗是否可以出九宫
        pygame.draw.rect(self.screen, BLACK, self.king_palace_checkbox, 2)
        if self.king_can_leave_palace:
            pygame.draw.line(self.screen, BLACK,
                             (self.king_palace_checkbox.left + 4, self.king_palace_checkbox.centery),
                             (self.king_palace_checkbox.centerx - 2, self.king_palace_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.king_palace_checkbox.centerx - 2, self.king_palace_checkbox.bottom - 4),
                             (self.king_palace_checkbox.right - 4, self.king_palace_checkbox.top + 4), 2)

        label_surface = self.option_font.render("汉/汗可以出九宫", True, BLACK)
        self.screen.blit(label_surface, self.king_palace_label)

        desc_surface = self.desc_font.render("允许汉/汗走出九宫区域", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.king_palace_label[0], self.king_palace_label[1] + 25))

        # 汉/汗出九宫后是否失去斜走能力
        pygame.draw.rect(self.screen, BLACK, self.king_diagonal_checkbox, 2)
        if self.king_lose_diagonal_outside_palace:
            pygame.draw.line(self.screen, BLACK,
                             (self.king_diagonal_checkbox.left + 4, self.king_diagonal_checkbox.centery),
                             (self.king_diagonal_checkbox.centerx - 2, self.king_diagonal_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.king_diagonal_checkbox.centerx - 2, self.king_diagonal_checkbox.bottom - 4),
                             (self.king_diagonal_checkbox.right - 4, self.king_diagonal_checkbox.top + 4), 2)

        label_surface = self.option_font.render("汉/汗出九宫后失去斜走能力", True, BLACK)
        self.screen.blit(label_surface, self.king_diagonal_label)

        desc_surface = self.desc_font.render("汉/汗走出九宫后只能横竖走，不能斜走", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.king_diagonal_label[0], self.king_diagonal_label[1] + 25))

        # 汉/汗在九宫内是否可以斜走
        pygame.draw.rect(self.screen, BLACK, self.king_diagonal_in_palace_checkbox, 2)
        if self.king_can_diagonal_in_palace:
            pygame.draw.line(self.screen, BLACK,
                             (self.king_diagonal_in_palace_checkbox.left + 4,
                              self.king_diagonal_in_palace_checkbox.centery),
                             (self.king_diagonal_in_palace_checkbox.centerx - 2,
                              self.king_diagonal_in_palace_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.king_diagonal_in_palace_checkbox.centerx - 2,
                              self.king_diagonal_in_palace_checkbox.bottom - 4),
                             (self.king_diagonal_in_palace_checkbox.right - 4,
                              self.king_diagonal_in_palace_checkbox.top + 4), 2)

        label_surface = self.option_font.render("汉/汗在九宫内可以斜走", True, BLACK)
        self.screen.blit(label_surface, self.king_diagonal_in_palace_label)

        desc_surface = self.desc_font.render("汉/汗在九宫内允许斜向移动", True, (100, 100, 100))
        self.screen.blit(desc_surface,
                         (self.king_diagonal_in_palace_label[0], self.king_diagonal_in_palace_label[1] + 25))

        # 汉/汗登场设置
        pygame.draw.rect(self.screen, BLACK, self.king_appear_checkbox, 2)
        if game_config.get_setting("king_appear", True):  # 将/帅默认总是登场
            pygame.draw.line(self.screen, BLACK,
                             (self.king_appear_checkbox.left + 4, self.king_appear_checkbox.centery),
                             (self.king_appear_checkbox.centerx - 2, self.king_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.king_appear_checkbox.centerx - 2, self.king_appear_checkbox.bottom - 4),
                             (self.king_appear_checkbox.right - 4, self.king_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("将/帅登场", True, BLACK)
        self.screen.blit(label_surface, self.king_appear_label)

        desc_surface = self.desc_font.render("将/帅必须登场（此选项不可更改）", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.king_appear_label[0], self.king_appear_label[1] + 25))

        # 绘制士区域标题图标
        self.draw_piece_icon("仕", self.shi_section_title[0], self.shi_section_title[1])

        # 士是否可以出九宫
        pygame.draw.rect(self.screen, BLACK, self.shi_palace_checkbox, 2)
        if self.shi_can_leave_palace:
            pygame.draw.line(self.screen, BLACK,
                             (self.shi_palace_checkbox.left + 4, self.shi_palace_checkbox.centery),
                             (self.shi_palace_checkbox.centerx - 2, self.shi_palace_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.shi_palace_checkbox.centerx - 2, self.shi_palace_checkbox.bottom - 4),
                             (self.shi_palace_checkbox.right - 4, self.shi_palace_checkbox.top + 4), 2)

        label_surface = self.option_font.render("士可以出九宫", True, BLACK)
        self.screen.blit(label_surface, self.shi_palace_label)

        desc_surface = self.desc_font.render("允许士走出九宫区域", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.shi_palace_label[0], self.shi_palace_label[1] + 25))

        # 士出九宫后是否获得直走能力
        pygame.draw.rect(self.screen, BLACK, self.shi_straight_checkbox, 2)
        if self.shi_gain_straight_outside_palace:
            pygame.draw.line(self.screen, BLACK,
                             (self.shi_straight_checkbox.left + 4, self.shi_straight_checkbox.centery),
                             (self.shi_straight_checkbox.centerx - 2, self.shi_straight_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.shi_straight_checkbox.centerx - 2, self.shi_straight_checkbox.bottom - 4),
                             (self.shi_straight_checkbox.right - 4, self.shi_straight_checkbox.top + 4), 2)

        label_surface = self.option_font.render("士出九宫后获得直走能力", True, BLACK)
        self.screen.blit(label_surface, self.shi_straight_label)

        desc_surface = self.desc_font.render("士走出九宫后可以横竖移动", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.shi_straight_label[0], self.shi_straight_label[1] + 25))

        # 士登场设置（仅绘制一次，无重复）
        pygame.draw.rect(self.screen, BLACK, self.shi_appear_checkbox, 2)
        if self.shi_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.shi_appear_checkbox.left + 4, self.shi_appear_checkbox.centery),
                             (self.shi_appear_checkbox.centerx - 2, self.shi_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.shi_appear_checkbox.centerx - 2, self.shi_appear_checkbox.bottom - 4),
                             (self.shi_appear_checkbox.right - 4, self.shi_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("士登场", True, BLACK)
        self.screen.blit(label_surface, self.shi_appear_label)

        # 绘制相区域标题图标
        self.draw_piece_icon("相", self.xiang_section_title[0], self.xiang_section_title[1])

        # 相是否可以过河
        pygame.draw.rect(self.screen, BLACK, self.xiang_cross_checkbox, 2)
        if self.xiang_can_cross_river:
            pygame.draw.line(self.screen, BLACK,
                             (self.xiang_cross_checkbox.left + 4, self.xiang_cross_checkbox.centery),
                             (self.xiang_cross_checkbox.centerx - 2, self.xiang_cross_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.xiang_cross_checkbox.centerx - 2, self.xiang_cross_checkbox.bottom - 4),
                             (self.xiang_cross_checkbox.right - 4, self.xiang_cross_checkbox.top + 4), 2)

        label_surface = self.option_font.render("相可以过河", True, BLACK)
        self.screen.blit(label_surface, self.xiang_cross_label)

        desc_surface = self.desc_font.render("允许相跨越楚河汉界", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.xiang_cross_label[0], self.xiang_cross_label[1] + 25))

        # 相过河后是否获得隔两格吃子能力
        pygame.draw.rect(self.screen, BLACK, self.xiang_jump_checkbox, 2)
        if self.xiang_gain_jump_two_outside_river:
            pygame.draw.line(self.screen, BLACK,
                             (self.xiang_jump_checkbox.left + 4, self.xiang_jump_checkbox.centery),
                             (self.xiang_jump_checkbox.centerx - 2, self.xiang_jump_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.xiang_jump_checkbox.centerx - 2, self.xiang_jump_checkbox.bottom - 4),
                             (self.xiang_jump_checkbox.right - 4, self.xiang_jump_checkbox.top + 4), 2)

        label_surface = self.option_font.render("相过河后获得隔两格吃子能力", True, BLACK)
        self.screen.blit(label_surface, self.xiang_jump_label)

        desc_surface = self.desc_font.render("相过河后可横竖方向隔一格吃子", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.xiang_jump_label[0], self.xiang_jump_label[1] + 25))

        # 相登场设置（仅绘制一次，无重复）
        pygame.draw.rect(self.screen, BLACK, self.xiang_appear_checkbox, 2)
        if self.xiang_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.xiang_appear_checkbox.left + 4, self.xiang_appear_checkbox.centery),
                             (self.xiang_appear_checkbox.centerx - 2, self.xiang_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.xiang_appear_checkbox.centerx - 2, self.xiang_appear_checkbox.bottom - 4),
                             (self.xiang_appear_checkbox.right - 4, self.xiang_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("相登场", True, BLACK)
        self.screen.blit(label_surface, self.xiang_appear_label)

        # 绘制马区域标题图标
        self.draw_piece_icon("马", self.ma_section_title[0], self.ma_section_title[1])

        # 马是否可以获得直走三格的能力
        pygame.draw.rect(self.screen, BLACK, self.ma_straight_checkbox, 2)
        if self.ma_can_straight_three:
            pygame.draw.line(self.screen, BLACK,
                             (self.ma_straight_checkbox.left + 4, self.ma_straight_checkbox.centery),
                             (self.ma_straight_checkbox.centerx - 2, self.ma_straight_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.ma_straight_checkbox.centerx - 2, self.ma_straight_checkbox.bottom - 4),
                             (self.ma_straight_checkbox.right - 4, self.ma_straight_checkbox.top + 4), 2)

        label_surface = self.option_font.render("马可以获得直走三格的能力", True, BLACK)
        self.screen.blit(label_surface, self.ma_straight_label)

        desc_surface = self.desc_font.render("马可以横竖方向走三格", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.ma_straight_label[0], self.ma_straight_label[1] + 25))

        # 马登场设置（仅绘制一次，无重复）
        pygame.draw.rect(self.screen, BLACK, self.ma_appear_checkbox, 2)
        if self.ma_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.ma_appear_checkbox.left + 4, self.ma_appear_checkbox.centery),
                             (self.ma_appear_checkbox.centerx - 2, self.ma_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.ma_appear_checkbox.centerx - 2, self.ma_appear_checkbox.bottom - 4),
                             (self.ma_appear_checkbox.right - 4, self.ma_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("馬登场", True, BLACK)
        self.screen.blit(label_surface, self.ma_appear_label)

        # 棋子登场设置 - 3列网格布局（无重复绘制）
        # 绘制棋子登场区域标题图标
        self.draw_piece_icon("棋", self.piece_appear_title[0], self.piece_appear_title[1])
        
        # 第1行: 車、炮、兵/卒
        # 車登场
        pygame.draw.rect(self.screen, BLACK, self.ju_appear_checkbox, 2)
        if self.ju_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.ju_appear_checkbox.left + 4, self.ju_appear_checkbox.centery),
                             (self.ju_appear_checkbox.centerx - 2, self.ju_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.ju_appear_checkbox.centerx - 2, self.ju_appear_checkbox.bottom - 4),
                             (self.ju_appear_checkbox.right - 4, self.ju_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("車登场", True, BLACK)
        self.screen.blit(label_surface, self.ju_appear_label)
        # 为車添加图标
        self.draw_piece_icon("車", self.ju_appear_label[0] - 30, self.ju_appear_label[1])

        # 炮登场
        pygame.draw.rect(self.screen, BLACK, self.pao_appear_checkbox, 2)
        if self.pao_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.pao_appear_checkbox.left + 4, self.pao_appear_checkbox.centery),
                             (self.pao_appear_checkbox.centerx - 2, self.pao_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.pao_appear_checkbox.centerx - 2, self.pao_appear_checkbox.bottom - 4),
                             (self.pao_appear_checkbox.right - 4, self.pao_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("炮登场", True, BLACK)
        self.screen.blit(label_surface, self.pao_appear_label)
        # 为炮添加图标
        self.draw_piece_icon("炮", self.pao_appear_label[0] - 30, self.pao_appear_label[1])

        # 兵/卒登场
        pygame.draw.rect(self.screen, BLACK, self.pawn_appear_checkbox, 2)
        if self.pawn_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.pawn_appear_checkbox.left + 4, self.pawn_appear_checkbox.centery),
                             (self.pawn_appear_checkbox.centerx - 2, self.pawn_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.pawn_appear_checkbox.centerx - 2, self.pawn_appear_checkbox.bottom - 4),
                             (self.pawn_appear_checkbox.right - 4, self.pawn_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("兵/卒登场", True, BLACK)
        self.screen.blit(label_surface, self.pawn_appear_label)
        # 为兵/卒添加图标
        self.draw_piece_icon("兵", self.pawn_appear_label[0] - 30, self.pawn_appear_label[1])

        # 第2行: 尉、射、檑
        # 尉登场
        pygame.draw.rect(self.screen, BLACK, self.wei_appear_checkbox, 2)
        if self.wei_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.wei_appear_checkbox.left + 4, self.wei_appear_checkbox.centery),
                             (self.wei_appear_checkbox.centerx - 2, self.wei_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.wei_appear_checkbox.centerx - 2, self.wei_appear_checkbox.bottom - 4),
                             (self.wei_appear_checkbox.right - 4, self.wei_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("尉登场", True, BLACK)
        self.screen.blit(label_surface, self.wei_appear_label)
        # 为尉添加图标
        self.draw_piece_icon("尉", self.wei_appear_label[0] - 30, self.wei_appear_label[1])

        # 射登场
        pygame.draw.rect(self.screen, BLACK, self.she_appear_checkbox, 2)
        if self.she_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.she_appear_checkbox.left + 4, self.she_appear_checkbox.centery),
                             (self.she_appear_checkbox.centerx - 2, self.she_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.she_appear_checkbox.centerx - 2, self.she_appear_checkbox.bottom - 4),
                             (self.she_appear_checkbox.right - 4, self.she_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("射登场", True, BLACK)
        self.screen.blit(label_surface, self.she_appear_label)
        # 为射添加图标
        self.draw_piece_icon("射", self.she_appear_label[0] - 30, self.she_appear_label[1])

        # 檑登场
        pygame.draw.rect(self.screen, BLACK, self.lei_appear_checkbox, 2)
        if self.lei_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.lei_appear_checkbox.left + 4, self.lei_appear_checkbox.centery),
                             (self.lei_appear_checkbox.centerx - 2, self.lei_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.lei_appear_checkbox.centerx - 2, self.lei_appear_checkbox.bottom - 4),
                             (self.lei_appear_checkbox.right - 4, self.lei_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("檑登场", True, BLACK)
        self.screen.blit(label_surface, self.lei_appear_label)
        # 为檑添加图标
        self.draw_piece_icon("檑", self.lei_appear_label[0] - 30, self.lei_appear_label[1])

        # 第3行: 甲、刺、盾
        # 甲登场
        pygame.draw.rect(self.screen, BLACK, self.jia_appear_checkbox, 2)
        if self.jia_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.jia_appear_checkbox.left + 4, self.jia_appear_checkbox.centery),
                             (self.jia_appear_checkbox.centerx - 2, self.jia_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.jia_appear_checkbox.centerx - 2, self.jia_appear_checkbox.bottom - 4),
                             (self.jia_appear_checkbox.right - 4, self.jia_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("甲登场", True, BLACK)
        self.screen.blit(label_surface, self.jia_appear_label)
        # 为甲添加图标
        self.draw_piece_icon("甲", self.jia_appear_label[0] - 30, self.jia_appear_label[1])

        # 刺登场
        pygame.draw.rect(self.screen, BLACK, self.ci_appear_checkbox, 2)
        if self.ci_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.ci_appear_checkbox.left + 4, self.ci_appear_checkbox.centery),
                             (self.ci_appear_checkbox.centerx - 2, self.ci_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.ci_appear_checkbox.centerx - 2, self.ci_appear_checkbox.bottom - 4),
                             (self.ci_appear_checkbox.right - 4, self.ci_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("刺登场", True, BLACK)
        self.screen.blit(label_surface, self.ci_appear_label)
        # 为刺添加图标
        self.draw_piece_icon("刺", self.ci_appear_label[0] - 30, self.ci_appear_label[1])

        # 盾登场
        pygame.draw.rect(self.screen, BLACK, self.dun_appear_checkbox, 2)
        if self.dun_appear:
            pygame.draw.line(self.screen, BLACK,
                             (self.dun_appear_checkbox.left + 4, self.dun_appear_checkbox.centery),
                             (self.dun_appear_checkbox.centerx - 2, self.dun_appear_checkbox.bottom - 4), 2)
            pygame.draw.line(self.screen, BLACK,
                             (self.dun_appear_checkbox.centerx - 2, self.dun_appear_checkbox.bottom - 4),
                             (self.dun_appear_checkbox.right - 4, self.dun_appear_checkbox.top + 4), 2)
        label_surface = self.option_font.render("盾登场", True, BLACK)
        self.screen.blit(label_surface, self.dun_appear_label)
        # 为盾添加图标
        self.draw_piece_icon("盾", self.dun_appear_label[0] - 30, self.dun_appear_label[1])

        # 绘制按钮
        self.confirm_button.draw(self.screen)
        self.back_button.draw(self.screen)

    def handle_event(self, event, mouse_pos):
        """处理事件（修复问题3：king_appear_checkbox非空判断）"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查复选框点击
            if self.king_palace_checkbox.collidepoint(mouse_pos):
                self.king_can_leave_palace = not self.king_can_leave_palace
            elif self.king_diagonal_checkbox.collidepoint(mouse_pos):
                self.king_lose_diagonal_outside_palace = not self.king_lose_diagonal_outside_palace
            elif self.king_diagonal_in_palace_checkbox.collidepoint(mouse_pos):
                self.king_can_diagonal_in_palace = not self.king_can_diagonal_in_palace
            elif self.shi_palace_checkbox.collidepoint(mouse_pos):
                self.shi_can_leave_palace = not self.shi_can_leave_palace
            elif self.shi_straight_checkbox.collidepoint(mouse_pos):
                self.shi_gain_straight_outside_palace = not self.shi_gain_straight_outside_palace
            elif self.xiang_cross_checkbox.collidepoint(mouse_pos):
                self.xiang_can_cross_river = not self.xiang_can_cross_river
            elif self.xiang_jump_checkbox.collidepoint(mouse_pos):
                self.xiang_gain_jump_two_outside_river = not self.xiang_gain_jump_two_outside_river
            elif self.ma_straight_checkbox.collidepoint(mouse_pos):
                self.ma_can_straight_three = not self.ma_can_straight_three
            # 检查棋子登场复选框点击
            elif self.ju_appear_checkbox.collidepoint(mouse_pos):
                self.ju_appear = not self.ju_appear
            elif self.ma_appear_checkbox.collidepoint(mouse_pos):
                self.ma_appear = not self.ma_appear
            elif self.xiang_appear_checkbox.collidepoint(mouse_pos):
                self.xiang_appear = not self.xiang_appear
            elif self.shi_appear_checkbox.collidepoint(mouse_pos):
                self.shi_appear = not self.shi_appear
            # 修复问题3：增加king_appear_checkbox非空判断
            elif self.king_appear_checkbox and self.king_appear_checkbox.collidepoint(mouse_pos):
                # 将/帅登场选项不允许更改，保持为True
                pass  # 不做任何操作，将/帅必须登场
            elif self.pao_appear_checkbox.collidepoint(mouse_pos):
                self.pao_appear = not self.pao_appear
            elif self.pawn_appear_checkbox.collidepoint(mouse_pos):
                self.pawn_appear = not self.pawn_appear
            elif self.wei_appear_checkbox.collidepoint(mouse_pos):
                self.wei_appear = not self.wei_appear
            elif self.she_appear_checkbox.collidepoint(mouse_pos):
                self.she_appear = not self.she_appear
            elif self.lei_appear_checkbox.collidepoint(mouse_pos):
                self.lei_appear = not self.lei_appear
            elif self.jia_appear_checkbox.collidepoint(mouse_pos):
                self.jia_appear = not self.jia_appear
            elif self.ci_appear_checkbox.collidepoint(mouse_pos):
                self.ci_appear = not self.ci_appear
            elif self.dun_appear_checkbox.collidepoint(mouse_pos):
                self.dun_appear = not self.dun_appear
            # 检查按钮点击
            elif self.confirm_button.is_clicked(mouse_pos, event):
                return "confirm"
            elif self.back_button.is_clicked(mouse_pos, event):
                return "back"

        # 更新按钮悬停状态
        self.confirm_button.check_hover(mouse_pos)
        self.back_button.check_hover(mouse_pos)

        return None

    def get_settings(self):
        """获取当前设置"""
        settings = {
            "king_can_leave_palace": self.king_can_leave_palace,
            "king_lose_diagonal_outside_palace": self.king_lose_diagonal_outside_palace,
            "king_can_diagonal_in_palace": self.king_can_diagonal_in_palace,
            "shi_can_leave_palace": self.shi_can_leave_palace,
            "shi_gain_straight_outside_palace": self.shi_gain_straight_outside_palace,
            "xiang_can_cross_river": self.xiang_can_cross_river,
            "xiang_gain_jump_two_outside_river": self.xiang_gain_jump_two_outside_river,
            "ma_can_straight_three": self.ma_can_straight_three,
            # 棋子登场设置（将/帅必须登场）
            "ju_appear": self.ju_appear,
            "ma_appear": self.ma_appear,
            "xiang_appear": self.xiang_appear,
            "shi_appear": self.shi_appear,
            "king_appear": True,  # 将/帅必须登场
            "pao_appear": self.pao_appear,
            "pawn_appear": self.pawn_appear,
            "wei_appear": self.wei_appear,
            "she_appear": self.she_appear,
            "lei_appear": self.lei_appear,
            "jia_appear": self.jia_appear,
            "ci_appear": self.ci_appear,
            "dun_appear": self.dun_appear
        }

        # 保存设置到全局配置
        game_config.update_settings(settings)

        return settings

    def draw_piece_icon(self, text, x, y):
        """绘制棋子图标，类似Avatar的实现（修复问题5：完善字体兜底逻辑）"""
        # 使用缓存避免重复创建Surface
        cache_key = (text, self.PIECE_RADIUS)
        if cache_key in self._piece_icon_cache:
            circle_surface = self._piece_icon_cache[cache_key]
        else:
            # 创建一个圆形背景
            radius = self.PIECE_RADIUS  # 小圆圈的半径
            circle_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(circle_surface, self.PIECE_BG_COLOR, (radius, radius), radius)  # 白色背景
            pygame.draw.circle(circle_surface, self.PIECE_BORDER_COLOR, (radius, radius), radius, 1)  # 黑色边框

            # 获取字体（修复问题5：完善兜底逻辑，避免None）
            piece_font = load_font(self.PIECE_FONT_SIZE, bold=True)
            if piece_font is None:
                print(f"警告: 自定义字体加载失败，使用系统内置字体渲染棋子图标：{text}")
                piece_font = pygame.font.SysFont("SimSun", self.PIECE_FONT_SIZE, bold=True)
                if piece_font is None:
                    piece_font = pygame.font.Font(None, self.PIECE_FONT_SIZE)

            # 渲染文字
            text_surface = piece_font.render(text, True, RED)
            text_rect = text_surface.get_rect(center=(radius, radius))
            circle_surface.blit(text_surface, text_rect)

            # 缓存这个图标
            self._piece_icon_cache[cache_key] = circle_surface

        # 将圆形图标绘制到屏幕上
        self.screen.blit(circle_surface, (x - self.PIECE_RADIUS, y - self.PIECE_RADIUS))

    def run(self):
        """运行设置界面"""
        clock = pygame.time.Clock()
        running = True

        while running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    self.window_width, self.window_height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
                    self.create_ui_elements()  # 重新创建UI，适配新窗口大小

                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "back"

                # 处理鼠标事件
                result = self.handle_event(event, mouse_pos)
                if result == "confirm":
                    return self.get_settings()
                elif result == "back":
                    return "back"

            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(60)

        return "back"


# 程序入口（用于测试）
if __name__ == "__main__":
    pygame.init()
    settings_screen = SettingsScreen()
    settings_screen.run()
    pygame.quit()