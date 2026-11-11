# v1.5.0 QA 报告

## 验收范围

- 内置头像资源尺寸、命名与三端打包路径。
- 账号头像标识校验、资料更新、房间快照传递。
- Web、桌面与 Android 离线头像选择、持久化和回退显示。
- v1.5.0 版本号、桌面/Web/APK 构建和交付校验。

## 暂缓项

- MCTS 默认 AI 档位接入。
- 自博弈与神经网络训练流水线。
- 用户任意本地图片上传、裁剪和服务端文件托管。

## 执行结果

- `pytest -q`: 94 passed，0 failed，1 条 Starlette/httpx 弃用警告。
- Web/Android JavaScript 语法、Python compileall、locale JSON 和 `git diff --check`: 通过。
- Windows PyInstaller 1.5.0: 构建成功。
- Web 1.5.0 ZIP: 构建成功，包含 9 张头像和共享头像模块。
- Android Release 1.5.0: 0 错误，保留既有 API/弃用警告；APK 包含 9 张离线头像。
- 生产版本号扫描：`src/web/android/packaging/deploy` 无 1.4.0 或 2.0.1 残留。
- Android 离线 `no_progress_draw`: 新增阈值、遇吃子/兵卒清零及结果原因回归守卫。

## 验收结论

未发现阻断级缺陷，满足 v1.5.0 交付条件。旧账号、外部头像 URL 和无头像回退逻辑保持兼容。
