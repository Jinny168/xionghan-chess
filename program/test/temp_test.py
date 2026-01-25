from program.core.game_rules import GameRules
from program.core.chess_pieces import She, Pawn

# 简单测试：射在(0,0)，夹逼棋子在(1,2)和(2,1)
pieces = []
she = She('red', 0, 0)
pieces.append(she)
pawn1 = Pawn('black', 1, 2)
pawn2 = Pawn('black', 2, 1)
pieces.append(pawn1)
pieces.append(pawn2)

# 测试射从(0,0)到(2,2)，应该被阻止
result = GameRules.is_valid_she_move(pieces, 0, 0, 2, 2)
print(f'射从(0,0)到(2,2)的移动: {result} (期望: False)')

# 测试射从(0,0)到(1,1)，应该允许
result = GameRules.is_valid_she_move(pieces, 0, 0, 1, 1)
print(f'射从(0,0)到(1,1)的移动: {result} (期望: True)')

# 测试射从(0,0)到(3,3)，也应该被阻止
result = GameRules.is_valid_she_move(pieces, 0, 0, 3, 3)
print(f'射从(0,0)到(3,3)的移动: {result} (期望: False)')