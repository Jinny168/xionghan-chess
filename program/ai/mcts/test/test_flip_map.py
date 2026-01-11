#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试flip_map函数的正确性
"""

from mcts_game import move_action2move_id, move_id2move_action, flip_map


def test_flip_map():
    """测试flip_map函数"""
    print("测试flip_map函数...")
    
    # 测试一些典型的移动
    test_moves = [
        "00000001",  # 从(0,0)到(0,1) - 向右移动
        "00000100",  # 从(0,0)到(1,0) - 向下移动
        "00050006",  # 从(0,5)到(0,6) - 向右移动
        "00120011",  # 从(0,12)到(0,11) - 向左移动
        "05050507",  # 从(5,5)到(5,7) - 向右移动
        "12000000",  # 从(12,0)到(0,0) - 斜向移动
    ]
    
    print("\n测试预定义的移动:")
    for move in test_moves:
        flipped = flip_map(move)
        print(f"原始移动: {move} -> 翻转后: {flipped}")
        
        # 检查翻转后的移动是否在合法动作字典中
        if flipped in move_action2move_id:
            print(f"  ✓ 翻转后的移动是合法的，对应ID: {move_action2move_id[flipped]}")
        else:
            print(f"  ✗ 翻转后的移动无效")
    
    print(f"\n总共有 {len(move_id2move_action)} 个动作ID映射")
    print(f"总共有 {len(move_action2move_id)} 个动作映射")
    
    # 测试一些边界情况
    print("\n测试边界情况:")
    edge_cases = [
        "00000012",  # 从(0,0)到(0,12)
        "00120000",  # 从(0,12)到(0,0)
        "12121200",  # 从(12,12)到(12,0)
    ]
    
    for move in edge_cases:
        flipped = flip_map(move)
        print(f"原始移动: {move} -> 翻转后: {flipped}")
        
        if flipped in move_action2move_id:
            print(f"  ✓ 翻转后的移动是合法的，对应ID: {move_action2move_id[flipped]}")
        else:
            print(f"  ✗ 翻转后的移动无效")


def test_move_construction():
    """测试移动构造函数"""
    print("\n\n测试移动构造函数...")
    
    # 检查move_id2move_action和move_action2move_id是否对称
    mismatch_count = 0
    for move_id, move_action in move_id2move_action.items():
        if move_action in move_action2move_id:
            if move_action2move_id[move_action] != move_id:
                print(f"ID不匹配: {move_id} -> {move_action} -> {move_action2move_id[move_action]}")
                mismatch_count += 1
        else:
            print(f"动作不在字典中: {move_action}")
            mismatch_count += 1
    
    print(f"检查完成，发现 {mismatch_count} 个不匹配项")
    
    # 验证flip_map的逻辑
    print("\n验证flip_map逻辑:")
    print("对于移动 'from_y,from_x,to_y,to_x'，flip_map应该翻转x坐标:")
    print("即: from_x变成 12-from_x, to_x变成 12-to_x")
    
    test_cases = [
        ("00000101", "00120111"),  # (0,0)->(1,1) 变成 (0,12)->(1,11)
        ("05060508", "05060504"),  # (5,6)->(5,8) 变成 (5,6)->(5,4) - 不对！应该是(5,6)->(5,4)变成(5,6)->(5,4)
        ("05060508", "05060504"),  # (5,6)->(5,8) 变成 (5,6)->(5,4)
    ]
    
    for original, expected in test_cases:
        result = flip_map(original)
        print(f"{original} -> {result} (期望: {expected}) {'✓' if result == expected else '✗'}")


if __name__ == "__main__":
    test_flip_map()
    test_move_construction()