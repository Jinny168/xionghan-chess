"""传统象棋游戏主类"""

import pygame
import sys
from program.core.traditional_chess_mode import TraditionalChessMode
from program.core.traditional_chess_rules import TraditionalChessRules
from program.ui.traditional_chess_board import TraditionalChessBoard
from program.ui.traditional_game_screen import TraditionalGameScreen  # 导入新的UI界面
# 从game_config_manager导入比例常量
from program.controllers.game_config_manager import LEFT_PANEL_WIDTH_RATIO
from program.controllers.sound_manager import sound_manager
from program.utils.utils import load_font, draw_background
from program.controllers.game_config_manager import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, RED, BLACK


class TraditionalGameState:
    """传统象棋游戏状态管理类"""
    
    def __init__(self):
        self.mode = TraditionalChessMode()
        self.pieces = self.mode.create_traditional_pieces()
        self.current_player = "red"  # 红方先行
        self.player_turn = "red"  # 兼容性属性，与current_player保持一致
        self.selected_piece = None
        self.valid_moves = []
        self.move_history = []
        self.game_over = False
        self.winner = None
        self.last_move = None  # 记录最后一步移动
        # 添加用于判断重复局面和自然限着的计数器
        self.move_count_without_capture_or_pawn = 0  # 无吃子和兵移动的步数
        # 添加将军状态
        self.is_check = False  # 当前是否被将军
        # 添加阵亡棋子记录
        self.captured_pieces = {"red": [], "black": []}  # 记录被吃掉的棋子


