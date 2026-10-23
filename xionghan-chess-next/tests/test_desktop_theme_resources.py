"""桌面资源访问器单测（阶段1 S1-1）。

`theme.resource()` / `theme.read_docs()` 是桌面端**唯一**的资源路径来源 ——
此前 app.py / audio.py / board_widget.py 各自用
`Path(__file__).resolve().parent / "resources"` 拼路径，一旦文件搬家就会
**静默指到不存在的目录**（BoardWidget 搬 `ui/` 时空背景图就是这么来的：
不报错、只是背景消失、音效静音）。

这里断言三件事：
1. 关键资源真的在 `theme.RESOURCES` 下找得到（搬文件后若路径算错，立刻红）；
2. `read_docs()` 读到的是真文档内容，不是错误串；
3. `read_docs()` 缺文件时返回可展示的中文提示，**不抛异常**
   （原三处内联实现就是靠 try/except 保证对话框永远打得开）。

依赖 PySide6（theme 模块 import 了 QtGui/QtWidgets），因此本文件在
CI 的 `desktop-smoke` job 里跑；无 PySide6 时整体跳过而不是报错。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="theme 模块依赖 PySide6，无桌面环境时跳过")

from xionghan_chess.desktop.ui import theme  # noqa: E402


def test_resources_dir_exists() -> None:
    assert theme.resources_dir().is_dir()


@pytest.mark.parametrize(
    "relpath",
    [
        "icon.ico",
        "fonts/msyh.ttc",
        "fonts/simkai.ttf",
        "sounds/drop.wav",
        "sounds/fc_background_sound.ogg",
        "sounds/qq_background_sound.ogg",
        "docs/HELP.md",
        "docs/ABOUT.md",
        "docs/PIECE_RULES.md",
        "avatars/avatar-01.webp",
    ],
)
def test_resource_resolves_to_existing_file(relpath: str) -> None:
    """这是「文件搬家后路径静默失效」的守卫：解析不到就红，与运行期不可见不同。"""
    path = theme.resource(*relpath.split("/"))
    assert path.is_file(), f"资源缺失：{path}"


def test_resource_returns_path_under_resources() -> None:
    path = theme.resource("sounds", "drop.wav")
    assert theme.resources_dir() in path.parents


def test_resource_does_not_require_existence_for_optional() -> None:
    """拼路径本身不该因文件不存在而抛（可选资源由调用方判断 exists）。"""
    assert theme.resource("nope", "missing.png").name == "missing.png"


@pytest.mark.parametrize(
    "name,expected_fragment",
    [
        ("PIECE_RULES.md", "棋"),
        ("HELP.md", ""),
        ("ABOUT.md", ""),
    ],
)
def test_read_docs_returns_real_content(name: str, expected_fragment: str) -> None:
    content = theme.read_docs(name)
    assert "读取失败" not in content, content
    assert len(content.strip()) > 0
    if expected_fragment:
        assert expected_fragment in content


def test_read_docs_missing_file_returns_message_not_raise() -> None:
    """对话框必须永远打得开 —— 缺文件时显示提示串而不是让菜单点击崩掉。"""
    content = theme.read_docs("NOT_EXIST.md", "规则文档")
    assert content.startswith("规则文档读取失败：")
    assert "NOT_EXIST.md" in content


def test_read_docs_default_label() -> None:
    assert theme.read_docs("NOT_EXIST.md").startswith("文档读取失败：")
