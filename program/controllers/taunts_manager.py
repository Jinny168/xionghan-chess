"""嘲讽语句管理模块"""
import json
import os
import random


class TauntManager:
    """嘲讽语句管理器"""
    
    def __init__(self, taunts_file_path=None):
        """初始化嘲讽管理器
        
        Args:
            taunts_file_path (str): 嘲讽语句配置文件路径，默认为 config/taunts.json
        """
        if taunts_file_path is None:
            # 默认使用 config 目录下的 taunts.json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            taunts_file_path = os.path.join(base_dir, "assets/docs", "taunts.json")
        
        self.taunts_file_path = taunts_file_path
        self.taunts = self.load_taunts()
    
    def load_taunts(self):
        """从配置文件加载嘲讽语句列表"""
        try:
            with open(self.taunts_file_path, 'r', encoding='utf-8') as f:
                taunts = json.load(f)
                # 确保返回的是列表
                if isinstance(taunts, list):
                    return taunts
                else:
                    print(f"警告: {self.taunts_file_path} 中的嘲讽语句格式不正确，应为列表格式")
                    return ["是我天下无敌啦！"]  # 默认嘲讽语句
        except FileNotFoundError:
            print(f"警告: 找不到嘲讽语句配置文件 {self.taunts_file_path}，使用默认语句")
            return ["是我天下无敌啦！"]
        except json.JSONDecodeError:
            print(f"警告: {self.taunts_file_path} 不是有效的JSON文件，使用默认语句")
            return ["是我天下无敌啦！"]
        except Exception as e:
            print(f"警告: 加载嘲讽语句时出错: {e}，使用默认语句")
            return ["是我天下无敌啦！"]
    
    def get_random_taunt(self):
        """获取一个随机的嘲讽语句
        
        Returns:
            str: 随机选择的嘲讽语句，如果没有可用语句则返回默认语句
        """
        if self.taunts:
            return random.choice(self.taunts)
        else:
            return "是我天下无敌啦！"
    
    def add_taunt(self, taunt):
        """添加新的嘲讽语句
        
        Args:
            taunt (str): 要添加的嘲讽语句
        """
        if taunt and taunt not in self.taunts:
            self.taunts.append(taunt)
    
    def refresh_taunts(self):
        """重新加载嘲讽语句配置文件"""
        self.taunts = self.load_taunts()


# 全局嘲讽管理器实例
taunt_manager = TauntManager()