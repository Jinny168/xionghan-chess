"""P0-1 断言：按 IP 的限流中间件必须**存在且行为符合语义**。

这条护栏的由来值得写下来：限流在 1.6.0 修过（`AUDIT_v1.6.0_reaudit.md:156`，
`service/app.py:59-77`），1.7.x 重构时整段被删，而**没有任何测试红过** ——
于是它安静地消失了两个版本，直到人工审计用 `grep` 才发现。所以这里断的不只是
"逻辑正确"，还有"它确实挂在 app 上"（反射 `app.user_middleware`）。**谁再删掉它，
这个文件立刻红。**

覆盖：
1. 中间件已挂载（反射 + 行为双证）；
2. 阈值=2 → 第 3 次 POST 429；阈值=0 / 未设 → 连发 10 次不 429；
3. GET 永不限流（幂等读 + 探活，误伤代价高）；
4. 429 响应体能被前端 `web/js/app.js` 的 `api()` 解析（读 `data.detail`）；
5. 被拒请求不占额度、按 IP 隔离、窗口到期释放、非法 env 值退化为关闭。
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from xionghan_chess.service.app import app  # noqa: E402
from xionghan_chess.service.ratelimit import (  # noqa: E402
    ENV_VAR,
    LIMITED_METHODS,
    LIMITER,
    MAX_TRACKED_CLIENTS,
    RateLimitMiddleware,
    SlidingWindowLimiter,
    configured_limit,
)

ROOM_BODY = {"profileId": "web", "mode": "local", "playerName": "限流测试"}


@pytest.fixture(autouse=True)
def clean_state(monkeypatch: pytest.MonkeyPatch):
    """每个用例都从「无 env、计数器已清空」出发。

    计数器是进程级单例（`LIMITER`），不清就会串味：上一条用例把 `testclient` 的
    窗口喂满，下一条用例一上来就 429，看着像中间件坏了。
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    LIMITER.reset()
    yield
    LIMITER.reset()


def _post_room(client: TestClient):
    return client.post("/api/rooms", json=ROOM_BODY)


# ---------------------------------------------------------------- 1. 挂载

def test_middleware_is_mounted_on_app() -> None:
    """反射断言：`add_middleware` 在 import 期执行过，且注入的是进程级计数器。

    为什么用反射而不是只看行为：行为断言只能证明"某处会 429"，删掉中间件后若有人
    在路由里补一段限流也会绿；这里钉的是**中间件这一层**本身在栈里。
    """
    mounted = [m for m in app.user_middleware if m.cls is RateLimitMiddleware]
    assert len(mounted) == 1, f"限流中间件应恰好挂载一次，实际 {len(mounted)} 次：{app.user_middleware}"
    assert mounted[0].kwargs["limiter"] is LIMITER, "中间件应持有进程级 LIMITER（测试才能 reset）"


def test_limited_methods_are_writes_only() -> None:
    """方法集合本身也是契约：GET/HEAD/OPTIONS 不在其中。"""
    assert LIMITED_METHODS == frozenset({"POST", "PUT", "PATCH", "DELETE"})
    for method in ("GET", "HEAD", "OPTIONS"):
        assert method not in LIMITED_METHODS


# ---------------------------------------------------------------- 2. 阈值语义

def test_third_post_is_rejected_when_limit_is_two(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, "2")
    client = TestClient(app)
    first, second = _post_room(client), _post_room(client)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    third = _post_room(client)
    assert third.status_code == 429, (third.status_code, third.text)
    body = third.json()
    assert isinstance(body["detail"], str) and body["detail"]
    assert body["limitPerMinute"] == 2
    assert isinstance(body["retryAfter"], int) and 1 <= body["retryAfter"] <= 60
    assert third.headers["Retry-After"] == str(body["retryAfter"])


def test_threshold_zero_disables_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """`XH_RATE_LIMIT_PER_MINUTE=0` = 关闭。这是让 900+ 条既有测试不受影响的开关。"""
    monkeypatch.setenv(ENV_VAR, "0")
    client = TestClient(app)
    codes = [_post_room(client).status_code for _ in range(10)]
    assert codes == [200] * 10, codes


def test_unset_env_disables_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """默认（变量不存在）也必须关闭，而不是"当作某个默认阈值"。"""
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert configured_limit() == 0
    client = TestClient(app)
    codes = [_post_room(client).status_code for _ in range(10)]
    assert 429 not in codes, codes


def test_invalid_env_value_disables_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """`abc` 不该让服务起不来，也不该变成 1 次/分钟这种"神秘严格"。"""
    monkeypatch.setenv(ENV_VAR, "abc")
    assert configured_limit() == 0
    client = TestClient(app)
    codes = [_post_room(client).status_code for _ in range(10)]
    assert 429 not in codes, codes


# ---------------------------------------------------------------- 3. GET 不限

