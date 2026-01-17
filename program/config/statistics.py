"""匈汉象棋数据统计管理模块"""

import json
import os
from datetime import datetime
from typing import Dict, Any

# 统计数据文件路径
STATISTICS_FILE = "statistics.json"


class StatisticsManager:
    """统计数据管理类"""
    def __init__(self):
        self.statistics_file = STATISTICS_FILE
        self.data = self._load_statistics()
    
    def _load_statistics(self) -> Dict[str, Any]:
        """加载统计数据，如果不存在则创建默认数据"""
        if os.path.exists(self.statistics_file):
            try:
                with open(self.statistics_file, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    # 确保数据结构完整
                    return self._ensure_structure(data)
            except (json.JSONDecodeError, FileNotFoundError):
                # 文件损坏或读取错误，返回默认数据
                return self._get_default_statistics()
        else:
            # 文件不存在，创建默认数据
            return self._get_default_statistics()
    
    def _get_default_statistics(self) -> Dict[str, Any]:
        """获取默认统计数据结构"""
        return {
            "games_played": 0,           # 总游戏数
            "games_won": {              # 各方胜利次数
                "red": 0,
                "black": 0,
                "draw": 0
            },
            "total_time_played": 0,      # 总游戏时长（秒）
            "pieces_captured": {        # 各类棋子被吃总数
                "ju": 0,                # 車
                "ma": 0,                # 馬
                "xiang": 0,             # 相/象
                "shi": 0,               # 士/仕
                "king": 0,              # 将/帅
                "pao": 0,               # 炮/砲
                "pawn": 0,              # 兵/卒
                "wei": 0,               # 尉/衛
                "she": 0,               # 射/䠶
                "lei": 0,               # 檑/礌
                "jia": 0,               # 甲/胄
                "ci": 0,                # 刺
                "dun": 0,               # 盾
                "xun": 0                # 巡/廵
            },
            "fastest_win": {            # 最快胜利记录（秒）
                "red": float('inf'),
                "black": float('inf')
            },
            "longest_game": 0,          # 最长单局时长（秒）
            "favorite_piece": {         # 最喜欢使用的棋子
                "red": "",
                "black": ""
            },
            "win_streak": {             # 连胜记录
                "red": 0,
                "black": 0,
                "current_streak": {"red": 0, "black": 0}
            },
            "last_played": "",          # 最后游戏时间
            "total_moves_made": 0       # 总走子数
        }
    
    def _ensure_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """确保统计数据结构完整，补充缺失字段"""
        default = self._get_default_statistics()
        for key, value in default.items():
            if key not in data:
                data[key] = value
            elif isinstance(value, dict) and isinstance(data[key], dict):
                # 递归处理嵌套字典
                for sub_key, sub_value in value.items():
                    if sub_key not in data[key]:
                        data[key][sub_key] = sub_value
        return data

    def save_statistics(self):
        """保存统计数据到文件"""
        try:
            with open(self.statistics_file, 'w', encoding='utf-8') as file:
                json.dump(self.data, file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存统计数据失败: {e}")

    def update_games_played(self, increment: int = 1):
        """更新游戏次数"""
        self.data["games_played"] += increment
        self.data["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_statistics()

    def update_game_result(self, winner: str, game_duration: float = 0):
        """更新游戏结果
        Args:
            winner: 获胜方 ("red", "black", "draw")
            game_duration: 游戏时长（秒）
        """
        if winner in ["red", "black"]:
            self.data["games_won"][winner] += 1
            # 更新最快胜利记录
            if game_duration > 0 and game_duration < self.data["fastest_win"][winner]:
                self.data["fastest_win"][winner] = game_duration
            # 更新连胜记录
            self.data["win_streak"]["current_streak"][winner] += 1
            if self.data["win_streak"]["current_streak"][winner] > self.data["win_streak"][winner]:
                self.data["win_streak"][winner] = self.data["win_streak"]["current_streak"][winner]
            # 更新其他方连败记录
            other_side = "black" if winner == "red" else "red"
            self.data["win_streak"]["current_streak"][other_side] = 0
        elif winner == "draw":
            self.data["games_won"]["draw"] += 1
            # 和局重置双方连胜记录
            self.data["win_streak"]["current_streak"]["red"] = 0
            self.data["win_streak"]["current_streak"]["black"] = 0

        # 更新总游戏时长和最长游戏记录
        if game_duration > 0:
            self.data["total_time_played"] += game_duration
            if game_duration > self.data["longest_game"]:
                self.data["longest_game"] = game_duration

        self.save_statistics()

    def update_pieces_captured(self, piece_type: str, increment: int = 1):
        """更新被吃棋子统计
        Args:
            piece_type: 棋子类型
            increment: 增量
        """
        if piece_type in self.data["pieces_captured"]:
            self.data["pieces_captured"][piece_type] += increment
        self.save_statistics()

    def update_total_moves(self, increment: int = 1):
        """更新总走子数"""
        self.data["total_moves_made"] += increment
        self.save_statistics()

    def get_statistics(self) -> Dict[str, Any]:
        """获取所有统计数据"""
        return self.data.copy()

    def reset_statistics(self):
        """重置所有统计数据"""
        self.data = self._get_default_statistics()
        self.save_statistics()


# 全局统计数据实例
statistics_manager = StatisticsManager()