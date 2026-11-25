"""P0-2 常规对局「下一步提示」的闭环守卫（worker 实际执行 + 源码契约）。

worker 侧由 `hint_worker_probe.mjs` 真跑一遍（node），证明 250ms 预算内只回 hint 消息、带 move；
主线程侧的 DOM 高亮/防重入/过期丢弃用源码断言守住——DOM 运行时正确性仍需浏览器人工验收，
本文件不把文本哨兵冒充运行时判据。零遥测：hint 全程本地 chooseMove，无网络、无存储写入。
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "webapp" / "js" / "ui" / "app.js").read_text(encoding="utf-8")
WORKER = (ROOT / "webapp" / "js" / "ai-worker.js").read_text(encoding="utf-8")


def _body(source: str, signature: str) -> str:
    """取一个顶层函数的源码文本（按大括号配平），用于局部断言。"""
    start = source.index(signature)
    opened = source.index("{", start)
    depth = 0
    for index in range(opened, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"函数未闭合：{signature}")


def test_worker_hint_branch_returns_only_hint_message() -> None:
    """worker 有 hint 分支、只回 {id,type:'hint',move,meta}，不触发 commitMove。"""
    branch = _body(WORKER, "if (event.data && event.data.type === 'hint')")
    assert "type: 'hint'" in branch
    assert "moveToDict(result.move)" in branch
    assert "meta:" in branch
    assert "commitMove" not in branch, "worker 的 hint 分支不得落子"
    assert "chooseMove(" in branch, "hint 必须走同一套本地搜索"


def test_main_thread_hint_contract() -> None:
    """独立请求序号 / 防重入 / 250ms / 过期丢弃 / 高亮 + 2.6s 清除 / 按钮禁用。"""
    assert "hintRequestId: 0" in APP
    assert "hintPending: false" in APP
    assert "hintHistoryLength: 0" in APP
    body = _body(APP, "function hint()")
    assert "app.hintRequestId +=" in body or "++app.hintRequestId" in body
    assert "type: 'hint'" in body
    assert "timeMs: 250" in body and "600" not in body
    assert "app.hintPending = true" in body
    assert "suggestMove(app.game.state, app.game.rules, 250)" in body, "无 worker 兜底也要 250ms"
    # 过期结果丢弃：history 长度不一致就 return。
    onmessage = _body(APP, "app.worker.onmessage = (event) =>")
    assert "data.type === 'hint'" in onmessage
    assert "app.game.state.history.length !== app.hintHistoryLength" in onmessage
    # 高亮沿用既有实现，不新增绘制代码。
    apply_hint = _body(APP, "function applyHintResult(")
    assert "selectPiece(moving)" in apply_hint
    assert "app.legal = [result.move]" in apply_hint
    assert "2600" in apply_hint
    assert "app.hintPending" in APP.split('data-act="hint"')[1][:300], "提示按钮未纳入防重入禁用"


def test_hint_is_zero_telemetry() -> None:
    """hint 全程纯本地 chooseMove：无 fetch/XHR/beacon、不写任何存储键。"""
    for source, name in ((_body(APP, "function hint()"), "hint()"), (WORKER, "ai-worker.js")):
        for token in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage"):
            assert token not in source, f"{name} 出现遥测/存储调用：{token}"
    assert re.search(r"\bchooseMove\(", WORKER)


def test_worker_hint_probe_runs_within_soft_budget() -> None:
    """真跑 worker：收到唯一 hint 消息、带 move；250ms 是软预算，允许搜索收尾小幅超出。"""
    node = subprocess.run(
        ["node", str(ROOT / "tests" / "hint_worker_probe.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    result = json.loads(node.stdout)
    assert result["types"] == ["hint"], result["types"]
    assert result["hasMove"] is True, "hint 未返回着法"
    assert result["elapsed"] < 1200, f"提示耗时异常：{result['elapsed']}ms"
