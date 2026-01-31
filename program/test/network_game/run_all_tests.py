"""
匈汉象棋网络对战测试套件
运行所有网络相关的测试
"""
import os
import sys
import time
import subprocess
import threading

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_test(test_name, test_file):
    """运行单个测试"""
    print(f"\n{'='*60}")
    print(f"运行测试: {test_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # 构建命令
        cmd = [sys.executable, test_file]
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(test_file),
            capture_output=True,
            text=True,
            timeout=120,  # 2分钟超时
            encoding='utf-8'  # 指定UTF-8编码
        )
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        print(f"测试耗时: {duration} 秒")
        
        if result.returncode == 0:
            print(f"✅ {test_name} - 通过")
            if result.stdout:
                print("标准输出:")
                print(result.stdout[-2000:])  # 只显示最后2000个字符
            return True
        else:
            print(f"❌ {test_name} - 失败")
            print("错误输出:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {test_name} - 超时")
        return False
    except Exception as e:
        print(f"❌ {test_name} - 执行出错: {e}")
        return False


def run_manual_tests():
    """运行手动测试（非自动化）"""
    print(f"\n{'='*60}")
    print("手动测试选项:")
    print("="*60)
    print("1. 交互式网络对战测试: python test_local_network.py")
    print("2. 状态同步调试: python sync_debugger.py")
    print("3. 查看所有测试文件:")


def list_test_files():
    """列出所有测试文件"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_files = [f for f in os.listdir(test_dir) if f.endswith('.py') and 'test' in f.lower()]
    
    print(f"\n测试目录中的文件:")
    for f in sorted(test_files):
        print(f"  - {f}")


def main():
    """主函数"""
    print("匈汉象棋网络对战测试套件")
    print("=" * 60)
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试文件列表
    test_files = [
        ("状态同步专项测试", "state_sync_test.py"),
        ("网络集成测试", "network_integration_test.py"),
        ("综合测试", "comprehensive_test.py"),
        ("同步调试工具", "sync_debugger.py")
    ]
    
    # 构建完整路径
    test_paths = []
    for test_name, test_file in test_files:
        full_path = os.path.join(script_dir, test_file)
        if os.path.exists(full_path):
            test_paths.append((test_name, full_path))
        else:
            print(f"⚠️  警告: 测试文件不存在: {full_path}")
    
    results = {}
    
    # 逐个运行测试
    for test_name, test_path in test_paths:
        success = run_test(test_name, test_path)
        results[test_name] = success
    
    # 运行手动测试说明
    run_manual_tests()
    list_test_files()
    
    # 输出汇总结果
    print(f"\n{'='*60}")
    print("测试汇总结果:")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    failed_tests = total_tests - passed_tests
    
    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print("-" * 60)
    print(f"总计: {total_tests} 个自动测试")
    print(f"通过: {passed_tests} 个")
    print(f"失败: {failed_tests} 个")
    
    if failed_tests == 0:
        print("\n🎉 自动测试全部通过!")
    else:
        print(f"\n⚠️  {failed_tests} 个自动测试失败，请检查错误信息")
    
    print(f"\n结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 提示: 运行单个测试文件以获得更详细的输出")
    print("   例如: python state_sync_test.py")


if __name__ == "__main__":
    main()