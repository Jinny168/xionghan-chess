"""G2c：异步链路的回调**到底有没有到达**（真实事件循环 + 真线程池）。

## 挡的是什么

`_request_json_async` 把阻塞 HTTP 丢进 `QThreadPool`，结果经 `signals.finished/failed`
回到 GUI 线程。但 PySide6 里连到 **functor**（lambda / 局部闭包 / 普通函数）的连接，
其注册挂在 **sender 的 Python 侧**：`QRunnable` 的 Python 包装被线程池丢弃后，注册随之
消失 —— 不报错、不回调、没有任何日志。

结果是四条链路**成对失效**：建了房不进房、加了房不进房、检查更新点了没反应、
网络失败连个提示都没有。用户视角是「点了按钮，什么都没发生」，比崩溃更难查。

## 为什么必须是真事件循环 + 真线程池

- 直接调 `worker.run()` 再 `processEvents()`：注册还没被回收，测不出问题；
- mock 掉 `QThreadPool.start`（改成同步执行）：同上，等于把要测的时序假设掉了。

所以本文件用**真的 `QThreadPool.globalInstance()`** + 真的嵌套 `QEventLoop`，
只打桩最外层的网络 IO（`workers.http_json_blocking`）——那是唯一不该在测试里真实发生的事。

## 判据

修复前：① ② ③ 与 ④ 的「回调抛异常」分支全红（回调不到达）。
修复后：回调到达、`_pending_http` 排空、用户回调抛异常也不影响清理。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="异步回调挂在真实窗口与真线程池上")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui import workers as workers_mod  # noqa: E402

#: 一轮等待的上限。真线程池 + 打桩 IO 通常 50ms 内回来，留 4s 只是给慢 CI 兜底；
#: 修复前这条路径是**永远**不回来，所以超时长度不影响红/绿的判定。
SPIN_TIMEOUT_MS = 4000


def _spin(predicate, timeout_ms: int = SPIN_TIMEOUT_MS) -> bool:
    """跑**真** Qt 事件循环，直到 `predicate()` 为真或超时。

    不用 `processEvents()` 而是嵌套 `QEventLoop`：跨线程信号走 queued connection，
    需要一个真正在跑的事件循环来派发（这正是线上代码的运行条件）。
    """
    if predicate():
        return True
    loop = QEventLoop()
    ticker = QTimer()
    ticker.setInterval(10)

    def _tick() -> None:
        if predicate():
            loop.quit()

    ticker.timeout.connect(_tick)
    ticker.start()
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    ticker.stop()
    return bool(predicate())


class BoxRecorder:
    """替代 `QMessageBox`：记下弹框调用，**不阻塞**测试。

    测的是"回调到没到"，不是"框长什么样"。真框会 `exec()` 挂住整个用例。
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def information(self, parent, title: str, text: str, *args, **kwargs) -> None:  # noqa: ANN001
        self.calls.append(("information", title, text))

    def warning(self, parent, title: str, text: str, *args, **kwargs) -> None:  # noqa: ANN001
        self.calls.append(("warning", title, text))

    def critical(self, parent, title: str, text: str, *args, **kwargs) -> None:  # noqa: ANN001
        self.calls.append(("critical", title, text))


class InputRecorder:
    """替代 `QInputDialog`：`getText` 直接返回预设值。"""

    def __init__(self, text: str = "ROOM1", ok: bool = True) -> None:
        self.text = text
        self.ok = ok

    def getText(self, *args, **kwargs):  # noqa: ANN001, N802 - Qt 命名
        return self.text, self.ok

    def getItem(self, *args, **kwargs):  # noqa: ANN001, N802 - Qt 命名
        return self.text, self.ok


def _stub_reply(**overrides):
    """`/api/rooms` 成功响应的最小形状（`open_network` 只用 roomId/token/snapshot）。"""
    data = {"roomId": "ABCD", "token": "tok", "snapshot": {"revision": 1}}
    data.update(overrides)
    return lambda url, payload=None, method="GET", token="": data


def _offline(url, payload=None, method="GET", token=""):
    """模拟服务不可达：`HttpWorker.run` 会把它转成 `signals.failed`。"""
    raise OSError("stub offline")


def _pending(window) -> list[object]:
    """在飞的 HTTP worker 集合。

    **修复前这个属性不存在**，`getattr` 返回空 —— 泄漏断言在红阶段是空跑的，
    这是刻意的：这个 bug 本身就是"根本没有登记表"，无从泄漏检测。
    绿阶段它才变成真断言（见 test_pending_requests_never_leak）。
    """
    return list(getattr(window, "_pending_http", []))


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(monkeypatch: pytest.MonkeyPatch, tmp_path, qt_app: QApplication):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    theme.load_bundled_fonts()
    win = appmod.MainWindow()
    win.show()
    qt_app.processEvents()
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


