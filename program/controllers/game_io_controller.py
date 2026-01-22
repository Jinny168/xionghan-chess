"""
游戏数据导入导出控制器

此模块负责处理棋局的导入和导出功能，使用FEN格式进行数据持久化
"""
import os
from tkinter import filedialog
from program.core.game_state import GameState


class GameIOController:
    """游戏数据导入导出控制器类"""
    
    def __init__(self, game_state=None):
        """初始化控制器
        
        Args:
            game_state: 游戏状态对象，如果为None则在调用时传入
        """
        self.game_state = game_state
    
    def export_game(self, game_state=None, filename=None):
        """导出当前游戏到文件
        
        Args:
            game_state: 游戏状态对象，如果为None则使用实例中的game_state
            filename (str, optional): 保存的文件名
            
        Returns:
            bool: 是否成功保存
        """
        target_game_state = game_state or self.game_state
        if not target_game_state:
            print("错误：未提供游戏状态对象")
            return False
        
        try:
            if filename is None:
                filename = filedialog.asksaveasfilename(
                    title="导出棋局",
                    defaultextension=".fen",
                    filetypes=[("FEN文件", "*.fen"), ("所有文件", "*.*")]
                )
                if not filename:
                    print("用户取消了保存操作")
                    return False
            
            # 生成FEN表示
            fen_string = target_game_state.export_position()
            
            # 保存到文件
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(fen_string)
            
            print(f"游戏已保存到: {filename}")
            return True
        except PermissionError:
            print(f"错误：没有权限写入文件 {filename}")
            return False
        except FileNotFoundError:
            print(f"错误：找不到指定的路径")
            return False
        except Exception as e:
            print(f"保存游戏失败: {str(e)}")
            return False

    def import_game(self, game_state=None, filename=None):
        """从文件导入游戏
        
        Args:
            game_state: 游戏状态对象，如果为None则使用实例中的game_state
            filename (str, optional): 要加载的文件名
            
        Returns:
            bool: 是否成功加载
        """
        target_game_state = game_state or self.game_state
        if not target_game_state:
            print("错误：未提供游戏状态对象")
            return False
        
        try:
            if filename is None:
                filename = filedialog.askopenfilename(
                    title="导入棋局",
                    filetypes=[("FEN文件", "*.fen"), ("所有文件", "*.*")]
                )
                if not filename:
                    print("用户取消了加载操作")
                    return False
            
            # 检查文件是否存在
            if not os.path.exists(filename):
                print(f"错误：文件 {filename} 不存在")
                return False
            
            # 从文件读取FEN字符串
            with open(filename, 'r', encoding='utf-8') as f:
                fen_string = f.read().strip()
                
            # 检查是否为空文件
            if not fen_string:
                print("错误：文件内容为空")
                return False
            
            # 导入位置
            success = target_game_state.import_position(fen_string)
            if success:
                print(f"游戏已从 {filename} 加载")
            else:
                print("导入游戏失败，可能是文件格式错误")
            
            return success
        except PermissionError:
            print(f"错误：没有权限读取文件 {filename}")
            return False
        except UnicodeDecodeError:
            print(f"错误：无法解码文件 {filename}，可能不是UTF-8编码")
            return False
        except Exception as e:
            print(f"加载游戏失败: {str(e)}")
            return False
    
    def auto_save_game(self, game_state, base_filename=None):
        """自动保存游戏（通常用于对局结束后）
        
        Args:
            game_state: 游戏状态对象
            base_filename (str, optional): 基础文件名，会添加时间戳
            
        Returns:
            bool: 是否成功保存
        """
        import time
        
        if not base_filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_filename = f"xionghan_chess_{timestamp}.fen"
        
        # 确保保存到games目录下
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'games')
        save_dir = os.path.abspath(save_dir)  # 获取绝对路径
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        
        full_path = os.path.join(save_dir, base_filename)
        
        return self.export_game(game_state, full_path)
    
    def get_saved_games(self):
        """获取已保存的游戏文件列表
        
        Returns:
            list: 已保存的游戏文件路径列表
        """
        save_dir = os.path.join(os.getcwd(), "games")
        if not os.path.exists(save_dir):
            return []
        
        saved_files = []
        for filename in os.listdir(save_dir):
            if filename.endswith('.fen'):
                saved_files.append(os.path.join(save_dir, filename))
        
        return sorted(saved_files, reverse=True)  # 按时间倒序排列


# 单例模式的全局控制器
game_io_controller = GameIOController()