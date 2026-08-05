# Docker 部署

```bash
cd xionghan-chess-next
cp deploy/.env.example deploy/.env
docker compose --env-file deploy/.env -f deploy/docker-compose.yml build
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d
docker compose --env-file deploy/.env -f deploy/docker-compose.yml logs -f
```

默认访问 `http://服务器IP:8000`。停止：

```bash
docker compose --env-file deploy/.env -f deploy/docker-compose.yml down
```

公网部署需开放 TCP 端口，反向代理需允许 WebSocket Upgrade。当前为单实例内存房间方案；多副本
部署前需增加 Redis 房间存储和跨进程广播。

`AI_DEFAULT_DIFFICULTY` 设置默认难度，`AI_TIME_SCALE` 按比例调整各档思考时间，
`MAX_ONLINE_GAMES` 限制同时存在的房间数量。
