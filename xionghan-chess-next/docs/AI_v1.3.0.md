# 匈汉象棋 AI 引擎优化 v1.3.0（方案 + 实施 + 审计）


> 本文件由 v1.3.0 迭代中的多份输出文档归并而成，保留完整审计痕迹，便于单点查阅。

## 目录

1. 一、AI 引擎优化方案（AI_OPTIMIZATION）
2. 二、AI 优化实施记录（AI_OPTIMIZATION_IMPLEMENTATION）

---

## 一、AI 引擎优化方案（AI_OPTIMIZATION）

## 匈汉象棋 AI 引擎优化方案 v1.3.0

> 实施与实测结果见 [AI_OPTIMIZATION_IMPLEMENTATION_v1.3.0.md](AI_OPTIMIZATION_IMPLEMENTATION_v1.3.0.md)。

> 基于对局 `xionghan_20260811_215539.xhgame` 复盘分析与国际象棋 AI 领域前沿技术调研  
> 约束：节约资源优先，可牺牲计算速度换取棋力，拒绝神经网络方案  
> 日期：2026-08-11

---

## 一、当前对局复盘——AI 为什么弱？

### 1.1 对局基本信息

| 项目 | 值 |
|------|-----|
| 棋种 | desktop_complete（完整模式 13×13） |
| 启用棋子 | 帥/將、俥/車、傌/馬、相/象、仕/士、炮/砲、兵/卒、射/䠶、檑/礌、巡/廵 共10种 |
| AI 执方 | 黑棋 |
| AI 难度 | HARD（深度6，时间9秒，分支限制14） |

### 1.2 典型失误分析

#### 失误①：炮吃兵后暴露被吃（第12-13手）

```
黑 砲 (4,5) 吃 (9,5)    ← 黑炮跨越5行跳到红方底线吃兵
红 傌 (10,3) 吃 (9,5)   ← 红马立即吃掉黑炮
```

- 黑炮价值 500，红兵价值 120
- 炮深入敌后吃掉兵后被马立即杀死
- **净亏 500 - 120 = 380 子力分**
- 根因：AI 搜索深度不够（6层），没看到第13手的马吃炮

#### 失误②：车连吃两炮后被象吃掉（第14-17手）

```
黑 車 (2,2) 吃 (10,2)   ← 黑车吃红炮（炮1，+500）
...
黑 車 (10,2) 吃 (10,7)  ← 黑车吃红炮（炮2，+500）
红 相 (12,9) 吃 (10,7)  ← 红象吃掉黑车！
```

- 黑车（900）吃掉两个炮（500+500=1000）
- 然后被红象（260）吃掉
- 表面净赚 100，但失去 900 分的主力战车
- **深度6无法前瞻到象吃车的第3步**

#### 失误③：卒冒进被吃（第19-21手）

```
黑 卒 (5,7) 至 (8,7)   ← 黑卒跃进3格进入红方阵地
...
黑 卒 (8,7) 吃 (9,7)   ← 黑卒吃红兵
红 傌 (10,9) 吃 (9,7)  ← 红马立即吃掉黑卒
```

- 黑卒（120）吃红兵（120），然后被红马（450）吃掉
- **净亏 120（等于白送一卒）**
- AI 只看2步：卒吃兵得120分 → 没有看到后续被马吃的损失

#### 失误④：车原地踏步被吃（第27-28手）

```
黑 車 (2,11) 至 (2,10)  ← 黑车只走1格（浪费一步）
红 俥 (8,10) 吃 (2,10)  ← 红车直冲过来吃掉黑车
```

- 车的走法完全在红车6格射程内
- AI 评估没有意识到车已暴露在敌方攻击范围

### 1.3 根因总结

| 根因 | 描述 | 严重度 |
|------|------|--------|
| **搜索深度浅** | HARD仅6层，13×13棋盘平均分支因子远超标准象棋，6层仅能看3回合 | P0 |
| **缺乏交换评估** | 无 SEE（静态交换评估），无法判断吃子序列的实际净值 | P0 |
| **评估函数粗糙** | 仅子力+中央权重，无位置表(PST)、无机动性、无阶段感知 | P1 |
| **无空着剪枝** | 缺少 Null-Move Pruning，无法高效跳过好局面 | P1 |
| **无LMR** | 缺少 Late Move Reduction，搜索效率低 | P1 |
| **静态搜索不足** | Quiescence 只考虑吃子，不检查将军 | P2 |
| **分支限制过于激进** | HARD 非将军局面仅搜14个分支，可能错过战术 | P2 |

