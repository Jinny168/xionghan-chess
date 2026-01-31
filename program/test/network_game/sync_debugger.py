"""
匈汉象棋状态同步调试工具
用于检测和解决网络对战中的状态同步问题
"""
import sys
import os
import json
import hashlib
import time
from datetime import datetime

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from program.core.game_state import GameState
from program.lan.network_game import NetworkChessGame


class SyncDebugger:
    """状态同步调试器"""
    
    def __init__(self):
        self.debug_logs = []
        self.sync_issues = []
        self.state_snapshots = []
        
    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.debug_logs.append(log_entry)
        print(log_entry)
    
    def capture_state_snapshot(self, game_state, label=""):
        """捕获游戏状态快照"""
        try:
            snapshot = {
                'timestamp': time.time(),
                'label': label,
                'player_turn': game_state.player_turn,
                'pieces_count': len(game_state.pieces),
                'pieces': [(p.name, p.color, p.row, p.col) for p in sorted(game_state.pieces, key=lambda x: (x.row, x.col, x.name))],
                'move_history_length': len(game_state.move_history),
                'captured_pieces': {
                    'red': [p.name for p in game_state.captured_pieces['red']],
                    'black': [p.name for p in game_state.captured_pieces['black']]
                },
                'game_over': game_state.game_over,
                'winner': game_state.winner,
                'is_check': game_state.is_check
            }
            
            # 计算哈希
            state_str = json.dumps(snapshot, sort_keys=True, default=str)
            snapshot['hash'] = hashlib.md5(state_str.encode()).hexdigest()
            
            self.state_snapshots.append(snapshot)
            self.log(f"状态快照已捕获: {label} (哈希: {snapshot['hash'][:8]})")
            return snapshot
            
        except Exception as e:
            self.log(f"捕获状态快照失败: {e}", "ERROR")
            return None
    
    def compare_states(self, state1, state2, comparison_label=""):
        """比较两个游戏状态"""
        try:
            if state1['hash'] == state2['hash']:
                self.log(f"✅ 状态比较通过: {comparison_label}")
                return True
            else:
                self.log(f"❌ 状态比较失败: {comparison_label}")
                self.log(f"  状态1哈希: {state1['hash']}")
                self.log(f"  状态2哈希: {state2['hash']}")
                
                # 详细比较差异
                differences = []
                if state1['player_turn'] != state2['player_turn']:
                    differences.append(f"玩家回合: {state1['player_turn']} vs {state2['player_turn']}")
                if state1['pieces_count'] != state2['pieces_count']:
                    differences.append(f"棋子数量: {state1['pieces_count']} vs {state2['pieces_count']}")
                if state1['move_history_length'] != state2['move_history_length']:
                    differences.append(f"移动历史长度: {state1['move_history_length']} vs {state2['move_history_length']}")
                if state1['game_over'] != state2['game_over']:
                    differences.append(f"游戏结束状态: {state1['game_over']} vs {state2['game_over']}")
                
                if differences:
                    self.log(f"  差异详情: {', '.join(differences)}")
                
                self.sync_issues.append({
                    'comparison_label': comparison_label,
                    'state1_hash': state1['hash'],
                    'state2_hash': state2['hash'],
                    'differences': differences,
                    'timestamp': time.time()
                })
                
                return False
                
        except Exception as e:
            self.log(f"状态比较出错: {e}", "ERROR")
            return False
    
    def detect_sync_issues(self):
        """检测同步问题"""
        self.log("开始检测同步问题...")
        
        # 检查状态快照序列
        for i in range(1, len(self.state_snapshots)):
            prev_snapshot = self.state_snapshots[i-1]
            curr_snapshot = self.state_snapshots[i]
            
            comparison_label = f"{prev_snapshot['label']} -> {curr_snapshot['label']}"
            self.compare_states(prev_snapshot, curr_snapshot, comparison_label)
        
        self.log(f"同步问题检测完成，发现 {len(self.sync_issues)} 个问题")
        return len(self.sync_issues)
    
    def run_sync_diagnostic(self):
        """运行同步诊断"""
        self.log("开始状态同步诊断...")
        
        # 创建两个游戏状态实例
        state_a = GameState()
        state_b = GameState()
        
        # 捕获初始状态
        initial_a = self.capture_state_snapshot(state_a, "初始状态A")
        initial_b = self.capture_state_snapshot(state_b, "初始状态B")
        
        # 比较初始状态
        self.compare_states(initial_a, initial_b, "初始状态对比")
        
        # 重置并重新创建状态，确保从完全相同的基础开始
        state_a = GameState()
        state_b = GameState()
        
        # 执行一些移动
        moves = [
            (6, 0, 7, 0),  # 红方兵移动
            (9, 1, 8, 1),  # 黑方马移动
            (7, 0, 8, 0),  # 红方兵继续移动
        ]
        
        for i, (from_row, from_col, to_row, to_col) in enumerate(moves):
            # 在状态A中执行移动
            success_a = state_a.move_piece(from_row, from_col, to_row, to_col)
            # 在状态B中执行相同移动
            success_b = state_b.move_piece(from_row, from_col, to_row, to_col)
            
            if success_a and success_b:
                # 捕获移动后的状态
                after_move_a = self.capture_state_snapshot(state_a, f"移动{i+1}_A")
                after_move_b = self.capture_state_snapshot(state_b, f"移动{i+1}_B")
                
                # 比较移动后状态
                self.compare_states(after_move_a, after_move_b, f"移动{i+1}后状态对比")
            else:
                self.log(f"❌ 移动执行失败: ({from_row},{from_col}) -> ({to_row},{to_col}), A成功:{success_a}, B成功:{success_b}")
        
        # 测试悔棋
        self.log("\n--- 测试悔棋同步 ---")
        if len(state_a.move_history) > 0 and len(state_b.move_history) > 0:
            undo_a = state_a.undo_move()
            undo_b = state_b.undo_move()
            
            if undo_a and undo_b:
                undo_a_snapshot = self.capture_state_snapshot(state_a, "悔棋后_A")
                undo_b_snapshot = self.capture_state_snapshot(state_b, "悔棋后_B")
                
                self.compare_states(undo_a_snapshot, undo_b_snapshot, "悔棋后状态对比")
            else:
                self.log(f"❌ 悔棋执行失败, A成功:{undo_a}, B成功:{undo_b}")
        else:
            self.log("⚠️  悔棋测试：移动历史不足")
        
        # 检测同步问题
        issue_count = self.detect_sync_issues()
        
        # 生成诊断报告
        self.generate_report(issue_count)
    
    def generate_report(self, issue_count):
        """生成诊断报告"""
        self.log(f"\n{'='*60}")
        self.log("状态同步诊断报告")
        self.log("="*60)
        
        self.log(f"状态快照总数: {len(self.state_snapshots)}")
        self.log(f"发现的问题数: {issue_count}")
        self.log(f"日志条目数: {len(self.debug_logs)}")
        
        if self.sync_issues:
            self.log("\n详细问题列表:")
            for i, issue in enumerate(self.sync_issues, 1):
                self.log(f"  {i}. {issue['comparison_label']}")
                self.log(f"     时间: {datetime.fromtimestamp(issue['timestamp']).strftime('%H:%M:%S')}")
                if issue['differences']:
                    self.log(f"     差异: {', '.join(issue['differences'])}")
        else:
            self.log("\n✅ 未发现同步问题!")
        
        # 保存报告到文件
        self.save_report()
    
    def save_report(self):
        """保存报告到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sync_diagnostics_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("匈汉象棋状态同步诊断报告\n")
                f.write("="*60 + "\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write(f"状态快照总数: {len(self.state_snapshots)}\n")
                f.write(f"发现的问题数: {len(self.sync_issues)}\n")
                f.write(f"日志条目数: {len(self.debug_logs)}\n\n")
                
                f.write("状态快照列表:\n")
                for snapshot in self.state_snapshots:
                    f.write(f"  {snapshot['label']}: {snapshot['hash'][:8]} (时间: {datetime.fromtimestamp(snapshot['timestamp']).strftime('%H:%M:%S')})\n")
                
                if self.sync_issues:
                    f.write(f"\n同步问题详情:\n")
                    for i, issue in enumerate(self.sync_issues, 1):
                        f.write(f"  问题 {i}:\n")
                        f.write(f"    比较: {issue['comparison_label']}\n")
                        f.write(f"    时间: {datetime.fromtimestamp(issue['timestamp']).strftime('%H:%M:%S')}\n")
                        if issue['differences']:
                            f.write(f"    差异: {', '.join(issue['differences'])}\n")
                        f.write(f"    状态1哈希: {issue['state1_hash']}\n")
                        f.write(f"    状态2哈希: {issue['state2_hash']}\n\n")
                else:
                    f.write("\n✅ 未发现同步问题!\n")
                
                f.write("\n详细日志:\n")
                f.write("-"*60 + "\n")
                for log in self.debug_logs:
                    f.write(log + "\n")
            
            self.log(f"\n诊断报告已保存到: {filename}")
            
        except Exception as e:
            self.log(f"保存报告失败: {e}", "ERROR")

    def get_game_state_hash(self, game_state):
        """获取游戏状态的哈希值"""
        try:
            # 创建状态快照，排除可能随时间变化的字段
            snapshot = {
                'player_turn': game_state.player_turn,
                'pieces_count': len(game_state.pieces),
                'pieces': [(p.name, p.color, p.row, p.col) for p in sorted(game_state.pieces, key=lambda x: (x.row, x.col, x.name))],
                'move_history_length': len(game_state.move_history),
                'captured_pieces': {
                    'red': [p.name for p in game_state.captured_pieces['red']],
                    'black': [p.name for p in game_state.captured_pieces['black']]
                },
                'game_over': game_state.game_over,
                'winner': game_state.winner,
                'is_check': game_state.is_check
                # 排除了时间相关的字段以确保一致性
            }
            
            # 计算哈希
            state_str = json.dumps(snapshot, sort_keys=True, default=str)
            state_hash = hashlib.md5(state_str.encode()).hexdigest()
            return state_hash
            
        except Exception as e:
            self.log(f"获取游戏状态哈希失败: {e}", "ERROR")
            return None


def main():
    """主函数"""
    debugger = SyncDebugger()
    debugger.run_sync_diagnostic()


if __name__ == "__main__":
    main()