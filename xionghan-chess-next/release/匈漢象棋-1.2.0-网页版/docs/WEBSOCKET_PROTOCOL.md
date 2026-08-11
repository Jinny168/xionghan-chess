# WebSocket 协议

连接地址：`/ws/{roomId}?token={reconnectToken}`，协议版本为 `1`。

```json
{"type":"move","roomId":"AB12CD","revision":8,"protocolVersion":1,"payload":{"from":{"row":8,"col":0},"to":{"row":7,"col":0},"promotion":null}}
```

客户端消息：`move`、`resign`、`draw_offer`、`draw_response`、`undo_request`、
`undo_response`、`resurrect`、`restart`、`chat`、`ping`。服务器返回 `state`、`chat` 或 `error`。

## 聊天与快捷短语

聊天使用 `chat` 消息，不改变棋局 `revision`，因此不会造成走棋状态冲突。文本去除首尾空白后
不能为空，最长 80 个字符。挑衅属于快捷短语的一种，不触发棋盘动画。

```json
{"type":"chat","roomId":"AB12CD","revision":8,"protocolVersion":1,"payload":{"text":"这一步，你可要想好了！","quick":true}}
```

服务器广播：

```json
{"type":"chat","roomId":"AB12CD","revision":8,"payload":{"color":"red","sender":"玩家","text":"这一步，你可要想好了！","quick":true,"timestamp":1785811200000}}
```
