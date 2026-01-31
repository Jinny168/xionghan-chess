"""
匈汉象棋局域网对战游戏类
"""
import pygame

from program.controllers.game_config_manager import (
    FPS,
    CAMP_RED, )
from program.controllers.game_config_manager import game_config
from program.controllers.replay_controller import ReplayController
from program.game import ChessGame
from program.lan.xhlan import XiangqiNetworkGame, SimpleAPI
from program.ui.dialogs import PopupDialog, ConfirmDialog
from program.ui.dialogs import PromotionDialog
from program.ui.network_game_screen import NetworkGameScreen
from program.utils import tools


class NetworkChessGame(ChessGame):
    """网络对战模式的匈汉象棋游戏"""
    
    def __init__(self, is_host=True):
        # 设置网络模式
        self.history_max_visible_lines = 15
        self.black_avatar = None
        self.is_host = is_host
        self.network_enabled = True
        self.opponent_connected = False
        
        # 根据是否为主机设置阵营
        self.player_camp = CAMP_RED if is_host else "black"
        
        # 先调用父类的初始化方法
        super().__init__(game_mode="NETWORK", player_camp=self.player_camp, game_settings=game_config.get_all_settings())
        
        self.game_mode = "NETWORK"  # 网络对战模式
        
        # 确保所有必要的对话框属性都被初始化
        self.pawn_resurrection_dialog = None
        self.promotion_dialog = None
        self.audio_settings_dialog = None
        
        # 添加网络对战状态跟踪
        self.undo_requested = False  # 是否已请求悔棋
        self.restart_requested = False  # 是否已请求重新开始
        self.processing_undo_request = False  # 是否正在处理悔棋请求
        self.processing_restart_request = False  # 是否正在处理重新开始请求
        
        # 重来后状态同步标志
        self.just_restarted = False  # 标记是否刚重来过，需要等待状态同步
        
        # 记录最后移动的玩家，用于悔棋权限控制
        # 游戏开始时，如果是主机（红方），则红方先走，所以最后移动玩家设为红方；
        # 如果是客户端（黑方），则等待红方先走，所以最后移动玩家设为红方
        self.last_moved_player = "red"  # 红方总是先走
        
        # 初始化网络功能 - 在这里我们不初始化SimpleAPI实例，因为已在外部完成
        # 我们直接设置XiangqiNetworkGame的game_instance
        XiangqiNetworkGame.game_instance = self
        self.network_game = XiangqiNetworkGame(self)  # 传递当前实例给网络类
        self.setup_network()
        
        # 使用专门的网络对战界面
        self.game_screen = NetworkGameScreen(self.window_width, self.window_height, self.game_mode, self.player_camp)
        
        # 更新全屏按钮的文本以反映当前状态
        self.game_screen.update_fullscreen_button_text(self.is_fullscreen)

    def setup_network(self):
        """设置网络连接"""
        # 设置网络模式，使用已存在的SimpleAPI实例
        role = 'SERVER' if self.is_host else 'CLIENT'
        XiangqiNetworkGame.set_network_mode(role, SimpleAPI.instance)
        print(f"{'主机' if self.is_host else '客户端'}模式初始化完成")
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        # 使用通用的全屏切换函数
        self.screen, self.window_width, self.window_height, self.is_fullscreen, self.windowed_size = \
            tools.toggle_fullscreen(self.window_width, self.window_height, self.is_fullscreen, self.windowed_size)

        # 更新界面布局
        self.game_screen.update_layout()
        
        # 更新全屏按钮的文本
        self.game_screen.update_fullscreen_button_text(self.is_fullscreen)

    def draw(self):
        """绘制游戏界面 - 网络对战模式特化版本"""
        # 使用专门的网络对战界面绘制
        self.game_screen.draw(
            self.screen, self.game_state, self.last_move, self.last_move_notation,
            self.popup, self.confirm_dialog, self.pawn_resurrection_dialog,
            self.promotion_dialog, self.audio_settings_dialog
        )

    def handle_click(self, pos):
        """处理鼠标点击事件 - 网络对战专用"""
        if self.game_state.game_over:
            return

        # 如果刚重来过，等待状态同步完成
        if hasattr(self, 'just_restarted') and self.just_restarted:
            print("[DEBUG] 刚重来过，等待状态同步完成...")
            return

        # 如果不是轮到本地玩家，忽略点击
        if self.game_state.player_turn != self.player_camp:
            print(f"[DEBUG] 不是本地玩家回合，当前玩家: {self.game_state.player_turn}, 本地玩家: {self.player_camp}")
            return

        # 获取点击的棋盘位置
        grid_pos = self.game_screen.board.get_grid_position(pos)
        if not grid_pos:
            return

        row, col = grid_pos

        # 如果正在等待升变选择，不处理棋盘点击
        if hasattr(self, 'promotion_dialog') and self.promotion_dialog:
            return

        # 检查是否点击了空闲的兵/卒起始位置，触发复活对话框
        current_player = self.game_state.player_turn
        if self.selected_piece is None:  # 如果没有选中任何棋子
            # 检查是否点击了兵/卒初始位置且该位置为空
            if ((current_player == "red" and row == 8) or (current_player == "black" and row == 4)) and \
               self.game_state.get_piece_at(row, col) is None:
                # 检查当前玩家在局的兵/卒数量是否小于7
                if self.game_state.get_pawn_count(current_player) < 7:
                    # 检查是否满足复活条件
                    resurrection_positions = self.game_state.get_resurrection_positions()
                    if (row, col) in resurrection_positions[current_player]:
                        # 弹出复活确认对话框
                        from program.ui.dialogs import PawnResurrectionDialog
                        self.pawn_resurrection_dialog = PawnResurrectionDialog(
                            500, 200, current_player, (row, col)
                        )
                        return

        # 选择棋子或移动棋子
        if self.selected_piece is None:
            # 尝试选择棋子
            piece = self.game_state.get_piece_at(row, col)
            if piece and piece.color == self.game_state.player_turn:
                self.selected_piece = (row, col)
                self.game_screen.board.highlight_position(row, col)

                # 计算可能的移动位置
                possible_moves, capturable = self.game_state.calculate_possible_moves(row, col)
                self.game_screen.board.set_possible_moves(possible_moves)
                self.game_screen.board.set_capturable_positions(capturable)
        else:
            sel_row, sel_col = self.selected_piece

            # 检查是否点击了同一个棋子（取消选择）
            if sel_row == row and sel_col == col:
                self.selected_piece = None
                self.game_screen.board.clear_highlights()
                return

            # 检查是否选择了另一个己方棋子（更换选择）
            new_piece = self.game_state.get_piece_at(row, col)
            if new_piece and new_piece.color == self.game_state.player_turn:
                self.selected_piece = (row, col)
                self.game_screen.board.highlight_position(row, col)

                # 计算新选择棋子的可能移动
                possible_moves, capturable = self.game_state.calculate_possible_moves(row, col)
                self.game_screen.board.set_possible_moves(possible_moves)
                self.game_screen.board.set_capturable_positions(capturable)
                return

            # 已选择棋子，尝试移动
            captured_piece = self.game_state.get_piece_at(row, col)
            move_successful = self.game_state.move_piece(sel_row, sel_col, row, col)

            if move_successful:
                print(f"[DEBUG] 移动成功: {sel_row},{sel_col} -> {row},{col}")
                
                # 发送移动到对手
                self.send_network_move(sel_row, sel_col, row, col)
                
                # 检查是否需要升变（兵/卒到达对方底线）
                if self.game_state.needs_promotion:
                    # 获取兵的颜色
                    pawn_color = self.game_state.promotion_pawn.color if self.game_state.promotion_pawn else self.game_state.player_turn
                    print(f"[DEBUG] 需要升变: {pawn_color}方兵到达底线")
                    # 自动弹出升变选择对话框
                    self.promotion_dialog = PromotionDialog(
                        500, 400, pawn_color, (row, col), self.game_state.available_promotion_pieces
                    )

                # 记录上一步走法
                self.last_move = (sel_row, sel_col, row, col)

                # 生成上一步走法的中文表示
                piece = self.game_state.get_piece_at(row, col)
                if piece:
                    from program.utils import tools
                    self.last_move_notation = tools.generate_move_notation(piece, sel_row, sel_col, row, col)

                # 播放选子音效
                if self.selected_piece and not captured_piece:
                    try:
                        self.sound_manager.play_sound('choose')
                    except (AttributeError, KeyError):
                        pass
                
                # 播放移动音效
                if captured_piece:
                    try:
                        self.sound_manager.play_sound('eat')
                    except (AttributeError, KeyError):
                        pass
                else:
                    try:
                        self.sound_manager.play_sound('drop')
                    except (AttributeError, KeyError):
                        pass

                # 记录最后移动的玩家（当前玩家）
                self.last_moved_player = self.player_camp
                print(f"[DEBUG] 记录最后移动玩家: {self.player_camp}")
                
                # 切换玩家回合（本地玩家移动后，轮到对手）
                # 在网络游戏中，本地玩家移动后，应该将回合交给对手
                # 注意：这里要确保切换到非本地玩家的阵营
                opponent_color = "black" if self.player_camp == "red" else "red"
                self.game_state.player_turn = opponent_color
                print(f"[DEBUG] 移动后切换玩家: {opponent_color} (当前玩家阵营: {self.player_camp})")
                
                # 更新头像状态
                self.update_avatars()

                # 更新悔棋按钮状态
                self.update_undo_button_state()

                # 播放将军/绝杀音效
                self.check_sound_play()

                # 移动完成后清除所有高亮显示
                self.game_screen.board.clear_highlights()
                self.selected_piece = None

                # 检查游戏是否结束
                if self.game_state.game_over:
                    winner_text = self.game_state.get_winner_text()

                    # 更新时间数据，确保获取最终值
                    red_time, black_time = self.game_state.update_times()
                    total_time = self.game_state.total_time

                    # 创建弹窗并传入时间信息
                    self.popup = PopupDialog(
                        400, 320,
                        winner_text,
                        total_time,
                        red_time,
                        black_time
                    )
            else:
                # 移动失败，可能是由于会导致送将，取消选择但不执行移动
                self.selected_piece = None
                self.game_screen.board.clear_highlights()

            # 无论如何都取消选择状态
            self.selected_piece = None
            self.game_screen.board.clear_highlights()

    def check_sound_play(self):
        # 检查游戏是否结束
        if self.game_state.game_over:
            return
        
        # 使用SoundManager中的通用方法播放将军/绝杀音效
        self.sound_manager.check_and_play_game_sound(self.game_state)

    @staticmethod
    def send_network_move(from_row, from_col, to_row, to_col):
        """发送移动到网络对手"""
        print(f"发送本地移动: {from_row},{from_col} -> {to_row},{to_col}")
        # 调用网络接口发送移动
        try:
            XiangqiNetworkGame.send_move(from_row, from_col, to_row, to_col)
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            print(f"发送网络移动失败: {e}")

    def receive_network_move(self, from_row, from_col, to_row, to_col):
        """接收来自网络对手的移动"""
        print(f"[DEBUG] 接收对手移动: {from_row},{from_col} -> {to_row},{to_col}")
        print(f"[DEBUG] 接收前玩家回合: {self.game_state.player_turn}, 本地玩家阵营: {self.player_camp}")
        
        # 如果刚重来过，可能需要一点时间来同步状态
        if hasattr(self, 'just_restarted') and self.just_restarted:
            # 重置标志
            self.just_restarted = False
            print("[DEBUG] 重来后接收移动，确保状态同步")
        
        # 记录最后移动的玩家（对手）
        self.last_moved_player = "black" if self.player_camp == "red" else "red"
        
        # 检查游戏是否已结束
        if self.game_state.game_over:
            print("[DEBUG] 游戏已结束，忽略对手移动")
            return
        
        # 执行对手的移动
        success = self.game_state.move_piece(from_row, from_col, to_row, to_col)
        if success:
            print(f"[DEBUG] 对手移动成功执行: {from_row},{from_col} -> {to_row},{to_col}")
            
            # 记录上一步走法
            self.last_move = (from_row, from_col, to_row, to_col)

            # 生成上一步走法的中文表示
            piece = self.game_state.get_piece_at(to_row, to_col)
            if piece:
                from program.utils import tools
                self.last_move_notation = tools.generate_move_notation(piece, from_row, from_col, to_row, to_col)

            # 播放音效
            captured_piece = self.game_state.get_piece_at(to_row, to_col)
            if captured_piece:
                try:
                    self.sound_manager.play_sound('eat')
                except (AttributeError, KeyError):
                    pass
            else:
                try:
                    self.sound_manager.play_sound('drop')
                except:
                    pass

            # 更新头像状态
            self.update_avatars()

            # 播放将军/绝杀音效
            self.check_sound_play()

            # 切换玩家回合（这是对手的移动，所以现在轮到本地玩家走棋）
            # 关键：接收到对手的移动后，应该切换到本地玩家的回合
            self.game_state.player_turn = self.player_camp
            print(f"[DEBUG] 收到对手移动后切换到本地玩家: {self.player_camp}")
            self.update_avatars()
            
            # 更新悔棋按钮状态以反映当前玩家状态
            self.update_undo_button_state()
        else:
            print(f"[DEBUG] 对手移动执行失败: {from_row},{from_col} -> {to_row},{to_col}")
            print(f"[DEBUG] 当前游戏状态: 玩家回合={self.game_state.player_turn}, 本地玩家阵营={self.player_camp}")
            print(f"[DEBUG] 棋子信息: ({from_row},{from_col}) -> {self.game_state.get_piece_at(from_row, from_col)}, ({to_row},{to_col}) -> {self.game_state.get_piece_at(to_row, to_col)}")
            
            # 移动失败可能是因为游戏状态不同步，特别是在重新开始后
            # 在这种情况下，需要重新同步状态
            if not self.processing_restart_request:  # 如果没有在处理重启请求
                # 即使移动失败，也要确保玩家回合正确切换
                # 重要：这里需要确保状态正确，而不是简单地切换回合
                self.game_state.player_turn = self.player_camp
                print(f"[DEBUG] 移动失败，但切换到本地玩家: {self.player_camp}")
                self.update_avatars()
                
                # 更新悔棋按钮状态
                self.update_undo_button_state()
            else:
                print("[DEBUG] 移动失败但正在处理重启请求，尝试重新同步状态")
                # 发送状态同步请求
                self.send_state_sync_confirmation()
                
            # 如果移动失败，可能是由于游戏状态不同步，需要特殊处理
            # 在重来后第一次移动时尤其可能出现这种情况

    def handle_opponent_win(self):
        """处理对手胜利的情况"""
        self.game_state.game_over = True
        self.game_state.winner = "black" if self.player_camp == "red" else "red"
        
        winner_text = self.game_state.get_winner_text()
        # 更新时间数据
        red_time, black_time = self.game_state.update_times()
        total_time = self.game_state.total_time

        # 创建弹窗并传入时间信息
        self.popup = PopupDialog(400, 320,
            winner_text,
            total_time,
            red_time,
            black_time
        )

    def perform_restart(self):
        """执行重新开始游戏"""
        # 保存当前的玩家阵营
        current_player_camp = self.player_camp
        
        self._reset_common_game_state()
        
        # 重新设置玩家回合 - 游戏开始时总是红方先走
        self.game_state.player_turn = "red"  # 游戏开始时红方先走
        # 重置后红方先走，但在游戏刚开始时，还没有人移动过
        # 根据经验法则，初始化时应该将last_moved_player设置为"red"，以确保悔棋功能在游戏开始时有正确的初始值
        self.last_moved_player = "red"  # 游戏开始时的初始值，红方先走
        
        # 确保界面状态同步
        self.update_avatars()
        
        # 更新悔棋按钮状态
        self.update_undo_button_state()
        
        # 确保绘制更新
        self.draw()
        
        # 标记刚重来过，需要等待状态同步
        self.just_restarted = True
        
        # 发送状态同步确认，确保双方状态一致
        self.send_state_sync_confirmation()
        
        # 重置刚重来的标志后稍作延迟，避免立即响应移动
        import threading
        def reset_restart_flag():
            import time
            time.sleep(0.5)  # 等待500毫秒，确保状态同步完成
            self.just_restarted = False
            print("[DEBUG] 重来后状态同步标志已重置")
        
        # 在后台线程中重置标志
        sync_thread = threading.Thread(target=reset_restart_flag)
        sync_thread.daemon = True
        sync_thread.start()
    
    def perform_undo(self):
        """执行悔棋操作"""
        # 悔棋操作只回退当前玩家的一步
        if len(self.game_state.move_history) >= 1:
            # 记录悔棋前的最后移动玩家，这个信息对于权限控制很重要
            original_last_moved_player = self.last_moved_player
            
            # 只回退一步（当前玩家的上一步）
            # 注意：每次调用undo_move会自动切换玩家回合
            self.game_state.undo_move()  # 撤销当前玩家的移动
            
            # 更新最后移动的玩家为当前玩家（即悔棋后应该走棋的玩家）
            self.last_moved_player = self.game_state.player_turn
            
            # 更新悔棋按钮状态
            self.update_undo_button_state()
            
            # 更新界面
            self.selected_piece = None
            self.last_move = None
            self.last_move_notation = ""
            
            # 更新头像状态
            self.update_avatars()
            
            # 发送状态同步确认，确保双方状态一致
            self.send_state_sync_confirmation()
    
    def send_state_sync_confirmation(self):
        """发送状态同步确认信息，确保双方状态一致"""
        if hasattr(XiangqiNetworkGame, 'api_instance') and XiangqiNetworkGame.api_instance:
            try:
                # 计算当前游戏状态的哈希值
                import hashlib
                import json
                
                # 创建状态快照
                state_snapshot = {
                    'player_turn': self.game_state.player_turn,
                    'pieces': [(p.name, p.color, p.row, p.col) for p in sorted(self.game_state.pieces, key=lambda x: (x.row, x.col, x.name))],
                    'move_history_length': len(self.game_state.move_history),
                    'captured_pieces': {
                        'red': [p.name for p in self.game_state.captured_pieces['red']],
                        'black': [p.name for p in self.game_state.captured_pieces['black']]
                    },
                    'last_moved_player': self.last_moved_player
                }
                
                # 计算哈希
                state_str = json.dumps(state_snapshot, sort_keys=True)
                state_hash = hashlib.md5(state_str.encode()).hexdigest()
                
                # 发送状态同步确认
                XiangqiNetworkGame.api_instance.send(state_sync={'hash': state_hash, 'snapshot': state_snapshot})
                print(f"[DEBUG] 发送状态同步确认: {state_hash}")
            except Exception as e:
                print(f"[DEBUG] 发送状态同步确认失败: {e}")
    
    def handle_state_sync_confirmation(self, state_data):
        """处理状态同步确认"""
        try:
            import hashlib
            import json
            
            # 重建本地状态快照
            local_snapshot = {
                'player_turn': self.game_state.player_turn,
                'pieces': [(p.name, p.color, p.row, p.col) for p in sorted(self.game_state.pieces, key=lambda x: (x.row, x.col, x.name))],
                'move_history_length': len(self.game_state.move_history),
                'captured_pieces': {
                    'red': [p.name for p in self.game_state.captured_pieces['red']],
                    'black': [p.name for p in self.game_state.captured_pieces['black']]
                },
                'last_moved_player': self.last_moved_player,
                'game_over': self.game_state.game_over,
                'winner': self.game_state.winner,
                'needs_promotion': self.game_state.needs_promotion,
                'promotion_pawn': (self.game_state.promotion_pawn.name, self.game_state.promotion_pawn.color, self.game_state.promotion_pawn.row, self.game_state.promotion_pawn.col) if self.game_state.promotion_pawn else None,
                'available_promotion_pieces': self.game_state.available_promotion_pieces[:]
            }
            
            # 计算本地哈希
            local_str = json.dumps(local_snapshot, sort_keys=True)
            local_hash = hashlib.md5(local_str.encode()).hexdigest()
            
            remote_hash = state_data['hash']
            
            print(f"[DEBUG] 本地状态哈希: {local_hash}")
            print(f"[DEBUG] 远程状态哈希: {remote_hash}")
            
            if local_hash != remote_hash:
                print("[DEBUG] 状态不一致，需要重新同步!")
                # 如果状态不一致，发送完整状态给对方
                XiangqiNetworkGame.api_instance.send(full_state_sync={'snapshot': local_snapshot})
            else:
                print("[DEBUG] 状态同步确认完成，双方状态一致")
                
                # 确保当前玩家状态正确
                if self.game_state.player_turn != local_snapshot['player_turn']:
                    self.game_state.player_turn = local_snapshot['player_turn']
                    self.update_avatars()
                    
        except Exception as e:
            print(f"[DEBUG] 处理状态同步确认失败: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_full_state_sync(self, full_state_data):
        """处理完整状态同步"""
        try:
            snapshot = full_state_data['snapshot']
            
            # 恢复棋子位置
            from program.core.chess_pieces import PieceFactory
            
            # 保存当前的游戏状态
            old_player_turn = self.game_state.player_turn
            old_captured_pieces = self.game_state.captured_pieces.copy()
            
            # 重新创建棋盘状态
            self.game_state.pieces.clear()
            for piece_data in snapshot['pieces']:
                name, color, row, col = piece_data
                # 根据名称创建相应类型的棋子
                piece = PieceFactory.create_piece_by_name(name, color, row, col)
                if piece:
                    self.game_state.pieces.append(piece)
            
            # 恢复被吃棋子 - 这部分比较复杂，需要重构被吃棋子列表
            # 我们需要根据原始被吃棋子的信息重建列表
            # 这里简化处理，直接清空被吃棋子列表
            self.game_state.captured_pieces = {'red': [], 'black': []}
            
            # 恢复游戏状态
            self.game_state.player_turn = snapshot['player_turn']
            self.last_moved_player = snapshot['last_moved_player']
            
            # 恢复其他状态
            self.game_state.game_over = False  # 确保游戏未结束
            self.game_state.winner = None
            
            print("[DEBUG] 完整状态同步完成")
        except Exception as e:
            print(f"[DEBUG] 处理完整状态同步失败: {e}")

    def _reset_common_game_state(self):
        """重置游戏状态的公共方法"""
        # 重置游戏状态
        self.game_state.reset()
        
        # 重置相关变量
        self.selected_piece = None
        self.last_move = None
        self.last_move_notation = ""
        self.popup = None
        self.confirm_dialog = None
        self.pawn_resurrection_dialog = None
        self.promotion_dialog = None
        self.undo_requested = False
        self.restart_requested = False
        
        # 重置最后移动玩家为红方（游戏开始时红方先走）
        self.last_moved_player = "red"
        
        # 重置界面状态
        self.game_screen.board.clear_highlights()
        self.game_screen.board.set_possible_moves([])
        self.game_screen.board.set_capturable_positions([])
        
        # 重置头像状态
        self.update_avatars()

    @staticmethod
    def display_chat_message(message):
        """显示聊天消息"""
        print(f"收到聊天消息: {message}")

    def handle_event(self, event, mouse_pos):
        """处理游戏事件 - 网络对战专用"""
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

        # 处理鼠标滚轮事件
        if event.type == pygame.MOUSEWHEEL:
            # 检查鼠标是否在棋谱区域
            right_panel_x = self.window_width - 350
            if right_panel_x <= mouse_pos[0] <= self.window_width - 10 and mouse_pos[1] >= 300:
                # 滚动棋谱
                self.history_scroll_y = max(0, self.history_scroll_y - event.y)
                total_moves = len(self.game_state.move_history)
                max_scroll = max(0, total_moves - self.history_max_visible_lines)
                self.history_scroll_y = min(self.history_scroll_y, max_scroll)

        # 处理鼠标点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查是否点击了悔棋按钮
            if (hasattr(self.game_screen, 'undo_button') and 
                self.game_screen.undo_button and 
                self.game_screen.undo_button.is_clicked(mouse_pos, event) and
                hasattr(self.game_screen.undo_button, 'enabled') and 
                self.game_screen.undo_button.enabled):
                # 发送悔棋请求
                if not self.undo_requested:  # 避免重复请求
                    self.undo_requested = True
                    XiangqiNetworkGame.send_undo_request()
                    
            # 检查是否点击了重来按钮
            elif (hasattr(self.game_screen, 'restart_button') and 
                  self.game_screen.restart_button and 
                  self.game_screen.restart_button.is_clicked(mouse_pos, event)):
                # 发送重来请求
                if not self.restart_requested:  # 避免重复请求
                    self.restart_requested = True
                    XiangqiNetworkGame.send_restart_request()
                    
            # 检查是否点击了全屏按钮
            elif hasattr(self.game_screen, 'fullscreen_button') and self.game_screen.fullscreen_button.is_clicked(mouse_pos, event):
                self.toggle_fullscreen()
            
            # 检查是否点击了音效设置按钮
            elif hasattr(self.game_screen, 'audio_settings_button') and self.game_screen.audio_settings_button.is_clicked(mouse_pos, event):
                from program.ui.dialogs import AudioSettingsDialog
                self.audio_settings_dialog = AudioSettingsDialog(500, 350, self.sound_manager)

            # 检查是否点击了退出游戏按钮
            elif hasattr(self.game_screen, 'exit_button') and self.game_screen.exit_button and self.game_screen.exit_button.is_clicked(mouse_pos, event):
                # 检查是否已经存在确认对话框，避免重复创建
                if self.confirm_dialog is None:
                    # 显示确认对话框确认退出游戏
                    self.confirm_dialog = ConfirmDialog(
                        400, 200, "是否要退出网络对局？\n这将视为认输。"
                    )
                    self.confirm_dialog.type = "exit_game"  # 标记为退出游戏对话框

            # 处理棋盘点击
            elif not self.game_state.game_over:
                self.handle_click(mouse_pos)

    def run(self):
        """网络对战游戏主循环"""
        while True:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # 发送认输信号
                    try:
                        XiangqiNetworkGame.send_resign()
                    except (ConnectionError, TimeoutError):
                        pass
                    self.sound_manager.stop_background_music()
                    return "back_to_menu"

                # 处理各种事件
                if hasattr(self, 'promotion_dialog') and self.promotion_dialog is not None:
                    result = self.promotion_dialog.handle_event(event, mouse_pos)
                    if result is not None:
                        if isinstance(result, tuple) and result[0]:
                            # 执行升变
                            selected_index = result[1]
                            self.game_state.perform_promotion(selected_index)
                            
                            # 清除升变对话框
                            self.promotion_dialog = None

                            # 记录最后移动的玩家（当前玩家）
                            self.last_moved_player = self.player_camp
                            print(f"[DEBUG] 兵升变后记录最后移动玩家: {self.player_camp}")
                            
                            # 切换玩家回合 - 升变完成后，轮到对手走棋
                            # 在网络游戏中，升变后同样需要切换到对手
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                            
                            # 跳过后续事件处理，防止同时处理其他操作
                            continue
                        elif result is False:
                            # 取消升变
                            self.promotion_dialog = None
        
                            # 切换玩家回合 - 即使取消升变，走子机会也已消耗，轮到对手
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变取消后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                            
                            # 跳过后续事件处理，防止同时处理其他操作
                            continue
                elif hasattr(self, 'pawn_resurrection_dialog') and self.pawn_resurrection_dialog is not None:
                    result = self.pawn_resurrection_dialog.handle_event(event, mouse_pos)
                    if result is not None:  # 用户已做出选择
                        if result:  # 确认复活
                            # 执行复活逻辑
                            current_player = self.game_state.player_turn
                            # 获取复活位置
                            resurrection_pos = self.pawn_resurrection_dialog.position
                        
                            # 执行复活
                            self.game_state.perform_pawn_resurrection(current_player, resurrection_pos)
                            
                            # 清除复活对话框
                            self.pawn_resurrection_dialog = None
                        
                            # 记录最后移动的玩家（当前玩家）
                            self.last_moved_player = self.player_camp
                            print(f"[DEBUG] 兵复活后记录最后移动玩家: {self.player_camp}")
                            
                            # 切换玩家回合 - 复活棋子后，轮到对手走棋
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵复活后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                            
                            # 跳过后续事件处理，防止同时处理其他操作
                            continue
                        else:  # 取消
                            # 清除复活对话框
                            self.pawn_resurrection_dialog = None
                        
                            # 记录最后移动的玩家（当前玩家）
                            self.last_moved_player = self.player_camp
                            print(f"[DEBUG] 兵复活取消后记录最后移动玩家: {self.player_camp}")
                            
                            # 即使取消复活，也应切换回合（因为点击了复活位置）
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵复活取消后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                            
                            # 跳过后续事件处理，防止同时处理其他操作
                            continue
                elif hasattr(self, 'confirm_dialog') and self.confirm_dialog:
                    result = self.confirm_dialog.handle_event(event, mouse_pos)
                    if result is not None:
                        if result:
                            # 检查确认对话框的类型
                            dialog_type = getattr(self.confirm_dialog, 'type', None)
                            
                            if dialog_type == "undo_request":
                                # 同意悔棋请求
                                XiangqiNetworkGame.send_undo_response(True)
                                self.perform_undo()
                                self.confirm_dialog = None  # 清除对话框
                            elif dialog_type == "restart_request":
                                # 同意重新开始请求
                                XiangqiNetworkGame.send_restart_response(True)
                                self.perform_restart()
                                self.confirm_dialog = None  # 清除对话框
                            elif dialog_type == "exit_game":
                                # 退出游戏确认
                                self.confirm_dialog = None
                                # 发送认输信号并退出
                                try:
                                    XiangqiNetworkGame.send_resign()
                                except (ConnectionError, TimeoutError):
                                    pass
                                self.sound_manager.stop_background_music()
                                return "back_to_menu"
                            else:
                                # 普通确认对话框（如退出游戏）
                                self.confirm_dialog = None
                                # 发送认输信号并退出
                                try:
                                    XiangqiNetworkGame.send_resign()
                                except (ConnectionError, TimeoutError):
                                    pass
                                self.sound_manager.stop_background_music()
                                return "back_to_menu"
                        else:
                            # 用户点击了"否"或取消
                            dialog_type = getattr(self.confirm_dialog, 'type', None)
                            
                            if dialog_type == "undo_request":
                                # 拒绝悔棋请求
                                XiangqiNetworkGame.send_undo_response(False)
                                self.confirm_dialog = None  # 清除对话框
                            elif dialog_type == "restart_request":
                                # 拒绝重新开始请求
                                XiangqiNetworkGame.send_restart_response(False)
                                self.confirm_dialog = None  # 清除对话框
                            elif dialog_type == "exit_game":
                                # 取消退出游戏
                                self.confirm_dialog = None
                            else:
                                self.confirm_dialog = None
                elif self.game_state.game_over:
                    # 即使没有弹窗，也要检查是否需要创建
                    if self.popup is None:
                        print("[DEBUG] 网络对战模式 - 游戏已结束，但弹窗尚未创建，正在创建弹窗")
                        # 创建弹窗
                        winner_text = self.game_state.get_winner_text()
                        red_time, black_time = self.game_state.update_times()
                        total_time = self.game_state.total_time
                        self.popup = PopupDialog(400, 320, winner_text, total_time, red_time, black_time)
                    # 处理弹窗事件
                    if self.popup:
                        popup_result = self.popup.handle_event(event, mouse_pos)
                        if popup_result == "restart":
                            # 网络对局结束后返回主菜单
                            self.sound_manager.stop_background_music()
                            return "back_to_menu"
                        elif popup_result == "replay":
                            # 进入复盘模式

                            from program.ui.replay_screen import ReplayScreen
                        
                            # 创建复盘控制器
                            replay_controller = ReplayController.enter_replay_mode(self.game_state)
                            
                            # 创建并运行复盘界面
                            replay_screen = ReplayScreen(self.game_state, replay_controller)
                            replay_screen.run()
                            
                            # 复盘结束后可能需要一些清理工作
                            # （例如，可能需要重新绘制游戏界面）
                        elif popup_result == "return":
                            # 返回主菜单
                            self.sound_manager.stop_background_music()
                            return "back_to_menu"
                elif self.audio_settings_dialog:
                    result = self.audio_settings_dialog.handle_event(event, mouse_pos)
                    if result == "ok":  # 确认设置
                        self.audio_settings_dialog = None
                    elif result == "cancel":  # 取消设置
                        self.audio_settings_dialog = None
                    elif result == "reset":  # 重置设置
                        # 对话框保持打开，但重置值
                        pass
                    elif result == "volume_changed" or result == "style_changed":  # 音量改变或风格切换
                        # 对话框保持打开
                        pass
                    # 不管返回什么结果，都要跳过后续的事件处理，防止同时处理其他操作
                    continue  # 跳过后续的事件处理，防止同时处理其他操作
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # 检查是否点击了悔棋按钮
                    if (hasattr(self.game_screen, 'undo_button') and 
                        self.game_screen.undo_button and 
                        self.game_screen.undo_button.is_clicked(mouse_pos, event) and
                        hasattr(self.game_screen.undo_button, 'enabled') and 
                        self.game_screen.undo_button.enabled):
                        # 发送悔棋请求
                        if not self.undo_requested:  # 避免重复请求
                            self.undo_requested = True
                            XiangqiNetworkGame.send_undo_request()
                    
                    # 检查是否点击了重来按钮
                    elif (hasattr(self.game_screen, 'restart_button') and 
                          self.game_screen.restart_button and 
                          self.game_screen.restart_button.is_clicked(mouse_pos, event)):
                        # 发送重来请求
                        if not self.restart_requested:  # 避免重复请求
                            self.restart_requested = True
                            XiangqiNetworkGame.send_restart_request()
                    
                    # 检查是否点击了全屏按钮
                    elif hasattr(self.game_screen, 'fullscreen_button') and self.game_screen.fullscreen_button.is_clicked(mouse_pos, event):
                        self.toggle_fullscreen()
                    
                    # 检查是否点击了音效设置按钮
                    elif hasattr(self.game_screen, 'audio_settings_button') and self.game_screen.audio_settings_button.is_clicked(mouse_pos, event):
                        from program.ui.dialogs import AudioSettingsDialog
                        self.audio_settings_dialog = AudioSettingsDialog(500, 350, self.sound_manager)

                    # 检查是否点击了退出游戏按钮
                    elif hasattr(self.game_screen, 'exit_button') and self.game_screen.exit_button and self.game_screen.exit_button.is_clicked(mouse_pos, event):
                        # 检查是否已经存在确认对话框，避免重复创建
                        if self.confirm_dialog is None:
                            # 显示确认对话框确认退出游戏
                            self.confirm_dialog = ConfirmDialog(
                                400, 200, "是否要退出网络对局？\n这将视为认输。"
                            )
                            self.confirm_dialog.type = "exit_game"  # 标记为退出游戏对话框

                    # 处理棋盘点击
                    elif not self.game_state.game_over:
                        self.handle_click(mouse_pos)

            # 更新按钮的悬停状态
            self.game_screen.update_button_states(mouse_pos)
            
            # 更新悔棋按钮的状态
            self.update_undo_button_state()

            # 绘制画面
            self.draw()
            # 绘制将军/绝杀提示
            self.check_checkmate_tip_manager.draw_tip(self.screen, self.game_state, self.game_screen.board)
            pygame.display.flip()
            self.clock.tick(FPS)
    
    def request_undo_confirmation(self):
        """请求本地玩家确认是否同意悔棋"""
        # 检查是否已经在处理悔棋请求
        if hasattr(self, 'processing_undo_request') and self.processing_undo_request:
            return  # 避免重复请求
        
        # 设置处理标志
        self.processing_undo_request = True
        
        # 显示一个确认对话框
        self.confirm_dialog = ConfirmDialog(
            400, 200, "对手请求悔棋，\n是否同意？"
        )
        # 特殊标记这个对话框是悔棋请求
        self.confirm_dialog.type = "undo_request"
    
    def handle_undo_response(self, accepted):
        """处理对手对悔棋请求的回复"""
        if accepted:
            print("对手同意悔棋，执行悔棋操作")
            # 执行悔棋操作
            self.perform_undo()
            # 重置悔棋请求状态
            self.undo_requested = False
            self.processing_undo_request = False
        else:
            print("对手拒绝悔棋请求")
            # 重置悔棋请求状态
            self.undo_requested = False
            self.processing_undo_request = False
            # 可以显示提示信息
            pass
    
    def request_restart_confirmation(self):
        """请求本地玩家确认是否同意重新开始"""
        # 检查是否已经在处理重新开始请求
        if hasattr(self, 'processing_restart_request') and self.processing_restart_request:
            return  # 避免重复请求
        
        # 设置处理标志
        self.processing_restart_request = True
        
        # 显示一个确认对话框
        self.confirm_dialog = ConfirmDialog(
            400, 200, "对手请求重新开始，\n是否同意？"
        )
        # 特殊标记这个对话框是重新开始请求
        self.confirm_dialog.type = "restart_request"
    
    def handle_restart_response(self, accepted):
        """处理对手对重新开始请求的回复"""
        if accepted:
            print("对手同意重新开始，执行重新开始操作")
            # 执行重新开始操作
            self.perform_restart()
            # 重置重新开始请求状态
            self.restart_requested = False
            self.processing_restart_request = False
        else:
            print("对手拒绝重新开始请求")
            # 重置重新开始请求状态
            self.restart_requested = False
            self.processing_restart_request = False
            # 可以显示提示信息
            pass

    def request_state_sync(self):
        """主动请求状态同步"""
        print("[DEBUG] 主动请求状态同步")
        self.send_state_sync_confirmation()
        
        # 设置定时器，在一定时间后检查状态是否同步
        import threading
        def check_sync_status():
            import time
            time.sleep(2)  # 等待2秒后检查状态
            print("[DEBUG] 检查状态同步状态")
            # 可以在这里添加额外的同步验证逻辑
            
        # 在后台线程中执行检查
        check_thread = threading.Thread(target=check_sync_status)
        check_thread.daemon = True
        check_thread.start()

    def update_undo_button_state(self):
        """更新悔棋按钮状态 - 网络对战模式特化版本"""
        # 检查游戏屏幕是否有悔棋按钮
        if (hasattr(self, 'game_screen') and 
            hasattr(self.game_screen, 'undo_button') and 
            self.game_screen.undo_button):
            # 悔棋按钮的启用条件：
            # 1. 游戏未结束
            # 2. 不在处理悔棋请求中
            # 3. 不在重来后等待状态同步期间
            # 4. 本地玩家有权悔棋（根据最后移动玩家判断）
            game_not_over = not self.game_state.game_over
            not_processing_undo = not hasattr(self, 'processing_undo_request') or not self.processing_undo_request
            not_just_restarted = not hasattr(self, 'just_restarted') or not self.just_restarted
            
            # 判断本地玩家是否可以悔棋：
            # 1. 本地玩家是最后移动的玩家（最常见的情况）
            # 2. 特殊情况：游戏开始时红方先走，但还没有移动过
            can_undo = (self.last_moved_player == self.player_camp)
            
            # 悔棋按钮在本地玩家有权悔棋且不在处理状态时可用
            self.game_screen.undo_button.enabled = (
                game_not_over and 
                not_processing_undo and 
                not_just_restarted and 
                can_undo
            )

    def update_avatars(self):
        """更新头像状态 - 网络对战模式特化版本"""
        # 使用专门的网络对战界面更新头像
        if hasattr(self, 'game_screen') and self.game_screen:
            self.game_screen.update_avatars(self.game_state, self.is_host)
