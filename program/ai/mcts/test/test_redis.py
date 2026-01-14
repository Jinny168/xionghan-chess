import redis

try:
    # 初始化Redis连接（严格匹配服务端配置）
    redis_client = redis.Redis(
        host='192.168.240.136',  # 虚拟机准确IP
        port=6379,  # 整数类型端口，不可加引号
        db=1,
        decode_responses=True,  # 自动解码bytes为字符串
        socket_timeout=10  # 10秒连接超时，避免无限等待
    )

    # 测试连接与数据读写
    print("Redis连接状态：", redis_client.ping())
    redis_client.set("chess_project_key", "redis_connection_success")
    print("测试数据读取：", redis_client.get("chess_project_key"))

except Exception as e:
    print("连接失败详情：", str(e))