#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试真实对局场景下的棋局导入导出功能
"""

import os
import tempfile
import json
from program.core.game_state import GameState
from program.controllers.game_io_controller import GameIOController


def simulate_gameplay(game_state):
    """模拟一些游戏步骤"""
    from program.core.game_rules import GameRules
    
    # 尝试执行一些有效的移动
    moves_attempted = 0
    successful_moves = 0
    
    # 遍历棋子寻找可移动的棋子
    for piece in game_state.pieces[:]:  # 使用副本避免迭代中修改
        if piece.color != game_state.player_turn:
            continue
            
        # 尝试找到一个有效的移动
        for dr in [-2, -1, 0, 1, 2]:
            for dc in [-2, -1, 0, 1, 2]:
                if dr == 0 and dc == 0:
                    continue
                    
                to_row, to_col = piece.row + dr, piece.col + dc
                
                # 检查边界
                if not (0 <= to_row < 13 and 0 <= to_col < 13):
                    continue
                
                # 检查移动是否合法
                if GameRules.is_valid_move(game_state.pieces, piece, piece.row, piece.col, to_row, to_col):
                    # 检查移动后是否会导致自己被将军（送将）
                    if not GameRules.would_be_in_check_after_move(game_state.pieces, piece, to_row, to_col):
                        # 执行移动
                        if game_state.move_piece(piece.row, piece.col, to_row, to_col):
                            successful_moves += 1
                            moves_attempted += 1
                            
                            # 如果已经成功移动了几个棋子，就停止
                            if successful_moves >= 3:
                                return successful_moves
                        break
            if successful_moves >= 3:
                break
        if successful_moves >= 3:
            break
    
    return successful_moves


def test_real_gameplay_export_import():
    """测试真实对局场景下的导出导入功能"""
    print("开始测试真实对局场景下的棋局导入导出功能...")
    
    # 创建游戏状态
    game_state = GameState()
    
    # 记录初始状态
    print(f"初始玩家: {game_state.player_turn}")
    print(f"初始棋子数量: {len(game_state.pieces)}")
    print(f"初始历史记录长度: {len(game_state.move_history)}")
    
    # 模拟一些游戏步骤
    moves_made = simulate_gameplay(game_state)
    print(f"模拟了 {moves_made} 步有效移动")
    print(f"移动后历史记录长度: {len(game_state.move_history)}")
    print(f"移动后当前玩家: {game_state.player_turn}")
    
    # 创建控制器
    controller = GameIOController()
    
    # 创建临时文件进行测试
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False, encoding='utf-8') as tmp_file:
        temp_filename = tmp_file.name
    
    try:
        # 测试导出
        print("\n--- 测试导出 ---")
        export_success = controller.export_game(game_state, temp_filename)
        print(f"导出结果: {export_success}")
        
        if export_success:
            # 检查文件是否创建成功
            if os.path.exists(temp_filename):
                print(f"文件已创建: {temp_filename}")
                
                # 读取文件内容
                with open(temp_filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"文件大小: {len(content)} 字节")
                    
                    # 尝试解析JSON
                    try:
                        game_data = json.loads(content)
                        print("文件内容格式: JSON")
                        print(f"包含字段: {list(game_data.keys())}")
                        
                        # 验证关键字段
                        required_fields = ['position', 'move_history', 'player_turn', 'captured_pieces']
                        for field in required_fields:
                            if field in game_data:
                                print(f"  ✓ {field}: 存在")
                                if field == 'move_history':
                                    print(f"    历史记录长度: {len(game_data[field])}")
                                    if len(game_data[field]) > 0:
                                        print(f"    示例历史记录: {game_data[field][0][:2]}...")  # 显示前两个元素
                                elif field == 'captured_pieces':
                                    total_captured = sum(len(pieces) for pieces in game_data[field].values())
                                    print(f"    阵亡棋子总数: {total_captured}")
                            else:
                                print(f"  ✗ {field}: 缺失")
                                
                    except json.JSONDecodeError:
                        print("文件内容格式: 非JSON")
                        print(f"内容预览: {content[:200]}...")
            else:
                print("文件未创建!")
        
        # 测试导入
        print("\n--- 测试导入 ---")
        # 创建一个新的game_state用于测试导入
        imported_game_state = GameState()
        print(f"导入前历史记录长度: {len(imported_game_state.move_history)}")
        print(f"导入前当前玩家: {imported_game_state.player_turn}")
        
        import_success = controller.import_game(imported_game_state, temp_filename)
        print(f"导入结果: {import_success}")
        
        if import_success:
            print(f"导入后历史记录长度: {len(imported_game_state.move_history)}")
            print(f"导入后玩家: {imported_game_state.player_turn}")
            print(f"导入后棋子数量: {len(imported_game_state.pieces)}")
            
            # 验证导入的数据是否正确
            if len(imported_game_state.move_history) == len(game_state.move_history):
                print("  ✓ 历史记录长度匹配")
            else:
                print(f"  ✗ 历史记录长度不匹配: 期望 {len(game_state.move_history)}, 实际 {len(imported_game_state.move_history)}")
                
            if imported_game_state.player_turn == game_state.player_turn:
                print("  ✓ 当前玩家匹配")
            else:
                print(f"  ✗ 当前玩家不匹配: 期望 {game_state.player_turn}, 实际 {imported_game_state.player_turn}")
                
            # 验证阵亡棋子
            original_captured = sum(len(pieces) for pieces in game_state.captured_pieces.values())
            imported_captured = sum(len(pieces) for pieces in imported_game_state.captured_pieces.values())
            if imported_captured == original_captured:
                print(f"  ✓ 阵亡棋子数量匹配: {imported_captured}")
            else:
                print(f"  ✗ 阵亡棋子数量不匹配: 期望 {original_captured}, 实际 {imported_captured}")
                
    finally:
        # 清理临时文件
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            print(f"\n已清理临时文件: {temp_filename}")


if __name__ == "__main__":
    test_real_gameplay_export_import()