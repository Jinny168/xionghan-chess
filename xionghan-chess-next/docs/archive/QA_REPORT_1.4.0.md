# v1.4.0 QA 报告

## 执行结果

- `pytest -q`: **91 passed**, 0 failed，1 条 Starlette/httpx 弃用警告。
- Web/Android JavaScript `node --check`: 通过。
- `locales/zh-CN.json`、`locales/en.json`: JSON 解析通过。
- `python -m compileall -q src`: 通过。
- `git diff --check`: 通过。
- Android Release `dotnet build android/XionghanChessAndroid.csproj -c Release -f net9.0-android`: 0 错误，22 条非阻断兼容性/弃用警告。

## 回归覆盖

规则校验、AI 博弈、棋谱导入导出、服务 API、WebSocket 协议、账号和云同步、主题与语言切换、Android 离线双页导航、重复选择音效防护、残局训练状态保留、页面分层跳转均已纳入回归用例。

## 已完成修复

- Android 离线端新增 `welcome.html`，设置/模式选择与棋局页分离；返回键从棋局页返回欢迎页。
- Android 选择同一棋子不重复播放选择音效；残局训练不会清空题目状态。
- Web/Desktop 新增并接入主要界面文案 i18n。
- 所有交付版本显示统一为 1.4.0。
- `android/bin`、`android/obj` 已从 Git 索引移除，构建产物由 `.gitignore` 排除。
- 旧 `.fen`/JSON 包装棋谱可在桌面、Web 与 Android 离线端迁移导入；Android 载入终局存档不再重复累计统计；在线重开改为双方确认；统计增加时长、最快胜局、连胜和分色维度。
- 后续迭代已加入纯 MCTS UCB1 推理模块、桌面/Web/Android 轨迹动画、三端将军提示、分场景挑衅语料和 Web 默认头像渲染。
- 本阶段完成 AI 场景化自动挑衅：开局、将军、胜利、失败事件通过聊天协议发送，并提供 Web/桌面独立开关、有限历史和事件去重。
- 账号新增可选 `avatarUrl` 字段与资料更新接口；旧 SQLite 数据库启动时自动迁移。Web 可编辑头像 URL，房间快照向 Web、Android 联机页和桌面联机请求传递头像资料。

## 残留风险

- Android 构建仍有 API 可用性与旧属性警告，不阻断发布，建议后续按 Android API 分支清理。
- 生产 APK 签名仍依赖项目 keystore；本地构建产物为可安装 Release APK。
- Docker 镜像构建需在安装 Docker CLI 的 CI/部署机执行。

## 验收结论

当前版本不存在已知阻断级 Bug，满足 v1.4.0 交付前自动化验收条件。MCTS 默认档位替换与自博弈/神经网络训练流水线按本阶段约束暂缓；头像文件上传、本地裁剪和 Android 离线身份系统仍属于后续范围。
