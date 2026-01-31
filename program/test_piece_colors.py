#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试匈汉象棋新增棋子配色功能
"""

from controllers.game_config_manager import get_piece_color, get_piece_text_color, theme_manager

def test_piece_colors():
    """测试新增棋子配色功能"""
    print("=== 匈汉象棋棋子配色测试 ===\n")
    
    # 测试棋子类型
    piece_types = ["漢", "仕", "相", "傌", "俥", "炮", "兵", "巡", "射", "檑", "甲", "楯", "刺", "尉"]
    
    print("1. 测试白天主题棋子配色:")
    print("-" * 60)
    for piece_type in piece_types:
        light_color = get_piece_color(piece_type, "day", "light_side")
        dark_color = get_piece_color(piece_type, "day", "dark_side")
        light_text_color = get_piece_text_color("day", "light_side")
        dark_text_color = get_piece_text_color("day", "dark_side")
        
        print(f"{piece_type:2s} | 浅色方: {light_color} | 深色方: {dark_color}")
    
    print("\n白天主题文字配色:")
    print(f"浅色方文字: {light_text_color}")
    print(f"深色方文字: {dark_text_color}")
    
    print("\n2. 测试夜晚主题棋子配色:")
    print("-" * 60)
    for piece_type in piece_types:
        light_color = get_piece_color(piece_type, "night", "light_side")
        dark_color = get_piece_color(piece_type, "night", "dark_side")
        light_text_color = get_piece_text_color("night", "light_side")
        dark_text_color = get_piece_text_color("night", "dark_side")
        
        print(f"{piece_type:2s} | 浅色方: {light_color} | 深色方: {dark_color}")
    
    print("\n夜晚主题文字配色:")
    print(f"浅色方文字: {light_text_color}")
    print(f"深色方文字: {dark_text_color}")
    
    print("\n3. 测试主题切换功能:")
    print("-" * 60)
    current_theme = theme_manager.get_current_theme()
    print(f"当前主题: {current_theme}")
    
    # 切换主题
    new_theme = theme_manager.toggle_theme()
    print(f"切换后主题: {new_theme}")
    
    # 恢复原主题
    theme_manager.toggle_theme()
    restored_theme = theme_manager.get_current_theme()
    print(f"恢复后主题: {restored_theme}")
    
    print("\n4. 测试异常情况处理:")
    print("-" * 60)
    # 测试未知棋子类型
    unknown_color = get_piece_color("未知", "day", "light_side")
    print(f"未知棋子配色: {unknown_color}")
    
    # 测试非法主题参数
    invalid_theme_color = get_piece_color("漢", "invalid", "light_side")
    print(f"非法主题配色: {invalid_theme_color}")
    
    # 测试非法阵营参数
    invalid_side_color = get_piece_color("漢", "day", "invalid")
    print(f"非法阵营配色: {invalid_side_color}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_piece_colors()