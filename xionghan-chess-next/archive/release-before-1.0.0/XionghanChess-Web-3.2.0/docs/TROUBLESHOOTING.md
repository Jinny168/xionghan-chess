# 常见问题

## `python` 没有输出或打开商店

使用 `py -3.11` 创建虚拟环境，后续直接调用 `.venv\Scripts\python.exe`。

## 桌面端缺少 PySide6

执行 `.\.venv\Scripts\python.exe -m pip install -e ".[desktop]"`。

## 浏览器无法连接 WebSocket

确认防火墙开放端口；反向代理必须转发 `Upgrade` 和 `Connection` 请求头。

## 两端棋盘版本不一致

服务器会拒绝旧 `revision` 的走棋并返回最新快照，不要绕过协议直接改棋盘。

## AI 高级档响应慢

高级档默认最多思考约 7 秒，可在界面降低难度。

## Docker 重启后房间消失

当前是单实例内存房间。需要重启持久化或多实例时应增加 Redis 存储适配器。

