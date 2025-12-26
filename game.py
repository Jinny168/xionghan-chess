import os
import random
import sys
from datetime import time

import pygame

from chess_ai import ChessAI
from chess_board import ChessBoard
from chess_pieces import King, Jia
from game_rules import GameRules
from game_state import GameState
from ui_elements import Avatar, Button
from dialogs import PopupDialog, ConfirmDialog
from utils import load_font
from config import game_config

# 初始化PyGame
pygame.init()
pygame.mixer.init()  # 初始化音频模块

# 常量定义
DEFAULT_WINDOW_WIDTH = 1200  # 默认窗口宽度
DEFAULT_WINDOW_HEIGHT = 900  # 默认窗口高度

LEFT_PANEL_WIDTH_RATIO = 130 / 850  # 左侧面板宽度比例
BOARD_MARGIN_TOP_RATIO = 50 / 850  # 棋盘顶部边距比例
FPS = 60

# 颜色定义
BACKGROUND_COLOR = (240, 217, 181)  # 更温暖的背景色
PANEL_COLOR = (230, 210, 185)       # 面板背景色
PANEL_BORDER = (160, 140, 110)      # 面板边框色
BLACK = (0, 0, 0)
RED = (180, 30, 30)  # 更深的红色
GREEN = (0, 128, 0)
WHITE = (255, 255, 255)
POPUP_BG = (250, 240, 230)  # 更亮的弹窗背景色
BUTTON_COLOR = (100, 100, 200)
BUTTON_HOVER = (120, 120, 220)
BUTTON_TEXT = (240, 240, 255)
GOLD = (218, 165, 32)
LAST_MOVE_SOURCE = (0, 200, 80, 100)      # 上一步起点颜色（绿色半透明）
LAST_MOVE_TARGET = (0, 200, 80, 150)      # 上一步终点颜色（绿色半透明但更深）

# 游戏模式
MODE_PVP = "pvp"  # 人人对战
MODE_PVC = "pvc"  # 人机对战

# 玩家阵营
CAMP_RED = "red"   # 玩家执红
CAMP_BLACK = "black"  # 玩家执黑

