"""按客户端 IP 的滑动窗口限流（P0-1：跨版本丢失后按当前结构重建）。

为什么需要
----------
`/api/auth/register` / `/api/auth/login` / `/api/rooms` 是**不需要任何凭证**就能打
的写端点。没有限流，一个脚本可以反复试密码（login 的 401 与"用户不存在"是可区分的
时间/语义差），也可以灌垃圾房间把 `manager.rooms` 撑起来 —— 而房间每 5 秒广播一轮、
每轮都算一遍快照。

设计取舍（每条都是"为什么不是另一种写法"）
------------------------------------------
* **默认 0 = 关闭**：`XH_RATE_LIMIT_PER_MINUTE` 未设或为 0 时，中间件只做一次
  `int` 比较就原样放行。既有 900+ 条测试与本地开发都不受影响 —— 限流是**部署
  策略**，不该成为开发机上的行为。
* **只压写操作**（POST/PUT/PATCH/DELETE）：GET 是幂等读取，限制它会误伤
  `/api/rooms/{id}` 的快照轮询、`/api/health` 探活与静态资源。WebSocket 也不在
  此列（`scope["type"] == "websocket"` 直接放行）—— 长连接本身已由房间/token 约束。
* **纯 ASGI 中间件**，不是 `BaseHTTPMiddleware`：后者会把响应包成流、额外起 task，
  且在异常分组/contextvar 上有历史坑。这里只看 `method` 与 `client` 两个字段，
  根本不碰 body，纯 ASGI 更便宜也更可预测。
* **不信任 `X-Forwarded-For`**：取 `scope["client"][0]`（真实对端）。XFF 是客户端
  可自填的，信它等于"改个请求头就绕过限流"。当前 `deploy/` 是 uvicorn 直连、
  无 nginx，前提成立。**日后加反代必须同步改成"信任 N 跳"**，否则所有客户端共享
  代理 IP，变成对全站的整体限流（见下方 RISK）。
* **内存实现**：单进程 uvicorn 够用，不引入 redis。多 worker / 多副本时每个进程
  各算各的，实际阈值 = 进程数 × 配置值。
* **被拒的请求不占额度**：只有放行的请求才 `append` 时间戳，否则重试风暴会自己
  把窗口喂饱、永远解不开。

RISK（已知，未在此处解决）
------------------------
1. 反代后 `scope["client"]` 全是代理 IP → 全站被一起限流。届时需引入
   `XH_RATE_LIMIT_TRUSTED_HOPS` 并只信最后一跳。
2. 单进程内存：`--workers N` / 多副本时阈值放大 N 倍；重启即清零。
3. 这是**防止脚本刷**的粗粒度闸门，不是 DDoS 防护；真正的流量清洗在边缘。
4. **env 写错时是"静默退化"而非启动失败**（刻意的：一个可选安全旋钮不该成为能让
   生产挂掉的单点）。代价是"以为开了其实没开"。运维核对方法 —— 日志里非法值只会打印
   **一行** warning，直接按这两句文案搜即可：
     `XH_RATE_LIMIT_PER_MINUTE='abc' 不是整数，限流已关闭`
     `XH_RATE_LIMIT_PER_MINUTE='-5' 为负数，按 0（关闭）处理`
   搜不到 = 配置合法（或从未被读到）。想确认**生效值**而不看日志：连打 N+1 次写请求，
   第 N+1 次应返回 429 且带 `Retry-After`（`curl -i` 一眼可见）；GET 不受影响。
   注意 warning 每个非法值只打一次（`_WARNED_RAW`），日志轮转后可能已不在当前文件里。
"""

from __future__ import annotations

from collections import deque
import logging
import math
import os
import time

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

LOGGER = logging.getLogger(__name__)

ENV_VAR = "XH_RATE_LIMIT_PER_MINUTE"

#: 窗口长度。命名成"每分钟"是配置口径，实现是滑动窗口（见 `hit`）。
WINDOW_SECONDS = 60.0

#: 内存护栏：最多跟踪多少个客户端键。房间/请求都会带上不同 IP，无上限就是内存
#: 泄漏点。4096 个键 × 一个短 deque，量级在百 KB，够真实部署用。
MAX_TRACKED_CLIENTS = 4096

#: 只压写操作。GET/HEAD/OPTIONS 与 WebSocket 一律放行。
LIMITED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: 已经是 429 的路径，重复触发时不再刷日志（否则限流本身成了日志放大器）。
_WARNED_RAW: set[str] = set()


