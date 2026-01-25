from program.core.game_state import GameState
from program.core.game_rules import GameRules
from program.core.chess_pieces import King, Ju

print('测试匈汉象棋将军/绝杀逻辑修复')

# 创建一个简单的绝杀场景
game_state = GameState()
game_state.pieces.clear()

# 红将在九宫内，被黑车将军且无法逃脱
red_king = King('red', 9, 6)  # 红将在九宫中心
black_ju = Ju('black', 8, 6)  # 黑车在上方将军

# 用其他棋子封锁红将的逃跑路线
blocker1 = Ju('red', 9, 5)  # 红棋在左边（自己的棋子阻挡）
blocker2 = Ju('red', 9, 7)  # 红棋在右边（自己的棋子阻挡）
blocker3 = Ju('black', 10, 6)  # 黑棋在下面阻挡

game_state.pieces = [red_king, black_ju, blocker1, blocker2, blocker3]

print('棋子位置:')
for piece in game_state.pieces:
    print(f'  {piece.name} at ({piece.row}, {piece.col}), color: {piece.color}')

print(f'红方是否被将军: {GameRules.is_check(game_state.pieces, "red")}')
print(f'红方是否被将死: {GameRules.is_checkmate(game_state.pieces, "red")}')

# 测试游戏结束逻辑
game_over, winner = GameRules.is_game_over(game_state.pieces, 'black')
print(f'游戏是否结束: {game_over}, 获胜方: {winner}')

print("\n测试完成！")