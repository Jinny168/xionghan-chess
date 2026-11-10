# WASM 可行性结论（2026-11-09）

**状态：不采纳（v2.0 前）。** 本文是 S4「WASM 可行性验证」的出口记录，结论只覆盖
「把 Python 规则/AI 编译成 WASM（Pyodide 或同类）给 Web/Android 用」这一条路径；
不涉及用 WASM 做渲染、音频或 UI。

## 1. 要解决的问题

当前三端共用 `src/xionghan_chess/core/`，但 Web 与 Android 离线包各有一份手抄的
JS 规则引擎（`web/js/offline.js`、`android/Resources/assets/offline/`）。目标是让
「规则逻辑只存在一份」，候选路径有：

| 路径 | 做法 | 结论 |
|---|---|---|
| A. 代码生成 | 从 `core` 的表数据生成 JS 数据区 | 已采纳（S5，范围含档位表） |
| B. WASM/Pyodide | 把 `rules.py`/`ai.py` 编译成 WASM，Web/Android 直接调用 | **本文结论：不做** |
| C. 收敛 | 明确离线只支持缩减规则集，并在 UI 声明 | 保留为兜底 |

## 2. 关键实测（本机，2026-11-09）

### 2.1 瓶颈是 movegen，不是解释器

d2 搜索一次约 1.9–2.3 s，按类方法包裹做墙钟归因：

| 项 | 次数 | 单次 | 占墙钟 |
|---|---|---|---|
| `legal_moves` | 23–25 | **47–49 ms** | **53–60%** |
| `_order`（含嵌套） | 57–116 | 4–9 ms | 21–26% |
| `_evaluate` | 88–167 | 2.4–2.6 ms | 11–19% |
| `in_check`（嵌套在预筛） | 3476–3791 | 0.13 ms | 22–25% |

结论：**一半以上的时间花在一次 47–49 ms 的合法着生成上**。换解释器（Pyodide 通常比
CPython 慢 1.5–6×，未在本机验证）只会把 47 ms 变得更大，不会带来 5× 收益。

### 2.2 分层成本：只有 d1/d2/d3 可卖

| 深度 | 每手耗时 |
|---|---|
| d1 | 0.25 s |
| d2 | 2.10 s |
| d3 | 6.53 s |
| d4 | 29.47 s |

WASM 若按乐观 2× 变慢估算：5 s 预算只能到 d1，12 s 勉强 d2。**离线端能拿到的只有
「入门/初级」强度**，而这一档完全可以用 200–300 行纯 JS 实现（现有 `offline.js`
已有完整规则引擎与 88 条对拍保护），不需要引入 Python 运行时。

### 2.3 安卓的两个硬阻塞（比性能更致命）

1. **origin 是 `file://`**：`MainActivity.cs` 用
   `file:///android_asset/offline/index.html` 加载，Pyodide 需要 `fetch()` wasm；
   必须换 `WebViewAssetLoader`（`https://appassets.androidplatform.net/...`）。
2. **换 origin = localStorage 全丢**：`offline.js` 重度使用
   `xh-offline-preferences` / `-replays` / `-statistics` / `-avatar` / `xh-offline-profile`。
   两套 origin 的 localStorage 不能互读，迁移需要「桥页面导出 → 新 origin 导入」，
   复杂度与风险都高于收益。

体积：APK 现为 39,564,507 B（38 MB），Pyodide 运行时量级约 10 MB（未验证），
首启加载还会增加。

## 3. 决策

**v2.0 前不引入 WASM/Pyodide，不新增任何相关依赖。**

理由按权重：

1. 瓶颈在 movegen（53–60% 墙钟），不在解释器；WASM 优化错了对象；
2. 即使成功，离线端也只有 d1/d2 可用，而这两档用纯 JS 更便宜；
3. Android 换 origin 会丢存档/统计/棋谱，迁移成本高于收益；
4. 包体 +10 MB、首启加载变慢，与「小而美、纯本地」的项目气质相反。

**替代路线**：保留 JS 规则镜像，先做 S5 代码生成（把 `TYPES`/`PROFILES`/
`DEFAULT_OPTIONS`/档位表从手抄改为生成），若将来确实需要离线 AI，按
「纯 JS depth-1 + 现有评估函数」实现，并只做一档隐藏的「离线练习」，
不进入在线档位阶梯。

## 4. 重新评估的触发条件（任一满足才重开）

1. movegen 完成重构（王受攻击者集合 + 钉子预计算），d3 每手 ≤2 s；
2. Android 完成 `WebViewAssetLoader` 迁移，并给出 localStorage 迁移脚本与回归用例；
3. Pyodide 实测：init ≤2 s、体积 ≤12 MB、相对 CPython ≤2×（三项全过）；
4. 产品明确要求「离线端支持 d3 及以上 AI」，且接受包体 +10 MB。

任一条件不满足，不得以「WASM 可能更快」为由重开；本项目的判据是实测，不是可能性。

## 5. 对路线图的影响

- S4 的「WASM 可行性验证」**关闭**，不再占用 v2.0 周期；
- S5（数据层 codegen）保持原计划，范围含档位表；
- 镜像风险仍在（逻辑型未消灭），由 S5 的数据生成 + 88 条对拍继续兜底；
- 不为 WASM 增依赖、不加构建链，Web 仍是零构建静态站。

## 6. 证据与复现

- 归因命令：`%TEMP%/s4_breakdown.py`（只读包裹类方法，未改仓库）；
- perft 吞吐：desktop_complete d2 11,647 叶子 / 5.06 s；
- APK 体积：`android/bin/Release/net9.0-android/com.xionghan.chess-Signed.apk`；
- 相关代码：`web/js/offline.js`、`android/.../MainActivity.cs`、`core/rules.py`。
