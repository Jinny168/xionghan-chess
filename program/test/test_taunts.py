"""嘲讽功能测试脚本"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from program.config.taunts_manager import taunt_manager


def test_taunt_manager():
    """测试嘲讽管理器功能"""
    print("=== 嘲讽管理器测试 ===")
    
    # 测试1: 验证加载的嘲讽语句数量
    print(f"加载的嘲讽语句数量: {len(taunt_manager.taunts)}")
    
    # 测试2: 获取多个随机嘲讽语句
    print("\n随机获取的5个嘲讽语句:")
    for i in range(5):
        taunt = taunt_manager.get_random_taunt()
        print(f"{i+1}. {taunt}")
    
    # 测试3: 验证是否会返回空结果
    print(f"\n单次随机获取: {taunt_manager.get_random_taunt()}")
    
    # 测试4: 添加新嘲讽语句（临时测试）
    original_count = len(taunt_manager.taunts)
    taunt_manager.add_taunt("这是一个测试嘲讽语句")
    print(f"\n添加新嘲讽后数量: {len(taunt_manager.taunts)} (应该比原来多1)")
    
    # 验证新添加的语句是否存在
    if "这是一个测试嘲讽语句" in taunt_manager.taunts:
        print("✓ 新嘲讽语句添加成功")
    else:
        print("✗ 新嘲讽语句添加失败")
    
    # 恢复原始状态（移除测试语句）
    taunt_manager.taunts.remove("这是一个测试嘲讽语句")
    
    print(f"\n恢复后数量: {len(taunt_manager.taunts)} (应该回到原来的数量)")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_taunt_manager()