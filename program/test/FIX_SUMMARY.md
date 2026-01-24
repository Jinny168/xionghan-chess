# 匈汉象棋将军/绝杀逻辑修复总结

## 问题描述
用户报告了两个问题：
1. 将军提示位置错误 - 在某些情况下，将军提示标识错误地绑定了错误的王
2. 绝杀时未正确显示结束界面 - 在绝杀情况下，游戏没有正确触发结束界面

## 修复内容

### 1. 修复 `get_checked_king_position` 方法
**文件**: `program/core/game_state.py`

**原代码问题**:
```python
def get_checked_king_position(self):
    """获取被将军的将/帅的位置"""
    if not self.is_check:
        return None
        
    # 检查是否是将死情况
    if self.is_checkmate():
        # 在将死情况下，被将死的是对手（即当前玩家的对手）
        opponent_color = "black" if self.player_turn == "red" else "red"
        for piece in self.pieces:
            if isinstance(piece, King) and piece.color == opponent_color:
                return piece.row, piece.col
    else:
        # 普通将军情况，被将军的是对手（即当前玩家的对手）
        # 由于player_turn在移动后已经切换，所以被将军的是对手
        opponent_color = "black" if self.player_turn == "red" else "red"
        for piece in self.pieces:
            if isinstance(piece, King) and piece.color == opponent_color:
                return piece.row, piece.col
    
    return None
```

**修复后代码**:
```python
def get_checked_king_position(self):
    """获取被将军的将/帅的位置"""
    if not self.is_check or self.game_over:
        return None  # 如果游戏已经结束，不应该再显示将军动画
        
    # 普通将军情况，被将军的是对手（即当前玩家的对手）
    # 由于player_turn在移动后已经切换，所以被将军的是对手
    opponent_color = "black" if self.player_turn == "red" else "red"
    for piece in self.pieces:
        if isinstance(piece, King) and piece.color == opponent_color:
            return piece.row, piece.col
    
    return None
```

**关键变更**:
- 添加了 `or self.game_over` 条件，确保在游戏结束后不再返回被将军的王的位置
- 简化了逻辑，移除了冗余的绝杀检查，因为绝杀时游戏已经结束

### 2. 修复 `should_show_check_animation` 方法
**文件**: `program/core/game_state.py`

**修复后代码**:
```python
def should_show_check_animation(self):
    """检查是否应该显示将军动画"""
    if not self.is_check or self.game_over:
        return False
        
    # 检查动画是否在有效时间内
    current_time = time.time()
    elapsed = current_time - self.check_animation_time
    return elapsed < self.check_animation_duration
```

**关键变更**:
- 添加了 `or self.game_over` 条件，确保在游戏结束后不显示将军动画

### 3. 优化 `move_piece` 方法中的游戏结束逻辑
**文件**: `program/core/game_state.py`

**关键变更**:
- 改进了绝杀检测逻辑，确保在绝杀时正确设置 `game_over` 和 `winner`
- 确保在绝杀时不切换玩家回合
- 在绝杀时重置将军状态 (`self.is_check = False`)，因为游戏已经结束

## 验证结果

所有测试均已通过：
- ✓ 将军提示位置正确
- ✓ 绝杀时不会显示将军动画
- ✓ 绝杀时游戏正确结束并确定获胜方
- ✓ 普通将军时正确显示将军动画

## 影响范围

- 修复了将军动画显示逻辑，避免在绝杀时错误显示
- 修复了游戏结束时的界面显示问题
- 保持了原有的游戏逻辑完整性
- 不影响其他游戏功能

## 测试覆盖

创建了以下测试用例验证修复：
- 普通将军场景
- 绝杀场景
- 游戏结束状态下的将军动画处理
- 将军动画显示条件验证