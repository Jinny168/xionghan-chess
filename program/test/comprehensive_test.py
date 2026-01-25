"""综合测试檑/礌削弱功能"""

from program.core.chess_pieces import *
from program.core.game_rules import GameRules

def comprehensive_test():
    """综合测试新规则"""
    print("=== 檑/礌削弱功能综合测试 ===")
    
    # 测试用例1：目标周围只有攻击者，可以攻击
    print("\n1. 目标周围只有攻击者（应该可以攻击）:")
    pieces1 = [Lei("red", 5, 5), Pawn("black", 4, 4)]
    result1 = GameRules.can_lei_attack(pieces1[0], pieces1[1], pieces1)
    print(f"   结果: {'✓ 可以攻击' if result1 else '✗ 不能攻击'}")
    
    # 测试用例2：目标周围有其他棋子，不能攻击
    print("\n2. 目标周围有其他棋子（不应该攻击）:")
    pieces2 = [Lei("red", 5, 5), Pawn("black", 4, 4), Pawn("red", 4, 5)]
    result2 = GameRules.can_lei_attack(pieces2[0], pieces2[1], pieces2)
    print(f"   结果: {'✓ 可以攻击' if result2 else '✗ 不能攻击'}")
    
    # 测试用例3：目标周围有其他檑，不能攻击
    print("\n3. 目标周围有其他檑（不应该攻击）:")
    pieces3 = [Lei("red", 5, 5), Pawn("black", 4, 4), Lei("black", 4, 5)]
    result3 = GameRules.can_lei_attack(pieces3[0], pieces3[1], pieces3)
    print(f"   结果: {'✓ 可以攻击' if result3 else '✗ 不能攻击'}")
    
    # 测试用例4：目标不在攻击范围内，不能攻击
    print("\n4. 目标不在攻击范围内（不应该攻击）:")
    pieces4 = [Lei("red", 5, 5), Pawn("black", 2, 2)]
    result4 = GameRules.can_lei_attack(pieces4[0], pieces4[1], pieces4)
    print(f"   结果: {'✓ 可以攻击' if result4 else '✗ 不能攻击'}")
    
    # 测试用例5：同色棋子，不能攻击
    print("\n5. 同色棋子（不应该攻击）:")
    pieces5 = [Lei("red", 5, 5), Pawn("red", 4, 4)]
    result5 = GameRules.can_lei_attack(pieces5[0], pieces5[1], pieces5)
    print(f"   结果: {'✓ 可以攻击' if result5 else '✗ 不能攻击'}")
    
    # 测试用例6：目标周围有多个其他棋子，不能攻击
    print("\n6. 目标周围有多个其他棋子（不应该攻击）:")
    pieces6 = [
        Lei("red", 5, 5), 
        Pawn("black", 4, 4), 
        Pawn("red", 3, 4), 
        Pawn("red", 5, 4)
    ]
    result6 = GameRules.can_lei_attack(pieces6[0], pieces6[1], pieces6)
    print(f"   结果: {'✓ 可以攻击' if result6 else '✗ 不能攻击'}")
    
    # 测试用例7：目标周围有我方檑，不能攻击
    print("\n7. 目标周围有我方檑（不应该攻击）:")
    pieces7 = [Lei("red", 5, 5), Pawn("black", 4, 4), Lei("red", 4, 5)]
    result7 = GameRules.can_lei_attack(pieces7[0], pieces7[1], pieces7)
    print(f"   结果: {'✓ 可以攻击' if result7 else '✗ 不能攻击'}")
    
    print("\n=== 测试总结 ===")
    all_results = [result1, not result2, not result3, not result4, not result5, not result6, not result7]
    passed = sum(all_results)
    total = len(all_results)
    print(f"通过测试: {passed}/{total}")
    
    if passed == total:
        print("✓ 所有测试通过！檑/礌削弱功能正常工作。")
    else:
        print("✗ 部分测试失败，请检查实现。")

if __name__ == "__main__":
    comprehensive_test()