def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容PyInstaller打包后的环境"""
    try:
        # PyInstaller创建的临时文件夹存储在sys._MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# 加载音效
try:
    # 使用完整路径加载音效
    check_sound_path = resource_path(os.path.join("sounds", "check.wav"))
    move_sound_path = resource_path(os.path.join("sounds", "move.wav"))
    capture_sound_path = resource_path(os.path.join("sounds", "capture.wav"))
    
    CHECK_SOUND = pygame.mixer.Sound(check_sound_path)
    MOVE_SOUND = pygame.mixer.Sound(move_sound_path)
    CAPTURE_SOUND = pygame.mixer.Sound(capture_sound_path)
    
    # 设置音量（值范围0.0到1.0）
    CHECK_SOUND.set_volume(0.8)  # 将军音效音量设为80%
    MOVE_SOUND.set_volume(0.6)   # 移动音效音量设为60%
    CAPTURE_SOUND.set_volume(0.7) # 吃子音效音量设为70%
except Exception as e:
    # 如果找不到音效文件，创建空声音对象
    CHECK_SOUND = pygame.mixer.Sound(bytes(bytearray(100)))
    MOVE_SOUND = pygame.mixer.Sound(bytes(bytearray(100)))
    CAPTURE_SOUND = pygame.mixer.Sound(bytes(bytearray(100)))
    # 设置音量为0（无声）
    CHECK_SOUND.set_volume(0)
    MOVE_SOUND.set_volume(0)
    CAPTURE_SOUND.set_volume(0)
    print(f"警告：未能加载音效文件。错误: {e}")

def draw_background(surface):
    """绘制统一的背景纹理"""
    # 填充基础背景色
    surface.fill(BACKGROUND_COLOR)
    
    # 添加纹理效果
    for i in range(0, surface.get_width(), 10):
        for j in range(0, surface.get_height(), 10):
            if (i + j) % 20 == 0:
                pygame.draw.rect(surface, (230, 207, 171), (i, j, 5, 5))

class ChessGame:
    def __init__(self, game_mode=MODE_PVP, player_camp=CAMP_RED, game_settings=None):
        """初始化游戏"""
        pygame.init()
        
        # 初始化窗口
        self.init_window()
        
        # 游戏模式和玩家阵营
        self.game_mode = game_mode
        self.player_camp = player_camp
        
        # 应用游戏设置
        if game_settings:
            GameRules.set_game_settings(game_settings)
        else:
            # 如果没有传入特定设置，应用全局配置
            GameRules.set_game_settings(game_config.get_all_settings())
        
        # 初始化游戏状态
        self.game_state = GameState()
        
        # 初始化AI（如果需要）
        self.ai = ChessAI("hard", "black") if game_mode == MODE_PVC else None
        self.ai_thinking = False  # AI是否正在思考
        self.ai_think_start_time = 0  # AI开始思考的时间
        self.async_ai_move = None  # 异步AI计算结果
        
        # AI超时设置（毫秒）- 设置更长的时间以匹配AI的思考时间
        self.ai_timeout = 10000  # 3秒超时，与AI内部限制一致
        self.ai_thread = None  # AI计算线程
        
        # 初始化棋盘和界面元素
        self.init_board_and_ui()
        
        # 选中的棋子
        self.selected_piece = None
        
        # 上一步走法记录 (from_row, from_col, to_row, to_col)
        self.last_move = None
        
        # 上一步走法的中文表示
        self.last_move_notation = ""
        
        # 弹窗和确认对话框
        self.popup = None
        self.confirm_dialog = None
        
        # 音效
        self.load_sounds()
        
        # 棋谱滚动相关变量
        self.history_scroll_y = 0  # 棋谱滚动位置
        self.history_max_visible_lines = 15  # 最大可见行数
        self.history_line_height = 22  # 行高
        self.history_area_height = self.history_max_visible_lines * self.history_line_height  # 滚动区域高度

    
    def init_window(self):
        """初始化窗口"""
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋")
        self.clock = pygame.time.Clock()
        
    def init_board_and_ui(self):
        """初始化棋盘和界面元素"""
        self.update_layout()  # 初始化布局
        
        # 创建全屏切换按钮
        self.fullscreen_button = Button(
            self.window_width - 50,  # 右上角
            10, 
            40, 
            30, 
            "全屏", 
            14
        )
        
        # 创建返回按钮
        self.back_button = Button(
            self.window_width - 100,  # 右上角
            10, 
            40, 
            30, 
            "返回", 
            14
        )
        
        # 如果是人机对战且AI先行，设置延迟启动AI
        if self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
            self.ai_thinking = True
            pygame.time.set_timer(pygame.USEREVENT, 500)  # 0.5秒后启动AI，更快响应
        
    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        self.panel_width = int(self.window_width * LEFT_PANEL_WIDTH_RATIO)
        self.board_margin_top = int(self.window_height * BOARD_MARGIN_TOP_RATIO)
        self.board_size = self.window_height - self.board_margin_top
        self.board_margin_left = (self.window_width - self.board_size) // 2
        
        # 更新棋盘位置
        self.chess_board = ChessBoard(
            self.board_margin_left,
            self.board_margin_top,
            self.board_size,
            self.board_size
        )
        
        # 更新棋子位置
        self.chess_board.update_pieces(self.game_state.pieces)
        
        # 更新玩家头像位置
        self.red_avatar.update_position(
            self.panel_width // 2,
            self.board_margin_top + self.board_size // 4,
            self.panel_width // 4
        )
        self.black_avatar.update_position(
            self.panel_width // 2,
            self.board_margin_top + self.board_size * 3 // 4,
            self.panel_width // 4
        )
        
        # 更新全屏按钮位置
        self.fullscreen_button.rect.topleft = (self.window_width - 50, 10)

    def run(self):
        """运行游戏"""
        while True:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.handle_resize((event.w, event.h))
                
                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                        event.key == pygame.K_RETURN and 
                        pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.fullscreen_button.is_clicked(mouse_pos, event):
                        self.toggle_fullscreen()
                    elif self.back_button.is_clicked(mouse_pos, event):
                        self.confirm_dialog = ConfirmDialog(
                            400, 200, "是否要返回主菜单？\n这将丢失您的当前对局信息。"
                        )
                    elif self.chess_board.is_inside(mouse_pos):
                        self.handle_board_click(mouse_pos)
                    elif self.popup and self.popup.handle_event(event, mouse_pos):
                        self.restart_game()
                    elif self.confirm_dialog and self.confirm_dialog.handle_event(event, mouse_pos) is not None:
                        result = self.confirm_dialog.result
                        self.confirm_dialog = None
                        if result:
                            self.restart_game()
                
                if event.type == pygame.USEREVENT and self.ai_thinking:
                    self.ai_thinking = False
                    self.ai_move()
            
            # 更新按钮悬停状态
            self.fullscreen_button.check_hover(mouse_pos)
            
            # 绘制界面
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
    
    def draw(self):
        """绘制游戏界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)
        
        # 绘制棋盘
        self.chess_board.draw(self.screen)
        
        # 绘制玩家头像
        self.red_avatar.draw(self.screen)
        self.black_avatar.draw(self.screen)
        
        # 绘制全屏按钮
        self.fullscreen_button.draw(self.screen)
        
        # 绘制返回按钮
        self.back_button.draw(self.screen)
        
        # 绘制棋谱
        self.draw_move_history()
        
        # 绘制选中的棋子
        if self.selected_piece:
            self.chess_board.draw_selected_piece(self.screen, self.selected_piece)
        
        # 绘制上一步走法
        if self.last_move:
            self.chess_board.draw_last_move(self.screen, self.last_move)
        
        # 绘制弹窗
        if self.popup:
            self.popup.draw(self.screen)
        
        # 绘制确认对话框
        if self.confirm_dialog:
            self.confirm_dialog.draw(self.screen)
    
    def handle_board_click(self, mouse_pos):
        """处理棋盘点击事件"""
        if self.game_state.is_game_over:
            return

        # 如果AI正在思考，忽略玩家点击
        if self.ai_thinking:
            return
        
        # 获取点击位置对应的棋盘坐标
        row, col = self.chess_board.get_board_position(mouse_pos)
        
        # 如果没有选中棋子，尝试选中棋子
        if not self.selected_piece:
            piece = self.game_state.get_piece_at(row, col)
            if piece and piece.camp == self.game_state.player_turn:
                self.selected_piece = piece
                return
        
        # 如果已经选中棋子，尝试移动棋子
        if self.selected_piece:
            move = (self.selected_piece.row, self.selected_piece.col, row, col)
            if self.game_state.is_valid_move(move):
                self.make_move(move)
                self.selected_piece = None
                return
        
        # 如果点击位置无效，取消选中
        self.selected_piece = None
    
    def make_move(self, move):
        """执行走法"""
        from_row, from_col, to_row, to_col = move
        
        # 执行走法
        self.game_state.make_move(move)
        
        # 更新棋盘上的棋子位置
        self.chess_board.update_pieces(self.game_state.pieces)
        
        # 更新上一步走法记录
        self.last_move = move
        self.last_move_notation = self.game_state.get_move_notation(move)
        
        # 播放音效
        if self.game_state.is_check:
            self.check_sound.play()
        elif self.game_state.is_capture:
            self.capture_sound.play()
        else:
            self.move_sound.play()
        
        # 检查游戏是否结束
        if self.game_state.is_game_over:
            self.show_game_over_popup()
            return
        
        # 如果是人机对战，启动AI
        if self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
            self.ai_thinking = True
            pygame.time.set_timer(pygame.USEREVENT, 1000)  # 1秒后启动AI

    def ai_move(self):
        """AI执行走法"""
        move = self.ai.get_best_move(self.game_state)
        if move:
            self.make_move(move)
    
    def show_game_over_popup(self):
        """显示游戏结束弹窗"""
        winner = self.game_state.winner
        if winner == "red":
            message = "红方胜利！"
        elif winner == "black":
            message = "黑方胜利！"
        else:
            message = "平局！"
        
        total_time = self.game_state.total_time
        red_time = self.game_state.red_time
        black_time = self.game_state.black_time
        
        self.popup = PopupDialog(400, 300, message, total_time, red_time, black_time)
    
    def restart_game(self):
        """重新开始游戏"""
        self.game_state = GameState()
        self.chess_board.update_pieces(self.game_state.pieces)
        self.selected_piece = None
        self.last_move = None
        self.last_move_notation = ""
        self.popup = None
        self.confirm_dialog = None
        self.ai_thinking = False
        if self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
            pygame.time.set_timer(pygame.USEREVENT + 1, 800)  # 延迟800毫秒后AI行动
            self.ai_thinking = True
            
    def load_sounds(self):
        """加载音效"""
        self.check_sound = CHECK_SOUND
        self.move_sound = MOVE_SOUND
        self.capture_sound = CAPTURE_SOUND
    
    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        # 计算左侧面板宽度和棋盘边距
        self.left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * self.window_width)
        self.board_margin_top = int(BOARD_MARGIN_TOP_RATIO * self.window_height)
        
        # 更新棋盘
        self.board = ChessBoard(
            self.window_width - self.left_panel_width, 
            self.window_height, 
            self.left_panel_width, 
            self.board_margin_top
        )
        
        # 更新按钮位置
        button_width = 120
        button_height = 40
        button_y = self.window_height - 60
        
        # 更新返回按钮位置
        self.back_button = Button(
            self.left_panel_width + 80, 
            button_y, 
            button_width, 
            button_height, 
            "返回", 
            22
        )
        
        # 更新悔棋按钮位置
        self.undo_button = Button(
            self.window_width - button_width - 80, 
            button_y, 
            button_width, 
            button_height, 
            "悔棋", 
            22
        )
        
        # 更新全屏按钮位置
        self.fullscreen_button = Button(
            self.window_width - 50, 
            10, 
            40, 
            30, 
            "全屏" if not self.is_fullscreen else "退出", 
            14
        )
        
        # 更新头像位置
        avatar_radius = 40
        panel_center_x = self.left_panel_width // 2
        black_y = self.window_height // 3 - 50
        red_y = self.window_height * 2 // 3
        
        # 创建头像
        self.black_avatar = Avatar(panel_center_x, black_y, avatar_radius, (245, 245, 235), "黑方", False)
        self.red_avatar = Avatar(panel_center_x, red_y, avatar_radius, (255, 255, 240), "红方", True)
        
        # 设置当前玩家的头像为活跃状态
        if hasattr(self, 'game_state'):
            is_red_turn = self.game_state.player_turn == "red"
            self.red_avatar.set_active(is_red_turn)
            self.black_avatar.set_active(not is_red_turn)
            
        # 计时器的字体
        self.timer_font = load_font(18)
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        self.is_fullscreen = not self.is_fullscreen
        
        if self.is_fullscreen:
            # 获取显示器信息
            info = pygame.display.Info()
            # 保存窗口模式的尺寸
            self.windowed_size = (self.window_width, self.window_height)
            # 切换到全屏模式
            self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
            self.window_width = info.current_w
            self.window_height = info.current_h
        else:
            # 恢复窗口模式
            self.window_width, self.window_height = self.windowed_size
            self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        
        # 更新布局
        self.update_layout()
        
    def handle_resize(self, new_size):
        """处理窗口大小变化"""
        self.window_width, self.window_height = new_size
        # 更新布局
        self.update_layout()

    def handle_event(self, event, mouse_pos):
        """处理游戏事件"""
        # 处理窗口大小变化
        if event.type == pygame.VIDEORESIZE:
            if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                self.handle_resize((event.w, event.h))
        
        # 处理键盘事件
        if event.type == pygame.KEYDOWN:
            # F11或Alt+Enter切换全屏
            if event.key == pygame.K_F11 or (
                event.key == pygame.K_RETURN and 
                pygame.key.get_mods() & pygame.KMOD_ALT
            ):
                self.toggle_fullscreen()
        
        # 处理鼠标滚轮事件（用于棋谱滚动）
        if event.type == pygame.MOUSEWHEEL:
            # 检查鼠标是否在棋谱区域
            right_panel_x = self.window_width - 350  # 与绘制位置保持一致
            # 检查鼠标是否在右侧信息面板区域内
            if mouse_pos[0] >= right_panel_x and mouse_pos[1] >= 300 and mouse_pos[0] <= self.window_width - 10:
                # 滚动棋谱
                self.history_scroll_y = max(0, self.history_scroll_y - event.y)
                # 确保不会滚动过多
                total_moves = len(self.game_state.move_history)
                max_scroll = max(0, total_moves - self.history_max_visible_lines)
                self.history_scroll_y = min(self.history_scroll_y, max_scroll)
        
        # 处理鼠标点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查是否点击了全屏按钮
            if self.fullscreen_button.is_clicked(mouse_pos, event):
                self.toggle_fullscreen()
            
            # 检查是否点击了悔棋按钮
            elif self.undo_button.is_clicked(mouse_pos, event):
                self.handle_undo()
            
            # 处理棋子操作，只有在当前回合是玩家回合时才处理
            elif not self.ai_thinking and (self.game_mode == MODE_PVP or 
                  self.game_state.player_turn == self.player_camp):
                self.handle_click(mouse_pos)
    
    def run(self):
        """游戏主循环"""
        while True:
            mouse_pos = pygame.mouse.get_pos()
            current_time = pygame.time.get_ticks()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.handle_resize((event.w, event.h))
                
                # 处理AI移动的计时器事件
                if event.type == pygame.USEREVENT + 1:
                    self.process_async_ai_result()
                    # 不再需要停止计时器，因为我们现在使用线程
                # 处理AI多线程计算完成事件
                if event.type == pygame.USEREVENT + 2:
                    self.process_async_ai_result()
                
                # 处理悔棋后解除AI思考状态的延迟事件
                if event.type == pygame.USEREVENT + 2:
                    self.ai_thinking = False
                    pygame.time.set_timer(pygame.USEREVENT + 2, 0)  # 停止计时器
                
                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                        event.key == pygame.K_RETURN and 
                        pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()
                
                # 如果有确认对话框，优先处理它的事件
                if self.confirm_dialog:
                    result = self.confirm_dialog.handle_event(event, mouse_pos)
                    if result is not None:  # 用户已做出选择
                        if result:  # 确认
                            self.confirm_dialog = None
                            return "back_to_menu"
                        else:  # 取消
                            self.confirm_dialog = None
                
                # 如果游戏结束，处理弹窗事件
                elif self.game_state.game_over and self.popup:
                    if self.popup.handle_event(event, mouse_pos):
                        self.__init__(self.game_mode, self.player_camp)  # 重置游戏，保持相同模式和阵营
                
                # 如果游戏未结束，处理鼠标点击
                elif not self.game_state.game_over:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        # 检查是否点击了全屏按钮
                        if self.fullscreen_button.is_clicked(mouse_pos, event):
                            self.toggle_fullscreen()
                        # 检查是否点击了返回按钮
                        elif self.back_button.is_clicked(mouse_pos, event):
                            # 显示确认对话框而不是直接返回
                            self.confirm_dialog = ConfirmDialog(
                                400, 200, "是否要返回主菜单？\n这将丢失您的当前对局信息。"
                            )
                        # 检查是否点击了悔棋按钮
                        elif self.undo_button.is_clicked(mouse_pos, event):
                            self.handle_undo()
                        # 处理棋子操作，只有在当前回合是玩家回合时才处理
                        elif not self.ai_thinking and (self.game_mode == MODE_PVP or 
                              self.game_state.player_turn == self.player_camp):
                            self.handle_click(mouse_pos)
            
            # 检查AI是否思考超时
            if self.ai_thinking and current_time - self.ai_think_start_time > self.ai_timeout:
                # AI思考超时，强制结束思考
                print("AI思考超时，执行当前已知最佳走法")
                self.ai_thinking = False
                pygame.time.set_timer(pygame.USEREVENT + 1, 0)  # 停止计时器
                
                # 如果是人机模式且轮到AI，执行当前已知最佳走法
                if self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
                    self.make_random_ai_move()
            
            # 更新按钮的悬停状态
            self.undo_button.check_hover(mouse_pos)
            self.back_button.check_hover(mouse_pos)
            self.fullscreen_button.check_hover(mouse_pos)
            
            # 检查是否需要触发AI移动（例如游戏开始或重新开始后）
            if (self.game_mode == MODE_PVC and 
                not self.game_state.game_over and 
                self.game_state.player_turn != self.player_camp and
                not self.ai_thinking):
                self.schedule_ai_move()
            
            # 绘制画面
            self.draw(mouse_pos)
            pygame.display.flip()
            self.clock.tick(FPS)

    def draw(self, mouse_pos):
        """绘制游戏界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)
        
        # 绘制左侧面板背景 - 使用与主界面一致的纹理
        left_panel_rect = pygame.Rect(0, 0, self.left_panel_width, self.window_height)
        
        # 先绘制与主背景一致的纹理
        left_panel_surface = pygame.Surface((self.left_panel_width, self.window_height))
        draw_background(left_panel_surface)  # 使用相同的背景绘制函数
        
        # 稍微调亮左侧面板使其有区分度
        overlay = pygame.Surface((self.left_panel_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 30))  # 半透明白色覆盖，轻微增亮
        left_panel_surface.blit(overlay, (0, 0))
        
        # 应用到主界面
        self.screen.blit(left_panel_surface, (0, 0))
        
        # 添加分隔线
        pygame.draw.line(self.screen, PANEL_BORDER, (self.left_panel_width, 0), 
                        (self.left_panel_width, self.window_height), 2)
        
        # 绘制棋盘和棋子 - 先绘制这些
        self.board.draw(self.screen, self.game_state.pieces)
        
        # 如果有上一步走法，在棋盘上标记出来
        if self.last_move:
            from_row, from_col, to_row, to_col = self.last_move
            self.board.highlight_last_move(self.screen, from_row, from_col, to_row, to_col)
        
        # 检查是否需要显示将军动画 - 在棋子之上显示动画
        if self.game_state.should_show_check_animation():
            king_pos = self.game_state.get_checked_king_position()
            if king_pos:
                self.board.draw_check_animation(self.screen, king_pos)
        
        # 绘制游戏信息面板
        self.draw_info_panel()
        
        # 绘制悔棋按钮和返回按钮
        self.undo_button.draw(self.screen)
        self.back_button.draw(self.screen)
        self.fullscreen_button.draw(self.screen)
        
        # 绘制玩家头像
        self.red_avatar.draw(self.screen)
        self.black_avatar.draw(self.screen)
        
        # 绘制计时器信息
        self.draw_timers()

        # 在左侧面板中添加VS标志
        vs_font = load_font(36, bold=True)
        vs_text = "VS"
        vs_surface = vs_font.render(vs_text, True, (100, 100, 100))
        vs_rect = vs_surface.get_rect(center=(self.left_panel_width // 2, self.window_height // 2))
        self.screen.blit(vs_surface, vs_rect)
        
        # 如果有上一步走法的记录，显示它
        if self.last_move_notation:
            move_font = load_font(18)
            move_text = f"上一步: {self.last_move_notation}"
            move_surface = move_font.render(move_text, True, BLACK)
            # 显示在左侧面板底部
            move_rect = move_surface.get_rect(center=(self.left_panel_width // 2, self.window_height - 80))
            self.screen.blit(move_surface, move_rect)
        
        # 如果是人机模式，显示模式和阵营提示
        if self.game_mode == MODE_PVC:
            mode_font = load_font(18)
            if self.player_camp == CAMP_RED:
                mode_text = "人机对战模式 - 您执红方"
            else:
                mode_text = "人机对战模式 - 您执黑方"
            mode_surface = mode_font.render(mode_text, True, BLACK)
            self.screen.blit(mode_surface, (self.left_panel_width + (self.window_width - self.left_panel_width)//2 - mode_surface.get_width()//2, 15))
            
            # 如果AI正在思考，显示提示
            if self.ai_thinking:
                thinking_font = load_font(24)
                thinking_text = "电脑思考中..."
                thinking_surface = thinking_font.render(thinking_text, True, RED)
                thinking_rect = thinking_surface.get_rect(center=(self.window_width//2, 45))
                self.screen.blit(thinking_surface, thinking_rect)
        
        # 绘制 captured pieces（阵亡棋子）
        self.draw_captured_pieces()
        
        # 绘制棋谱历史记录
        self.draw_move_history()
        
        # 如果游戏结束，显示弹窗
        if self.game_state.game_over and self.popup:
            self.popup.draw(self.screen)
        
        # 如果有确认对话框，显示它
        if self.confirm_dialog:
            self.confirm_dialog.draw(self.screen)
    
    def draw_timers(self):
        """绘制计时器信息"""
        # 获取当前的时间状态
        red_time, black_time = self.game_state.update_times()
        total_time = self.game_state.total_time
        
        # 转换为分钟:秒格式
        red_time_str = f"{int(red_time//60):02}:{int(red_time%60):02}"
        black_time_str = f"{int(black_time//60):02}:{int(black_time%60):02}"
        total_time_str = f"{int(total_time//60):02}:{int(total_time%60):02}"
        
        # 绘制红方时间 - 在红方头像下方
        red_time_surface = self.timer_font.render(f"用时: {red_time_str}", True, RED)
        red_time_rect = red_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.red_avatar.y + self.red_avatar.radius + 50)
        )
        self.screen.blit(red_time_surface, red_time_rect)
        
        # 绘制黑方时间 - 在黑方头像下方
        black_time_surface = self.timer_font.render(f"用时: {black_time_str}", True, BLACK)
        black_time_rect = black_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.black_avatar.y + self.black_avatar.radius + 50)
        )
        self.screen.blit(black_time_surface, black_time_rect)
        
        # 绘制总时间 - 在左侧面板顶部
        total_time_surface = self.timer_font.render(f"对局时长: {total_time_str}", True, BLACK)
        self.screen.blit(total_time_surface, (10, 10))
    
    def draw_info_panel(self):
        """绘制游戏信息面板"""
        # 当游戏进行中，在左上角显示当前回合
        if not self.game_state.game_over:
            # 创建回合信息文本
            turn_color = RED if self.game_state.player_turn == "red" else BLACK
            turn_text = f"当前回合: {'红方' if self.game_state.player_turn == 'red' else '黑方'}"
            
            # 计算位置 - 在左上角，对局时长下方
            font = load_font(20)
            text_surface = font.render(turn_text, True, turn_color)
            # 位于对局时长信息的下方
            text_rect = text_surface.get_rect(
                topleft=(10, 40)  # 在左上角，对局时长下方
            )
            self.screen.blit(text_surface, text_rect)

        # 绘制 captured pieces（阵亡棋子）
        self.draw_captured_pieces()
        
        # 绘制棋谱历史记录
        self.draw_move_history()

    def draw_captured_pieces(self):
        """绘制双方阵亡棋子"""
        # 绘制标题
        title_font = load_font(20, bold=True)
        red_title = title_font.render("红方阵亡:", True, RED)
        black_title = title_font.render("黑方阵亡:", True, BLACK)
        
        # 将阵亡棋子信息移到右侧
        right_panel_x = self.window_width - 550  # 右侧边栏起始x坐标
        self.screen.blit(red_title, (right_panel_x, 60))
        self.screen.blit(black_title, (right_panel_x, 180))
        
        # 绘制红方阵亡棋子
        x_start, y_start = right_panel_x, 90
        x, y = x_start, y_start
        for piece in self.game_state.captured_pieces["red"]:
            piece_text = title_font.render(piece.name, True, RED)
            # 减小右边距，提供更多空间给棋子显示
            if x + piece_text.get_width() > self.window_width - 40:
                x = x_start
                y += 25
            self.screen.blit(piece_text, (x, y))
            x += piece_text.get_width() + 5
        
        # 绘制黑方阵亡棋子
        x_start, y_start = right_panel_x, 210
        x, y = x_start, y_start
        for piece in self.game_state.captured_pieces["black"]:
            piece_text = title_font.render(piece.name, True, BLACK)
            # 减小右边距，提供更多空间给棋子显示
            if x + piece_text.get_width() > self.window_width - 40:
                x = x_start
                y += 25
            self.screen.blit(piece_text, (x, y))
            x += piece_text.get_width() + 5

    def draw_move_history(self):
        """绘制棋谱历史记录"""
        # 绘制标题
        title_font = load_font(20, bold=True)
        history_title = title_font.render("棋谱记录:", True, (0, 0, 0))
        
        # 将棋谱记录移到右侧
        right_panel_x = self.window_width - 550  # 右侧边栏起始x坐标
        self.screen.blit(history_title, (right_panel_x, 300))
        
        # 绘制历史记录（带滚动功能）
        history_font = load_font(18)
        y_start = 330
        line_height = self.history_line_height
        
        # 计算最大可见行数
        max_visible_lines = min(self.history_max_visible_lines, 
                               (self.window_height - y_start - 50) // line_height)
        
        # 计算要显示的历史记录范围
        total_moves = len(self.game_state.move_history)
        start_index = max(0, total_moves - max_visible_lines - self.history_scroll_y)
        end_index = min(total_moves, start_index + max_visible_lines)
        
        # 显示历史记录
        y = y_start
        for i in range(start_index, end_index):
            move_record = self.game_state.move_history[i]
            piece, from_row, from_col, to_row, to_col, captured_piece = move_record
            
            # 生成记谱表示
            notation = self.generate_move_notation(piece, from_row, from_col, to_row, to_col)
            
            # 添加回合数
            move_number = i + 1
            move_text = f"{move_number:2d}. {notation}"
            
            # 如果有被吃子，添加标识
            if captured_piece:
                move_text += " (吃子)"
            
            text_surface = history_font.render(move_text, True, BLACK)
            # 限制文本宽度，避免超出边界
            max_text_width = 300
            if text_surface.get_width() > max_text_width:
                # 如果文本太长，截断并在末尾添加省略号
                move_text = move_text[:20] + "..."  # 简单截断
                text_surface = history_font.render(move_text, True, BLACK)
            self.screen.blit(text_surface, (right_panel_x + 5, y))
            y += line_height
            
        # 绘制滚动条（如果需要）
        if total_moves > max_visible_lines:
            # 滚动条背景
            scrollbar_x = self.window_width - 300  # 将滚动条向左移动，远离窗口边缘
            scrollbar_y = y_start
            scrollbar_height = max_visible_lines * line_height
            pygame.draw.rect(self.screen, (200, 200, 200), 
                           (scrollbar_x, scrollbar_y, 15, scrollbar_height))  # 增加宽度到15像素
            
            # 滚动条滑块
            thumb_height = max(20, scrollbar_height * max_visible_lines // total_moves)
            max_scroll = total_moves - max_visible_lines
            if max_scroll > 0:  # 避免除零错误
                thumb_y = scrollbar_y + (self.history_scroll_y / max_scroll) * (scrollbar_height - thumb_height)
            else:
                thumb_y = scrollbar_y
            pygame.draw.rect(self.screen, (100, 100, 100), 
                           (scrollbar_x, thumb_y, 15, thumb_height))  # 增加宽度到15像素
    def handle_click(self, pos):
        """处理鼠标点击事件"""
        # 获取点击的棋盘位置
        grid_pos = self.board.get_grid_position(pos)
        if not grid_pos:
            return
            
        row, col = grid_pos
        
        # 选择棋子或移动棋子
        if self.selected_piece is None:
            # 尝试选择棋子
            piece = self.game_state.get_piece_at(row, col)
            if piece and piece.color == self.game_state.player_turn:
                self.selected_piece = (row, col)
                self.board.highlight_position(row, col)
                
                # 计算可能的移动位置
                possible_moves, capturable = self.game_state.calculate_possible_moves(row, col)
                self.board.set_possible_moves(possible_moves)
                self.board.set_capturable_positions(capturable)
        else:
            sel_row, sel_col = self.selected_piece
            
            # 检查是否点击了同一个棋子（取消选择）
            if sel_row == row and sel_col == col:
                self.selected_piece = None
                self.board.clear_highlights()
                return
                
            # 检查是否选择了另一个己方棋子（更换选择）
            new_piece = self.game_state.get_piece_at(row, col)
            if new_piece and new_piece.color == self.game_state.player_turn:
                self.selected_piece = (row, col)
                self.board.highlight_position(row, col)
                
                # 计算新选择棋子的可能移动
                possible_moves, capturable = self.game_state.calculate_possible_moves(row, col)
                self.board.set_possible_moves(possible_moves)
                self.board.set_capturable_positions(capturable)
                return
            
            # 已选择棋子，尝试移动
            captured_piece = self.game_state.get_piece_at(row, col)
            move_successful = self.game_state.move_piece(sel_row, sel_col, row, col)
            
            if move_successful:
                # 记录上一步走法
                self.last_move = (sel_row, sel_col, row, col)
                
                # 生成上一步走法的中文表示
                piece = self.game_state.get_piece_at(row, col)
                if piece:
                    self.last_move_notation = self.generate_move_notation(piece, sel_row, sel_col, row, col)
                
                # 播放移动音效
                if captured_piece:
                    try:
                        CAPTURE_SOUND.play()
                    except:
                        pass
                else:
                    try:
                        MOVE_SOUND.play()
                    except:
                        pass
                
                # 更新头像状态
                self.update_avatars()
                
                # 如果新的状态是将军，播放将军音效
                if self.game_state.is_check:
                    try:
                        CHECK_SOUND.play()
                    except:
                        pass
                
                # 检查游戏是否结束
                if self.game_state.game_over:
                    winner_text = self.game_state.get_winner_text()
                    
                    # 更新时间数据，确保获取最终值
                    red_time, black_time = self.game_state.update_times()
                    total_time = self.game_state.total_time
                    
                    # 创建弹窗并传入时间信息
                    self.popup = PopupDialog(
                        400, 320,  # 增加高度以适应更多内容
                        winner_text,
                        total_time,
                        red_time,
                        black_time
                    )
                # 如果是人机模式且轮到AI走子，触发AI移动
                elif self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
                    self.schedule_ai_move()
                else:
                    # 立即刷新界面，确保玩家的移动能立刻显示
                    pygame.display.flip()
            
            # 无论如何都取消选择状态
            self.selected_piece = None
            self.board.clear_highlights()
    
    def generate_move_notation(self, piece, from_row, from_col, to_row, to_col):
        """生成走法的中文表示，如"炮二平五"、"马8进7"等"""
        from chess_pieces import King, Shi, Xiang, Ma, Ju, Pao, Pawn, Wei, She, Lei, Jia
        
        piece_names = {
            "king": "汉" if piece.color == "red" else "汗",
            "advisor": "仕" if piece.color == "red" else "士",
            "elephant": "相" if piece.color == "red" else "象",
            "horse": "馬" if piece.color == "red" else "马",
            "rook": "車" if piece.color == "red" else "车",
            "cannon": "炮" if piece.color == "red" else "砲",
            "pawn": "兵" if piece.color == "red" else "卒",
            "wei": "尉" if piece.color == "red" else "衛",
            "she": "射" if piece.color == "red" else "䠶",
            "lei": "檑" if piece.color == "red" else "礌",
            "jia": "甲" if piece.color == "red" else "胄"
        }
        
        # 获取棋子名称
        if isinstance(piece, King):
            piece_name = piece_names["king"]
        elif isinstance(piece, Shi):
            piece_name = piece_names["advisor"]
        elif isinstance(piece, Xiang):
            piece_name = piece_names["elephant"]
        elif isinstance(piece, Ma):
            piece_name = piece_names["horse"]
        elif isinstance(piece, Ju):
            piece_name = piece_names["rook"]
        elif isinstance(piece, Pao):
            piece_name = piece_names["cannon"]
        elif isinstance(piece, Pawn):
            piece_name = piece_names["pawn"]
        elif isinstance(piece, Wei):
            piece_name = piece_names["wei"]
        elif isinstance(piece, She):
            piece_name = piece_names["she"]
        elif isinstance(piece, Lei):
            piece_name = piece_names["lei"]
        elif isinstance(piece, Jia):
            piece_name = piece_names["jia"]
        else:
            piece_name = piece.name  # 直接使用棋子名称
        
        # 转换列数为中文数字或数字 - 从右至左标识
        # 红方用一至十三标识，黑方用1-13标识
        col_names_red = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三"]
        col_names_black = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
        
        # 根据棋子颜色选择合适的列名表示
        col_names = col_names_red if piece.color == "red" else col_names_black
        
        # 计算棋盘坐标到列标识的映射（从右到左）
        col_index = 12 - from_col  # 从右到左映射 (0-12 -> 12-0)
        from_col_name = col_names[col_index]
        
        # 判断移动方向
        direction = ""
        if to_row < from_row:  # 向上移动
            direction = "进" if piece.color == "red" else "退"
        elif to_row > from_row:  # 向下移动
            direction = "退" if piece.color == "red" else "进"
        else:  # 水平移动
            direction = "平"
        
        # 获取目标位置
        if direction == "平":
            # 平移表示目标列
            to_col_index = 12 - to_col  # 从右到左映射
            to_col_name = col_names[to_col_index]
            notation = f"{piece_name}{from_col_name}{direction}{to_col_name}"
        else:
            # 进退表示移动的距离或目标列
            # 检查是否是马、象、士或新增的对角线移动棋子
            is_diagonal_piece = (isinstance(piece, Ma) or isinstance(piece, Xiang) or 
                               isinstance(piece, Shi) or isinstance(piece, She) or
                               isinstance(piece, Wei))
            
            if is_diagonal_piece:
                # 马、象、士、射、尉用目标列表示
                to_col_index = 12 - to_col  # 从右到左映射
                to_col_name = col_names[to_col_index]
                notation = f"{piece_name}{from_col_name}{direction}{to_col_name}"
            else:
                # 其他棋子用移动距离表示
                distance = abs(from_row - to_row)
                # 确保距离在有效范围内
                if distance < 1:
                    distance = 1
                elif distance > 12:  # 最大可能距离是12格（从第0行到第12行）
                    distance = 12
                    
                if piece.color == "black" and direction == "进":
                    # 黑方前进和红方后退是增加行号
                    # 确保索引在有效范围内
                    index = min(distance-1, len(col_names_black)-1)
                    distance_str = col_names_black[index]
                elif piece.color == "black" and direction == "退":
                    # 黑方后退和红方前进是减少行号
                    # 确保索引在有效范围内
                    index = min(distance-1, len(col_names_black)-1)
                    distance_str = col_names_black[index]
                else:
                    # 红方使用汉字数字表示距离
                    # 确保索引在有效范围内
                    # 扩展红方距离表示以适应13x13棋盘
                    red_distance_names = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
                    index = min(distance-1, len(red_distance_names)-1)
                    distance_str = red_distance_names[index]
                notation = f"{piece_name}{from_col_name}{direction}{distance_str}"
        
        return notation
    
    def handle_undo(self):
        """处理悔棋操作"""
        # 如果AI正在思考，不允许悔棋
        if self.ai_thinking:
            return False
        
        # 如果游戏已经结束，先清除状态
        if self.game_state.game_over:
            self.popup = None
            self.game_state.game_over = False
        
        if self.game_mode == MODE_PVP:
            # 人人模式直接悔棋
            if self.game_state.undo_move():
                # 悔棋成功
                self.selected_piece = None
                self.board.clear_highlights()
                self.update_avatars()
                
                # 清除上一步记录
                self.last_move = None
                self.last_move_notation = ""
                
                # 如果还有移动历史，更新上一步记录
                if hasattr(self.game_state, 'move_history') and len(self.game_state.move_history) > 0:
                    last_history = self.game_state.move_history[-1]
                    if 'from_pos' in last_history and 'to_pos' in last_history:
                        from_row, from_col = last_history['from_pos']
                        to_row, to_col = last_history['to_pos']
                        self.last_move = (from_row, from_col, to_row, to_col)
                        piece = self.game_state.get_piece_at(to_row, to_col)
                        if piece:
                            self.last_move_notation = self.generate_move_notation(
                                piece, from_row, from_col, to_row, to_col
                            )
                
                return True
        else:  # 人机模式
            # 首先停止任何AI计时器
            pygame.time.set_timer(pygame.USEREVENT + 1, 0)
            pygame.time.set_timer(pygame.USEREVENT + 2, 0)
            self.ai_thinking = False
            
            # 移动历史为空，没有步骤可以悔棋
            if not hasattr(self.game_state, 'move_history') or len(self.game_state.move_history) == 0:
                return False
            
            # 判断当前是玩家回合还是AI回合
            is_player_turn = self.game_state.player_turn == self.player_camp
            
            if is_player_turn:
                # 玩家回合 - 需要悔两步（玩家和AI各一步）
                if len(self.game_state.move_history) >= 1:
                    # 至少有一步可以悔棋
                    self.game_state.undo_move()  # 悔掉玩家上一步
                    
                    # 如果还有更多步骤，尝试悔掉AI的上一步
                    if len(self.game_state.move_history) >= 1:
                        self.game_state.undo_move()  # 悔掉AI上一步
                    
                    self.selected_piece = None
                    self.board.clear_highlights()
                    self.update_avatars()
                    return True
            else:
                # AI回合 - 悔一步（AI刚下的或上一个玩家步骤）
                if len(self.game_state.move_history) >= 1:
                    self.game_state.undo_move()
                    self.selected_piece = None
                    self.board.clear_highlights()
                    self.update_avatars()
                    
                    # 如果悔棋后轮到AI行动，延迟1秒
                    if self.game_state.player_turn != self.player_camp:
                        self.ai_thinking = True
                        pygame.time.set_timer(pygame.USEREVENT + 2, 1000)
                    
                    return True
        
        # 重置滚动位置
        self.history_scroll_y = 0
        
        return False

    def make_random_ai_move(self):
        """当AI思考超时时，执行当前已知的最优移动"""
        if not self.ai or self.game_mode != MODE_PVC:
            return
        
        # 首先尝试获取AI已计算出的最佳走法
        best_move = self.ai.get_computed_move()
        if best_move is None:
            # 如果没有计算出的走法，则使用AI内部保存的最佳走法
            best_move = self.ai.best_move_so_far
        
        if best_move is None:
            # 如果仍然没有最佳走法，则随机选择一个移动
            ai_color = "black" if self.player_camp == CAMP_RED else "red"
            valid_moves = []
            
            for piece in self.game_state.pieces:
                if piece.color == ai_color:
                    possible_moves, _ = self.game_state.calculate_possible_moves(piece.row, piece.col)
                    for to_row, to_col in possible_moves:
                        valid_moves.append(((piece.row, piece.col), (to_row, to_col)))
            
            if valid_moves:
                best_move = random.choice(valid_moves)
        
        if best_move:
            from_pos, to_pos = best_move
            from_row, from_col = from_pos
            to_row, to_col = to_pos
            
            # 检查目标位置是否有棋子（吃子）
            target_piece = self.game_state.get_piece_at(to_row, to_col)
            
            # 执行移动
            self.game_state.move_piece(from_row, from_col, to_row, to_col)
            
            # 记录上一步走法
            self.last_move = (from_row, from_col, to_row, to_col)
            
            # 生成上一步走法的中文表示
            piece = self.game_state.get_piece_at(to_row, to_col)
            if piece:
                self.last_move_notation = self.generate_move_notation(piece, from_row, from_col, to_row, to_col)
            
            # 播放音效
            if target_piece:
                try:
                    CAPTURE_SOUND.play()
                except:
                    pass
            else:
                try:
                    MOVE_SOUND.play()
                except:
                    pass
            
            # 更新头像状态
            self.update_avatars()
            
            # 如果新的状态是将军，播放将军音效
            if self.game_state.is_check:
                try:
                    CHECK_SOUND.play()
                except:
                    pass
            
            # 检查游戏是否结束
            if self.game_state.game_over:
                winner_text = self.game_state.get_winner_text()
                
                # 更新时间数据，确保获取最终值
                red_time, black_time = self.game_state.update_times()
                total_time = self.game_state.total_time
                
                # 创建弹窗并传入时间信息
                self.popup = PopupDialog(
                    400, 320,  # 增加高度以适应更多内容
                    winner_text,
                    total_time,
                    red_time,
                    black_time
                )

    def update_avatars(self):
        """更新头像状态"""
        is_red_turn = self.game_state.player_turn == "red"
        self.red_avatar.set_active(is_red_turn)
        self.black_avatar.set_active(not is_red_turn)
        
        # 更新玩家标识
        if self.game_mode == MODE_PVC:
            if self.player_camp == CAMP_RED:
                self.red_avatar.player_name = "玩家"
                self.black_avatar.player_name = "电脑"
            else:
                self.red_avatar.player_name = "电脑"
                self.black_avatar.player_name = "玩家"
        else:
            self.red_avatar.player_name = "红方"
            self.black_avatar.player_name = "黑方"

    def schedule_ai_move(self):
        """安排AI移动"""
        # 设置AI思考开始时间
        self.ai_think_start_time = pygame.time.get_ticks()
        # 立即启动异步AI计算
        self.start_async_ai_computation()
        self.ai_thinking = True

    def move_piece(self, from_row, from_col, to_row, to_col):
        """移动棋子
        
        Args:
            from_row (int): 起始行
            from_col (int): 起始列
            to_row (int): 目标行
            to_col (int): 目标列
            
        Returns:
            bool: 移动是否成功
        """
        # 获取要移动的棋子
        piece = self.get_piece_at(from_row, from_col)
        if not piece or piece.color != self.player_turn:
            return False
        
        # 检查移动是否合法
        if not GameRules.is_valid_move(self.pieces, piece, from_row, from_col, to_row, to_col):
            return False
        
        # 获取目标位置的棋子（如果有）
        captured_piece = self.get_piece_at(to_row, to_col)
        
        # 记录移动历史
        self.move_history.append((
            piece,
            from_row,
            from_col,
            to_row,
            to_col,
            captured_piece
        ))
        
        # 更新当前玩家的用时
        current_time = time.time()
        elapsed = current_time - self.current_turn_start_time
        if self.player_turn == "red":
            self.red_time += elapsed
        else:
            self.black_time += elapsed
        
        # 如果有棋子被吃掉，移除它并记录到阵亡列表
        if captured_piece:
            self.pieces.remove(captured_piece)
            self.captured_pieces[captured_piece.color].append(captured_piece)
            
            # 如果吃掉的是对方将/帅/汉/汗，游戏结束
            if isinstance(captured_piece, King):
                self.game_over = True
                self.winner = piece.color
                # 更新游戏总时长
                self.total_time = current_time - self.start_time
                return True
        
        # 执行移动
        piece.move_to(to_row, to_col)

        # 处理甲/胄的特殊吃子规则（移动后检查）
        if isinstance(piece, Jia):
            # 查找所有被吃掉的敌方棋子
            captured_pieces = GameRules.find_jia_capture_moves(self.pieces, piece)
            
            # 实际移除被吃掉的棋子
            for captured in captured_pieces:
                if captured in self.pieces:
                    self.pieces.remove(captured)
                    self.captured_pieces[captured.color].append(captured)
                    
                    # 如果吃掉的是对方将/帅/汉/汗，游戏结束
                    if isinstance(captured, King):
                        self.game_over = True
                        self.winner = piece.color
                        # 更新游戏总时长
                        current_time = time.time()
                        self.total_time = current_time - self.start_time
                        # 切换玩家
                        opponent_color = "black" if self.player_turn == "red" else "red"
                        return True

        # 切换玩家
        opponent_color = "black" if self.player_turn == "red" else "red"
        
        # 检查是否将军
        self.is_check = GameRules.is_checkmate(self.pieces, opponent_color)
        if self.is_check:
            # 设置将军动画计时器
            self.check_animation_time = current_time
        
        # 检查是否将死或获胜
        game_over, winner = GameRules.is_game_over(self.pieces, self.player_turn)
        
        if game_over:
            self.game_over = True
            self.winner = winner
            # 更新游戏总时长
            self.total_time = current_time - self.start_time
        else:
            # 切换玩家回合
            self.player_turn = opponent_color
            # 重置当前回合开始时间
            self.current_turn_start_time = current_time
            
        # 重置棋谱滚动位置
        # 注意：这个修改是在GameState类中，但我们在这里注释提醒需要同步修改
        
        return True

    def start_async_ai_computation(self):
        """启动异步AI计算"""
        # 使用AI进行多线程计算
        self.ai.get_move_async(self.game_state)
        
    def _compute_ai_move(self):
        """在单独线程中计算AI移动"""
        # 执行AI计算
        self.async_ai_move = self.ai._get_best_move(self.game_state)
        # 计算完成后，通过pygame事件通知主线程
        pygame.event.post(pygame.event.Event(pygame.USEREVENT + 1))
    
    def process_async_ai_result(self):
        """处理异步AI计算结果"""
        if not self.ai:
            self.ai_thinking = False
            return
        
        # 等待线程结束（应该已经结束了）
        if hasattr(self, 'ai_thread') and self.ai_thread is not None and self.ai_thread.is_alive():
            self.ai_thread.join(timeout=1)  # 最多等待1秒
        
        # 使用预先计算好的AI移动，如果未完成则使用当前最佳走法
        move = self.async_ai_move
        
        # 如果没有完成的计算结果，尝试获取当前最佳走法
        if not move:
            move = self.ai.get_computed_move()
        
        if move:
            from_pos, to_pos = move
            from_row, from_col = from_pos
            to_row, to_col = to_pos
            
            # 检查目标位置是否有棋子（吃子）
            target_piece = self.game_state.get_piece_at(to_row, to_col)
            
            # 执行移动
            self.game_state.move_piece(from_row, from_col, to_row, to_col)
            
            # 记录上一步走法
            self.last_move = (from_row, from_col, to_row, to_col)
            
            # 生成上一步走法的中文表示
            piece = self.game_state.get_piece_at(to_row, to_col)
            if piece:
                self.last_move_notation = self.generate_move_notation(piece, from_row, from_col, to_row, to_col)
            
            # 播放音效
            if target_piece:
                try:
                    CAPTURE_SOUND.play()
                except:
                    pass
            else:
                try:
                    MOVE_SOUND.play()
                except:
                    pass
            
            # 如果新的状态是将军，播放将军音效
            if self.game_state.is_check:
                try:
                    CHECK_SOUND.play()
                except:
                    pass
            
            # 更新头像状态
            self.update_avatars()
            
            # 检查游戏是否结束
            if self.game_state.game_over:
                winner_text = self.game_state.get_winner_text()
                
                # 更新时间数据，确保获取最终值
                red_time, black_time = self.game_state.update_times()
                total_time = self.game_state.total_time
                
                # 创建弹窗并传入时间信息
                self.popup = PopupDialog(
                    400, 320,  # 增加高度以适应更多内容
                    winner_text,
                    total_time,
                    red_time,
                    black_time
                )
            
            # 立即刷新界面，确保AI的移动能立刻显示
            pygame.display.flip()
        
        self.ai_thinking = False