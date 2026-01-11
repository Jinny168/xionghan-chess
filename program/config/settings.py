import pygame

from program.utils.utils import load_font
from .general_drawers import draw_category
from program.ui.scrollbar import ScrollBar
from program.ui.button import Button
from .config import game_config, BACKGROUND_COLOR, RED, BLACK


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
        # 棋子设置配置 - 按棋子类型组织
        self.piece_settings = {
            # 汗/汗设置
            "king": {
                "can_leave_palace": None,           # 汗/汗是否可以出九宫
                "lose_diagonal_outside_palace": None,  # 汗/汗出九宫后是否失去斜走能力
                "can_diagonal_in_palace": None,     # 汗/汗在九宫内是否可以斜走
                "appear": None,                     # 将/帅登场设置（固定为True）
                "section_title": None,
                "palace_checkbox": None,
                "palace_label": None,
                "diagonal_checkbox": None,
                "diagonal_label": None,
                "diagonal_in_palace_checkbox": None,
                "diagonal_in_palace_label": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 士设置
            "shi": {
                "can_leave_palace": None,           # 士是否可以出九宫
                "gain_straight_outside_palace": None,  # 士出九宫后是否获得直走能力
                "appear": None,                     # 士登场设置
                "section_title": None,
                "palace_checkbox": None,
                "palace_label": None,
                "straight_checkbox": None,
                "straight_label": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 相设置
            "xiang": {
                "can_cross_river": None,            # 相是否可以过河
                "gain_jump_two_outside_river": None, # 相过河后是否获得隔两格吃子能力
                "appear": None,                     # 相登场设置
                "section_title": None,
                "cross_checkbox": None,
                "cross_label": None,
                "jump_checkbox": None,
                "jump_label": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 马设置
            "ma": {
                "can_straight_three": None,         # 马是否可以获得直走三格的能力
                "appear": None,                     # 马登场设置
                "section_title": None,
                "straight_checkbox": None,
                "straight_label": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 車设置
            "ju": {
                "appear": None,                     # 車登场设置
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 炮设置
            "pao": {
                "appear": None,                     # 炮登场设置
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 兵/卒设置
            "pawn": {
                "appear": None,                     # 兵/卒登场设置
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 尉设置
            "wei": {
                "appear": None,                     # 尉登场设置
                "section_title": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 射设置
            "she": {
                "appear": None,                     # 射登场设置
                "section_title": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 檵/檑设置
            "lei": {
                "appear": None,                     # 檵/檑登场设置
                "section_title": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 甲设置
            "jia": {
                "appear": None,                     # 甲登场设置
                "section_title": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 刺设置
            "ci": {
                "appear": None,                     # 刺登场设置
                "section_title": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 盾设置
            "dun": {
                "appear": None,                     # 盾登场设置
                "section_title": None,
                "appear_checkbox": None,
                "appear_label": None,
            },
            # 游戏模式设置
            "game_mode": {
                "classic_mode": None,               # 经典模式设置
                "section_title": None,
                "classic_checkbox": None,
                "classic_label": None,
            }
        }

        # 按钮
        self.confirm_button = None
        self.back_button = None

        self.window_width = 1200  # 增加宽度以容纳横向布局
        self.window_height = 900
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 自定义设置")
        
        # 分类布局相关属性
        self.category_background_color = (230, 230, 230)  # 分类背景色
        self.category_border_color = (180, 180, 180)  # 分类边框色
        self.category_padding = 15  # 分类内边距
        self.category_spacing = 20  # 分类间间距
        self.category_title_height = 40  # 分类标题高度
        self.category_title_font = load_font(20, bold=True)  # 分类标题字体
        self.category_icon_radius = 15  # 分类图标半径
        self.category_icon_bg_color = (255, 255, 240)  # 分类图标背景色
        self.category_icon_border_color = (0, 0, 0)  # 分类图标边框色
        self.category_icon_text_color = RED  # 分类图标文字颜色
        
        # 滚动相关属性
        self.scroll_y = 0
        self.max_scroll = 0
        self.dragging_scroll = False
        self.scroll_bar = ScrollBar(self.window_width - 20, 100, 15, self.window_height - 200, 1200)

        # 从全局配置中加载设置
        self.load_settings()

        # 创建界面元素
        self.create_ui_elements()
        
        # 初始化滚动
        self.update_max_scroll()

    def load_settings(self):
        """从全局配置加载设置"""
        # 汉/汗设置
        self.piece_settings["king"]["can_leave_palace"] = game_config.get_setting("king_can_leave_palace", True)
        self.piece_settings["king"]["lose_diagonal_outside_palace"] = game_config.get_setting("king_lose_diagonal_outside_palace", True)
        self.piece_settings["king"]["can_diagonal_in_palace"] = game_config.get_setting("king_can_diagonal_in_palace", True)
        self.piece_settings["king"]["appear"] = True  # 将/帅必须登场，固定为True

        # 士设置
        self.piece_settings["shi"]["can_leave_palace"] = game_config.get_setting("shi_can_leave_palace", True)
        self.piece_settings["shi"]["gain_straight_outside_palace"] = game_config.get_setting("shi_gain_straight_outside_palace", True)
        self.piece_settings["shi"]["appear"] = game_config.get_setting("shi_appear", True)

        # 相设置
        self.piece_settings["xiang"]["can_cross_river"] = game_config.get_setting("xiang_can_cross_river", True)
        self.piece_settings["xiang"]["gain_jump_two_outside_river"] = game_config.get_setting("xiang_gain_jump_two_outside_river", True)
        self.piece_settings["xiang"]["appear"] = game_config.get_setting("xiang_appear", True)

        # 马设置
        self.piece_settings["ma"]["can_straight_three"] = game_config.get_setting("ma_can_straight_three", True)
        self.piece_settings["ma"]["appear"] = game_config.get_setting("ma_appear", True)

        # 其他棋子设置
        self.piece_settings["ju"]["appear"] = game_config.get_setting("ju_appear", True)
        self.piece_settings["pao"]["appear"] = game_config.get_setting("pao_appear", True)
        self.piece_settings["pawn"]["appear"] = game_config.get_setting("pawn_appear", True)
        self.piece_settings["wei"]["appear"] = game_config.get_setting("wei_appear", True)
        self.piece_settings["she"]["appear"] = game_config.get_setting("she_appear", True)
        self.piece_settings["lei"]["appear"] = game_config.get_setting("lei_appear", True)
        self.piece_settings["jia"]["appear"] = game_config.get_setting("jia_appear", True)
        self.piece_settings["ci"]["appear"] = game_config.get_setting("ci_appear", True)
        self.piece_settings["dun"]["appear"] = game_config.get_setting("dun_appear", True)
        
        # 游戏模式设置
        self.piece_settings["game_mode"]["classic_mode"] = game_config.get_setting("classic_mode", False)

    def create_ui_elements(self):
        """创建界面元素，按棋子类型进行分类"""
        # 标题字体
        self.title_font = load_font(48)
        self.option_font = load_font(18)  # 减小字体
        self.desc_font = load_font(14)  # 减小描述字体

        # 分类布局参数
        self.category_padding = 15  # 分类内边距
        self.category_bg_color = (240, 240, 240)  # 分类背景色
        self.category_border_color = (200, 200, 200)  # 分类边框色
        self.category_title_height = 40  # 分类标题高度
        self.category_icon_size = 20  # 分类图标大小

        # 重新组织元素，使用按棋子类型的分类布局
        y_pos = self.Y_START
        section_spacing = 25  # 减少间距
        option_spacing = 30  # 减少选项间距

        # 汉/汗设置区域（相对坐标：x基于窗口宽度比例）
        left_col_x = self.window_width * 0.08  # 左侧列x坐标（8%窗口宽度）
        checkbox_x = self.window_width * 0.15  # 复选框x坐标（15%窗口宽度）
        label_x = self.window_width * 0.18  # 标签x坐标（18%窗口宽度）

        # 汉/汗分类标题
        self.piece_settings["king"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间

        # 汉/汗是否可以出九宫
        self.piece_settings["king"]["palace_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["king"]["palace_label"] = (label_x, y_pos)
        y_pos += option_spacing

        # 汉/汗出九宫后是否失去斜走能力
        self.piece_settings["king"]["diagonal_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["king"]["diagonal_label"] = (label_x, y_pos)
        y_pos += option_spacing

        # 汉/汗在九宫内是否可以斜走
        self.piece_settings["king"]["diagonal_in_palace_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["king"]["diagonal_in_palace_label"] = (label_x, y_pos)
        y_pos += option_spacing

        # 汉/汗登场设置（整合到规则设置中）
        self.piece_settings["king"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["king"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing  # 增加段间距

        # 士分类标题
        self.piece_settings["shi"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间

        # 士是否可以出九宫
        self.piece_settings["shi"]["palace_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["shi"]["palace_label"] = (label_x, y_pos)
        y_pos += option_spacing

        # 士出九宫后是否获得直走能力
        self.piece_settings["shi"]["straight_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["shi"]["straight_label"] = (label_x, y_pos)
        y_pos += option_spacing

        # 士登场设置（整合到规则设置中）
        self.piece_settings["shi"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["shi"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing

        # 相分类标题
        self.piece_settings["xiang"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间

        # 相是否可以过河
        self.piece_settings["xiang"]["cross_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["xiang"]["cross_label"] = (label_x, y_pos)
        y_pos += option_spacing

        # 相过河后是否获得隔两格吃子能力
        self.piece_settings["xiang"]["jump_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["xiang"]["jump_label"] = (label_x, y_pos)
        y_pos += option_spacing

        # 相登场设置（整合到规则设置中）
        self.piece_settings["xiang"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["xiang"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing

        # 马分类标题
        self.piece_settings["ma"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间

        # 马是否可以获得直走三格的能力
        self.piece_settings["ma"]["straight_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["ma"]["straight_label"] = (label_x, y_pos)
        y_pos += option_spacing

        # 马登场设置（整合到规则设置中）
        self.piece_settings["ma"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["ma"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing

        # 尉棋子设置
        self.piece_settings["wei"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间
        self.piece_settings["wei"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["wei"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing
        
        # 射棋子设置
        self.piece_settings["she"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间
        self.piece_settings["she"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["she"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing
        
        # 檵/檑棋子设置
        self.piece_settings["lei"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间
        self.piece_settings["lei"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["lei"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing
        
        # 甲棋子设置
        self.piece_settings["jia"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间
        self.piece_settings["jia"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["jia"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing
        
        # 刺棋子设置
        self.piece_settings["ci"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间
        self.piece_settings["ci"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["ci"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing
        
        # 盾棋子设置
        self.piece_settings["dun"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间
        self.piece_settings["dun"]["appear_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["dun"]["appear_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing
        
        # 游戏模式设置
        self.piece_settings["game_mode"]["section_title"] = (left_col_x, y_pos - 10)
        y_pos += 30  # 为标题留出空间
        self.piece_settings["game_mode"]["classic_checkbox"] = pygame.Rect(checkbox_x, y_pos, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)
        self.piece_settings["game_mode"]["classic_label"] = (label_x, y_pos)
        y_pos += option_spacing + section_spacing

        # 确认按钮 & 返回按钮（位于界面底部，不受滚动影响）
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
        """绘制设置界面（按棋子类型分类）"""
        # 绘制背景
        self.screen.fill(BACKGROUND_COLOR)

        # 绘制标题
        title_surface = self.title_font.render("自定义设置", True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width // 2, 80))
        self.screen.blit(title_surface, title_rect)

        # 设置可视区域裁剪，实现滚动效果
        scroll_area_rect = pygame.Rect(30, 100, self.window_width - 50, self.window_height - 180)
        self.screen.set_clip(scroll_area_rect)
        
        # 使用模块化方式绘制各个棋子分类
        y_offset = 150  # 初始Y坐标
        
        # 汉/汗棋子分类
        king_items = self.create_king_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "将", "汉/汗", king_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 士棋子分类
        shi_items = self.create_shi_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "士", "士", shi_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 相棋子分类
        xiang_items = self.create_xiang_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "相", "相", xiang_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 马棋子分类
        ma_items = self.create_ma_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "馬", "馬", ma_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 車棋子分类
        ju_items = self.create_ju_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "車", "車", ju_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 炮棋子分类
        pao_items = self.create_pao_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "炮", "炮", pao_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 兵/卒棋子分类
        pawn_items = self.create_pawn_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "兵", "兵/卒", pawn_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 尉棋子分类
        wei_items = self.create_wei_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "尉", "尉", wei_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 射棋子分类
        she_items = self.create_she_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "射", "射", she_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 檵/檑棋子分类
        lei_items = self.create_lei_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "檑", "檑", lei_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 甲棋子分类
        jia_items = self.create_jia_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "甲", "甲", jia_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 刺棋子分类
        ci_items = self.create_ci_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "刺", "刺", ci_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 盾棋子分类
        dun_items = self.create_dun_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "盾", "盾", dun_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing
        
        # 游戏模式分类
        game_mode_items = self.create_game_mode_items(y_offset)
        category_height = draw_category(
            self.screen, self.category_background_color, self.category_border_color,
            self.category_padding, self.category_title_height, self.category_title_font,
            self.CHECKBOX_SIZE, self.scroll_y, self.window_width,
            self.option_font, self.desc_font, self.draw_piece_icon,
            "模", "游戏模式", game_mode_items, y_offset
        )
        y_offset = y_offset + category_height + self.category_spacing

        # 取消裁剪区域
        self.screen.set_clip(None)
        
        # 绘制滚动条
        self.scroll_bar.draw(self.screen)
        
        # 绘制按钮（在可视区域之外）
        self.confirm_button.draw(self.screen)
        self.back_button.draw(self.screen)

    def handle_event(self, event, mouse_pos):
        """处理事件（考虑滚动位置）"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 考虑滚动位置调整鼠标坐标用于检测
            adjusted_mouse_pos = (mouse_pos[0], mouse_pos[1] + self.scroll_y)
            
            # 检查复选框点击 - 使用实际绘制位置
            y_offset = 150  # 初始Y坐标，与draw方法中的一致
            
            # 汉/汗棋子分类
            king_items = self.create_king_items(y_offset)
            clicked_item = self.check_category_click(king_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "汉/汗可以出九宫":
                    self.piece_settings["king"]["can_leave_palace"] = not self.piece_settings["king"]["can_leave_palace"]
                elif text == "汉/汗出九宫后失去斜走能力":
                    self.piece_settings["king"]["lose_diagonal_outside_palace"] = not self.piece_settings["king"]["lose_diagonal_outside_palace"]
                elif text == "汉/汗在九宫内可以斜走":
                    self.piece_settings["king"]["can_diagonal_in_palace"] = not self.piece_settings["king"]["can_diagonal_in_palace"]
                elif text == "将/帅登场":
                    # 将/帅登场选项不允许更改，保持为True
                    pass
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(king_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 士棋子分类
            shi_items = self.create_shi_items(y_offset)
            clicked_item = self.check_category_click(shi_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "士可以出九宫":
                    self.piece_settings["shi"]["can_leave_palace"] = not self.piece_settings["shi"]["can_leave_palace"]
                elif text == "士出九宫后获得直走能力":
                    self.piece_settings["shi"]["gain_straight_outside_palace"] = not self.piece_settings["shi"]["gain_straight_outside_palace"]
                elif text == "士登场":
                    self.piece_settings["shi"]["appear"] = not self.piece_settings["shi"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(shi_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 相棋子分类
            xiang_items = self.create_xiang_items(y_offset)
            clicked_item = self.check_category_click(xiang_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "相可以过河":
                    self.piece_settings["xiang"]["can_cross_river"] = not self.piece_settings["xiang"]["can_cross_river"]
                elif text == "相过河后获得隔两格吃子能力":
                    self.piece_settings["xiang"]["gain_jump_two_outside_river"] = not self.piece_settings["xiang"]["gain_jump_two_outside_river"]
                elif text == "相登场":
                    self.piece_settings["xiang"]["appear"] = not self.piece_settings["xiang"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(xiang_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 马棋子分类
            ma_items = self.create_ma_items(y_offset)
            clicked_item = self.check_category_click(ma_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "马可以获得直走三格的能力":
                    self.piece_settings["ma"]["can_straight_three"] = not self.piece_settings["ma"]["can_straight_three"]
                elif text == "馬登场":
                    self.piece_settings["ma"]["appear"] = not self.piece_settings["ma"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(ma_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 車棋子分类
            ju_items = self.create_ju_items(y_offset)
            clicked_item = self.check_category_click(ju_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "車登场":
                    self.piece_settings["ju"]["appear"] = not self.piece_settings["ju"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(ju_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 炮棋子分类
            pao_items = self.create_pao_items(y_offset)
            clicked_item = self.check_category_click(pao_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "炮登场":
                    self.piece_settings["pao"]["appear"] = not self.piece_settings["pao"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(pao_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 兵/卒棋子分类
            pawn_items = self.create_pawn_items(y_offset)
            clicked_item = self.check_category_click(pawn_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "兵/卒登场":
                    self.piece_settings["pawn"]["appear"] = not self.piece_settings["pawn"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(pawn_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 尉棋子分类
            wei_items = self.create_wei_items(y_offset)
            clicked_item = self.check_category_click(wei_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "尉登场":
                    self.piece_settings["wei"]["appear"] = not self.piece_settings["wei"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(wei_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 射棋子分类
            she_items = self.create_she_items(y_offset)
            clicked_item = self.check_category_click(she_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "射登场":
                    self.piece_settings["she"]["appear"] = not self.piece_settings["she"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(she_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 檵/檑棋子分类
            lei_items = self.create_lei_items(y_offset)
            clicked_item = self.check_category_click(lei_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "檑登场":
                    self.piece_settings["lei"]["appear"] = not self.piece_settings["lei"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(lei_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 甲棋子分类
            jia_items = self.create_jia_items(y_offset)
            clicked_item = self.check_category_click(jia_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "甲登场":
                    self.piece_settings["jia"]["appear"] = not self.piece_settings["jia"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(jia_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 刺棋子分类
            ci_items = self.create_ci_items(y_offset)
            clicked_item = self.check_category_click(ci_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "刺登场":
                    self.piece_settings["ci"]["appear"] = not self.piece_settings["ci"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(ci_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 盾棋子分类
            dun_items = self.create_dun_items(y_offset)
            clicked_item = self.check_category_click(dun_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "盾登场":
                    self.piece_settings["dun"]["appear"] = not self.piece_settings["dun"]["appear"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(dun_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 游戏模式分类
            game_mode_items = self.create_game_mode_items(y_offset)
            clicked_item = self.check_category_click(game_mode_items, adjusted_mouse_pos, y_offset)
            if clicked_item is not None:
                checkbox, label, value, text, desc, is_disabled = clicked_item
                if text == "经典模式":
                    self.piece_settings["game_mode"]["classic_mode"] = not self.piece_settings["game_mode"]["classic_mode"]
                return  # 处理完后直接返回，避免其他检测
            
            # 更新y_offset
            category_height = len(game_mode_items) * 60 + self.category_title_height + 2 * self.category_padding
            y_offset = y_offset + category_height + self.category_spacing
            
            # 检查按钮点击（按钮不受滚动影响）
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.confirm_button.is_clicked(mouse_pos, event):
                return "confirm"
            elif self.back_button.is_clicked(mouse_pos, event):
                return "back"

        # 更新按钮悬停状态（按钮不受滚动影响）
        self.confirm_button.check_hover(mouse_pos)
        self.back_button.check_hover(mouse_pos)

        return None

    def check_category_click(self, items, mouse_pos, y_position):
        """检查分类中的点击事件，与draw_category中的绘制逻辑保持一致"""
        # 计算分类区域的尺寸
        category_width = self.window_width - 100  # 留出边距
        items_count = len(items)  # 该分类下的设置项数量
        category_height = items_count * 60 + self.category_title_height + 2 * self.category_padding  # 包含标题高度和内边距
        
        # 分类区域矩形
        category_rect = pygame.Rect(50, y_position - self.category_padding, category_width, category_height)
        
        # 分类标题下方开始绘制内容
        item_y = y_position + self.category_title_height + self.category_padding
        
        for index, item in enumerate(items):
            checkbox, label, value, text, desc, is_disabled = item
            
            # 计算每项的背景框
            item_rect = pygame.Rect(category_rect.left + 10, item_y - 5, category_rect.width - 20, 55)
            
            # 计算复选框位置 - 与draw_category中一致
            checkbox_x = item_rect.left + 10  # 在背景框内留出一些边距
            checkbox_y = item_rect.top + (item_rect.height - self.CHECKBOX_SIZE) // 2  # 垂直居中
            actual_checkbox = pygame.Rect(
                checkbox_x,
                checkbox_y,
                self.CHECKBOX_SIZE, 
                self.CHECKBOX_SIZE
            )
            
            # 检查鼠标是否点击了这个复选框
            if actual_checkbox.collidepoint(mouse_pos):
                return item  # 返回被点击的项目
            
            item_y += 60
        
        return None  # 没有点击任何复选框

    def get_settings(self):
        """获取当前设置"""
        settings = {
            "king_can_leave_palace": self.piece_settings["king"]["can_leave_palace"],
            "king_lose_diagonal_outside_palace": self.piece_settings["king"]["lose_diagonal_outside_palace"],
            "king_can_diagonal_in_palace": self.piece_settings["king"]["can_diagonal_in_palace"],
            "shi_can_leave_palace": self.piece_settings["shi"]["can_leave_palace"],
            "shi_gain_straight_outside_palace": self.piece_settings["shi"]["gain_straight_outside_palace"],
            "xiang_can_cross_river": self.piece_settings["xiang"]["can_cross_river"],
            "xiang_gain_jump_two_outside_river": self.piece_settings["xiang"]["gain_jump_two_outside_river"],
            "ma_can_straight_three": self.piece_settings["ma"]["can_straight_three"],
            # 棋子登场设置（将/帅必须登场）
            "ju_appear": self.piece_settings["ju"]["appear"],
            "ma_appear": self.piece_settings["ma"]["appear"],
            "xiang_appear": self.piece_settings["xiang"]["appear"],
            "shi_appear": self.piece_settings["shi"]["appear"],
            "king_appear": True,  # 将/帅必须登场
            "pao_appear": self.piece_settings["pao"]["appear"],
            "pawn_appear": self.piece_settings["pawn"]["appear"],
            "wei_appear": self.piece_settings["wei"]["appear"],
            "she_appear": self.piece_settings["she"]["appear"],
            "lei_appear": self.piece_settings["lei"]["appear"],
            "jia_appear": self.piece_settings["jia"]["appear"],
            "ci_appear": self.piece_settings["ci"]["appear"],
            "dun_appear": self.piece_settings["dun"]["appear"]
        }

        # 添加游戏模式设置
        settings["classic_mode"] = self.piece_settings["game_mode"]["classic_mode"]

        # 保存设置到全局配置
        game_config.update_settings(settings)

        return settings

    def draw_piece_icon(self, text, x, y, size=None):
        """绘制棋子图标，类似Avatar的实现（修复问题5：完善字体兜底逻辑）"""
        # 使用缓存避免重复创建Surface
        icon_size = size or self.PIECE_RADIUS
        cache_key = (text, icon_size)
        if cache_key in self._piece_icon_cache:
            circle_surface = self._piece_icon_cache[cache_key]
        else:
            # 创建一个圆形背景
            radius = icon_size  # 小圆圈的半径
            circle_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(circle_surface, self.PIECE_BG_COLOR, (radius, radius), radius)  # 白色背景
            pygame.draw.circle(circle_surface, self.PIECE_BORDER_COLOR, (radius, radius), radius, 1)  # 黑色边框

            # 获取字体（修复问题5：完善兜底逻辑，避免None）
            piece_font_size = size or self.PIECE_FONT_SIZE
            piece_font = load_font(piece_font_size, bold=True)
            if piece_font is None:
                print(f"警告: 自定义字体加载失败，使用系统内置字体渲染棋子图标：{text}")
                piece_font = pygame.font.SysFont("SimSun", piece_font_size, bold=True)
                if piece_font is None:
                    piece_font = pygame.font.Font(None, piece_font_size)

            # 渲染文字
            text_surface = piece_font.render(text, True, RED)
            text_rect = text_surface.get_rect(center=(radius, radius))
            circle_surface.blit(text_surface, text_rect)

            # 缓存这个图标
            self._piece_icon_cache[cache_key] = circle_surface

        # 将圆形图标绘制到屏幕上
        self.screen.blit(circle_surface, (x - icon_size, y - icon_size))

    def _draw_category(self, title, icon_text, items, y_pos):
        """绘制棋子分类区域"""
        # 计算分类区域的尺寸
        category_width = self.window_width - 100  # 留出边距
        category_height = len(items) * 60 + self.category_title_height + 2 * self.category_padding  # 包含标题高度和内边距
        
        # 绘制分类背景
        category_rect = pygame.Rect(50, y_pos - self.category_padding, category_width, category_height)
        pygame.draw.rect(self.screen, self.category_background_color, category_rect)
        pygame.draw.rect(self.screen, self.category_border_color, category_rect, 2)
        
        # 绘制分类标题和图标
        title_y = y_pos
        self.draw_piece_icon(icon_text, 65, title_y + self.category_title_height // 2)
        title_surface = self.category_title_font.render(title, True, BLACK)
        self.screen.blit(title_surface, (90, title_y))
        
        # 绘制分类内容
        item_y = y_pos + self.category_title_height + self.category_padding
        for i, item in enumerate(items):
            checkbox, label_text, setting_var, desc_text = item
            
            # 根据复选框确定实际文本内容
            actual_text = ""
            if checkbox == self.king_appear_checkbox:
                actual_text = "将/帅登场"
            elif checkbox == self.shi_appear_checkbox:
                actual_text = "士登场"
            elif checkbox == self.xiang_appear_checkbox:
                actual_text = "相登场"
            elif checkbox == self.ma_appear_checkbox:
                actual_text = "馬登场"
            elif checkbox == self.ju_appear_checkbox:
                actual_text = "車登场"
            elif checkbox == self.pao_appear_checkbox:
                actual_text = "炮登场"
            elif checkbox == self.pawn_appear_checkbox:
                actual_text = "兵/卒登场"
            elif checkbox == self.wei_appear_checkbox:
                actual_text = "尉登场"
            elif checkbox == self.she_appear_checkbox:
                actual_text = "射登场"
            elif checkbox == self.lei_appear_checkbox:
                actual_text = "檑登场"
            elif checkbox == self.jia_appear_checkbox:
                actual_text = "甲登场"
            elif checkbox == self.ci_appear_checkbox:
                actual_text = "刺登场"
            elif checkbox == self.dun_appear_checkbox:
                actual_text = "盾登场"
            elif checkbox == self.king_palace_checkbox:
                actual_text = "汉/汗可以出九宫"
            elif checkbox == self.king_diagonal_checkbox:
                actual_text = "汉/汗出九宫后失去斜走能力"
            elif checkbox == self.king_diagonal_in_palace_checkbox:
                actual_text = "汉/汗在九宫内可以斜走"
            elif checkbox == self.shi_palace_checkbox:
                actual_text = "士可以出九宫"
            elif checkbox == self.shi_straight_checkbox:
                actual_text = "士出九宫后获得直走能力"
            elif checkbox == self.xiang_cross_checkbox:
                actual_text = "相可以过河"
            elif checkbox == self.xiang_jump_checkbox:
                actual_text = "相过河后获得隔两格吃子能力"
            elif checkbox == self.ma_straight_checkbox:
                actual_text = "马可以获得直走三格的能力"
            
            # 绘制复选框 - 如果是禁用选项（如将/帅登场），显示为灰色且不可点击
            is_disabled = (actual_text == "将/帅登场")  # 检查是否为将/帅登场选项
            
            # 调整复选框位置以随滚动移动
            adjusted_checkbox = pygame.Rect(checkbox.x, checkbox.y - self.scroll_y, checkbox.width, checkbox.height)
            
            if is_disabled:
                # 灰色表示禁用状态
                pygame.draw.rect(self.screen, (150, 150, 150), adjusted_checkbox, 2)  # 灰色边框
                if setting_var:  # 尽管是禁用的，但值始终为True
                    pygame.draw.line(self.screen, (100, 100, 100),  # 灰色勾选标记
                                     (adjusted_checkbox.left + 4, adjusted_checkbox.centery),
                                     (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4), 2)
                    pygame.draw.line(self.screen, (100, 100, 100),
                                     (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4),
                                     (adjusted_checkbox.right - 4, adjusted_checkbox.top + 4), 2)
            else:
                # 正常状态
                pygame.draw.rect(self.screen, BLACK, adjusted_checkbox, 2)
                if setting_var:
                    pygame.draw.line(self.screen, BLACK,
                                     (adjusted_checkbox.left + 4, adjusted_checkbox.centery),
                                     (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4), 2)
                    pygame.draw.line(self.screen, BLACK,
                                     (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4),
                                     (adjusted_checkbox.right - 4, adjusted_checkbox.top + 4), 2)
            
            # 调整标签位置以随滚动移动
            adjusted_label_pos = (label_text[0], label_text[1] - self.scroll_y)
            
            # 绘制标签 - 禁用选项也显示为灰色
            label_color = (100, 100, 100) if is_disabled else BLACK
            label_surface = self.option_font.render(actual_text, True, label_color)
            self.screen.blit(label_surface, adjusted_label_pos)
            
            # 调整描述位置以随滚动移动
            adjusted_desc_pos = (label_text[0], label_text[1] - self.scroll_y + 25)
            
            # 绘制描述 - 禁用选项也显示为灰色
            desc_color = (150, 150, 150) if is_disabled else (100, 100, 100)
            desc_surface = self.desc_font.render(desc_text, True, desc_color)
            self.screen.blit(desc_surface, adjusted_desc_pos)
            
            item_y += 60
        
        return category_height + self.category_spacing

    def update_max_scroll(self):
        """更新最大滚动值"""
        # 计算内容总高度，包括所有分类
        # 使用与draw方法相同的逻辑来计算总高度
        y_offset = 150  # 初始Y坐标，与draw方法中的一致
        
        # 汉/汗棋子分类
        king_items = self.create_king_items(y_offset)
        category_height = len(king_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 士棋子分类
        shi_items = self.create_shi_items(y_offset)
        category_height = len(shi_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 相棋子分类
        xiang_items = self.create_xiang_items(y_offset)
        category_height = len(xiang_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 马棋子分类
        ma_items = self.create_ma_items(y_offset)
        category_height = len(ma_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 車棋子分类
        ju_items = self.create_ju_items(y_offset)
        category_height = len(ju_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 炮棋子分类
        pao_items = self.create_pao_items(y_offset)
        category_height = len(pao_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 兵/卒棋子分类
        pawn_items = self.create_pawn_items(y_offset)
        category_height = len(pawn_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 尉棋子分类
        wei_items = self.create_wei_items(y_offset)
        category_height = len(wei_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 射棋子分类
        she_items = self.create_she_items(y_offset)
        category_height = len(she_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 檵/檑棋子分类
        lei_items = self.create_lei_items(y_offset)
        category_height = len(lei_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 甲棋子分类
        jia_items = self.create_jia_items(y_offset)
        category_height = len(jia_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 刺棋子分类
        ci_items = self.create_ci_items(y_offset)
        category_height = len(ci_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        # 盾棋子分类
        dun_items = self.create_dun_items(y_offset)
        category_height = len(dun_items) * 60 + self.category_title_height + 2 * self.category_padding
        y_offset = y_offset + category_height + self.category_spacing
        
        total_height = y_offset  # 总高度就是最后一个分类的底部位置
        
        visible_height = self.window_height - 180  # 可视区域高度
        self.max_scroll = max(0, total_height - visible_height)
        
        # 更新滚动条
        self.scroll_bar = ScrollBar(self.window_width - 20, 100, 15, self.window_height - 180, total_height)

    def handle_scroll_event(self, event, mouse_pos):
        """处理滚动事件"""
        # 传递事件给滚动条
        self.scroll_bar.handle_event(event, mouse_pos)
        # 更新滚动位置
        self.scroll_y = self.scroll_bar.get_scroll_offset()
        
        # 限制滚动范围
        self.scroll_y = max(0, min(self.scroll_y, max(0, self.max_scroll)))

    def run(self):
        """运行设置界面"""
        clock = pygame.time.Clock()
        running = True

        while running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    self.window_width, self.window_height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
                    # 重新计算滚动条
                    self.update_max_scroll()

                # 处理滚动事件
                if event.type == pygame.MOUSEWHEEL:
                    # 处理鼠标滚轮
                    self.scroll_y -= event.y * 30  # 滚动距离
                    self.scroll_y = max(0, min(self.scroll_y, max(0, self.max_scroll)))
                    # 同步更新滚动条位置
                    self.scroll_bar.scroll_pos = self.scroll_y
                    self.scroll_bar._update_slider_position()
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                    self.handle_scroll_event(event, mouse_pos)
                    # 更新滚动位置
                    self.scroll_y = self.scroll_bar.get_scroll_offset()
                    # 限制滚动范围
                    self.scroll_y = max(0, min(self.scroll_y, max(0, self.max_scroll)))

                # 处理其他事件
                result = self.handle_event(event, mouse_pos)
                if result == "confirm":
                    # 保存设置并退出
                    self.get_settings()
                    return "confirm"
                elif result == "back":
                    return "back"

            # 绘制界面
            self.draw()

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()

    def create_king_items(self, y_offset):
        """创建汉/汗相关的设置项"""
        return [
            (self.piece_settings["king"]["palace_checkbox"], 
             self.piece_settings["king"]["palace_label"], 
             self.piece_settings["king"]["can_leave_palace"], 
             "汉/汗可以出九宫", 
             "允许汉/汗走出九宫区域", 
             False),
            (self.piece_settings["king"]["diagonal_checkbox"], 
             self.piece_settings["king"]["diagonal_label"], 
             self.piece_settings["king"]["lose_diagonal_outside_palace"], 
             "汉/汗出九宫后失去斜走能力", 
             "汉/汗走出九宫后只能横竖走，不能斜走", 
             False),
            (self.piece_settings["king"]["diagonal_in_palace_checkbox"], 
             self.piece_settings["king"]["diagonal_in_palace_label"], 
             self.piece_settings["king"]["can_diagonal_in_palace"], 
             "汉/汗在九宫内可以斜走", 
             "汉/汗在九宫内允许斜向移动", 
             False),
            (self.piece_settings["king"]["appear_checkbox"], 
             self.piece_settings["king"]["appear_label"], 
             True,  # 将/帅必须登场，固定为True
             "将/帅登场", 
             "将/帅必须登场（此选项不可更改）", 
             True)  # 永远禁用
        ]

    def create_shi_items(self, y_offset):
        """创建士相关的设置项"""
        return [
            (self.piece_settings["shi"]["palace_checkbox"], 
             self.piece_settings["shi"]["palace_label"], 
             self.piece_settings["shi"]["can_leave_palace"], 
             "士可以出九宫", 
             "允许士走出九宫区域", 
             False),
            (self.piece_settings["shi"]["straight_checkbox"], 
             self.piece_settings["shi"]["straight_label"], 
             self.piece_settings["shi"]["gain_straight_outside_palace"], 
             "士出九宫后获得直走能力", 
             "士走出九宫后可以横竖移动", 
             False),
            (self.piece_settings["shi"]["appear_checkbox"], 
             self.piece_settings["shi"]["appear_label"], 
             self.piece_settings["shi"]["appear"], 
             "士登场", 
             "士登场", 
             False)
        ]

    def create_xiang_items(self, y_offset):
        """创建相相关的设置项"""
        return [
            (self.piece_settings["xiang"]["cross_checkbox"], 
             self.piece_settings["xiang"]["cross_label"], 
             self.piece_settings["xiang"]["can_cross_river"], 
             "相可以过河", 
             "允许相跨越楚河汉界", 
             False),
            (self.piece_settings["xiang"]["jump_checkbox"], 
             self.piece_settings["xiang"]["jump_label"], 
             self.piece_settings["xiang"]["gain_jump_two_outside_river"], 
             "相过河后获得隔两格吃子能力", 
             "相过河后可横竖方向隔一格吃子", 
             False),
            (self.piece_settings["xiang"]["appear_checkbox"], 
             self.piece_settings["xiang"]["appear_label"], 
             self.piece_settings["xiang"]["appear"], 
             "相登场", 
             "相登场", 
             False)
        ]

    def create_ma_items(self, y_offset):
        """创建马相关的设置项"""
        return [
            (self.piece_settings["ma"]["straight_checkbox"], 
             self.piece_settings["ma"]["straight_label"], 
             self.piece_settings["ma"]["can_straight_three"], 
             "马可以获得直走三格的能力", 
             "马可以横竖方向走三格", 
             False),
            (self.piece_settings["ma"]["appear_checkbox"], 
             self.piece_settings["ma"]["appear_label"], 
             self.piece_settings["ma"]["appear"], 
             "馬登场", 
             "馬登场", 
             False)
        ]

    def create_ju_items(self, y_offset):
        """创建車相关的设置项"""
        return [
            (self.piece_settings["ju"]["appear_checkbox"], 
             self.piece_settings["ju"]["appear_label"], 
             self.piece_settings["ju"]["appear"], 
             "車登场", 
             "車登场", 
             False)
        ]

    def create_pao_items(self, y_offset):
        """创建炮相关的设置项"""
        return [
            (self.piece_settings["pao"]["appear_checkbox"], 
             self.piece_settings["pao"]["appear_label"], 
             self.piece_settings["pao"]["appear"], 
             "炮登场", 
             "炮登场", 
             False)
        ]

    def create_pawn_items(self, y_offset):
        """创建兵/卒相关的设置项"""
        return [
            (self.piece_settings["pawn"]["appear_checkbox"], 
             self.piece_settings["pawn"]["appear_label"], 
             self.piece_settings["pawn"]["appear"], 
             "兵/卒登场", 
             "兵/卒登场", 
             False)
        ]

    def create_wei_items(self, y_offset):
        """创建尉相关的设置项"""
        return [
            (self.piece_settings["wei"]["appear_checkbox"], 
             self.piece_settings["wei"]["appear_label"], 
             self.piece_settings["wei"]["appear"], 
             "尉登场", 
             "尉登场", 
             False)
        ]

    def create_she_items(self, y_offset):
        """创建射相关的设置项"""
        return [
            (self.piece_settings["she"]["appear_checkbox"], 
             self.piece_settings["she"]["appear_label"], 
             self.piece_settings["she"]["appear"], 
             "射登场", 
             "射登场", 
             False)
        ]

    def create_lei_items(self, y_offset):
        """创建檑相关的设置项"""
        return [
            (self.piece_settings["lei"]["appear_checkbox"], 
             self.piece_settings["lei"]["appear_label"], 
             self.piece_settings["lei"]["appear"], 
             "檑登场", 
             "檑登场", 
             False)
        ]

    def create_jia_items(self, y_offset):
        """创建甲相关的设置项"""
        return [
            (self.piece_settings["jia"]["appear_checkbox"], 
             self.piece_settings["jia"]["appear_label"], 
             self.piece_settings["jia"]["appear"], 
             "甲登场", 
             "甲登场", 
             False)
        ]

    def create_ci_items(self, y_offset):
        """创建刺相关的设置项"""
        return [
            (self.piece_settings["ci"]["appear_checkbox"], 
             self.piece_settings["ci"]["appear_label"], 
             self.piece_settings["ci"]["appear"], 
             "刺登场", 
             "刺登场", 
             False)
        ]

    def create_dun_items(self, y_offset):
        """创建盾相关的设置项"""
        return [
            (self.piece_settings["dun"]["appear_checkbox"], 
             self.piece_settings["dun"]["appear_label"], 
             self.piece_settings["dun"]["appear"], 
             "盾登场", 
             "盾登场", 
             False)
        ]

    def create_game_mode_items(self, y_offset):
        """创建游戏模式相关的设置项"""
        return [
            (self.piece_settings["game_mode"]["classic_checkbox"], 
             self.piece_settings["game_mode"]["classic_label"], 
             self.piece_settings["game_mode"]["classic_mode"], 
             "经典模式", 
             "采用传统布局，只包含车、马、相、士、将/帅、炮、兵/卒，以及新增的射和檑", 
             False)
        ]
