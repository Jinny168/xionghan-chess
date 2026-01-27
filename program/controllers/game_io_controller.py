"""
游戏数据导入导出控制器

此模块负责处理棋局的导入和导出功能，使用FEN格式进行数据持久化
"""
import json
import os
from tkinter import filedialog


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
            
            # 生成完整的棋局表示，包含当前位置和历史记录
            # 需要将复杂对象转换为可序列化的格式
            
            # 序列化走子历史 - 将棋子对象转换为基本信息
            serialized_move_history = []
            for move in target_game_state.move_history:
                if len(move) >= 8:  # 包含甲/胄吃子信息和刺兑子信息
                    piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces, ci_captured_pieces = move
                    serialized_move = [
                        {
                            'name': piece.name,
                            'color': piece.color,
                            'type': piece.__class__.__name__,
                            'row': piece.row,
                            'col': piece.col
                        },
                        from_row, from_col, to_row, to_col,
                        {
                            'name': captured_piece.name,
                            'color': captured_piece.color,
                            'type': captured_piece.__class__.__name__,
                            'row': captured_piece.row,
                            'col': captured_piece.col
                        } if captured_piece else None,
                        [{'name': p.name, 'color': p.color, 'type': p.__class__.__name__, 'row': p.row, 'col': p.col} for p in jia_captured_pieces],
                        [{'name': p.name, 'color': p.color, 'type': p.__class__.__name__, 'row': p.row, 'col': p.col} for p in ci_captured_pieces]
                    ]
                elif len(move) >= 7:  # 包含甲/胄吃子信息
                    piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces = move
                    serialized_move = [
                        {
                            'name': piece.name,
                            'color': piece.color,
                            'type': piece.__class__.__name__,
                            'row': piece.row,
                            'col': piece.col
                        },
                        from_row, from_col, to_row, to_col,
                        {
                            'name': captured_piece.name,
                            'color': captured_piece.color,
                            'type': captured_piece.__class__.__name__,
                            'row': captured_piece.row,
                            'col': captured_piece.col
                        } if captured_piece else None,
                        [{'name': p.name, 'color': p.color, 'type': p.__class__.__name__, 'row': p.row, 'col': p.col} for p in jia_captured_pieces]
                    ]
                else:  # 旧格式
                    piece, from_row, from_col, to_row, to_col, captured_piece = move
                    serialized_move = [
                        {
                            'name': piece.name,
                            'color': piece.color,
                            'type': piece.__class__.__name__,
                            'row': piece.row,
                            'col': piece.col
                        },
                        from_row, from_col, to_row, to_col,
                        {
                            'name': captured_piece.name,
                            'color': captured_piece.color,
                            'type': captured_piece.__class__.__name__,
                            'row': captured_piece.row,
                            'col': captured_piece.col
                        } if captured_piece else None
                    ]
                serialized_move_history.append(serialized_move)
            
            # 序列化阵亡棋子
            serialized_captured_pieces = {}
            for color, pieces in target_game_state.captured_pieces.items():
                serialized_captured_pieces[color] = [
                    {
                        'name': piece.name,
                        'color': piece.color,
                        'type': piece.__class__.__name__,
                        'row': piece.row,
                        'col': piece.col
                    } for piece in pieces
                ]
            
            game_data = {
                'position': target_game_state.export_position(),  # 当前棋盘状态
                'move_history': serialized_move_history,  # 序列化的走子历史
                'captured_pieces': serialized_captured_pieces,  # 序列化的阵亡棋子
                'player_turn': target_game_state.player_turn,  # 当前玩家
                'game_over': target_game_state.game_over,  # 游戏是否结束
                'winner': target_game_state.winner,  # 获胜方
                'total_time': target_game_state.total_time,  # 总游戏时间
                'red_time': target_game_state.red_time,  # 红方用时
                'black_time': target_game_state.black_time,  # 黑方用时
                'is_check': target_game_state.is_check,  # 是否将军
                'moves_count': target_game_state.moves_count,  # 走子数
            }
            
            # 保存到文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(game_data, f, ensure_ascii=False, indent=2)  # type: ignore
            
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
            
            # 从文件读取游戏数据
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # 检查是否为空文件
            if not content:
                print("错误：文件内容为空")
                return False
            
            # 尝试解析JSON格式
            try:
                game_data = json.loads(content)
                
                # 使用导入的数据恢复游戏状态
                if 'position' in game_data:
                    # 先导入基本位置
                    fen_string = game_data['position']
                    target_game_state.import_position(fen_string)
                    
                    # 恢复历史记录和其他状态
                    if 'move_history' in game_data:
                        # 反序列化走子历史
                        deserialized_move_history = []
                        for serialized_move in game_data['move_history']:
                            if len(serialized_move) >= 8:  # 包含甲/胄吃子信息和刺兑子信息
                                piece_data, from_row, from_col, to_row, to_col, captured_piece_data, jia_captured_pieces_data, ci_captured_pieces_data = serialized_move
                                # 创建棋子对象
                                piece = self._create_piece_from_data(piece_data)
                                                
                                captured_piece = None
                                if captured_piece_data:
                                    captured_piece = self._create_piece_from_data(captured_piece_data)
                                                
                                jia_captured_pieces = [self._create_piece_from_data(p_data) for p_data in jia_captured_pieces_data]
                                ci_captured_pieces = [self._create_piece_from_data(p_data) for p_data in ci_captured_pieces_data]
                                                
                                deserialized_move = (piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces, ci_captured_pieces)
                            elif len(serialized_move) >= 7:  # 包含甲/胄吃子信息
                                piece_data, from_row, from_col, to_row, to_col, captured_piece_data, jia_captured_pieces_data = serialized_move
                                piece = self._create_piece_from_data(piece_data)
                                                
                                captured_piece = None
                                if captured_piece_data:
                                    captured_piece = self._create_piece_from_data(captured_piece_data)
                                                
                                jia_captured_pieces = [self._create_piece_from_data(p_data) for p_data in jia_captured_pieces_data]
                                                
                                deserialized_move = (piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces)
                            else:  # 旧格式
                                piece_data, from_row, from_col, to_row, to_col, captured_piece_data = serialized_move
                                piece = self._create_piece_from_data(piece_data)
                                                
                                captured_piece = None
                                if captured_piece_data:
                                    captured_piece = self._create_piece_from_data(captured_piece_data)
                                                
                                deserialized_move = (piece, from_row, from_col, to_row, to_col, captured_piece)
                                            
                            deserialized_move_history.append(deserialized_move)
                        target_game_state.move_history = deserialized_move_history
                                    
                    if 'captured_pieces' in game_data:
                        # 反序列化阵亡棋子
                        deserialized_captured_pieces = {}
                        for color, pieces_data in game_data['captured_pieces'].items():
                            deserialized_pieces = [self._create_piece_from_data(piece_data) for piece_data in pieces_data]
                            deserialized_captured_pieces[color] = deserialized_pieces
                        target_game_state.captured_pieces = deserialized_captured_pieces
                                    
                    if 'player_turn' in game_data:
                        target_game_state.player_turn = game_data['player_turn']
                    if 'game_over' in game_data:
                        target_game_state.game_over = game_data['game_over']
                    if 'winner' in game_data:
                        target_game_state.winner = game_data['winner']
                    if 'total_time' in game_data:
                        target_game_state.total_time = game_data['total_time']
                    if 'red_time' in game_data:
                        target_game_state.red_time = game_data['red_time']
                    if 'black_time' in game_data:
                        target_game_state.black_time = game_data['black_time']
                    if 'is_check' in game_data:
                        target_game_state.is_check = game_data['is_check']
                    if 'moves_count' in game_data:
                        target_game_state.moves_count = game_data['moves_count']
                
                print(f"游戏已从 {filename} 加载")
                return True
            except json.JSONDecodeError:
                # 如果不是JSON格式，尝试旧的FEN格式
                print("检测到旧格式FEN文件，尝试导入...")
                success = target_game_state.import_position(content)
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
    
    @staticmethod
    def get_saved_games():
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

    @staticmethod
    def _create_piece_from_data(piece_data):
        """根据序列化的数据创建棋子对象
        
        Args:
            piece_data (dict): 包含棋子信息的字典
            
        Returns:
            ChessPiece: 棋子对象
        """
        if piece_data is None:
            return None
            
        # 导入棋子类
        from program.core.chess_pieces import (
            Ju, Ma, Xiang, Shi, King, Pao, Pawn, Wei, She, Lei, Jia, Ci, Dun, Xun
        )
        
        # 根据类型名映射到实际的类
        piece_classes = {
            'Ju': Ju,
            'Ma': Ma,
            'Xiang': Xiang,
            'Shi': Shi,
            'King': King,
            'Pao': Pao,
            'Pawn': Pawn,
            'Wei': Wei,
            'She': She,
            'Lei': Lei,
            'Jia': Jia,
            'Ci': Ci,
            'Dun': Dun,
            'Xun': Xun
        }
        
        piece_type = piece_data['type']
        piece_class = piece_classes.get(piece_type)
        
        if piece_class is None:
            print(f"警告：未知的棋子类型 {piece_type}，使用默认棋子")
            return None
        
        # 创建棋子实例
        piece = piece_class(piece_data['color'], piece_data['row'], piece_data['col'])
        piece.name = piece_data['name']
        
        return piece


# 单例模式的全局控制器
game_io_controller = GameIOController()