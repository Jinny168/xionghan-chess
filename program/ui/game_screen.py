"""游戏主界面UI管理模块"""
import pygame

from program.config.config import (
    LEFT_PANEL_WIDTH_RATIO, BOARD_MARGIN_TOP_RATIO,
    PANEL_BORDER, BLACK, RED
)
from program.config.taunts_manager import taunt_manager
from program.ui.avatar import Avatar
from program.ui.button import Button
from program.ui.chess_board import ChessBoard
from program.ui.dialogs import AudioSettingsDialog
from program.utils.utils import load_font, draw_background


class MenuItem:
    """菜单项类"""
    def __init__(self, text, action=None, separator=False):
        self.text = text
        self.action = action
        self.separator = separator
        self.rect = None
        

class Menu:
    """菜单类"""
    def __init__(self, x, y, width, title="菜单", collapsed=True):
        self.x = x
        self.y = y
        self.width = width
        self.title = title
        self.collapsed = collapsed
        self.items = []
        self.item_height = 35
        self.font = load_font(18)
        self.hovered_item = None
        
    def add_item(self, text, action=None, separator=False):
        """添加菜单项"""
        item = MenuItem(text, action, separator)
        self.items.append(item)
        
    def toggle(self):
        """切换菜单展开/折叠状态"""
        self.collapsed = not self.collapsed
        
    def get_height(self):
        """获取菜单实际高度"""
        height = 0
        for item in self.items:
            if not item.separator:
                height += self.item_height
            else:
                height += 10  # 分隔符高度
        return height
        
    def get_rect(self):
        """获取菜单矩形区域"""
        if self.collapsed:
            return pygame.Rect(self.x, self.y, self.width, 30)
        else:
            return pygame.Rect(self.x, self.y, self.width, 30 + self.get_height())
        
    def handle_event(self, event, mouse_pos):
        """处理菜单事件"""
        menu_rect = self.get_rect()
        if not menu_rect.collidepoint(mouse_pos):
            return None
            
        # 检查是否点击了菜单标题区域（包括齿轮图标）
        title_rect = pygame.Rect(self.x, self.y, self.width, 30)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and title_rect.collidepoint(mouse_pos):
            self.toggle()
            return "toggle"
            
        # 如果菜单是展开的，检查菜单项点击
        if not self.collapsed:
            item_y = self.y + 30
            for item in self.items:
                if item.separator:
                    item_y += 10
                    continue
                item_rect = pygame.Rect(self.x, item_y, self.width, self.item_height)
                if item_rect.collidepoint(mouse_pos):
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if item.action:
                            return item.action
                        return item.text
                item_y += self.item_height
                    
        return None
        
    def draw(self, screen):
        """绘制菜单"""
        # 绘制菜单标题
        title_color = (50, 50, 150) if self.hovered_item == -1 else (100, 100, 200)
        pygame.draw.rect(screen, title_color, (self.x, self.y, self.width, 30))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, 30), 2)
        
        # 绘制标题文本
        title_text = self.font.render(self.title, True, BLACK)
        screen.blit(title_text, (self.x + 10, self.y + 5))
        
        # 绘制齿轮图标替代展开/折叠箭头
        gear_text = "⚙"  # 使用齿轮图标
        gear_surface = self.font.render(gear_text, True, BLACK)
        screen.blit(gear_surface, (self.x + self.width - 30, self.y + 5))
        
        # 如果菜单是展开的，绘制菜单项
        if not self.collapsed:
            item_y = self.y + 30
            for i, item in enumerate(self.items):
                if item.separator:
                    # 绘制分隔线
                    pygame.draw.line(screen, (150, 150, 150), (self.x, item_y + 5), (self.x + self.width, item_y + 5), 2)
                    item_y += 10
                    continue
                    
                item_rect = pygame.Rect(self.x, item_y, self.width, self.item_height)
                
                # 绘制菜单项背景
                if self.hovered_item == i:
                    pygame.draw.rect(screen, (200, 200, 255), item_rect)
                else:
                    pygame.draw.rect(screen, (240, 240, 240), item_rect)
                pygame.draw.rect(screen, (150, 150, 150), item_rect, 1)
                
                # 绘制菜单项文本
                item_text = self.font.render(item.text, True, BLACK)
                screen.blit(item_text, (self.x + 10, item_y + 8))
                
                item_y += self.item_height
        
    def check_hover(self, mouse_pos):
        """检查鼠标悬停状态"""
        menu_rect = self.get_rect()
        if not menu_rect.collidepoint(mouse_pos):
            self.hovered_item = None
            return
            
        # 检查是否悬停在菜单标题上
        title_rect = pygame.Rect(self.x, self.y, self.width, 30)
        if title_rect.collidepoint(mouse_pos):
            self.hovered_item = -1
            return
            
        # 如果菜单是展开的，检查菜单项
        if not self.collapsed:
            item_y = self.y + 30
            for i, item in enumerate(self.items):
                if item.separator:
                    item_y += 10
                    continue
                item_rect = pygame.Rect(self.x, item_y, self.width, self.item_height)
                if item_rect.collidepoint(mouse_pos):
                    self.hovered_item = i
                    return
                item_y += self.item_height
            
        self.hovered_item = None


