"""测试规则查看器功能"""

import pygame
from program.ui.rules_viewer import RulesViewer

def test_rules_viewer():
    """测试规则查看器是否能正确读取help.md文件"""
    try:
        # 初始化pygame
        pygame.init()
        pygame.display.set_mode((800, 600))  # 创建一个虚拟显示
        
        # 创建规则查看器实例（不运行界面）
        viewer = RulesViewer()
        
        print(f"成功读取到 {len(viewer.pages)} 个页面")
        
        # 显示每个页面的简要信息
        for i, page in enumerate(viewer.pages):
            print(f"\n页面 {i+1}: 包含 {len(page)} 个内容项")
        
        print("\n规则查看器初始化成功！")
        print("页面总数:", len(viewer.pages))
        
        # 检查是否至少有一些内容
        total_items = sum(len(page) for page in viewer.pages)
        print(f"总内容项数: {total_items}")
        
        if len(viewer.pages) > 0 and total_items > 0:
            print("✅ help.md 文件已成功读取和解析")
        else:
            print("❌ 未能正确解析help.md文件")
        
        pygame.quit()
            
    except Exception as e:
        print(f"❌ 初始化规则查看器时出错: {e}")
        import traceback
        traceback.print_exc()
        try:
            pygame.quit()
        except:
            pass

if __name__ == "__main__":
    test_rules_viewer()