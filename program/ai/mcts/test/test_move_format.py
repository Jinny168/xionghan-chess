#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试移动字符串格式和相关函数
"""

from program.ai.mcts.mcts_game import move_action2move_id, move_id2move_action, flip_map, get_all_legal_moves


def test_move_format():
    """测试移动格式"""
    print("测试移动字符串格式...")
    
    print(f"总共有 {len(move_id2move_action)} 个动作ID映射")
    print(f"总共有 {len(move_action2move_id)} 个动作映射")
    
    # 验证格式
    sample_moves = list(move_id2move_action.values())[:10]  # 取前10个示例
    print("\n前10个动作示例:")
    for i, move in enumerate(sample_moves):
        print(f"ID {i}: '{move}' (长度: {len(move)})")
        if len(move) != 8:
            print(f"  错误: 移动格式不正确，应该是8位数字")
    
    # 测试一些特定的移动
    print("\n测试特定移动格式:")
    test_cases = [
        "00000001",  # (0,0) -> (0,1)
        "00000100",  # (0,0) -> (1,0)
        "05050507",  # (5,5) -> (5,7)
        "12121111",  # (12,12) -> (11,11)
    ]
    
    for move in test_cases:
        if move in move_action2move_id:
            print(f"✓ 移动 '{move}' 是合法的，ID为 {move_action2move_id[move]}")
        else:
            print(f"✗ 移动 '{move}' 不在合法移动字典中")
    
    # 测试翻转功能
    print("\n测试翻转功能:")
    for move in test_cases[:5]:
        if move in move_action2move_id:
            flipped = flip_map(move)
            print(f"'{move}' -> '{flipped}' (翻转后是否合法: {flipped in move_action2move_id})")
    
    # 检查是否所有翻转后的移动都是合法的
    print("\n随机检查一些翻转移动:")
    count_valid = 0
    count_total = 0
    for move_id, move_action in list(move_id2move_action.items())[:100]:  # 检查前100个
        flipped = flip_map(move_action)
        if flipped in move_action2move_id:
            count_valid += 1
        count_total += 1
    
    print(f"前100个移动中，翻转后仍然合法的比例: {count_valid}/{count_total} = {count_valid/count_total:.2%}")


def test_move_generation_consistency():
    """测试移动生成的一致性"""
    print("\n\n测试移动生成一致性...")
    
    # 重新生成移动空间
    new_move_id2move_action, new_move_action2move_id = get_all_legal_moves()
    
    print(f"重新生成的移动空间: {len(new_move_id2move_action)} 个移动")
    
    # 检查是否与全局变量一致
    if len(new_move_id2move_action) == len(move_id2move_action):
        print("✓ 移动空间大小一致")
    else:
        print("✗ 移动空间大小不一致")
    
    # 检查一些具体的移动
    sample_moves = list(move_id2move_action.values())[:5]
    for move in sample_moves:
        if move in new_move_action2move_id:
            original_id = move_action2move_id[move]
            new_id = new_move_action2move_id[move]
            if original_id == new_id:
                print(f"✓ 移动 '{move}' ID一致: {original_id}")
            else:
                print(f"✗ 移动 '{move}' ID不一致: 原始={original_id}, 重新生成={new_id}")
        else:
            print(f"✗ 移动 '{move}' 在重新生成中丢失")


def analyze_move_patterns():
    """分析移动模式"""
    print("\n\n分析移动模式...")
    
    # 统计不同类型的移动
    straight_moves = 0  # 直线移动（横或竖）
    diagonal_moves = 0  # 斜线移动
    knight_moves = 0    # 马步移动
    
    for move_action in list(move_id2move_action.values())[:1000]:  # 只检查前1000个以节省时间
        from_y = int(move_action[0:2])
        from_x = int(move_action[2:4])
        to_y = int(move_action[4:6])
        to_x = int(move_action[6:8])
        
        dy = abs(to_y - from_y)
        dx = abs(to_x - from_x)
        
        if dx == 0 or dy == 0:  # 横向或纵向移动
            straight_moves += 1
        elif dx == dy:  # 斜向移动
            diagonal_moves += 1
        elif (dx == 1 and dy == 2) or (dx == 2 and dy == 1):  # 马步
            knight_moves += 1
    
    print(f"前1000个移动中:")
    print(f"  直线移动: {straight_moves}")
    print(f"  斜线移动: {diagonal_moves}")
    print(f"  马步移动: {knight_moves}")
    print(f"  总计: {straight_moves + diagonal_moves + knight_moves}")


if __name__ == "__main__":
    test_move_format()
    test_move_generation_consistency()
    analyze_move_patterns()