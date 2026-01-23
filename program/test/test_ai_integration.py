#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试AI算法集成功能
"""
from program.config.config import game_config
print('当前AI算法设置:', game_config.get_setting('ai_algorithm', 'negamax'))

# 测试设置AI算法为mcts
game_config.set_setting('ai_algorithm', 'mcts')
print('更新后的AI算法设置:', game_config.get_setting('ai_algorithm', 'negamax'))

# 测试创建各种算法的ChessAI
from program.ai.chess_ai import ChessAI

print("\n测试各种AI算法:")

# 测试MCTS
try:
    ai_mcts = ChessAI('mcts', 'hard', 'red')
    print('✓ MCTS ChessAI 创建成功')
except Exception as e:
    print(f'✗ MCTS ChessAI 创建失败: {e}')

# 测试Negamax
try:
    ai_negamax = ChessAI('negamax', 'hard', 'red')
    print('✓ Negamax ChessAI 创建成功')
except Exception as e:
    print(f'✗ Negamax ChessAI 创建失败: {e}')

# 测试Minimax
try:
    ai_minimax = ChessAI('minimax', 'hard', 'red')
    print('✓ Minimax ChessAI 创建成功')
except Exception as e:
    print(f'✗ Minimax ChessAI 创建失败: {e}')

# 测试Alpha-Beta
try:
    ai_alpha_beta = ChessAI('alpha-beta', 'hard', 'red')
    print('✓ Alpha-Beta ChessAI 创建成功')
except Exception as e:
    print(f'✗ Alpha-Beta ChessAI 创建失败: {e}')

# 测试AI Manager是否能正确使用AI算法设置
from program.config.config import MODE_PVC, CAMP_RED
from program.controllers.ai_manager import AIManager

print("\n测试AI Manager:")
game_settings = {'ai_algorithm': 'mcts'}
try:
    ai_manager = AIManager(MODE_PVC, CAMP_RED, game_settings)
    print(f'✓ AI Manager 使用 MCTS 算法创建成功')
    print(f'  AI算法类型: {ai_manager.ai.algorithm}')
except Exception as e:
    print(f'✗ AI Manager 创建失败: {e}')

# 测试设置回Negamax
game_config.set_setting('ai_algorithm', 'negamax')
game_settings = {'ai_algorithm': 'negamax'}
try:
    ai_manager2 = AIManager(MODE_PVC, CAMP_RED, game_settings)
    print(f'✓ AI Manager 使用 Negamax 算法创建成功')
    print(f'  AI算法类型: {ai_manager2.ai.algorithm}')
except Exception as e:
    print(f'✗ AI Manager 创建失败: {e}')

print("\n所有测试完成！")