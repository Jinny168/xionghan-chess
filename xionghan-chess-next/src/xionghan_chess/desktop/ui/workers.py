"""桌面端的后台任务 worker（阶段1 S1-1 第一切片）。

从 `app.py` 抽出。本模块**只依赖 QtCore 的 QRunnable/QObject/Signal，不碰任何
Widget** —— 因此可以被无显示环境（CI offscreen）安全导入与单测。

现状：
- `AIWorker`      —— AI 搜索（长任务；实测 HARD 1.481s，而 refresh tick 仅 1.28ms）
- `HttpWorker`    —— 建连 / 云同步的阻塞 HTTP（原在 GUI 线程跑，最长冻结 15s）
- `AnalysisWorker`—— 复盘分析（40 ply；原在 GUI 线程同步跑）

它们都通过 `signals.finished/failed` 把结果送回 GUI 线程（跨线程发射 +
AutoConnection，Qt 官方语义）。
"""
from __future__ import annotations

import json
import threading
import urllib.request

from PySide6.QtCore import QObject, QRunnable, Signal

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.analysis import analyze_game
from xionghan_chess.core.game import Game


class WorkerSignals(QObject):
    """worker → GUI 线程的信号载体。

    `finished`/`failed` 的载荷是 `object`：三个 worker 的形状不同
    （AI 传 `(move, cancel)`、HTTP 传解析后的 JSON、分析传结果字典）——
    刻意不强行统一，避免为"好看的类型"引入包装层。
    """

    finished = Signal(object)
    failed = Signal(object)


class AIWorker(QRunnable):
    """在后台线程跑一次 AI 搜索。`Game` 先克隆，避免与 GUI 线程共享可变状态。"""

    def __init__(self, game: Game, difficulty: str, cancel: threading.Event) -> None:
        super().__init__()
        self.game = Game.from_state(game.state.clone(), game.options)
        self.ai = ChessAI(difficulty)
        self.cancel = cancel
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.finished.emit((self.ai.choose_move(self.game, self.cancel), self.cancel))
        except Exception as exc:  # noqa: BLE001 —— 必须把任何失败转成信号回到 GUI 线程
            self.signals.failed.emit((str(exc), self.cancel))


def http_json_blocking(url: str, payload: dict | None = None,
                       method: str = "GET", token: str = "") -> object:
    """阻塞版 HTTP JSON 请求。**只允许在 worker 线程里调用。**

    抽出原因：原先是 `MainWindow.request_json` / `http_json` 两个静态方法，在 GUI
    线程同步 `urlopen(timeout=15/8)` —— 服务不可达时窗口"未响应"最长 15 秒。
    """
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, body, headers, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


class HttpWorker(QRunnable):
    """把阻塞 HTTP 请求移到线程池（S0-C：建连/云同步不再冻结 GUI）。"""

    def __init__(self, url: str, payload: dict | None = None,
                 method: str = "GET", token: str = "") -> None:
        super().__init__()
        self.url, self.payload, self.method, self.token = url, payload, method, token
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.finished.emit(
                http_json_blocking(self.url, self.payload, self.method, self.token)
            )
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(str(exc))


class AnalysisWorker(QRunnable):
    """把复盘分析移到线程池（S0-C：show_analysis 不再冻结 GUI）。"""

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.finished.emit(analyze_game(self.game, Difficulty.BEGINNER, 40))
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(str(exc))