def configured_limit() -> int:
    """读 env，每次调用都读 —— 让运维改环境变量与测试用 monkeypatch 都能生效。

    非法值（`"abc"`、负数）**回落到 0（关闭）并只警告一次**：限流是一道附加闸门，
    配错了不该让服务起不来，但必须留下痕迹，否则"以为开了其实没开"。
    """
    raw = os.getenv(ENV_VAR)
    if raw is None or not raw.strip():
        return 0
    try:
        value = int(raw.strip())
    except ValueError:
        _warn_once(raw, "不是整数，限流已关闭")
        return 0
    if value < 0:
        _warn_once(raw, "为负数，按 0（关闭）处理")
        return 0
    return value


def _warn_once(raw: str, reason: str) -> None:
    if raw in _WARNED_RAW:
        return
    _WARNED_RAW.add(raw)
    LOGGER.warning("%s=%r %s", ENV_VAR, raw, reason)


class SlidingWindowLimiter:
    """每个键一个时间戳队列，窗口内计数。

    `hit()` 返回 `0` 表示放行，返回正数表示"还要等多少秒"（供 `Retry-After`）。
    单事件循环内是同步代码，读-改-写之间没有 await，所以不需要锁。
    """

    def __init__(self, window_seconds: float = WINDOW_SECONDS,
                 max_keys: int = MAX_TRACKED_CLIENTS) -> None:
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str, limit: int, now: float | None = None) -> int:
        if limit <= 0:
            return 0
        stamp = time.monotonic() if now is None else now
        hits = self._hits.get(key)
        if hits is None:
            self._enforce_capacity(stamp, keep=key)
            hits = self._hits[key] = deque()
        cutoff = stamp - self.window_seconds
        # 队列按时间升序，弹出窗口外的旧记录即完成滑动。
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            # 最早那条过期时才能腾出名额。
            return max(1, math.ceil(hits[0] + self.window_seconds - stamp))
        hits.append(stamp)
        return 0

    def _enforce_capacity(self, now: float, keep: str) -> None:
        if len(self._hits) < self.max_keys:
            return
        cutoff = now - self.window_seconds
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
            del self._hits[key]
        while len(self._hits) >= self.max_keys:
            victim = next((k for k in self._hits if k != keep), None)
            if victim is None:          # 只剩要保留的这个键
                break
            del self._hits[victim]

    def reset(self) -> None:
        """清空全部计数（测试用；进程内重启等价语义）。"""
        self._hits.clear()

    def tracked(self) -> int:
        return len(self._hits)


#: 进程级单例。中间件持有它，测试可以直接 `reset()` 而不必重建 app。
LIMITER = SlidingWindowLimiter()


def client_key(scope: Scope) -> str:
    """限流键。取真实对端，**不看** X-Forwarded-For（理由见模块 docstring）。"""
    client = scope.get("client")
    if not client:
        return "unknown"
    host = client[0] if isinstance(client, (tuple, list)) else str(client)
    return host or "unknown"


class RateLimitMiddleware:
    """`add_middleware(RateLimitMiddleware, limiter=LIMITER)` 挂载。

    `limiter` 可注入，是为了让测试能塞一个受控时钟/独立计数器，而不必动全局。
    """

    def __init__(self, app: ASGIApp, limiter: SlidingWindowLimiter | None = None) -> None:
        self.app = app
        self.limiter = LIMITER if limiter is None else limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or scope.get("method") not in LIMITED_METHODS:
            await self.app(scope, receive, send)
            return
        limit = configured_limit()
        if limit <= 0:                   # 默认路径：未配置，零成本放行
            await self.app(scope, receive, send)
            return
        retry_after = self.limiter.hit(client_key(scope), limit)
        if not retry_after:
            await self.app(scope, receive, send)
            return
        # 错误体与项目既有格式一致：`{"detail": "..."}`。前端 `web/js/app.js` 的
        # `api()` 就是读 `data.detail` 弹提示的，多带两个字段不破坏解析。
        response = JSONResponse(
            status_code=429,
            content={
                "detail": f"请求过于频繁（上限 {limit} 次/分钟），请 {retry_after} 秒后重试",
                "retryAfter": retry_after,
                "limitPerMinute": limit,
            },
            headers={"Retry-After": str(retry_after)},
        )
        await response(scope, receive, send)
