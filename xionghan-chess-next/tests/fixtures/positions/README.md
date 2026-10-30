# 基准局面快照

## dense_62_85.json

- 指纹：62 子 / 85 合法着
- 来源：desktop_complete / medium / seed 12345 / 6 plies
- 用途：负对照 —— medium 下 5s 与 6s 均为 depth 1（t_d1 约 0.8–1.2s），d2 在 6s 内也拿不到

## 正/负对照用法

- 正对照 L0（62/108，可直接 `Game("desktop_complete")` 生成）：判"预算够不够"
- 负对照 dense_62_85：判"加预算是不是白加"
- 规则：调预算只用正对照下结论；负对照只用来验证"加了也没用"

## 测量纪律

1. 生成用 seed/plies；2. 测量用快照；3. 报告附 pieces/legal 指纹

跨快照引用一律无效（实例：同名 L6 从 62/129 变为 62/85）
