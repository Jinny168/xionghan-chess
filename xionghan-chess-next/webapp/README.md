# 匈汉象棋 · 网页版

十三路棋盘上的中国象棋变体。完整规则内核移植到 JavaScript，**不依赖任何后端**：
打开页面即可对弈，所有计算都在浏览器里完成。

线上地址：<https://xionghan-chess-90721.app.workbuddy.host/?sharecode=HK75LU3HOF>

---

## 为什么是「静态单页」

桌面端（PySide6）与旧网页端共用 Python 内核，旧网页端必须连 FastAPI 才能走棋。
本目录是面向公网分享重做的形态：

| 维度 | 旧 `web/` | 本目录 `webapp/` |
| --- | --- | --- |
| 规则计算 | Python 服务端 | 浏览器（JS 移植） |
| AI | Python 服务端 | Web Worker |
| 部署 | 需要常驻服务 + WebSocket | 纯静态，单文件即可 |
| 首屏请求 | 12 个 | 1 个（构建后） |
| 断网 | 不可用 | 已加载的页面可继续下 |

## 目录

```text
webapp/
├── index.html            # 入口（开发态，按模块加载）
├── css/app.css           # 设计系统与布局
├── js/
│   ├── core/             # 规则内核（Python core/ 的等价实现）
│   │   ├── model.js      # 棋盘状态与序列化（兼容 .xhgame）
│   │   ├── profiles.js   # 四套规则档案与开关
│   │   ├── rules.js      # 走法判定（逐行对应 rules.py）
│   │   ├── game.js       # 对局流程、计时、结算
│   │   ├── movegen.js    # 快速着法生成（供搜索使用）
│   │   └── ai.js         # 迭代加深 + alpha-beta + 静态搜索
│   ├── ui/
│   │   ├── board.js      # Canvas 棋盘渲染
│   │   ├── sound.js      # WebAudio 合成音效（零素材）
│   │   └── app.js        # 交互与流程编排
│   ├── ai-worker.js      # AI 工作线程
│   └── i18n.js           # 中英文案
├── dist/index.html       # 构建产物（单文件，用于发布）
├── tests/                # 规则一致性门禁
└── screenshots/          # 投稿用截图
```

## 本地运行

```bash
cd webapp
python -m http.server 8123
# 打开 http://127.0.0.1:8123/
```

## 构建单文件版

```bash
python scripts/build_webapp_bundle.py   # 在仓库根目录执行
# 产物：webapp/dist/index.html（约 267 KB，自包含）
```

构建脚本会把 CSS、全部 ES 模块和 AI Worker 内联进一个 HTML。
这样做不只是为了体积——WorkBuddy「发布为网站」的分享链接在首次访问时只授权
HTML 文档本身，子资源会拿到 403；单文件部署可以让评审第一次点开就能玩。

## 验证

规则移植是这件事里唯一不能出错的部分，因此有两道门禁：

```bash
# 1. 用 Python 参考实现导出的黄金用例，逐局面、逐着法比对
node webapp/tests/verify-rules.mjs

# 2. 快速着法生成器 ↔ 逐格枚举参考实现交叉校验
node webapp/tests/verify-movegen.mjs

# 3. 题库：开局未结束、解法合法、一步杀确实将死
node webapp/tests/verify-puzzles.mjs
```

当前结果：

| 项目 | 数量 | 结果 |
| --- | --- | --- |
| 局面比对 | 372 | 全部一致 |
| 走子结算 | 848 | 全部一致 |
| 合法着法 | 23,741 | 逐条一致 |
| 快速生成器 | 23,741 | 与参考实现一致 |

黄金用例由 `scripts/gen_rule_fixtures.py` 生成，覆盖四套规则档案、随机布局、
规则开关变体与自对弈序列。

## 云服务

`online/cloud-config.json` 保存 publicConfig（endpoint / publishableKey），由 `online/server.mjs`
在返回 index.html 时注入 `window.__CLOUD_CONFIG__`，前端不硬编码环境地址。

- 登录：邮箱验证码（`sendOtp` → `verifyOtp`），会话由 SDK 维护
- 数据表：`sync_state`（owner_id 默认 `auth.uid()`，RLS 仅本人可读写）
- 备份内容：偏好设置、棋谱库、对局统计、残局通关记录
- SDK 走 CDN 延迟加载，只在打开「云同步」时拉取，不影响首屏与离线游玩

## 联机对战

`online/` 是一个极小的 Node 服务，同时托管单文件应用与联机 API：

```bash
cd online
PORT=3000 node server.mjs
# 打开 http://127.0.0.1:3000/
```

- 传输：HTTP 长轮询（不用 WebSocket，避开代理的 upgrade 限制）
- 权威：服务端复用 `online/core`（与前端同一份规则内核）校验每一手
- 房间：4 位房间号，内存态，单房间 2 人，服务重启即失效

构建时 `scripts/build_webapp_bundle.py` 会把最新单文件与内核同步到 `online/`，避免两处不一致。
`online/public/` 与 `online/core/` 均为构建产物（不入库），首次 clone 后需先跑一次该脚本再启动服务：

```bash
python scripts/build_webapp_bundle.py
cd online && PORT=3000 node server.mjs
```

云同步为可选项：复制 `online/cloud-config.example.json` 为 `online/cloud-config.json` 并填入自己的
`resourceId` / `endpoint` / `publishableKey`。真实配置不入库；文件缺失时服务端不注入配置，
前端自动降级为纯离线游玩，联机与人机对战不受影响。

## 功能

- 四套规则档案：完整 / 经典 / 精简 / 传统象棋（9×10）
- 十四种棋子，含射、檑、甲、刺、楯、巡六种特色棋子
- 人机对战五档棋力（含大师）、双人同机、悔棋、提示、暂停、提和、认输、兵卒复活、全屏
- 走子动画、上一步标记、将军提醒、可行落点
- 复盘（逐手 / 播放 / 跳转）、棋谱导出与读取（`.xhgame`）、本地对局统计
- 残局训练：9 道走法教学 + 12 道引擎校验的一步杀，支持导入外部题库（JSON）
- 登场棋子：按类型同步增减双方棋子（主帅固定），可玩让子局
- 棋谱库：结束后自动保存最近 12 局，支持复盘、载入、删除
- AI 复盘：逐手评分（好棋/尚可/不够精确/失误/严重失误）与红方胜率曲线
- 棋子图谱：点亮任一棋子，展示它在本棋盘上的全部可达点
- 三种棋盘主题、三种棋子风格、中英双语
- 局面图导出（带落款，便于分享）
- 全部音效由 WebAudio 现场合成，不加载任何音频文件

## 已知边界

- 联机对战未包含在本静态版本中（旧 `web/` + FastAPI 版本仍支持）。
- 大师级（MCTS + 策略价值网络）未移植，最高档为 alpha-beta 深搜。
- 单文件构建下不注册 Service Worker，刷新后需要网络。

## 浏览器支持

Chrome / Edge 90+、Safari 15+、Firefox 90+。需要 Canvas 2D 与 WebAudio；
AI 线程优先使用 Blob Worker，不支持时自动回退到主线程。
