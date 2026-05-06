"""
单元测试 - 常量配置测试
"""
import pytest
from desktop.config.constants import GameConstants


class TestGameConstants:
    """游戏常量测试类"""
    
    def test_board_size_constants(self):
        """测试棋盘尺寸常量"""
        assert GameConstants.BOARD_SIZE_XIONGHAN == 13
        assert GameConstants.BOARD_SIZE_TRADITIONAL == 9
        assert GameConstants.BOARD_ROWS_TRADITIONAL == 10
    
    def test_window_constants(self):
        """测试窗口常量"""
        assert GameConstants.DEFAULT_WINDOW_WIDTH == 1200
        assert GameConstants.DEFAULT_WINDOW_HEIGHT == 900
        assert GameConstants.MIN_WINDOW_WIDTH == 800
        assert GameConstants.MIN_WINDOW_HEIGHT == 600
    
    def test_fps_constants(self):
        """测试FPS常量"""
        assert GameConstants.NORMAL_FPS == 60
        assert GameConstants.AI_THINKING_FPS == 15
        assert GameConstants.DIALOG_FPS == 30
    
    def test_time_constants(self):
        """测试时间常量"""
        assert GameConstants.AI_THINK_TIMEOUT_MS == 10000
        assert GameConstants.AI_MOVE_DELAY_MS == 800
        assert GameConstants.CHECK_ANIMATION_DURATION_S == 4.0
    
    def test_game_mode_constants(self):
        """测试游戏模式常量"""
        assert GameConstants.MODE_PVP == "pvp"
        assert GameConstants.MODE_PVC == "pvc"
        assert GameConstants.MODE_NETWORK == "network"
        
        assert GameConstants.CAMP_RED == "red"
        assert GameConstants.CAMP_BLACK == "black"
    
    def test_ai_constants(self):
        """测试AI常量"""
        assert GameConstants.AI_DIFFICULTY_EASY == "easy"
        assert GameConstants.AI_DIFFICULTY_HARD == "hard"
        assert GameConstants.AI_ALGORITHM_NEGAMAX == "negamax"
        assert GameConstants.AI_ALGORITHM_MCTS == "mcts"
    
    def test_color_constants(self):
        """测试颜色常量"""
        assert GameConstants.BLACK == (0, 0, 0)
        assert GameConstants.WHITE == (255, 255, 255)
        assert GameConstants.RED == (180, 30, 30)
        assert GameConstants.GREEN == (0, 128, 0)
    
    def test_sound_constants(self):
        """测试音效常量"""
        assert GameConstants.SOUND_MOVE == "drop"
        assert GameConstants.SOUND_CAPTURE == "eat"
        assert GameConstants.SOUND_CHECK == "warn"
    
    def test_network_constants(self):
        """测试网络常量"""
        assert GameConstants.NETWORK_DEFAULT_PORT == 10087
        assert GameConstants.NETWORK_BUFFER_SIZE == 1024
        assert GameConstants.MSG_TYPE_MOVE == "move"
    
    def test_get_board_size_method(self):
        """测试获取棋盘尺寸方法"""
        # 默认返回匈汉象棋尺寸
        assert GameConstants.get_board_size() == 13
        
        # 传统模式返回传统象棋尺寸
        assert GameConstants.get_board_size(traditional_mode=True) == 9
        assert GameConstants.get_board_size(traditional_mode=False) == 13
    
    def test_get_fps_method(self):
        """测试获取FPS方法"""
        # 正常情况
        assert GameConstants.get_fps() == 60
        
        # AI思考时
        assert GameConstants.get_fps(ai_thinking=True) == 15
        
        # 对话框显示时
        assert GameConstants.get_fps(dialog_showing=True) == 30
        
        # 对话框优先级更高
        assert GameConstants.get_fps(ai_thinking=True, dialog_showing=True) == 30
    
    def test_pawn_constants(self):
        """测试兵卒常量"""
        assert GameConstants.PAWN_INITIAL_COUNT == 7
        assert GameConstants.PAWN_RESURRECTION_ROW_RED == 8
        assert GameConstants.PAWN_RESURRECTION_ROW_BLACK == 4
    
    def test_history_limits(self):
        """测试历史记录限制"""
        assert GameConstants.MAX_MOVE_HISTORY == 1000
        assert GameConstants.MAX_BOARD_POSITION_HISTORY == 100
    
    def test_font_sizes(self):
        """测试字体大小配置"""
        assert GameConstants.SMALL_FONT_SIZE < GameConstants.DEFAULT_FONT_SIZE
        assert GameConstants.DEFAULT_FONT_SIZE < GameConstants.TITLE_FONT_SIZE
        assert GameConstants.TITLE_FONT_SIZE < GameConstants.LARGE_FONT_SIZE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

