"""发布后回读：确认线上真的跑的是这一版。

## 为什么要它

2026-11-03 出过一次「发了但没发出去」：部署调用返回空，我没回读就继续往下写，
线上实际还停在上一版。**部署工具说"成功"不等于线上换了版本**，只有回读能证明。

## 用法

    python scripts/verify_deploy.py                 # 核对默认站点
    python scripts/verify_deploy.py --url https://...
    python scripts/verify_deploy.py --expect 1.9.2  # 指定期望版本（默认取 __version__）

退出码：0 全部一致；1 有不一致（可写在发布步骤的最后一步，非 0 就说明这次没发上去）。

## 检查三项

1. `GET /api/version` 返回的版本 == 本地 `__version__`
2. 首页里的缓存戳 `?v=<版本>` 全部等于该版本（否则浏览器还在用旧 JS/CSS）
3. 首页里不残留**更早**的版本号字符串（防"改了一半"）

网络不可达时给 `NETWORK` 结论、退出码 2 —— 与"版本不对"区分开，
免得把断网误判成发版失败而反复重试。
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess import __version__  # noqa: E402

DEFAULT_URL = "https://xionghan-chess-40904.app.workbuddy.host/?sharecode=OFRPAI5BC4"


def _opener() -> urllib.request.OpenerDirector:
    """带 cookie 的 opener —— 站点要先访问带 `?sharecode=` 的地址拿到会话 cookie，
    否则后续请求一律 403（这一点吃过亏：裸 urllib 直接 403）。"""
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _get(opener: urllib.request.OpenerDirector, url: str, timeout: float = 20.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "xionghan-verify-deploy"})
    with opener.open(request, timeout=timeout) as response:  # noqa: S310
        return response.read().decode("utf-8", "replace")


def check(url: str = DEFAULT_URL, expect: str | None = None) -> dict:
    """返回 `{ok, network, version, busters, stale, messages}`。不抛异常。"""
    expect = expect or __version__
    base = url.split("?")[0].rstrip("/")
    result: dict = {"ok": False, "network": False, "version": None, "busters": set(), "stale": set(), "messages": []}

    opener = _opener()
    try:
        _get(opener, url)  # 先用 sharecode 建立会话
        payload = json.loads(_get(opener, f"{base}/api/version"))
        result["version"] = payload.get("version")
        html = _get(opener, f"{base}/")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        result["network"] = True
        result["messages"].append(f"网络不可达或响应异常：{error}")
        return result

    result["busters"] = set(re.findall(r"\?v=([0-9]+\.[0-9]+\.[0-9]+)", html))
    result["stale"] = {v for v in result["busters"] if v != expect}
    # 页面里出现比期望更旧的版本号 => 只改了部分文件
    for found in set(re.findall(r"\b(\d+\.\d+\.\d+)\b", html)):
        if found != expect and found < expect:
            result["stale"].add(found)

    problems = []
    if result["version"] != expect:
        problems.append(f"/api/version 是 {result['version']}，期望 {expect}")
    if result["busters"] != {expect}:
        problems.append(f"缓存戳是 {sorted(result['busters'])}，期望全部为 {expect}")
    if any(isinstance(item, str) and item.count(".") == 2 for item in result["stale"]):
        problems.append(f"页面残留旧版本号：{sorted(result['stale'])}")

    result["messages"] = problems
    result["ok"] = not problems
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="回读线上版本，确认发布真的生效")
    parser.add_argument("--url", default=DEFAULT_URL, help="站点地址（可带 sharecode）")
    parser.add_argument("--expect", default=None, help="期望版本，默认取本地 __version__")
    args = parser.parse_args()

    expect = args.expect or __version__
    result = check(args.url, expect)
    if result["network"]:
        print(f"NETWORK  无法访问 {args.url}")
        for message in result["messages"]:
            print(f"         {message}")
        return 2
    if result["ok"]:
        print(f"OK       线上版本 {result['version']}，缓存戳 {sorted(result['busters'])}")
        return 0
    print(f"MISMATCH 期望 {expect}，实际 {result['version']}")
    for message in result["messages"]:
        print(f"         {message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
