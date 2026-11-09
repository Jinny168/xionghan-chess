"""D-4：短命对话框的 0 拍定时器不得在销毁后回调。

## 为什么要有这个文件（替代一条依赖执行顺序的"护栏"）

`desktop/ui/dialogs.py::_fit_to_content` 会给自己排一个 `QTimer.singleShot(0, ...)`
（等布局算完再收窗口尺寸）。它被 **6 个**对话框共用（设置 / 让子 / 教学 / 棋谱库 /
训练 …，`grep -n "_fit_to_content("` 可查全部调用点）。原来那个定时器**没有 context 对象**，
于是"用户打开设置页立刻关掉 / 被程序化取消"会在下一拍事件循环里访问已删除的
C++ 对象：

    RuntimeError: libshiboken: Internal C++ object (SettingsDialog) already deleted.

这是**产品崩溃**，不是测试脏。但它在测试里只在一种情况下显形：
`test_desktop_piece_atlas.py` 留下一个 `deleteLater()` 的 `SettingsDialog`
（全程不推事件循环），随后 `test_desktop_play_again.py` 的 `drain()` 把它推了出去。
换句话说，旧护栏是「**三个文件的收集顺序**」——换个顺序、加个文件、并行跑，都可能在
产品还坏着的时候显示绿色。这在本项目已经吃过一次亏（1.6.0 的限流就是这么"修好又丢掉"）。

所以这里用一条 ~几十毫秒的定向用例，把不变量钉在**与顺序无关**的地方：
「销毁后的对话框，不能再被回调」。

## 两面都必须断言

只断言"销毁后不报错"是不够的 —— 如果有人把 context 传错（例如传了个长命对象），
回调照样会被执行，但正常路径也会跟着变哑：对话框打开时尺寸不再自适应。
所以第一面（对象活着 → 回调必须执行且尺寸真的变了）和第二面（对象销毁 → 不执行、
不抛异常）缺一不可。
"""

from __future__ import annotations

import os

# 必须在导入 QtWidgets 之前定下平台插件：CI 是 headless（`QT_QPA_PLATFORM=offscreen`），
# 本机可能已经设过，`setdefault` 只兜底、不覆盖。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6", reason="桌面端用例依赖 PySide6")

import shiboken6  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from xionghan_chess.desktop.ui.dialogs import _fit_to_content  # noqa: E402

BIG = 2000  # 故意放大，保证 apply 一定会改动尺寸（否则"没变"无法区分"没执行"）


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _drain(qt_app: QApplication, rounds: int = 3) -> None:
    """推若干拍事件循环。0 拍定时器在 `processEvents()` 里就会触发，但多推几拍更稳。"""
    for _ in range(rounds):
        qt_app.processEvents()


class _SpyDialog(QDialog):
    """记录 `sizeHint` 被调了几次。

    计数放在**外部 list** 里而不是 `self` 上：`shiboken6.delete()` 之后 Python 包装对象
    虽然还在，但读取它的属性容易踩到"对象已删除"的边界；外部 list 与被测对象完全解耦。
    """

    def __init__(self, calls: list[int]) -> None:
        super().__init__()
        self._calls = calls

    def sizeHint(self):                      # noqa: N802 - Qt 命名
        self._calls.append(1)
        return super().sizeHint()


def test_alive_dialog_is_still_fitted(qt_app: QApplication) -> None:
    """**第一面**：对话框活着时，回调必须照常执行、尺寸真的被收过。

    这条防的是"修悬空时把正常路径也弄哑"：context 传错对象（比如传了 QApplication）
    同样能消除崩溃，但 `_fit_to_content` 从此不再生效 —— 那种改法会让本用例红。
    """
    calls: list[int] = []
    dialog = _SpyDialog(calls)
    dialog.resize(BIG, BIG)
    hint = dialog.sizeHint()                 # 先量一次基准 hint
    calls.clear()

    _fit_to_content(dialog)
    assert calls == [], "回调应排到下一拍，不能在调用期同步执行（构造期 sizeHint 偏小）"

    _drain(qt_app)
    assert calls == [1], f"对话框尚未销毁，回调必须执行一次，实际 {calls!r}"

    expected_width = max(dialog.minimumWidth(), min(BIG, int(hint.width() * 1.2)))
    expected_height = max(dialog.minimumHeight(), min(BIG, int(hint.height() * 1.2)))
    assert (dialog.width(), dialog.height()) == (expected_width, expected_height), (
        f"尺寸未按内容收敛：得到 {(dialog.width(), dialog.height())}，"
        f"应为 {(expected_width, expected_height)}"
    )
    assert dialog.width() < BIG, "基准放大到 2000 后必须真的被收小，否则断言区分不出'执行'与'没执行'"

    dialog.deleteLater()
    _drain(qt_app)                           # 把自己留下的对象清干净，别污染同进程的其它用例


def test_deleted_dialog_is_never_called_back(qt_app: QApplication) -> None:
    """**第二面**：对话框销毁后，回调既不许执行，也不许抛异常。

    修前这里是红的（`RuntimeError: Internal C++ object ... already deleted`），
    修后语义应是"定时器被自动断开"—— 所以必须断言 `calls == []`：
    只断言"没抛异常"会把"照跑但吞掉异常"的假修法放过去。
    """
    calls: list[int] = []
    dialog = _SpyDialog(calls)
    dialog.resize(BIG, BIG)

    _fit_to_content(dialog)                  # 排一个 0 拍回调
    shiboken6.delete(dialog)                 # 模拟"用户打开就关掉 / 被程序化取消"

    try:
        _drain(qt_app)                       # 下一拍：修前在这里抛 RuntimeError
    except RuntimeError as exc:              # noqa: PERF203 - 失败信息要指向真因
        pytest.fail(
            "对话框已销毁，0 拍回调仍在执行（定时器未与 dialog 绑定生命周期）："
            f"{exc}。修法是 `QTimer.singleShot(0, dialog, apply)` —— 带 context 对象。"
        )

    assert calls == [], (
        f"对话框已销毁，回调不许执行（应为自动断开），实际执行 {len(calls)} 次。"
        "若这里非空但没抛异常，说明 context 传错了对象：崩溃被掩盖，产品仍会读到旧尺寸。"
    )