class OperationPanel:
    """操作面板类，包含常用操作按钮"""
    def __init__(self, board_right, window_height):
        self.board_right = board_right
        self.window_height = window_height
        self.expanded = False
        self.buttons = {}
        self.toggle_button = None
        self.update_positions()
        
    def update_positions(self):
        """更新操作面板按钮位置"""
        # 操作按钮（齿轮图标按钮）
        button_size = 40
        self.toggle_button = Button(
            self.board_right - button_size - 10,
            self.window_height - button_size - 10,
            button_size,
            button_size,
            "⚙",
            24
        )
        
        # 展开后的按钮
        button_width = 100
        button_height = 35
        button_y = self.window_height - 50 - button_height
        
        # 计算按钮位置（水平排列）
        num_buttons = 5
        total_width = num_buttons * button_width + (num_buttons - 1) * 10
        start_x = self.board_right - total_width
        
        self.buttons["undo"] = Button(
            start_x,
            button_y,
            button_width,
            button_height,
            "悔棋",
            18
        )
        
        self.buttons["restart"] = Button(
            start_x + button_width + 10,
            button_y,
            button_width,
            button_height,
            "重来",
            18
        )
        
        self.buttons["back"] = Button(
            start_x + 2 * (button_width + 10),
            button_y,
            button_width,
            button_height,
            "返回",
            18
        )
        
        self.buttons["exit"] = Button(
            start_x + 3 * (button_width + 10),
            button_y,
            button_width,
            button_height,
            "退出",
            18
        )
        
        self.buttons["taunt"] = Button(
            start_x + 4 * (button_width + 10),
            button_y,
            button_width,
            button_height,
            "嘲讽",
            18
        )
        
    def toggle(self):
        """切换操作面板展开/折叠"""
        self.expanded = not self.expanded
        
    def handle_event(self, event, mouse_pos):
        """处理操作面板事件"""
        # 检查是否点击了展开按钮
        if self.toggle_button.is_clicked(mouse_pos, event):
            self.toggle()
            return "toggle"
            
        # 如果面板展开，检查其他按钮
        if self.expanded:
            for key, button in self.buttons.items():
                if button.is_clicked(mouse_pos, event):
                    return key
        
        return None
        
    def draw(self, screen):
        """绘制操作面板"""
        # 绘制展开/折叠按钮
        self.toggle_button.draw(screen)
        
        # 如果面板展开，绘制操作按钮
        if self.expanded:
            for button in self.buttons.values():
                button.draw(screen)
        
    def update_hover(self, mouse_pos):
        """更新按钮悬停状态"""
        self.toggle_button.check_hover(mouse_pos)
        if self.expanded:
            for button in self.buttons.values():
                button.check_hover(mouse_pos)