---

## 二、优化方案全景图

```
┌─────────────────────────────────────────────────────────┐
│                    优化路线图 v1.3.0                      │
├─────────────────────────────────────────────────────────┤
│  Tier 1 立即实施（修复"愚蠢吃子"）                        │
│  ├── 交换静态评估 (SEE)         ← 判断吃子实际盈亏        │
│  ├── 增强静态搜索               ← SEE过滤坏吃子           │
│  └── SEE驱动走子排序            ← 好吃子优先/坏吃子延后   │
├─────────────────────────────────────────────────────────┤
│  Tier 2 核心增强（提升棋力50%+）                          │
│  ├── 棋子位置表 (PST)           ← 位置感知评估            │
│  ├── 阶段化评估 (Tapered Eval)  ← 开局/中局/残局分段     │
│  ├── 机动性评估                 ← 合法走子数评分           │
│  └── 王安全评估增强             ← 多维度将帅安全           │
├─────────────────────────────────────────────────────────┤
│  Tier 3 搜索增强（提升深度2-3层）                         │
│  ├── 空着剪枝 (NMP)             ← 翻倍有效搜索深度        │
│  ├── 延迟走子减少 (LMR)         ← 晚搜索走子降深度         │
│  ├── 试探窗口 (Aspiration)      ← 收窄alpha-beta窗口      │
│  └── 自适应分支限制             ← 根据深度动态调整         │
└─────────────────────────────────────────────────────────┘
```

---

## 三、Tier 1：修复"愚蠢吃子"（立即实施）

### 3.1 静态交换评估 (Static Exchange Evaluation, SEE)

**核心原理**：对一个目标格，用双方最便宜的棋子交替模拟吃子，算出吃子序列的实际净值。

```
算法伪代码：
function SEE(square, attacker_color):
    gain[0] = captured_piece_value
    depth = 0
    piece = get_least_valuable_attacker(square, attacker_color)
    while piece exists:
        depth++
        gain[depth] = piece_value[piece] - gain[depth-1]
        if max(gain[depth], 0) < threshold:
            break
        piece = get_least_valuable_attacker(square, opponent(attacker_color))
    return gain 序列的最优净收益
```

**对匈汉象棋的适配**：

```python
# 新增 ai.py 中的SEE实现

SEE_PIECE_ORDER = [
    PieceType.PAWN,      # 120  (最便宜)
    PieceType.PATROL,    # 360
    PieceType.ARMOR,     # 420
    PieceType.ASSASSIN,  # 430
    PieceType.HORSE,     # 450
    PieceType.ARCHER,    # 480
    PieceType.CANNON,    # 500
    PieceType.GUARD,     # 520
    PieceType.SHIELD,    # 600
    PieceType.THUNDER,   # 650
    PieceType.ROOK,      # 900
    PieceType.ELEPHANT,  # 260 (但通常最后吃)
    PieceType.ADVISOR,   # 240
    PieceType.KING,      # 50000
]

def _see(self, game: Game, move: Move, margin: float = 0) -> bool:
    """返回该吃子是否净收益 >= margin"""
    state = game.state
    target = state.piece_at(move.target)
    if target is None:
        return margin <= 0  # 非吃子走法，SEE不适用
    
    # 第一步强制执行
    moving = state.piece_at(move.source)
    gain = VALUES[target.type]
    if gain < margin:
        return False
    
    # 模拟交换序列（迭代实现）
    balance = [gain]  # balance[i] = 第i次交换后的余额
    current_color = state.turn.opponent  # 轮到对手吃
    target_square = move.target
    
    # 临时棋子的位置（简化处理）
    # 在完整实现中需要跟踪X-ray攻击者
    
    # 关键：用最便宜的棋子吃
    attackers = self._attackers_to(game, target_square, current_color)
    
    while attackers:
        best_attacker = min(attackers, key=lambda p: VALUES.get(p.type, 99999))
        captured_value = VALUES.get(best_attacker.type, 0)
        new_balance = captured_value - balance[-1]
        balance.append(new_balance)
        current_color = current_color.opponent
        # 如果当前方可以选择不吃（pat），取 max(0, ...)
        if new_balance < 0:
            break
        attackers = self._attackers_to(game, target_square, current_color)
    
    net_gain = max(balance[-1], 0)
    return net_gain >= margin
```

