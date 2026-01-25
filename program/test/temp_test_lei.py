from program.core.game_rules import GameRules
from program.core.chess_pieces import Lei, Pawn

# 测试：檑在(0,0)，夹逼棋子在(1,2)和(2,1)
pieces = []
lei = Lei('red', 0, 0)
pieces.append(lei)
pawn1 = Pawn('black', 1, 2)
pawn2 = Pawn('black', 2, 1)
pieces.append(pawn1)
pieces.append(pawn2)

# 测试檑从(0,0)到(2,2)，应该被夹逼规则阻止
result = GameRules.is_valid_lei_move(pieces, 0, 0, 2, 2)
print(f'檑从(0,0)到(2,2)的移动: {result} (期望: False，如果路径受夹逼影响)')

# 测试檑从(0,0)到(1,1)，应该允许
result = GameRules.is_valid_lei_move(pieces, 0, 0, 1, 1)
print(f'檑从(0,0)到(1,1)的移动: {result} (期望: True，如果路径无阻挡)')

# 测试檑从(0,0)到(3,3)，也应该被阻止
result = GameRules.is_valid_lei_move(pieces, 0, 0, 3, 3)
print(f'檑从(0,0)到(3,3)的移动: {result} (期望: False，如果路径受夹逼影响)')