class TauntAnimation:
    """嘲讽动画类"""
    def __init__(self, window_width, window_height):
        self.window_width = window_width
        self.window_height = window_height
        self.text = taunt_manager.get_random_taunt()
        self.font = load_font(36, bold=True)
        self.text_surface = self.font.render(self.text, True, (255, 0, 0))  # 红色文字
        self.text_width = self.text_surface.get_width()
        
        # 动画参数
        self.start_x = self.window_width  # 从屏幕右侧开始
        self.end_x = -self.text_width     # 到屏幕左侧结束
        self.current_x = self.start_x
        self.speed = 5  # 每帧移动像素
        self.active = False
        
    def start(self):
        """开始动画"""
        # 随机选择一个新的嘲讽语句
        self.text = taunt_manager.get_random_taunt()
        # 重新渲染文本表面
        self.text_surface = self.font.render(self.text, True, (255, 0, 0))
        self.text_width = self.text_surface.get_width()
        
        self.current_x = self.start_x
        self.active = True
        
    def update(self):
        """更新动画位置"""
        if self.active:
            self.current_x -= self.speed
            if self.current_x < self.end_x:
                self.active = False
                return False  # 动画结束
        return True  # 动画继续
        
    def draw(self, screen):
        """绘制动画"""
        if self.active:
            y_pos = self.window_height // 2 - 50  # 在屏幕中央上方显示
            screen.blit(self.text_surface, (self.current_x, y_pos))


def draw_info_panel(screen, game_state):
    """绘制游戏信息面板"""
    # 当游戏进行中，在左上角显示当前回合
    if not game_state.game_over:
        # 创建回合信息文本
        turn_color = RED if game_state.player_turn == "red" else BLACK
        turn_text = f"当前回合: {'红方' if game_state.player_turn == 'red' else '黑方'}"

        # 计算位置 - 在左上角，对局时长下方，避开菜单栏
        font = load_font(20)
        text_surface = font.render(turn_text, True, turn_color)
        # 位于对局时长信息的下方
        text_rect = text_surface.get_rect(
            topleft=(10, 75)  # 在左上角，对局时长下方，避开菜单栏
        )
        screen.blit(text_surface, text_rect)


