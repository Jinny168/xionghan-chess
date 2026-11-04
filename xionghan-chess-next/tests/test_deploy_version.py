"""发布后回读的守卫：检查器本身要准，线上核对要能一键跑。

两类用例：
1. **离线单测**（总是跑）：用假的响应喂给 `check()`，确认"版本不对 / 缓存戳不对"
   真的会被判红 —— 检查器自己判错，比没有检查器更糟。
2. **线上核对**（默认跳过）：设 `XIONGHAN_VERIFY_DEPLOY=1` 才执行，避免日常门禁依赖网络。
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

from xionghan_chess import __version__

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_deploy.py"


def _module():
    spec = importlib.util.spec_from_file_location("verify_deploy_for_tests", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_get(version: str, buster: str):
    def _get(_opener, url: str, timeout: float = 20.0) -> str:  # noqa: ARG001
        if url.endswith("/api/version"):
            return json.dumps({"version": version})
        return f'<link href="/css/app.css?v={buster}"><script src="/js/app.js?v={buster}"></script>'
    return _get


def test_checker_passes_when_everything_matches(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(module, "_get", _fake_get(__version__, __version__))
    result = module.check("https://example.test/?sharecode=x")
    assert result["ok"], result["messages"]


def test_checker_catches_a_stale_deployment(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(module, "_get", _fake_get("0.0.1", "0.0.1"))
    result = module.check("https://example.test/?sharecode=x")
    assert not result["ok"]
    assert any("/api/version" in message for message in result["messages"])


def test_checker_catches_stale_cache_busters(monkeypatch) -> None:
    """版本对了但缓存戳没跟上 —— 浏览器会继续用旧 JS，和没发一样。"""
    module = _module()
    monkeypatch.setattr(module, "_get", _fake_get(__version__, "0.0.1"))
    result = module.check("https://example.test/?sharecode=x")
    assert not result["ok"]
    assert any("缓存戳" in message for message in result["messages"])


@pytest.mark.deploy
def test_live_site_is_running_this_version() -> None:
    if os.environ.get("XIONGHAN_VERIFY_DEPLOY") != "1":
        pytest.skip("线上核对需显式开启：XIONGHAN_VERIFY_DEPLOY=1")
    module = _module()
    result = module.check(os.environ.get("XIONGHAN_DEPLOY_URL", module.DEFAULT_URL))
    assert not result["network"], f"网络不可达：{result['messages']}"
    assert result["ok"], "；".join(result["messages"])
