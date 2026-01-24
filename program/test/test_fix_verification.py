"""
匈汉象棋将军/绝杀逻辑修复验证脚本
"""

from program.core.game_state import GameState
from program.core.game_rules import GameRules
from program.core.chess_pieces import *

def test_check_scenario():
    """测试将军场景"""
    print("=== 测试将军场景 ===")
    game_state = GameState()
    game_state.pieces.clear()

    # 设置一个简单的将军场景：红帅被黑车将军
    red_king = King('red', 9, 6)  # 红将在九宫中心
    black_ju = Ju('black', 7, 6)  # 黑车在下方将军（直线攻击）

    game_state.pieces = [red_king, black_ju]
    game_state.player_turn = 'black'  # 黑方回合

    # 检查将军状态
    is_red_in_check = GameRules.is_check(game_state.pieces, 'red')
    print(f'红方被将军: {is_red_in_check}')

    # 测试get_checked_king_position方法
    game_state.is_check = is_red_in_check
    king_pos = game_state.get_checked_king_position()
    print(f'被将军的王的位置: {king_pos}')
    print(f'预期位置: (9, 6)')

    # 验证位置是否正确
    if is_red_in_check and king_pos == (9, 6):
        print("✓ 将军位置正确")
    else:
        print("✗ 将军位置错误")

def test_checkmate_scenario():
    """测试绝杀场景"""
    print("\n=== 测试绝杀场景 ===")
    game_state = GameState()
    game_state.pieces.clear()

    # 红将在九宫被黑车绝杀的场景
    red_king = King('red', 9, 6)
    black_ju = Ju('black', 8, 6)
    # 用其他棋子封锁逃跑路线
    blocker1 = Shi('red', 8, 5)  # 左边被己方士挡住
    blocker2 = Shi('red', 8, 7)  # 右边被己方士挡住
    blocker3 = Ju('black', 10, 6)  # 下面被黑车挡住
    blocker4 = Ju('black', 9, 5)  # 左边被黑车挡住
    blocker5 = Ju('black', 9, 7)  # 右边被黑车挡住

    game_state.pieces = [red_king, black_ju, blocker1, blocker2, blocker3, blocker4, blocker5]
    game_state.player_turn = 'black'

    is_red_in_check = GameRules.is_check(game_state.pieces, 'red')
    is_red_in_checkmate = GameRules.is_checkmate(game_state.pieces, 'red')
    print(f'红方被将军: {is_red_in_check}')
    print(f'红方被将死: {is_red_in_checkmate}')

    # 检查游戏结束逻辑
    game_over, winner = GameRules.is_game_over(game_state.pieces, 'black')
    print(f'游戏结束: {game_over}, 获胜方: {winner}')

    # 设置游戏状态
    game_state.is_check = is_red_in_check
    game_state.game_over = game_over
    game_state.winner = winner

    # 测试在绝杀情况下不应该显示将军动画
    king_pos = game_state.get_checked_king_position()
    print(f'被将军的王的位置 (绝杀场景): {king_pos}')
    print(f'游戏结束状态: {game_state.game_over}')
    
    # 在绝杀情况下，game_over应为True，因此get_checked_king_position应返回None
    if game_over and king_pos is None:
        print("✓ 绝杀时不会显示将军动画（正确）")
    elif game_over and king_pos is not None:
        print("✗ 绝杀时仍显示将军动画（错误）")
    else:
        print("? 非绝杀情况")

def test_normal_check():
    """测试普通将军情况（非绝杀）"""
    print("\n=== 测试普通将军情况（非绝杀） ===")
    game_state = GameState()
    game_state.pieces.clear()

    # 设置一个普通的将军场景，但不是绝杀
    red_king = King('red', 9, 6)  # 红将在九宫中心
    black_ju = Ju('black', 8, 6)  # 黑车在下方将军
    # 给红将留出一个逃跑路径

    game_state.pieces = [red_king, black_ju]
    game_state.player_turn = 'black'

    is_red_in_check = GameRules.is_check(game_state.pieces, 'red')
    is_red_in_checkmate = GameRules.is_checkmate(game_state.pieces, 'red')
    print(f'红方被将军: {is_red_in_check}')
    print(f'红方被将死: {is_red_in_checkmate}')

    game_state.is_check = is_red_in_check
    game_state.game_over = False  # 确保游戏未结束

    king_pos = game_state.get_checked_king_position()
    print(f'被将军的王的位置 (普通将军): {king_pos}')

    if is_red_in_check and not is_red_in_checkmate and king_pos is not None:
        print("✓ 普通将军时正确显示将军动画")
    else:
        print("✗ 普通将军时显示错误")

def run_all_tests():
    """运行所有测试"""
    print("匈汉象棋将军/绝杀逻辑修复验证")
    print("=" * 50)
    
    test_check_scenario()
    test_checkmate_scenario()
    test_normal_check()
    
    print("\n" + "=" * 50)
    print("测试完成!")

if __name__ == "__main__":
    run_all_tests()
