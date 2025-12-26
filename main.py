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
from utils import load_font

from menu_screens import ModeSelectionScreen, RulesScreen, CampSelectionScreen
from settings import SettingsScreen
from game import ChessGame

# 初始化PyGame
pygame.init()
pygame.mixer.init()  # 初始化音频模块

# 游戏模式
MODE_PVP = "pvp"  # 人人对战
MODE_PVC = "pvc"  # 人机对战

# 玩家阵营
CAMP_RED = "red"  # 玩家执红
CAMP_BLACK = "black"  # 玩家执黑


def main():
    """主函数，处理游戏流程"""
    # 首先显示模式选择界面
    mode_screen = ModeSelectionScreen()
    game_mode = mode_screen.run()
    
    # 运行游戏循环
    while True:
        settings_result = None  # 初始化settings_result变量
        
        if game_mode == "settings":  # 如果选择了设置界面
            settings_screen = SettingsScreen()
            settings_result = settings_screen.run()
            
            if settings_result == "back":
                # 返回到模式选择界面
                mode_screen = ModeSelectionScreen()
                game_mode = mode_screen.run()
                continue
            else:
                # 保存设置并返回到模式选择界面
                # 这里可以保存设置到全局变量或文件
                mode_screen = ModeSelectionScreen()
                game_mode = mode_screen.run()
                continue
        
        if game_mode == "rules":  # 如果选择了规则界面
            rules_screen = RulesScreen()
            rules_screen.run()
            # 返回到模式选择界面
            mode_screen = ModeSelectionScreen()
            game_mode = mode_screen.run()
            continue
        
        player_camp = CAMP_RED  # 默认玩家执红
        
        # 如果是人机对战模式，显示阵营选择界面
        if game_mode == MODE_PVC:
            camp_screen = CampSelectionScreen()
            player_camp = camp_screen.run()
        
        # 根据选择的模式和阵营创建游戏，传递设置
        game = ChessGame(game_mode, player_camp, game_settings=settings_result if isinstance(settings_result, dict) else None)
        result = game.run()
        
        # 如果返回到菜单，重新显示模式选择界面
        if result == "back_to_menu":
            mode_screen = ModeSelectionScreen()
            game_mode = mode_screen.run()

if __name__ == "__main__":
    main()