**预期效果**：
- 完全消除車吃炮被象吃这种负收益吃子
- 静态度搜索只搜 SEE ≥ 0 的吃子
- QQ：+80-120 分棋力提升（来源于 SEE 文献的 Elo 增益）
- 资源消耗：每次 SEE 计算约 10-50 次攻击检查，低开销

### 3.2 增强静态搜索（Quiescence Search）

**当前问题**：Quiescence 搜索所有吃子，包括注定亏损的吃子。

**改进**：
```python
def _quiescence(self, game, alpha, beta, deadline, cancel, ply, remaining, legal=None):
    # ... stand_pat ...
    
    # ★新增：只搜索 SEE ≥ 0 的吃子
    tactical = [move for move in moves 
                if self._see(game, move, margin=0)]
    
    # ★新增：将军时也搜索所有走法（不仅是吃子）
    if in_check:
        tactical = game.rules.legal_moves(game.state)  # 全部合法走法
    
    for move in self._order(game, tactical, ply=ply):
        # ... 递归搜索 ...
```

### 3.3 SEE 驱动走子排序

**当前**：MVV-LVA（被吃子价值最高、吃子棋子价值最低优先）

**改进**：SEE 排序优先于 MVV-LVA

```python
def _order(self, game, moves, preferred=None, ply=0):
    def score(move):
        # ...现有逻辑...
        capture = self._capture_value(game, move)
        if capture > 0:
            # ★ SEE 加权：好交换加分，坏交换减分
            see_score = self._see(game, move)
            if see_score >= 0:
                value += 2000 + see_score  # 好交换大幅提升权重
            else:
                value -= 3000  # 坏交换推到队尾
        return value
```

---

## 四、Tier 2：评估函数增强（核心棋力提升）

### 4.1 棋子位置表 (Piece-Square Tables, PST)

**原理**：每种棋子在不同位置有不同的战略价值。例如：
- 马在中路比在边路更有价值
- 炮在河沿比在底线威慑力更大
- 兵过河后机动性增加
- 车控制开放线得分更高

**实现**（以黑棋为例，红棋需翻转行坐标）：