def test_get_is_never_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    """阈值=1 时连打 10 次 GET `/api/health` 仍应全 200；随后写操作才受限。"""
    monkeypatch.setenv(ENV_VAR, "1")
    client = TestClient(app)
    assert [client.get("/api/health").status_code for _ in range(10)] == [200] * 10
    assert _post_room(client).status_code == 200
    assert _post_room(client).status_code == 429


# ---------------------------------------------------------------- 4. 前端可解析

def test_429_body_is_parseable_by_web_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """复刻 `web/js/app.js::api()` 的解析路径：`response.json().detail` 直接当提示语。

    前端那段是 `if(!response.ok) throw new Error(data.detail || t('error.request_failed'))`，
    所以 429 **必须是 JSON 且带非空 detail**（不是纯文本、不是空体）。
    """
    monkeypatch.setenv(ENV_VAR, "1")
    client = TestClient(app)
    _post_room(client)
    response = _post_room(client)
    assert response.status_code == 429
    assert response.headers["content-type"].startswith("application/json")
    data = json.loads(response.text)          # 与 fetch().json() 等价
    assert data["detail"] == response.json()["detail"]
    assert data["detail"].strip(), "detail 为空会让前端只显示兜底文案"
    assert "频繁" in data["detail"], data["detail"]


# ---------------------------------------------------------------- 5. 边界语义

def test_gate_is_in_middleware_not_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    """业务失败（400）也计数 —— 证明闸门在路由之前，而不是某个端点里。

    这正是限流要拦的场景：刷 `/api/auth/login` 的失败请求也是最该被限的请求。
    """
    monkeypatch.setenv(ENV_VAR, "2")
    client = TestClient(app)
    bad = {"profileId": "web", "mode": "nonsense", "playerName": "x"}
    assert client.post("/api/rooms", json=bad).status_code == 400
    assert client.post("/api/rooms", json=bad).status_code == 400
    assert client.post("/api/rooms", json=bad).status_code == 429


def test_rejected_request_does_not_extend_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """被拒的那次不能自己喂饱窗口：阈值=1 时第 2、3 次都 429，且等待秒数不增长。

    如果实现里"先 append 再判断"，重试风暴会不断刷新最早时间戳，窗口永远滑不出去
    —— 用户被永久锁死。这条钉子钉的就是这个。
    """
    monkeypatch.setenv(ENV_VAR, "1")
    client = TestClient(app)
    assert _post_room(client).status_code == 200
    second = _post_room(client)
    third = _post_room(client)
    assert [second.status_code, third.status_code] == [429, 429]
    assert third.json()["retryAfter"] <= second.json()["retryAfter"], "等待时间不应因重试而变长"


def test_limit_is_per_client_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 打满后 B 不受影响 —— 否则一个人刷就能把全站闸死。"""
    monkeypatch.setenv(ENV_VAR, "1")
    alice = TestClient(app, client=("10.0.0.1", 50000))
    bob = TestClient(app, client=("10.0.0.2", 50001))
    assert _post_room(alice).status_code == 200
    assert _post_room(alice).status_code == 429
    assert _post_room(bob).status_code == 200, "另一个 IP 应保有自己的一份额度"


def test_sliding_window_releases_slot_after_window_expires() -> None:
    """直接对限流器注入时钟，验证"滑动"而非"整分钟重置"。

    时间线（阈值 2、窗口 60s）：
    t=1000 放行[1] → t=1030 放行[2] → t=1050 拒（1000 那条要到 1060 才过期，等 10s）
    → t=1060.5 放行（1000 出窗，1030 还在）→ t=1061 拒（1030 要到 1090 才过期，等 29s）
    → t=1090.5 放行。若是"整分钟重置"的桶实现，这组时刻的答案会完全不同。
    """
    limiter = SlidingWindowLimiter(window_seconds=60.0)
    assert limiter.hit("ip", 2, now=1000.0) == 0
    assert limiter.hit("ip", 2, now=1030.0) == 0
    blocked = limiter.hit("ip", 2, now=1050.0)
    assert blocked == 10, f"最早一条在 t=1060 过期，1050 时应还等 10 秒，实际 {blocked}"
    assert limiter.hit("ip", 2, now=1060.5) == 0, "第一条出窗后应放出名额"
    assert limiter.hit("ip", 2, now=1061.0) == 29, "t=1030 那条要到 t=1090 才出窗"
    assert limiter.hit("ip", 2, now=1090.5) == 0


def test_limiter_memory_is_bounded() -> None:
    """无上限的 `dict[ip]` 就是一个内存泄漏点：伪造来源打进来即可撑爆。"""
    limiter = SlidingWindowLimiter(window_seconds=60.0, max_keys=8)
    for i in range(200):
        limiter.hit(f"10.0.0.{i}", 5, now=1000.0)
    assert limiter.tracked() <= 8, limiter.tracked()
    assert limiter.tracked() <= MAX_TRACKED_CLIENTS
