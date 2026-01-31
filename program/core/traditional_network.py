"""传统象棋网络模式实现"""

import json
import threading
import time
from program.lan.xhlan import SimpleAPI
from program.core.traditional_game import TraditionalGame, TraditionalGameState


class TraditionalNetworkGame:
    """传统象棋网络对战类"""
    
    def __init__(self, is_host=True):
        """
        初始化网络对战
        :param is_host: 是否为主机
        """
        self.is_host = is_host
        self.game = TraditionalGame("network")
        self.api = SimpleAPI
        self.connected = True
        self.receive_thread = None
        self.running = True
        
        # 根据角色分配颜色
        if is_host:
            self.player_color = "red"
            self.opponent_color = "black"
        else:
            self.player_color = "black"
            self.opponent_color = "red"
    
    def send_move(self, from_pos, to_pos, piece_name):
        """发送移动信息到对方"""
        move_data = {
            "type": "move",
            "from": from_pos,
            "to": to_pos,
            "piece": piece_name,
            "player": self.player_color
        }
        try:
            self.api.send(json.dumps(move_data))
        except Exception as e:
            print(f"发送移动数据失败: {e}")
    
    def receive_data(self):
        """接收对方数据的线程函数"""
        while self.running:
            try:
                data = self.api.recv()
                if data:
                    move_data = json.loads(data)
                    if move_data["type"] == "move":
                        self.process_opponent_move(move_data)
                    elif move_data["type"] == "resign":
                        print(f"{move_data['player']} 投降")
                        # 处理对手投降
                        self.game.state.game_over = True
                        self.game.state.winner = "red" if move_data["player"] == "black" else "black"
            except Exception as e:
                if self.running:  # 只在非主动停止时报告错误
                    print(f"接收数据失败: {e}")
                time.sleep(0.1)
    
    def process_opponent_move(self, move_data):
        """处理对手的移动"""
        from_pos = tuple(move_data["from"])
        to_pos = tuple(move_data["to"])
        piece_name = move_data["piece"]
        
        # 找到对应的棋子
        for piece in self.game.state.pieces:
            if (piece.row, piece.col) == from_pos and piece.name == piece_name:
                # 执行移动
                # 检查目标位置是否有对方棋子
                target_piece = self.game._get_piece_at(to_pos[0], to_pos[1])
                if target_piece:
                    self.game.state.pieces.remove(target_piece)
                
                # 移动棋子
                piece.row, piece.col = to_pos[0], to_pos[1]
                
                # 记录移动历史
                self.game.state.move_history.append({
                    'piece': piece,
                    'from': from_pos,
                    'to': to_pos,
                    'captured': target_piece
                })
                self.game.state.last_move = (from_pos[0], from_pos[1], to_pos[0], to_pos[1])
                
                # 检查游戏是否结束
                self.game.state.game_over, self.game.state.winner = self.game.state.mode.is_traditional_game_over(
                    self.game.state.pieces, self.game.state.current_player
                )
                
                # 切换玩家
                self.game.state.current_player = "black" if self.game.state.current_player == "red" else "red"
                
                # 清除选择
                self.game.clear_selection()
                break
    
    def resign(self):
        """投降"""
        resign_data = {
            "type": "resign",
            "player": self.player_color
        }
        try:
            self.api.send(json.dumps(resign_data))
            self.game.state.game_over = True
            self.game.state.winner = "black" if self.player_color == "red" else "red"
        except Exception as e:
            print(f"发送投降信息失败: {e}")
    
    def run(self):
        """运行网络对战"""
        # 启动接收线程
        self.receive_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.receive_thread.start()
        
        # 运行游戏
        pygame = __import__('pygame')
        sys = __import__('sys')
        
        pygame.init()
        screen = pygame.display.set_mode((1200, 900), pygame.RESIZABLE)
        pygame.display.set_caption(f"传统象棋 - 网络对战 ({'主机' if self.is_host else '客户端'})")
        clock = pygame.time.Clock()
        
        running = True
        while running and not self.game.state.game_over:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.running = False
                
                if event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    new_width, new_height = event.w, event.h
                    from program.ui.traditional_chess_board import TraditionalChessBoard
                    # 从game_config_manager导入比例常量
                    from program.controllers.game_config_manager import LEFT_PANEL_WIDTH_RATIO
                    left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * new_width)
                    self.game.board = TraditionalChessBoard(new_width, new_height, left_panel_width + 20, 50)
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # 检查是否是当前玩家的回合
                    if self.game.state.current_player == self.player_color:
                        grid_pos = self.game.board.get_grid_position(mouse_pos)
                        if grid_pos:
                            row, col = grid_pos
                            
                            if self.game.state.selected_piece:
                                if self.game.move_piece(row, col):
                                    # 发送移动信息给对方
                                    piece = self.game.state.selected_piece
                                    self.send_move((piece.row, piece.col), (row, col), piece.name)
                                    
                                    # 清除选择
                                    self.game.clear_selection()
                            else:
                                # 选择己方棋子
                                if self.game.select_piece(row, col):
                                    # 检查选中的是否是己方棋子
                                    if self.game.state.selected_piece.color != self.player_color:
                                        self.game.clear_selection()
            
            # 绘制游戏画面
            self.game.draw(screen)
            
            # 显示当前玩家信息
            font = self.game.board.chess_font or __import__('program.utils.utils').utils.load_font(24)
            player_text = f"当前玩家: {'红方' if self.game.state.current_player == 'red' else '黑方'}"
            player_color = (255, 0, 0) if self.game.state.current_player == 'red' else (0, 0, 0)
            text_surface = font.render(player_text, True, player_color)
            screen.blit(text_surface, (50, 50))
            
            pygame.display.flip()
            clock.tick(60)
        
        # 游戏结束后显示结果
        if self.game.state.game_over:
            self.game.draw_game_over(screen)
            pygame.display.flip()
            # 等待几秒钟后退出
            time.sleep(3)
        
        self.running = False
        pygame.quit()
        sys.exit()


def run_traditional_network_game(is_host=True):
    """
    启动传统象棋网络对战
    :param is_host: 是否为主机
    """
    network_game = TraditionalNetworkGame(is_host)
    network_game.run()