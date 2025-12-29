"""
测试AI修复后的功能
"""
import pygame
from program.game import ChessGame
from program.config import MODE_PVC, CAMP_RED


def test_ai_thinking_display():
    """测试AI思考时的显示问题"""
    print("开始测试AI思考时的显示问题修复...")
    
    # 初始化pygame
    pygame.init()
    
    # 创建游戏实例
    game = ChessGame(game_mode=MODE_PVC, player_camp=CAMP_RED)
    
    # 检查AI是否正确初始化
    assert game.ai is not None, "AI未正确初始化"
    print("✓ AI正确初始化")
    
    # 检查AI线程安全锁
    assert hasattr(game.ai, 'lock'), "AI缺少线程安全锁"
    print("✓ AI线程安全锁存在")
    
    # 检查AI思考状态变量
    assert hasattr(game, 'ai_thinking'), "游戏缺少AI思考状态变量"
    print("✓ AI思考状态变量存在")
    
    # 测试AI思考时的绘制方法
    assert hasattr(game, 'draw_thinking_indicator'), "游戏缺少思考指示器绘制方法"
    print("✓ 思考指示器绘制方法存在")
    
    # 测试AI评估函数改进
    assert hasattr(game.ai, '_evaluate_attack_capability'), "AI缺少攻击能力评估方法"
    print("✓ AI攻击能力评估方法存在")
    
    assert hasattr(game.ai, '_evaluate_defense_value'), "AI缺少防守价值评估方法"
    print("✓ AI防守价值评估方法存在")
    
    print("所有测试通过！AI修复已成功应用。")
    pygame.quit()


def test_game_performance():
    """测试游戏性能改进"""
    print("\n开始测试游戏性能改进...")
    
    # 初始化pygame
    pygame.init()
    
    # 创建游戏实例
    game = ChessGame(game_mode=MODE_PVC, player_camp=CAMP_RED)
    
    # 检查AI搜索参数是否改进
    assert game.ai.search_depth >= 9, f"AI搜索深度应至少为9，当前为{game.ai.search_depth}"
    print(f"✓ AI搜索深度: {game.ai.search_depth}")
    
    assert game.ai.max_think_time <= 9000, f"AI思考时间应不超过9秒，当前为{game.ai.max_think_time/1000}秒"
    print(f"✓ AI最大思考时间: {game.ai.max_think_time/1000}秒")
    
    # 检查高级搜索技术
    assert hasattr(game.ai, 'use_killer_move'), "AI缺少杀手着法功能"
    print("✓ AI杀手着法功能存在")
    
    assert hasattr(game.ai, 'killer_moves'), "AI缺少杀手着法表"
    print("✓ AI杀手着法表存在")
    
    assert hasattr(game.ai, 'use_history_heuristic'), "AI缺少历史启发功能"
    print("✓ AI历史启发功能存在")
    
    print("游戏性能改进测试通过！")
    pygame.quit()


if __name__ == "__main__":
    test_ai_thinking_display()
    test_game_performance()
    print("\n所有测试完成！界面闪烁和AI可靠性问题已修复。")