```python
# 新增 PST 常量表（13x13 棋盘）

# 卒的位置价值（过河后大幅提升）
PAWN_PST_BLACK = [
    [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [10,10,10,10,10,10,10,10,10,10,10,10,10],
    [10,10,15,15,15,15,15,15,15,15,15,10,10],
    [15,15,20,25,25,30,25,25,25,20,15,15,15],  # 中路最高价值
    [20,25,30,35,35,40,35,35,30,30,25,20,20],  # 底线全向移动
    [25,30,35,40,40,45,40,40,35,35,30,25,25],  # ♟ 威胁对方底线
    [30,35,40,45,45,50,45,45,40,40,35,30,30],
    [35,40,45,50,50,55,50,50,45,45,40,35,35],
    [40,45,50,55,55,60,55,55,50,50,45,40,40],
    [45,50,55,60,60,65,60,60,55,55,50,45,45],
]

# 马的位置价值（中心强，边角弱）
HORSE_PST_BLACK = [
    [-80,-50,-40,-30,-30,-30,-30,-30,-30,-40,-50,-80],
    [-50,-30,-10,  0,  0,  5,  0,  0,  0,-10,-30,-50],
    [-40,-10, 10, 15, 20, 25, 20, 15, 10, 10,-10,-40],
    [-30,  0, 15, 25, 30, 35, 30, 25, 15, 15,  0,-30],
    [-30,  0, 20, 30, 40, 45, 40, 30, 20, 20,  0,-30],
    [-30,  5, 25, 35, 45, 50, 45, 35, 25, 25,  5,-30],
    [-30,  5, 25, 35, 45, 50, 45, 35, 25, 25,  5,-30],
    [-30,  0, 20, 30, 40, 45, 40, 30, 20, 20,  0,-30],
    [-30,  0, 15, 25, 30, 35, 30, 25, 15, 15,  0,-30],
    [-40,-10, 10, 15, 20, 25, 20, 15, 10, 10,-10,-40],
    [-50,-30,-10,  0,  0,  5,  0,  0,  0,-10,-30,-50],
    [-80,-50,-40,-30,-30,-30,-30,-30,-30,-40,-50,-80],
    [-120,-80,-60,-50,-50,-50,-50,-50,-50,-60,-80,-120],
]

# 炮的位置价值（河沿威慑力最大）
CANNON_PST_BLACK = [
    [-20,-10,  0,  5, 10, 10, 10, 10,  5,  0,-10,-20],
    [-10,  0, 10, 15, 20, 20, 20, 20, 15, 10,  0,-10],
    [  0, 10, 20, 25, 30, 30, 30, 30, 25, 20, 10,  0],
    [  5, 15, 25, 30, 35, 40, 35, 30, 30, 25, 15,  5],
    [ 10, 20, 30, 35, 45, 50, 45, 35, 35, 30, 20, 10],
    [ 10, 20, 30, 35, 45, 50, 45, 35, 35, 30, 20, 10],
    [  5, 15, 25, 30, 35, 40, 35, 30, 30, 25, 15,  5],
    [  0, 10, 20, 25, 30, 30, 30, 30, 25, 20, 10,  0],
    [-10,  0, 10, 15, 20, 20, 20, 20, 15, 10,  0,-10],
    [-20,-10,  0,  5, 10, 10, 10, 10,  5,  0,-10,-20],
    [-30,-20,-10, -5,  0,  0,  0,  0, -5,-10,-20,-30],
    [-40,-30,-20,-15,-10,-10,-10,-10,-15,-20,-30,-40],
    [-50,-40,-30,-25,-20,-20,-20,-20,-25,-30,-40,-50],
]

# 车的位置价值
ROOK_PST_BLACK = [
    [  0,  0,  0,  5,  5,  5,  5,  5,  5,  0,  0,  0,  0],
    [  5, 10, 10, 15, 15, 15, 15, 15, 15, 10, 10,  5,  5],
    [  5, 10, 10, 15, 20, 20, 20, 20, 15, 10, 10,  5,  5],
    [  0,  5, 10, 15, 20, 25, 25, 20, 15, 10,  5,  0,  0],
    [  0,  5, 10, 15, 20, 25, 25, 20, 15, 10,  5,  0,  0],
    [  0,  5, 10, 15, 20, 25, 25, 20, 15, 10,  5,  0,  0],
    [  0,  5, 10, 15, 20, 25, 25, 20, 15, 10,  5,  0,  0],
    [  0,  5, 10, 15, 20, 25, 25, 20, 15, 10,  5,  0,  0],
    [  0,  5, 10, 15, 20, 25, 25, 20, 15, 10,  5,  0,  0],
    [  0,  5, 10, 15, 20, 25, 25, 20, 15, 10,  5,  0,  0],
    [  0,  5, 10, 15, 20, 25, 25, 20, 15, 10,  5,  0,  0],
    [  0,  5, 10, 15, 25, 30, 30, 25, 15, 10,  5,  0,  0],
    [  0,  0,  0,  5, 15, 20, 20, 15,  5,  0,  0,  0,  0],
]

# 象的位置价值（防守阵型加分）
ELEPHANT_PST_BLACK = [
    [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0, 10,  0,  0, 15,  0,  0,  0, 10,  0,  0,  0],
    [  0, 10, 0,  0, 20,  0, 20,  0,  0,  0, 10,  0,  0],
    [  0,  0,  0,  0,  0, 25,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0, 15,  0,  0, 30,  0,  0,  0, 15,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    ....
]
# (完整13x13表格需填充，此处展示主要结构)
```

**PST 集成**：
```python
def _evaluate(self, game, color):
    score = 0.0
    for piece in game.state.pieces:
        sign = 1 if piece.color is color else -1
        
        # ★ 材料分
        material = VALUES[piece.type]
        
        # ★ 位置分（PST）
        if piece.color is Color.BLACK:
            positional = self._pst_lookup(piece, piece.position.row, piece.position.col)
        else:
            # 红棋翻转PST（行对称）
            positional = self._pst_lookup(piece, 
                game.profile.rows - 1 - piece.position.row, piece.position.col)
        
        score += sign * (material + positional)
    return score
```

### 4.2 阶段化评估 (Tapered Evaluation)

棋局分为开局、中局、残局三个阶段，不同阶段子力价值不同。例如：
- 开局：位置发展和机动性更重要
- 中局：子力价值和攻守平衡最重要
- 残局：兵的价值上升，王的活动能力重要