class GameScreen:
    """管理游戏主界面的UI组件和绘制逻辑"""
    
    def __init__(self, window_width, window_height, game_mode, player_camp):
        """初始化游戏界面组件"""
        self.window_width = window_width
        self.window_height = window_height
        self.game_mode = game_mode
        self.player_camp = player_camp
        
        # 初始化界面组件
        self.board = None
        self.red_avatar = None
        self.black_avatar = None
        self.timer_font = None
        
        # 按钮组件
        self.back_button = None
        self.restart_button = None
        self.exit_button = None
        self.undo_button = None
        self.fullscreen_button = None
        self.audio_settings_button = None
        self.import_button = None
        self.export_button = None
        
        # 布局参数
        self.left_panel_width = None
        self.board_margin_top = None
        
        # 新增：菜单系统
        self.option_menu = None
        self.help_menu = None
        self.operation_panel = None
        self.taunt_animation = None
        
        # 预创建左侧面板背景Surface
        self.left_panel_surface_cache = None
        self.left_panel_overlay_cache = None
        
        # 初始化所有UI组件
        self.init_ui_components()
        
    def init_ui_components(self):
        """初始化所有UI组件"""
        self.update_layout()
        # 初始化菜单系统
        self.init_menus()
        # 初始化操作面板
        self.init_operation_panel()
        # 初始化嘲讽动画
        self.init_taunt_animation()
        
    def init_menus(self):
        """初始化菜单系统"""
        # 选项菜单 - 放在左上角，避开左侧面板
        # 确保菜单不会遮挡其他界面元素
        self.option_menu = Menu(10, 10, 150, "选项", collapsed=True)
        self.option_menu.add_item("导入棋局")
        self.option_menu.add_item("导出棋局")
        self.option_menu.add_item("", separator=True)  # 分隔符
        self.option_menu.add_item("音效设置")
        self.option_menu.add_item("", separator=True)  # 分隔符
        self.option_menu.add_item("窗口切换")
        self.option_menu.add_item("", separator=True)  # 分隔符
        self.option_menu.add_item("统计数据")
        
        # 帮助菜单 - 紧邻选项菜单，但需要确保不遮挡其他元素
        self.help_menu = Menu(170, 10, 150, "帮助", collapsed=True)
        self.help_menu.add_item("游戏规则")
        self.help_menu.add_item("关于")
        
    def init_operation_panel(self):
        """初始化操作面板"""
        self.operation_panel = OperationPanel(
            self.window_width - self.left_panel_width,  # 棋盘右侧
            self.window_height
        )
        
    def init_taunt_animation(self):
        """初始化嘲讽动画"""
        self.taunt_animation = TauntAnimation(self.window_width, self.window_height)
        
    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        # 计算左侧面板宽度和棋盘边距
        old_width, old_height = getattr(self, 'left_panel_width', 0), getattr(self, 'window_height', 0)
        
        self.left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * self.window_width)
        self.board_margin_top = int(BOARD_MARGIN_TOP_RATIO * self.window_height)
        
        # 确保棋盘和其他组件有足够的间距，避免被菜单遮挡
        # 为菜单栏预留空间，增加顶部边距
        adjusted_board_margin_top = max(self.board_margin_top, 80)  # 确保有足够空间给菜单
        
        # 如果窗口尺寸发生变化，清除缓存的Surface
        if old_width != self.left_panel_width or old_height != self.window_height:
            self.left_panel_surface_cache = None
            self.left_panel_overlay_cache = None

        # 更新棋盘 - 整体右移，确保不被菜单遮挡
        self.board = ChessBoard(
            self.window_width - self.left_panel_width - 40,  # 增加更多右边距
            self.window_height,
            self.left_panel_width + 30,  # 棋盘起始位置右移更多
            adjusted_board_margin_top  # 使用调整后的顶部边距
        )

        # 更新操作面板位置
        if self.operation_panel:
            self.operation_panel.update_positions()

        # 创建按钮
        self.create_buttons()

        # 创建头像
        self.create_avatars()

        # 计时器的字体
        self.timer_font = load_font(18)
        
        # 初始化缓存Surface
        self.left_panel_surface_cache = None
        self.left_panel_overlay_cache = None
        
    def _draw_background_and_side_panel(self, screen):
        """绘制背景和左侧边栏"""
        # 使用统一的背景绘制函数
        draw_background(screen)
        
        # 绘制左侧面板背景
        # 检查缓存的Surface是否仍然有效（大小匹配）
        if (self.left_panel_surface_cache is None or 
            self.left_panel_surface_cache.get_size() != (self.left_panel_width, self.window_height)):
            # 创建新的缓存Surface
            self.left_panel_surface_cache = pygame.Surface((self.left_panel_width, self.window_height))
            self.left_panel_overlay_cache = pygame.Surface((self.left_panel_width, self.window_height), pygame.SRCALPHA)
            self.left_panel_overlay_cache.fill((255, 255, 255, 30))  # 半透明白色覆盖，轻微增亮
            
            # 绘制背景到缓存Surface
            draw_background(self.left_panel_surface_cache)
            # 应用半透明覆盖
            self.left_panel_surface_cache.blit(self.left_panel_overlay_cache, (0, 0))
        
        # 应用到主界面
        screen.blit(self.left_panel_surface_cache, (0, 0))
        
        # 添加分隔线
        pygame.draw.line(screen, PANEL_BORDER, (self.left_panel_width, 0),
                         (self.left_panel_width, self.window_height), 2)
        
    def create_buttons(self):
        """创建所有按钮"""
        # 移除底部的重复功能按钮，只保留全屏和音效设置按钮
        # 因为功能已整合到菜单中，所以不再创建重复的按钮
        button_width = 80
        button_height = 30
        
        # 创建全屏切换按钮
        self.fullscreen_button = Button(
            self.window_width - button_width - 10,
            10,
            button_width,
            button_height,
            "全屏" if self.window_width != pygame.display.Info().current_w else "窗口",
            14
        )
        # 音效设置按钮放在全屏按钮下方
        self.audio_settings_button = Button(
            self.window_width - button_width - 10,
            50,
            button_width,
            button_height,
            "音效",
            14
        )

    def create_avatars(self):
        """创建玩家头像"""
        avatar_radius = 40
        panel_center_x = self.left_panel_width // 2
        # 调整头像位置，避免与菜单栏重叠
        black_y = self.window_height // 3 - 80  # 增加顶部间距
        red_y = self.window_height * 2 // 3 + 30  # 增加与黑方头像的间距

        # 创建头像
        self.black_avatar = Avatar(panel_center_x, black_y, avatar_radius, (245, 245, 235), "黑方", False)
        self.red_avatar = Avatar(panel_center_x, red_y, avatar_radius, (255, 255, 240), "红方", True)

    def update_avatars(self, game_state):
        """更新头像状态"""
        is_red_turn = game_state.player_turn == "red"
        self.red_avatar.set_active(is_red_turn)
        self.black_avatar.set_active(not is_red_turn)

        # 更新玩家标识
        if self.game_mode == "pvc":  # MODE_PVC
            if self.player_camp == "red":  # CAMP_RED
                self.red_avatar.player_name = "玩家"
                self.black_avatar.player_name = "电脑"
            else:
                self.red_avatar.player_name = "电脑"
                self.black_avatar.player_name = "玩家"
        else:
            self.red_avatar.player_name = "红方"
            self.black_avatar.player_name = "黑方"

    def update_button_states(self, mouse_pos):
        """更新按钮悬停状态"""
        # 更新全屏按钮悬停状态
        if self.fullscreen_button:
            self.fullscreen_button.check_hover(mouse_pos)
        # 更新音效设置按钮悬停状态
        if self.audio_settings_button:
            self.audio_settings_button.check_hover(mouse_pos)
        
        # 更新菜单悬停状态
        self.option_menu.check_hover(mouse_pos)
        self.help_menu.check_hover(mouse_pos)
        
        # 更新操作面板按钮悬停状态
        if self.operation_panel:
            self.operation_panel.update_hover(mouse_pos)

    def draw(self, screen, game_state, last_move=None, last_move_notation="",
             popup=None, confirm_dialog=None, pawn_resurrection_dialog=None,
             promotion_dialog=None, audio_settings_dialog=None):
        """绘制整个游戏界面"""
        # 绘制完整的界面背景
        self._draw_background_and_side_panel(screen)

        # 绘制棋盘和棋子 - 已经右移以避免被菜单遮挡
        self.board.draw(screen, game_state.pieces, game_state)

        # 如果有上一步走法，在棋盘上标记出来
        if last_move:
            from_row, from_col, to_row, to_col = last_move
            self.board.highlight_last_move(screen, from_row, from_col, to_row, to_col)

        # 检查是否需要显示将军动画
        if game_state.should_show_check_animation():
            king_pos = game_state.get_checked_king_position()
            if king_pos:
                self.board.draw_check_animation(screen, king_pos, game_state)

        # 绘制游戏信息面板
        draw_info_panel(screen, game_state)

        # 绘制按钮 - 只绘制必要的按钮
        self.draw_buttons(screen)

        # 绘制玩家头像
        self.red_avatar.draw(screen)
        self.black_avatar.draw(screen)

        # 绘制计时器信息
        self.draw_timers(screen, game_state)

        # 在左侧面板中添加VS标志
        vs_font = load_font(36, bold=True)
        vs_text = "VS"
        vs_surface = vs_font.render(vs_text, True, (100, 100, 100))
        vs_rect = vs_surface.get_rect(center=(self.left_panel_width // 2, self.window_height // 2))
        screen.blit(vs_surface, vs_rect)

        # 如果有上一步走法的记录，显示它
        if last_move_notation:
            move_font = load_font(18)
            move_text = f"上一步: {last_move_notation}"
            move_surface = move_font.render(move_text, True, BLACK)
            # 显示在左侧面板底部
            move_rect = move_surface.get_rect(center=(self.left_panel_width // 2, self.window_height - 80))
            screen.blit(move_surface, move_rect)

        # 如果是人机模式，显示模式和阵营提示
        if self.game_mode == "pvc":  # MODE_PVC
            mode_font = load_font(18)
            if self.player_camp == "red":  # CAMP_RED
                mode_text = "人机对战模式 - 您执红方"
            else:
                mode_text = "人机对战模式 - 您执黑方"
            mode_surface = mode_font.render(mode_text, True, BLACK)
            screen.blit(mode_surface, (
                self.left_panel_width + (self.window_width - self.left_panel_width) // 2 - mode_surface.get_width() // 2,
                15))

        # 绘制 captured pieces（阵亡棋子）
        self.draw_captured_pieces(screen, game_state)

        # 绘制棋谱历史记录
        self.draw_move_history(screen, game_state)

        # 绘制菜单
        self.option_menu.draw(screen)
        self.help_menu.draw(screen)

        # 绘制操作面板
        if self.operation_panel:
            self.operation_panel.draw(screen)

        # 更新和绘制嘲讽动画
        if self.taunt_animation:
            self.taunt_animation.update()
            self.taunt_animation.draw(screen)

        # 如果游戏结束，显示弹窗
        if popup:
            popup.draw(screen)

        # 如果有确认对话框，显示它
        if confirm_dialog:
            confirm_dialog.draw(screen)

        # 如果有兵/卒复活对话框，显示它
        if pawn_resurrection_dialog:
            pawn_resurrection_dialog.draw(screen)

        # 如果有升变对话框，显示它
        if promotion_dialog:
            promotion_dialog.draw(screen)

        # 如果有音效设置对话框，显示它
        if audio_settings_dialog:
            audio_settings_dialog.draw(screen)

    def draw_thinking_indicator(self, screen, game_state):
        """绘制AI思考时的指示器，减少闪烁"""
        # 绘制完整的界面背景
        self._draw_background_and_side_panel(screen)

        # 绘制棋盘和棋子（使用稳定的游戏状态）
        self.board.draw(screen, game_state.pieces, game_state)

    def draw_timers(self, screen, game_state):
        """绘制计时器信息"""
        # 获取当前的时间状态
        red_time, black_time = game_state.update_times()
        total_time = game_state.total_time

        # 转换为分钟:秒格式
        red_time_str = f"{int(red_time // 60):02}:{int(red_time % 60):02}"
        black_time_str = f"{int(black_time // 60):02}:{int(black_time % 60):02}"
        total_time_str = f"{int(total_time // 60):02}:{int(total_time % 60):02}"

        # 绘制总时间 - 在左上角，但避开菜单栏
        total_time_surface = self.timer_font.render(f"对局时长: {total_time_str}", True, BLACK)
        screen.blit(total_time_surface, (10, 45))  # 将Y坐标从10改为45，避开菜单

        # 绘制红方时间 - 在红方头像下方
        red_time_surface = self.timer_font.render(f"用时: {red_time_str}", True, RED)
        red_time_rect = red_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.red_avatar.y + self.red_avatar.radius + 60)  # 增加间距
        )
        screen.blit(red_time_surface, red_time_rect)

        # 绘制黑方时间 - 在黑方头像下方
        black_time_surface = self.timer_font.render(f"用时: {black_time_str}", True, BLACK)
        black_time_rect = black_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.black_avatar.y + self.black_avatar.radius + 60)  # 增加间距
        )
        screen.blit(black_time_surface, black_time_rect)

    def handle_menu_events(self, event, mouse_pos, game, game_state):
        """处理菜单事件"""
        # 处理选项菜单事件
        option_result = self.option_menu.handle_event(event, mouse_pos)
        if option_result == "toggle":
            # 选项菜单切换展开/折叠，不需要进一步处理
            pass
        elif option_result == "导入棋局":
            from program.controllers.game_io_controller import game_io_controller
            if game_io_controller.import_game(game_state):
                # 进入复盘模式
                from program.controllers.replay_controller import ReplayController
                from program.ui.replay_screen import ReplayScreen
                
                replay_controller = ReplayController(game_state)
                replay_controller.start_replay()
                
                replay_screen = ReplayScreen(game_state, replay_controller)
                replay_screen.run()
            return "handled"
        elif option_result == "导出棋局":
            from program.controllers.game_io_controller import game_io_controller
            game_io_controller.export_game(game_state)
            return "handled"
        elif option_result == "音效设置":
            game.audio_settings_dialog = AudioSettingsDialog(600, 400, game.sound_manager)
            return "handled"
        elif option_result == "窗口切换":
            game.toggle_fullscreen()
            return "handled"
        elif option_result == "统计数据":
            # 打开统计数据界面
            from program.ui.dialogs import StatisticsDialog
            game.stats_dialog = StatisticsDialog()
            return "handled"
        
        # 处理帮助菜单事件
        help_result = self.help_menu.handle_event(event, mouse_pos)
        if help_result == "toggle":
            # 帮助菜单切换展开/折叠，不需要进一步处理
            pass
        elif help_result == "游戏规则":
            # 打开游戏规则界面
            from program.ui.rules_screen import RulesScreen
            rules_screen = RulesScreen()
            rules_screen.run()
            return "handled"
        elif help_result == "关于":
            # 打开关于界面，显示作者信息
            from program.ui.about_screen import AboutScreen
            # 创建AboutScreen实例，使用当前游戏窗口尺寸
            game.about_screen = AboutScreen(self.window_width, self.window_height)
            return "handled"
        
        return None

    def handle_operation_panel_events(self, event, mouse_pos, game):
        """处理操作面板事件"""
        if not self.operation_panel:
            return None
            
        op_result = self.operation_panel.handle_event(event, mouse_pos)
        if op_result == "toggle":
            # 操作面板切换展开/折叠，不需要进一步处理
            return "handled"
        elif op_result == "undo":
            from program.controllers.input_handler import input_handler
            input_handler.handle_undo(game)
            return "handled"
        elif op_result == "restart":
            game.restart_game()
            return "handled"
        elif op_result == "back":
            from program.ui.dialogs import ConfirmDialog
            game.confirm_dialog = ConfirmDialog(400, 200, "是否要返回主菜单？\n这将丢失您的当前对局信息。")
            return "handled"
        elif op_result == "exit":
            from program.ui.dialogs import ConfirmDialog
            game.confirm_dialog = ConfirmDialog(400, 200, "是否要退出游戏？\n这将结束当前对局。")
            return "handled"
        elif op_result == "taunt":
            if self.taunt_animation:
                self.taunt_animation.start()
            return "handled"
        
        return None

    def draw_buttons(self, screen):
        """绘制所有按钮"""
        # 不再绘制音效和全屏按钮，因为它们的功能已整合到菜单中
        # 保留此方法以备将来可能的其他按钮使用
        pass

    def draw_captured_pieces(self, screen, game_state):
        """绘制双方阵亡棋子"""
        # 绘制标题
        title_font = load_font(20, bold=True)
        red_title = title_font.render("红方阵亡:", True, RED)
        black_title = title_font.render("黑方阵亡:", True, BLACK)

        # 将阵亡棋子信息移到右侧
        right_panel_x = self.window_width - 250  # 右侧边栏起始x坐标
        screen.blit(red_title, (right_panel_x, 60))
        screen.blit(black_title, (right_panel_x, 180))

        # 定义颜色和位置配置
        configurations = [
            {"color": "red", "x_start": right_panel_x, "y_start": 90, "text_color": RED},
            {"color": "black", "x_start": right_panel_x, "y_start": 210, "text_color": BLACK}
        ]

        # 绘制阵亡棋子
        for config in configurations:
            x, y = config["x_start"], config["y_start"]
            for piece in game_state.captured_pieces[config["color"]]:
                piece_text = title_font.render(piece.name, True, config["text_color"])
                # 减小右边距，提供更多空间给棋子显示
                if x + piece_text.get_width() > self.window_width - 40:
                    x = config["x_start"]
                    y += 25
                screen.blit(piece_text, (x, y))
                x += piece_text.get_width() + 5

    def draw_move_history(self, screen, game_state):
        """绘制棋谱历史记录"""
        # 只显示最近的棋谱记录
        if hasattr(game_state, 'move_history') and game_state.move_history:
            # 绘制标题
            title_font = load_font(20, bold=True)
            history_title = title_font.render("棋谱历史:", True, BLACK)
            screen.blit(history_title, (self.window_width - 250, 300))

            # 显示最近的10条记录
            recent_moves = game_state.move_history[-10:]
            start_y = 330  # 起始y坐标
            line_spacing = 25  # 行间距

            for i, move_record in enumerate(recent_moves):
                # 处理新旧格式的历史记录
                if len(move_record) >= 8:  # 新格式：包含甲/胄吃子信息和刺兑子信息
                    piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces, ci_captured_pieces = move_record
                elif len(move_record) >= 7:  # 新格式：包含甲/胄吃子信息
                    piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces = move_record
                else:  # 旧格式：6个元素
                    piece, from_row, from_col, to_row, to_col, captured_piece = move_record

                # 生成棋谱记号
                from program.utils import tools
                notation = tools.generate_move_notation(piece, from_row, from_col, to_row, to_col)

                # 计算正确编号，避免负数
                move_index = max(0, len(game_state.move_history) - 10) + i + 1

                # 根据玩家颜色确定文字颜色
                if piece.color == "red":
                    move_text = f"{move_index}. {notation}"
                    text_surface = load_font(16).render(move_text, True, RED)
                else:
                    text_surface = load_font(16).render(f"{move_index}. {notation}", True, BLACK)

                # 绘制文本
                screen.blit(text_surface, (self.window_width - 250, start_y + i * line_spacing))