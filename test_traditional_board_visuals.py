#!/usr/bin/env python
"""
传统象棋棋盘可视化测试脚本
用于展示美化的棋盘和棋子效果
"""

import pygame
import sys
from program.core.traditional_chess_mode import TraditionalChessMode
from program.ui.traditional_chess_board import TraditionalChessBoard
from program.controllers.game_config_manager import LEFT_PANEL_WIDTH_RATIO
from program.controllers.game_config_manager import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
from program.utils.utils import draw_background


def test_traditional_board_visuals():
    """测试传统象棋棋盘的视觉效果"""
    print("开始测试传统象棋棋盘视觉效果...")
    
    # 初始化pygame
    pygame.init()
    
    # 创建窗口
    screen = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("传统象棋棋盘视觉效果测试")
    clock = pygame.time.Clock()
    
    # 创建传统象棋模式和棋盘
    mode = TraditionalChessMode()
    pieces = mode.create_traditional_pieces()
    
    # 使用比例计算左侧面板宽度
    left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * DEFAULT_WINDOW_WIDTH)
    board = TraditionalChessBoard(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, 
                                left_panel_width + 20, 50)
    
    # 添加一些测试高亮效果
    test_highlight = True
    test_moves = [(3, 3), (3, 4), (3, 5)]  # 测试可能移动位置
    test_captures = [(4, 3), (4, 5)]       # 测试可吃子位置
    test_selected = (2, 4)                  # 测试选中位置
    
    board.highlight_position(test_selected[0], test_selected[1])
    board.set_possible_moves(test_moves)
    board.set_capturable_positions(test_captures)
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.VIDEORESIZE:
                # 处理窗口大小调整
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                # 更新棋盘尺寸
                new_width, new_height = event.w, event.h
                left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * new_width)
                board = TraditionalChessBoard(new_width, new_height, left_panel_width + 20, 50)
                # 重新设置测试高亮
                board.highlight_position(test_selected[0], test_selected[1])
                board.set_possible_moves(test_moves)
                board.set_capturable_positions(test_captures)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                # 将屏幕坐标转换为棋盘坐标
                grid_pos = board.get_grid_position(mouse_pos)
                if grid_pos:
                    row, col = grid_pos
                    print(f"点击位置: ({row}, {col})")
                    
                    # 切换选中位置
                    if board.highlighted and board.highlighted == (row, col):
                        board.clear_highlights()
                    else:
                        board.highlight_position(row, col)
                        # 为选中位置添加一些可能的移动
                        test_moves = [(row+i, col+j) for i in [-1, 0, 1] for j in [-1, 0, 1] 
                                      if 0 <= row+i <= 9 and 0 <= col+j <= 8 and (i != 0 or j != 0)]
                        board.set_possible_moves(test_moves[:4])  # 限制显示4个可能移动
        
        # 绘制背景
        draw_background(screen)
        
        # 绘制棋盘和棋子
        board.draw(screen, pieces)
        
        # 显示操作提示
        font = pygame.font.Font(None, 24)
        hint_text = font.render("点击棋子查看选中效果，点击空白处高亮位置", True, (0, 0, 0))
        screen.blit(hint_text, (20, 20))
        
        hint_text2 = font.render("调整窗口大小以测试响应式设计", True, (0, 0, 0))
        screen.blit(hint_text2, (20, 50))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    print("传统象棋棋盘视觉效果测试完成！")


if __name__ == "__main__":
    test_traditional_board_visuals()