```python
def _evaluate(self, game, color):
    # ★ 计算阶段权重
    total_material = sum(VALUES[p.type] for p in game.state.pieces 
                        if p.type is not PieceType.KING)
    max_material = sum(VALUES[t] * count 
                      for t, count in self._initial_counts().items())
    
    # game_phase: 0=开局, 1=残局
    game_phase = 1.0 - min(1.0, total_material / max_material)
    
    for piece in game.state.pieces:
        sign = 1 if piece.color is color else -1
        
        material = VALUES[piece.type]
        pst_opening = self._pst_lookup(piece, row, col, phase='opening')
        pst_endgame = self._pst_lookup(piece, row, col, phase='endgame')
        
        # ★ 阶段混合评估
        pst = pst_opening * (1 - game_phase) + pst_endgame * game_phase
        
        score += sign * (material + pst)
    
    # ★ 残局王活跃度加分
    if game_phase > 0.5:
        score += self._king_endgame_activity(game, color) * game_phase
    
    return score
```

### 4.3 机动性评估 (Mobility)

**原理**：合法走子数越多，棋子越活跃，局势越好。

```python
def _mobility_score(self, game, color):
    """计算一方所有棋子的机动性分数"""
    state = replace(game.state, turn=color)
    total = 0
    
    for piece in state.pieces:
        if piece.color is not color:
            continue
        # 轻量计算每个棋子的合法走子数
        moves = self._count_moves(game, piece)
        
        # 不同棋子机动性权重不同
        weights = {
            PieceType.ROOK: 2, PieceType.HORSE: 3,
            PieceType.CANNON: 2, PieceType.PAWN: 1,
            PieceType.ELEPHANT: 1, PieceType.ADVISOR: 1,
            PieceType.ARCHER: 2, PieceType.THUNDER: 2,
            PieceType.PATROL: 1,
        }
        weight = weights.get(piece.type, 1)
        total += moves * weight
    
    return total
```

### 4.4 王安全增强

```python
def _king_safety(self, game, color):
    """综合评估将帅安全性"""
    king = self._find_king(game.state, color)
    if king is None:
        return -10000
    
    score = 0
    
    # 1. 九宫安全性
    in_palace = game.rules.palace(color, king.position)
    if in_palace:
        score += 30
    
    # 2. 护卫棋子数（士象在将帅周围）
    guards = self._count_guards(game.state, king)
    score += guards * 15
    
    # 3. 暴露度（相邻空格数，暴露越多越危险）
    open_squares = self._count_open_adjacent(game.state, king)
    score -= open_squares * 12
    
    # 4. 对方面向王方向的攻击子力
    threats = self._count_threats_toward_king(game, color)
    score -= threats * 25
    
    # 5. 王周围敌方棋子密度
    enemy_nearby = self._count_enemy_near_king(game.state, king)
    score -= enemy_nearby * 20
    
    return score
```

---

## 五、Tier 3：搜索算法增强（提升有效深度）

### 5.1 空着剪枝 (Null-Move Pruning, NMP)

**原理**：如果跳过一步（空着），对方仍然无法打破 beta，说明当前局面太好，可以直接剪枝。

**对匈汉象棋的适配**：

```python
def _search(self, game, depth, alpha, beta, deadline, cancel, ply):
    # ... TT lookup ...
    # ... check depth <= 0 ...
    
    # ★ 空着剪枝（关键优化）
    # 前提：不是将军状态，不是PV节点，深度够深
    if (depth >= 3 
        and not game.rules.in_check(game.state, game.state.turn)
        and beta < VALUES[PieceType.KING]):  # 不是将死搜索
        
        R = 3 + depth // 4  # 缩减系数，越深缩减越多
        
        # 跳过当前回合（转换走子方）
        null_state = replace(game.state, turn=game.state.turn.opponent)
        null_game = Game.from_state(null_state, game.options)
        
        score = -self._search(null_game, depth - 1 - R, -beta, -beta + 1,
                             deadline, cancel, ply + 1)
        
        if score >= beta:
            return beta  # 剪枝！
    
    # ... 正常搜索 ...
```

**约束条件（防止楚茨文格误判）**：
- 不用于将军局面（必须应将）
- 不用于残局（子力少时楚茨文格风险高）
- 本方剩余子力 > 3 时才启用

