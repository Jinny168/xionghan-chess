"""用户目录隔离的**自检**：`isolated_user_data` 到底有没有真的挂上。

`tests/conftest.py` 里那套 autouse 隔离如果哪天失效，表现是**静默**的 ——
测试照样绿，只是把开发者的真实 `settings.json` 写坏。所以这里留三条正面的
存在性断言，任何一条红都说明隔离没生效：

1. 什么都不声明时，配置根也必须已经落在 pytest 临时目录下（autouse 的意义）；
2. `MainWindow()` **构造**之后，真实写盘点上出现过一次保存（只覆盖 save 是不够的，
   `config_path()` 自带 `mkdir`，构造期就会建目录）；
3. 落盘内容确实写进了 tmp 里的 settings.json（不是只在内存里改了 config 字典）。

"真实文件一个字节都没动"由 conftest 的 session 级判据兜（那里才有起始快照）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.desktop import config as desktop_config  # noqa: E402
from xionghan_chess.desktop.app import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_config_root_is_already_isolated_without_declaring_anything(tmp_path) -> None:
    """**不**把 `isolated_user_data` 写进参数 —— autouse 必须自己生效。

    这正是本次改动的核心：靠"新测试记得加装饰器"是靠不住的。
    """
    root = desktop_config.config_root()
    assert root.is_relative_to(tmp_path), \
        f"配置根没落进 tmp：{root}（tmp={tmp_path}）—— autouse 隔离失效"
    assert desktop_config.config_path().is_relative_to(tmp_path)
    assert desktop_config.data_dir().is_relative_to(tmp_path)
    assert desktop_config.games_dir().is_relative_to(tmp_path)


def test_mainwindow_construction_saves_into_tmp(qt_app, isolated_user_data) -> None:
    """构造 `MainWindow()` 就要被兜住：它读配置、建目录，关窗还要写一次。"""
    window = MainWindow()
    try:
        qt_app.processEvents()
    finally:
        window.close()

    assert isolated_user_data.saves, "构造 + 关窗过程中一次保存都没有 —— 断言『保存确实发生过』会失效"
    assert isolated_user_data.settings.exists(), \
        "settings.json 没有落在 tmp 里 —— 写盘仍然指向别处"
    saved = json.loads(isolated_user_data.settings.read_text(encoding="utf-8"))
    assert isinstance(saved, dict) and saved, "落盘内容不是有效配置"
    # 记账与落盘是同一份：spy 收到的最后一次入参应当就是文件内容
    assert saved == isolated_user_data.saves[-1]


def test_user_data_paths_resolve_under_the_isolated_root(isolated_user_data) -> None:
    """`data_dir()` / `games_dir()` / `puzzles_file()` 同源，且全都在隔离根下。"""
    root = isolated_user_data.root
    assert desktop_config.data_dir() == root
    assert desktop_config.games_dir() == root / "games"
    assert desktop_config.puzzles_file() == root / "puzzles.json"
    assert all(p.is_relative_to(Path(root)) for p in
               (desktop_config.data_dir(), desktop_config.games_dir(),
                desktop_config.puzzles_file()))