class TraditionalGame:
    """传统象棋游戏主类"""
    
    def __init__(self, game_type="pvp", ai_difficulty="medium"):
        """
        初始化传统象棋游戏
        :param game_type: 游戏类型 ("pvp"=双人, "pvc"=人机, "network"=网络)
        :param ai_difficulty: AI难度 ("easy", "medium", "hard")
        """
        self.about_screen = None
        self.game_type = game_type
        self.state = TraditionalGameState()
        # 使用比例计算左侧面板宽度
        left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * DEFAULT_WINDOW_WIDTH)
        self.board = TraditionalChessBoard(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, 
                                          left_panel_width + 20, 50)
        self.sound_manager = sound_manager
        
        # 初始化游戏界面
        self.game_screen = TraditionalGameScreen(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, 
                                               game_type, "red")  # 默认玩家执红
        self.player_camp = "red"  # 默认玩家执红方
        
        # AI相关
        if game_type == "pvc":
            from program.ai.traditional_ai import TraditionalAI
            self.ai = TraditionalAI(difficulty=ai_difficulty)
        
        # 网络相关
        if game_type == "network":
            # 网络功能会在游戏运行时初始化
            self.network = None
        
        # 确认对话框
        self.confirm_dialog = None
        
        # 初始化游戏开始时间
        import time
        self.start_time = time.time()
        
        # 初始化窗口尺寸
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        
        # 初始化全屏相关属性
        self.is_fullscreen = False
        self.windowed_size = None  # 初始时未设置，将在第一次切换全屏时设置
        
        # 初始化屏幕
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
    
    def select_piece(self, row, col):
        """选择棋子"""
        if self.state.game_over:
            return False
            
        # 查找点击位置的棋子
        for piece in self.state.pieces:
            if piece.row == row and piece.col == col and piece.color == self.state.current_player:
                self.state.selected_piece = piece
                moves, capturable = self.state.mode.get_traditional_possible_moves(
                    self.state.pieces, piece)
                self.state.valid_moves = moves + capturable
                # 过滤掉会导致送将的移动
                self.state.valid_moves = self.filter_invalid_moves_for_check(piece, self.state.valid_moves)
                self.board.highlight_position(row, col)
                self.board.set_possible_moves(moves)
                self.board.set_capturable_positions(capturable)
                return True
        return False
    
    def filter_invalid_moves_for_check(self, piece, moves):
        """过滤会导致送将的移动"""
        filtered_moves = []
        for to_row, to_col in moves:
            # 模拟移动
            original_row, original_col = piece.row, piece.col
            captured_piece = self._get_piece_at(to_row, to_col)
            
            # 移动棋子
            piece.row, piece.col = to_row, to_col
            
            # 如果有棋子被吃掉，暂时移除它
            if captured_piece:
                self.state.pieces.remove(captured_piece)
            
            # 检查移动后是否会被将军
            is_in_check = TraditionalChessRules.is_in_check(self.state.pieces, piece.color)
            
            # 恢复棋子位置
            piece.row, piece.col = original_row, original_col
            
            # 如果之前吃了棋子，恢复它
            if captured_piece:
                self.state.pieces.append(captured_piece)
            
            # 如果移动后不会被将军，则该移动是合法的
            if not is_in_check:
                filtered_moves.append((to_row, to_col))
        
        return filtered_moves
    
    def move_piece(self, to_row, to_col):
        """移动棋子"""
        if self.state.game_over or not self.state.selected_piece:
            return False
        
        # 检查移动是否在有效范围内
        if (to_row, to_col) not in self.state.valid_moves:
            return False
        
        piece = self.state.selected_piece
        from_row, from_col = piece.row, piece.col
        
        # 检查移动是否合法（传统象棋规则）
        if not self.state.mode.is_valid_traditional_move(
            self.state.pieces, piece, from_row, from_col, to_row, to_col
        ):
            return False
        
        # 执行移动
        # 检查是否吃子
        target_piece = self._get_piece_at(to_row, to_col)
        is_capture = target_piece is not None
        if target_piece:
            self.state.pieces.remove(target_piece)
            # 将被吃掉的棋子加入阵亡列表
            self.state.captured_pieces[target_piece.color].append(target_piece)
            # 检查是否吃掉了对方的将/帅，如果吃掉了则立即结束游戏
            from program.core.chess_pieces import King
            if isinstance(target_piece, King):
                self.state.game_over = True
                self.state.winner = piece.color
                self.sound_manager.play_sound('eat')  # 播放吃子音效
                # 记录移动历史
                move_record = {
                    'piece': piece,
                    'from': (from_row, from_col),
                    'to': (to_row, to_col),
                    'captured': target_piece
                }
                self.state.move_history.append(move_record)
                self.state.last_move = (from_row, from_col, to_row, to_col)
                # 清除选择
                self.clear_selection()
                return True
        
        # 检查是否是兵/卒移动
        from program.core.chess_pieces import Pawn  # 在函数内部导入，避免循环导入
        is_pawn_move = isinstance(piece, Pawn)
        
        # 移动棋子
        piece.row, piece.col = to_row, to_col
        
        # 记录移动历史
        move_record = {
            'piece': piece,
            'from': (from_row, from_col),
            'to': (to_row, to_col),
            'captured': target_piece
        }
        self.state.move_history.append(move_record)
        self.state.last_move = (from_row, from_col, to_row, to_col)
        
        # 更新无吃子和兵移动的计数器
        if is_capture or is_pawn_move:
            self.state.move_count_without_capture_or_pawn = 0
        else:
            self.state.move_count_without_capture_or_pawn += 1
        
        # 检查移动后对方是否被将军
        opponent_color = "black" if self.state.current_player == "red" else "red"
        is_opponent_in_check = self.state.mode.is_traditional_check(self.state.pieces, opponent_color)
        
        # 检查是否将死
        self.state.game_over, self.state.winner = self.state.mode.is_traditional_game_over(
            self.state.pieces, self.state.current_player, self.state.move_history, 
            self.state.move_count_without_capture_or_pawn
        )
        
        # 如果对方被将军，播放将军音效
        if is_opponent_in_check and not self.state.game_over:
            self.sound_manager.play_sound('check')  # 播放将军音效
            self.state.is_check = True
        else:
            self.state.is_check = False
        
        # 切换玩家
        self.state.current_player = "black" if self.state.current_player == "red" else "red"
        
        # 播放音效
        if is_capture:
            self.sound_manager.play_sound('eat')  # 播放吃子音效
        else:
            self.sound_manager.play_sound('move')  # 播放移动音效
        
        # 清除选择
        self.clear_selection()
        
        return True
    
    def _get_piece_at(self, row, col):
        """获取指定位置的棋子"""
        for piece in self.state.pieces:
            if piece.row == row and piece.col == col:
                return piece
        return None
    
    def clear_selection(self):
        """清除选择状态"""
        self.state.selected_piece = None
        self.state.valid_moves = []
        self.board.clear_highlights()
    
    def is_game_over(self):
        """检查游戏是否结束"""
        return self.state.game_over
    
    def get_winner(self):
        """获取获胜者"""
        return self.state.winner
    
    def undo_move(self):
        """悔棋"""
        if not self.state.move_history:
            return False
        
        # 获取最后一步
        last_move = self.state.move_history.pop()
        piece = last_move['piece']
        from_pos = last_move['from']
        to_pos = last_move['to']
        captured_piece = last_move['captured']
        
        # 恢复棋子位置
        piece.row, piece.col = from_pos[0], from_pos[1]
        
        # 如果有被吃的棋子，恢复它
        if captured_piece:
            self.state.pieces.append(captured_piece)
            # 从阵亡列表中移除
            if captured_piece in self.state.captured_pieces[captured_piece.color]:
                self.state.captured_pieces[captured_piece.color].remove(captured_piece)
        
        # 恢复玩家
        self.state.current_player = "black" if self.state.current_player == "red" else "red"
        
        # 清除游戏结束状态
        self.state.game_over = False
        self.state.winner = None
        
        return True
    
    def reset_game(self):
        """重置游戏"""
        self.state = TraditionalGameState()
        # 确保新状态对象也有player_turn属性
        self.state.player_turn = self.state.current_player
        self.board.clear_highlights()
    
    def run(self):
        """运行传统象棋游戏"""
        pygame.init()
        screen = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("传统象棋")
        clock = pygame.time.Clock()
        
        running = True
        print("[DEBUG] 传统象棋游戏开始运行")
        
        while running:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("[DEBUG] 接收到QUIT事件，退出游戏")
                    running = False
                
                if event.type == pygame.VIDEORESIZE:
                    # 处理窗口大小调整，但如果当前是全屏模式，则不处理VIDEORESIZE事件
                    if not self.is_fullscreen:
                        screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                        # 更新游戏界面尺寸
                        self.game_screen = TraditionalGameScreen(event.w, event.h, 
                                                               self.game_type, self.player_camp)
                        print(f"[DEBUG] 窗口大小调整为: {event.w}x{event.h}")
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # 如果存在确认对话框，优先处理对话框事件
                    if self.confirm_dialog:
                        result = self.confirm_dialog.handle_event(event, mouse_pos)
                        if result is True:  # 用户确认
                            # 用户确认，根据对话框类型执行相应操作
                            if "返回主菜单" in self.confirm_dialog.message:
                                print("[DEBUG] 用户选择返回主菜单")
                                return "back_to_menu"  # 返回模式选择界面
                            elif "退出游戏" in self.confirm_dialog.message:
                                print("[DEBUG] 用户选择退出游戏")
                                running = False  # 结束游戏循环，退出游戏
                            self.confirm_dialog = None
                        elif result is False:  # 用户取消
                            print("[DEBUG] 用户取消对话框")
                            # 用户取消，关闭对话框
                            self.confirm_dialog = None
                    else:
                        # 使用游戏界面处理点击事件
                        self.game_screen.handle_event(event, mouse_pos, self)
                
                # 如果存在统计数据对话框，优先处理它的事件
                if hasattr(self, 'stats_dialog') and self.stats_dialog:
                    result = self.stats_dialog.handle_event(event, mouse_pos)
                    if result == "close":
                        self.stats_dialog = None
                    elif result == "reset":
                        # 重置统计数据
                        from program.controllers.statistics_manager import statistics_manager
                        statistics_manager.reset_statistics()
                        # 重新创建对话框以更新显示
                        from program.ui.dialogs import StatisticsDialog
                        self.stats_dialog = StatisticsDialog()
                    # 不管返回什么结果，都要跳过后续的事件处理，防止同时处理其他操作
                    continue  # 跳过后续的事件处理，防止同时处理其他操作
                
                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # 悔棋快捷键：U键
                    if event.key == pygame.K_u:
                        print("[DEBUG] 按下悔棋键(U)")
                        self.undo_move()
                        
                    # 重来快捷键：R键
                    if event.key == pygame.K_r:
                        print("[DEBUG] 按下重来键(R)")
                        self.reset_game()
                        
                    # 返回主菜单快捷键：ESC键
                    if event.key == pygame.K_ESCAPE:
                        print("[DEBUG] 按下ESC键，显示返回主菜单确认对话框")
                        from program.ui.dialogs import ConfirmDialog
                        self.confirm_dialog = ConfirmDialog(400, 200, "是否要返回主菜单？\n这将丢失您的当前对局信息。")
            
            # 绘制游戏画面
            self.draw(screen)
            
            # 如果存在确认对话框，绘制它
            if self.confirm_dialog:
                self.confirm_dialog.draw(screen)
            # 如果存在统计数据对话框，绘制它
            elif hasattr(self, 'stats_dialog') and self.stats_dialog:
                self.stats_dialog.draw(screen)
            
            pygame.display.flip()
            clock.tick(60)
        
        print("[DEBUG] 传统象棋游戏结束")
        pygame.quit()
        sys.exit()
    
    def ai_make_move(self):
        """AI执行移动（仅在人机模式下使用）"""
        if self.game_type != "pvc" or self.state.current_player != "black" or self.state.game_over:
            return
        
        # 使用AI计算最佳移动
        best_move = self.ai.get_best_move(self.state.pieces, self.state.current_player)
        if best_move:
            piece, to_row, to_col = best_move
            # 选择棋子并移动
            self.state.selected_piece = piece
            moves, capturable = self.state.mode.get_traditional_possible_moves(
                self.state.pieces, piece)
            # 过滤掉会导致送将的移动
            all_moves = moves + capturable
            filtered_moves = self.filter_invalid_moves_for_check(piece, all_moves)
            self.state.valid_moves = filtered_moves
            self.move_piece(to_row, to_col)
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        from program.utils.tools import toggle_fullscreen
        
        # 如果windowed_size未初始化，先设置为当前窗口尺寸
        if self.windowed_size is None:
            self.windowed_size = (self.window_width, self.window_height)
        
        self.screen, self.window_width, self.window_height, self.is_fullscreen, self.windowed_size = \
            toggle_fullscreen(self.window_width, self.window_height, self.is_fullscreen, self.windowed_size)
        
        # 更新游戏界面布局
        self.game_screen.handle_resize((self.window_width, self.window_height))
    
    def draw(self, screen):
        """绘制游戏画面"""
        # 使用游戏界面绘制
        self.game_screen.draw(screen, self.state, self.state.last_move)
        
        # 如果游戏结束，绘制结束信息
        if self.state.game_over:
            self.draw_game_over(screen)
        
        # 关于界面由主循环负责绘制，这里不需要额外处理
    
    def draw_game_over(self, screen):
        """绘制游戏结束信息"""
        overlay = pygame.Surface((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        font = load_font(48, bold=True)
        if self.state.winner:
            winner_text = "红方获胜!" if self.state.winner == "red" else "黑方获胜!"
        else:
            winner_text = "平局!"
        
        text_surface = font.render(winner_text, True, (255, 255, 0))
        text_rect = text_surface.get_rect(center=(DEFAULT_WINDOW_WIDTH // 2, DEFAULT_WINDOW_HEIGHT // 2))
        screen.blit(text_surface, text_rect)


def run_traditional_chess(game_type="pvp"):
    """
    传统象棋入口函数
    :param game_type: 游戏类型 ("pvp"=双人, "pvc"=人机, "network"=网络)
    """
    if game_type == "network":
        from program.core.traditional_network import TraditionalNetworkGame
        # 这里需要知道是否为主机，对于入口函数，我们可以默认为客户端或提供选择
        # 为了简化，我们在这里提供一个简单的选择机制
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.title("网络对战选择")
        root.geometry("300x150")
        
        choice = None
        
        def set_host():
            nonlocal choice
            choice = True
            root.destroy()
        
        def set_client():
            nonlocal choice
            choice = False
            root.destroy()
        
        tk.Label(root, text="选择网络对战角色:").pack(pady=10)
        tk.Button(root, text="作为主机", command=set_host).pack(pady=5)
        tk.Button(root, text="作为客户端", command=set_client).pack(pady=5)
        
        root.mainloop()
        
        if choice is not None:
            network_game = TraditionalNetworkGame(is_host=choice)
            network_game.run()
        else:
            # 如果没有选择，启动双人模式
            game = TraditionalGame("pvp")
            game.run()
    else:
        game = TraditionalGame(game_type)
        game.run()


if __name__ == "__main__":
    # 如果直接运行此文件，默认启动双人对战模式
    run_traditional_chess("pvp")