```python
def _can_null_move(self, game):
    """检查是否可以使用空着剪枝"""
    # 己方剩余子力数
    my_pieces = sum(1 for p in game.state.pieces 
                    if p.color is game.state.turn and p.type is not PieceType.KING)
    return my_pieces >= 3  # 至少还有3个其他棋子
```

### 5.2 延迟走子减少 (Late Move Reduction, LMR)

**原理**：排在前面的走子通常是最好的（经过走子排序），排在后面的走子很可能不好，用更浅的深度搜索，如果看起来不错再重新深搜。

```python
def _search(self, game, depth, alpha, beta, deadline, cancel, ply):
    # ... 
    moves = game.rules.legal_moves(game.state)
    ordered = self._order(game, moves, entry.best_move if entry else None, ply)
    
    for i, move in enumerate(ordered):
        self._guard(deadline, cancel)
        
        # ★ LMR：第4个及之后的安静走子减少搜索深度
        reduction = 0
        if (i >= 3                          # 前3个走子不减
            and depth >= 3                   # 够深才减
            and not self._capture_value(game, move)  # 安静走子
            and not game.rules.in_check(game.state, game.state.turn)):  # 不将军
            
            reduction = 1 + (i - 3) // 5     # 渐进式缩减
            reduction = min(reduction, depth - 1)  # 不超过depth-1
        
        child = Game.from_state(...)
        if reduction > 0:
            # 先用减深度搜索
            score = -self._search(child, depth - 1 - reduction, 
                                 -alpha - 1, -alpha, deadline, cancel, ply + 1)
            if score <= alpha:
                continue  # 确实不好，跳过
            # 如果看起来不错（score > alpha），重新全深度搜索
            score = -self._search(child, depth - 1, -beta, -alpha,
                                 deadline, cancel, ply + 1)
        else:
            score = -self._search(child, depth - 1, -beta, -alpha,
                                 deadline, cancel, ply + 1)
        
        # ... alpha-beta 更新 ...
```

### 5.3 试探窗口搜索 (Aspiration Windows)

```python
def choose_move(self, game, cancel=None):
    cfg = CONFIGS[self.difficulty]
    # ...
    
    # ★ 试探窗口：基于上一轮迭代结果缩小窗口
    prev_score = 0
    window = 50  # 初始窗口半宽
    
    for depth in range(1, cfg.depth + 1):
        alpha = prev_score - window
        beta = prev_score + window
        
        while True:
            score, candidate = self._root(game, search_moves, depth, 
                                         deadline, cancel, alpha, beta)
            
            if score <= alpha:
                # 估计值太低，扩大下界
                alpha = -math.inf
                window *= 2
            elif score >= beta:
                # 估计值太高，扩大上界
                beta = math.inf
                window *= 2
            else:
                # 窗口合适
                best = candidate
                prev_score = score
                window = 30  # 重置窗口
                break
```

### 5.4 自适应分支限制

```python
# 当前 HARD: branch_limit=14, root_limit=28
# 改进：根据深度和搜索阶段动态调整

ADAPTIVE_CONFIGS = {
    Difficulty.HARD: {
        1: SearchConfig(..., branch_limit=28, root_limit=28),  # 根节点不限制
        2: SearchConfig(..., branch_limit=24, root_limit=24),
        3: SearchConfig(..., branch_limit=20, root_limit=20),
        4: SearchConfig(..., branch_limit=18, root_limit=18),
        5: SearchConfig(..., branch_limit=16, root_limit=16),
        6: SearchConfig(..., branch_limit=14, root_limit=14),
        7: SearchConfig(..., branch_limit=12, root_limit=12),
        8: SearchConfig(..., branch_limit=10, root_limit=10),
    }
}
```

---

## 六、难度等级重新设计

### 6.1 新版难度配置

