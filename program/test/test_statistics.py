"""测试匈汉象棋统计数据功能"""

from program.controllers.statistics_manager import statistics_manager

def test_statistics():
    print("测试匈汉象棋统计数据功能...")
    
    # 获取当前统计数据
    stats = statistics_manager.get_statistics()
    print(f"当前游戏次数: {stats['games_played']}")
    print(f"红方胜利: {stats['games_won']['red']}")
    print(f"黑方胜利: {stats['games_won']['black']}")
    print(f"平局: {stats['games_won']['draw']}")
    print(f"总游戏时长: {stats['total_time_played']}秒")
    
    # 测试更新游戏次数
    statistics_manager.update_games_played(1)
    print("已增加游戏次数")
    
    # 测试更新游戏结果
    statistics_manager.update_game_result("red", 120.5)  # 红方胜利，用时120.5秒
    print("已记录红方胜利")
    
    # 测试更新被吃棋子
    statistics_manager.update_pieces_captured("ju", 2)  # 車被吃2次
    print("已更新車被吃次数")
    
    # 测试更新总走子数
    statistics_manager.update_total_moves(10)
    print("已更新总走子数")
    
    # 再次获取统计数据验证
    stats = statistics_manager.get_statistics()
    print("\n更新后的统计数据:")
    print(f"当前游戏次数: {stats['games_played']}")
    print(f"红方胜利: {stats['games_won']['red']}")
    print(f"黑方胜利: {stats['games_won']['black']}")
    print(f"平局: {stats['games_won']['draw']}")
    print(f"總遊戲時長: {stats['total_time_played']}秒")
    print(f"車被吃次数: {stats['pieces_captured']['ju']}")
    print(f"总走子数: {stats['total_moves_made']}")
    
    print("\n统计数据功能测试完成!")

if __name__ == "__main__":
    test_statistics()