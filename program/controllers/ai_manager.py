"""
AI管理器 - 将游戏中的AI相关操作独立出来
"""
import random
import pygame
from program.ai.chess_ai import ChessAI


class AIManager:
    """AI管理器类，负责处理游戏中所有与AI相关的操作"""
    
    def __init__(self, game_mode, player_camp, game_settings=None):
        """初始化AI管理器
        
        Args:
            game_mode: 游戏模式
            player_camp: 玩家阵营
            game_settings: 游戏设置
        """
        self.game_mode = game_mode
        self.player_camp = player_camp
        
        # AI相关属性
        self.ai = None
        self.ai_thinking = False  # AI是否正在思考
        self.ai_think_start_time = 0  # AI开始思考的时间
        self.async_ai_move = None  # 异步AI计算结果
        
        # AI超时设置（毫秒）
        self.ai_timeout = 10000  # 10秒超时
        self.ai_thread = None  # AI计算线程
        
        # 初始化AI（如果需要）
        from program.config.config import MODE_PVC
        if game_mode == MODE_PVC:  # 人机模式
            ai_algorithm = game_settings.get('ai_algorithm', 'negamax') if game_settings else 'negamax'
            ai_color = "black" if player_camp == "red" else "red"  # AI的颜色与玩家相反
            self.ai = ChessAI(ai_algorithm, "hard", ai_color)
    
    def is_ai_turn(self, current_player_turn):
        """判断当前是否轮到AI行动
        
        Args:
            current_player_turn: 当前玩家回合
            
        Returns:
            bool: 是否轮到AI行动
        """
        from program.config.config import MODE_PVC
        return self.game_mode == MODE_PVC and current_player_turn != self.player_camp
    
    def start_ai_thinking(self):
        """启动AI思考"""
        self.ai_think_start_time = pygame.time.get_ticks()
        self.ai_thinking = True
    
    def start_async_ai_computation(self, game_state):
        """启动异步AI计算
        
        Args:
            game_state: 当前游戏状态
        """
        if self.ai:
            self.ai.get_move_async(game_state)
    
    def process_async_ai_result(self):
        """处理异步AI计算结果
        
        Returns:
            tuple: AI计算的移动，如果没有则返回None
        """
        if not self.ai:
            self.ai_thinking = False
            return None

        # 获取AI计算好的最佳走法
        move = self.ai.get_computed_move()
        self.ai_thinking = False
        return move
    
    def get_ai_move(self, game_state):
        """获取AI的移动（同步方法）
        
        Args:
            game_state: 当前游戏状态
            
        Returns:
            tuple: AI计算的移动，如果没有则返回None
        """
        if self.ai:
            return self.ai.get_best_move(game_state)
        return None
    
    def check_ai_timeout(self, current_time):
        """检查AI是否思考超时
        
        Args:
            current_time: 当前时间戳
            
        Returns:
            bool: 是否超时
        """
        return (self.ai_thinking and 
                current_time - self.ai_think_start_time > self.ai_timeout)
    
    def handle_ai_timeout(self, game_state):
        """处理AI思考超时情况
        
        Args:
            game_state: 当前游戏状态
            
        Returns:
            tuple: 超时情况下的AI移动，如果没有则返回None
        """
        print("AI思考超时，执行当前已知最佳走法")
        
        # 首先尝试获取AI已计算出的最佳走法
        best_move = self.ai.get_computed_move() if self.ai else None
        if best_move is None:
            # 如果没有计算出的走法，则使用AI内部保存的最佳走法
            best_move = getattr(self.ai, 'best_move_so_far', None) if self.ai else None

        if best_move is None:
            # 如果仍然没有最佳走法，则随机选择一个移动
            ai_color = "black" if self.player_camp == "red" else "red"
            valid_moves = []

            for piece in game_state.pieces:
                if piece.color == ai_color:
                    possible_moves, _ = game_state.calculate_possible_moves(piece.row, piece.col)
                    for to_row, to_col in possible_moves:
                        valid_moves.append(((piece.row, piece.col), (to_row, to_col)))

            if valid_moves:
                best_move = random.choice(valid_moves)

        return best_move
    
    def reset_ai_state(self):
        """重置AI状态"""
        self.ai_thinking = False
        self.ai_think_start_time = 0
        self.async_ai_move = None
        if self.ai_thread:
            self.ai_thread = None