```python
NEW_CONFIGS = {
    Difficulty.BEGINNER: SearchConfig(
        depth=2,          # 2层
        time_limit=0.5,   # 0.5秒
        randomness=0.35,  # 高随机性
        quiescence_depth=1,
        candidate_count=5,
        branch_limit=3,   # 激进剪枝
        root_limit=5,
       ),
    Difficulty.EASY: SearchConfig(
        depth=4,          # 4层（+1）
        time_limit=1.5,   # 1.5秒
        randomness=0.15,
        quiescence_depth=3,  # 更安静的搜索（+1）
        candidate_count=4,
        branch_limit=6,
        root_limit=10,
       ),
    Difficulty.MEDIUM: SearchConfig(
        depth=6,          # 6层（+2）
        time_limit=5.0,   # 5秒（+1.5）
        randomness=0.05,
        quiescence_depth=4,
        candidate_count=3,
        branch_limit=10,  # 更多分支
        root_limit=18,
       ),
    Difficulty.HARD: SearchConfig(
        depth=8,          # 8层（+2，仅靠NMP+LMR可达）
        time_limit=12.0,  # 12秒（+3）
        randomness=0.0,   # 无随机性
        quiescence_depth=6,  # 深度静态搜索
        candidate_count=1,  # 只选最优
        branch_limit=18,  # 大幅增加
        root_limit=32,
       ),
}
```

---

## 七、实施优先级与预期效果

### 7.1 实施路线图

| 阶段 | 内容 | 代码量 | 预期棋力提升 | 实施风险 |
|------|------|--------|:----------:|----------|
| **阶段1** | SEE + 增强Quiescence + SEE排序 | ~200行 | +80~120分 | 低 |
| **阶段2** | PST + 阶段评估 + 机动性 | ~400行 | +100~180分 | 中（需调参） |
| **阶段3** | NMP + LMR + Aspiration | ~150行 | +80~150分 | 中（需测试） |
| **阶段4** | 难度重塑 + 自适应分支限制 | ~100行 | 使用体验 | 低 |

**总计预估棋力提升**：+260~450 分（从当前约 600-800 分到 1000-1300 分）

### 7.2 资源消耗评估

| 当前 (HARD) | 优化后 (HARD) | 变化 |
|:---:|:---:|:---:|
| 深度 6 层 | 深度 8 层（有效约 10-12 层） | 实质提升 |
| ~50万节点 | ~80万节点 | 1.6x |
| 9 秒 | 12 秒 | 1.3x |
| 内存 ~20MB | 内存 ~30MB | 1.5x |

### 7.3 关键风险

1. **PST 数值需要调优**：初始值来自标准象棋经验的迁移，可能不完全适配匈汉象棋。建议后续通过自对弈数据微调。
2. **NMP 楚茨文格**：匈汉象棋规则复杂（兵复活、升变等），残局更可能出现楚茨文格。必须在残局阶段禁用 NMP。
3. **LMR 可能剪掉好棋**：LMR 需要"重搜索"机制确保不遗漏关键走法。

---

## 八、代码改动清单

### 8.1 修改文件

| 文件 | 改动内容 |
|------|----------|
| `src/xionghan_chess/core/ai.py` | 主修改：SEE、PST、NMP、LMR、Aspiration、增强评估、增强Quiescence |
| `src/xionghan_chess/core/ai_pst.py` | **新增**：PST表定义（开局/残局两套） |
| `src/xionghan_chess/core/ai_see.py` | **新增**：SEE 实现 |

### 8.2 影响范围

- 仅修改 AI 引擎模块，不影响规则引擎、联机、UI
- 客户端无需任何改动
- 向下兼容（旧棋谱格式不受影响）
- 测试套件覆盖：`tests/test_qa_regressions.py` 需补充 AI 专项测试

---

## 九、专项回归测试用例

```python
# tests/test_ai_optimization.py （新增）

def test_see_rook_eats_cannon_guarded():
    """测试SEE能正确判断車吃被象保护的炮"""
    # 构造局面：黑车可以吃红炮，但红象可以吃回来
    # SEE应该返回负值（或False），阻止这个吃子
    ...

def test_see_pawn_trade():
    """测试SEE能正确判断卒吃兵被马保护"""
    ...

def test_null_move_pruning_basic():
    """测试空着剪枝在优势局面能正确剪枝"""
    ...

def test_lmr_does_not_miss_tactics():
    """测试LMR不会遗漏关键战术"""
    ...

def test_pst_evaluation_symmetry():
    """测试PST评估在对称局面给出相反分数"""
    ...

def test_tapered_evaluation_endgame():
    """测试残局阶段评估切换到残局PST"""
    ...
```

---

## 十、参考文献