def test_create_online_callback_reaches_gui(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """建房成功 → 真的进房 + 真的弹「房间已创建」。

    修复前：`_created` 是函数体内定义的局部函数（functor），连接注册随 worker 包装
    一起消失 → `open_network` 一次不调、弹框 0 次。玩家看到的是按钮没反应。
    """
    box = BoxRecorder()
    monkeypatch.setattr(appmod, "QMessageBox", box)
    monkeypatch.setattr(window, "server_base", lambda: "http://stub.invalid")
    monkeypatch.setattr(workers_mod, "http_json_blocking", _stub_reply())

    opened: list[tuple[str, object]] = []
    monkeypatch.setattr(
        window, "open_network", lambda base, data, spectator=False: opened.append((base, data))
    )

    window.create_online()
    arrived = _spin(lambda: bool(opened) and bool(box.calls))

    assert arrived, (
        "建房回调在真实事件循环里丢了：open_network 调用 "
        f"{len(opened)} 次、弹框 {len(box.calls)} 次（期望各 1 次）"
    )
    assert opened[0][0] == "http://stub.invalid"
    assert opened[0][1]["roomId"] == "ABCD"
    assert box.calls[0][0] == "information"
    assert "ABCD" in box.calls[0][2], "房间号没进提示文案，玩家拿不到房号"
    assert _pending(window) == [], "请求已落地，登记表里还留着 worker"


def test_join_online_callback_reaches_gui(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """加房成功 → 真的进房。

    与建房同型（`_joined` 也是局部函数），但**单独钉一条**：两条入口各自失效、
    也各自可能被单独改坏，合并成一条断言就会互相掩护。
    """
    box = BoxRecorder()
    monkeypatch.setattr(appmod, "QMessageBox", box)
    monkeypatch.setattr(appmod, "QInputDialog", InputRecorder("ROOM1"))
    monkeypatch.setattr(window, "server_base", lambda: "http://stub.invalid")
    monkeypatch.setattr(workers_mod, "http_json_blocking", _stub_reply())

    opened: list[tuple[str, object]] = []
    monkeypatch.setattr(
        window, "open_network", lambda base, data, spectator=False: opened.append((base, data))
    )

    window.join_online()
    arrived = _spin(lambda: bool(opened))

    assert arrived, "加房回调在真实事件循环里丢了：open_network 一次都没被调用"
    assert opened[0][1]["roomId"] == "ABCD"
    assert _pending(window) == [], "请求已落地，登记表里还留着 worker"


def test_failure_callbacks_reach_gui(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """失败路径的两条分支都要能到。

    分支 A：调用方**给了** `on_error`（`check_updates` 的 `failed` 是局部函数）。
    分支 B：调用方**没给** `on_error`（`_request_json_async` 的默认失败回调）。
    两条是不同代码路径，合并断言会掩护掉其中一条。
    """
    box = BoxRecorder()
    monkeypatch.setattr(appmod, "QMessageBox", box)
    monkeypatch.setattr(workers_mod, "http_json_blocking", _offline)

    # 分支 A：给了 on_error 的闭包
    window.check_updates()
    arrived = _spin(lambda: bool(box.calls))
    assert arrived, "检查更新失败的回调没到达：玩家点了菜单，什么都不会发生"
    assert box.calls[0][0] == "warning"
    assert "检查更新失败" in box.calls[0][1]
    assert _pending(window) == [], "失败请求落地后登记表没清空"

    # 分支 B：没给 on_error → 走默认失败回调（P1-10 通道，error 级）
    window.feedback.clear()
    window._request_json_async("http://stub.invalid/whatever")
    shown = _spin(lambda: bool(window.feedback.current_text))
    assert shown, "默认失败回调没到达：网络请求失败时界面一片安静"
    assert window.feedback.current_level == "error", "网络失败应当被当成 error 级反馈"
    assert window.feedback.current_timeout_ms != 0, "网络失败提示不该常驻（会话没结束）"
    assert _pending(window) == [], "默认失败分支跑完登记表没清空"


def test_pending_requests_never_leak(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """登记表必须**随回调一起排空**，包括用户回调自己抛异常的那次。

    若清理注册在用户回调**之后**，一次异常就会把清理跳过 —— worker 永久留在表里，
    长会话下是无上限的内存增长。所以本用例故意让用户回调炸一次。
    """
    box = BoxRecorder()
    monkeypatch.setattr(appmod, "QMessageBox", box)
    monkeypatch.setattr(window, "server_base", lambda: "http://stub.invalid")
    monkeypatch.setattr(window, "open_network", lambda base, data, spectator=False: None)

    offline = {"on": False}

    def _io(url, payload=None, method="GET", token=""):
        if offline["on"]:
            raise OSError("stub offline")
        return {"roomId": "ABCD", "token": "tok", "snapshot": {"revision": 1}}

    monkeypatch.setattr(workers_mod, "http_json_blocking", _io)

    # 三轮正常请求：成功 / 失败（给了 on_error）/ 失败（默认分支）
    window._request_json_async("http://stub.invalid/1", on_done=lambda data: None)
    assert _spin(lambda: _pending(window) == []), "成功请求跑完登记表还有 worker"

    offline["on"] = True
    window._request_json_async("http://stub.invalid/2", on_error=lambda message: None)
    assert _spin(lambda: _pending(window) == []), "失败请求跑完登记表还有 worker"

    window._request_json_async("http://stub.invalid/3")
    assert _spin(lambda: _pending(window) == []), "默认失败分支跑完登记表还有 worker"

    # 关键一轮：用户回调自己抛异常
    offline["on"] = False
    called: list[object] = []

    def _explode(data) -> None:  # noqa: ANN001
        called.append(data)
        raise RuntimeError("用户回调故意炸一次")

    window._request_json_async("http://stub.invalid/4", on_done=_explode)
    drained = _spin(lambda: bool(called) and _pending(window) == [])
    assert called, "抛异常那次连回调都没到达，说明连接本身已经丢了"
    assert drained, "用户回调抛异常后登记表没排空：清理被异常跳过了（清理必须在用户回调之前）"

    assert _pending(window) == [], "四条请求都跑完了，登记表仍非空"