1. Chess Programming Wiki - Static Exchange Evaluation: https://www.chessprogramming.org/Static_Exchange_Evaluation
2. Chess Programming Wiki - Null Move Pruning: https://www.chessprogramming.org/Null_Move_Pruning
3. Chess Programming Wiki - Late Move Reductions: https://www.chessprogramming.org/Late_Move_Reductions
4. Chess Programming Wiki - Piece-Square Tables: https://www.chessprogramming.org/Piece-Square_Tables
5. Chess Programming Wiki - Tapered Eval: https://www.chessprogramming.org/Tapered_Eval
6. Yen et al. (2004) "Computer Chinese Chess" - 中国象棋子力权重与PST
7. Li, Cuanqi (2008) UCLA Thesis - 中国象棋PST设计与调优
8. hien-duc/simple-chinese-chess-engine (DeepWiki) - 中国象棋引擎搜索优化
9. maksimKorzh/wukong-xiangqi (DeepWiki) - JavaScript 中国象棋引擎 PST 设计
10. DanielLFS/Chess-AI (GitHub) - Python象棋引擎优化基准

---

*报告由匈汉象棋项目QA助手基于代码分析、对局复盘和技术调研自动生成*  
*建议评审人：研发负责人、AI算法负责人*


---

## 二、AI 优化实施记录（AI_OPTIMIZATION_IMPLEMENTATION）

## 匈汉象棋 AI 优化实施记录 v1.3.0

## 实施范围

| 模块 | 实现 |
|---|---|
| 静态交换评估 | 新增基于权威规则状态逐步执行的 SEE，支持炮架、马腿、遮挡、将军约束、升变、盾保护和间接吃子后的落点状态。 |
| 战术搜索 | Quiescence 在被将军时搜索全部应将着；普通局面过滤负 SEE 吃子并限制战术分支。 |
| 走子排序 | 好交换优先，负交换后置；根节点额外识别高价值棋子的安静悬子。 |
| 位置评估 | 加入棋局阶段、缩放位置权重、兵卒推进、轻量阻塞感知机动性和阶段化将帅安全。 |
| 搜索 | 加入窄窗迭代、受保护的空着剪枝、带全深度重搜索的 LMR、自适应分支上限。 |
| 难度 | 四档重新配置；HARD 上限 8 层、12 秒，无随机选着。深度是迭代上限，不保证复杂局面必然完成。 |
| 可观测性 | 引擎记录完成深度、普通/静态节点、SEE 次数、NMP 剪枝和 LMR 重搜索次数。 |

## 原棋谱复验

来源：`xionghan_20260811_215539.xhgame`，完整模式，87 ply，红方将死获胜。

| Ply | 历史着法 | SEE | 复验结论 |
|---:|---|---:|---|
| 12 | 黑炮吃红兵，随后被马吃 | -380 | 确认是负交换；优化后 HARD 不再选择。 |
| 16 | 黑车吃红炮，随后被象吃 | -400 | 确认是负交换；优化后 HARD 不再选择。 |
| 26 | 黑卒吃红兵，随后被马吃 | 0 | 方案原文写为 -120 不准确；双方各损一兵，属于等价交换。 |
| 28 | 黑车移入红车线路，随后双方车被吃 | 0 | 后续黑礌立即吃回红车，不能按单边丢车计算。优化后仍选择其他安全着。 |

HARD 在第 12 ply 的 12 秒实测完成 2 层主搜索并带 6 层静态搜索，选择 SEE 为 0 的安全着。原方案预计的“有效 10-12 层”不适用于当前纯 Python 权威合法着生成器，因此未作为交付结论。

## 安全约束

- 完整模式启用兵卒复活时禁用空着剪枝。
- 将军局面、稀疏残局和本方非王棋子不足时禁用空着剪枝。
- LMR 不缩减吃子、升变、将军、应将及前四个高排序着法；缩减结果提高 alpha 时自动全深度重搜。
- SEE 不复制国际象棋攻击表，而是调用项目现有规则引擎，不新增或推测匈汉象棋规则。

## 验证覆盖

- 炮吃兵后被马吃：SEE 为 -380。
- 车吃炮后被象吃：SEE 为 -400。
- 安静移车直接悬车：SEE 为 -900。
- 四档 AI 均避开立即亏炮着法。
- 红黑换色并镜像棋盘后，评估值保持对称。
- 兵卒复活和稀疏残局禁用 NMP；传统中局可执行 NMP。
- 原棋谱四个关键局面均完成自动复算。

## 文件

- `src/xionghan_chess/core/ai.py`
- `src/xionghan_chess/core/ai_see.py`
- `tests/test_ai_optimization.py`


---
