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
        # S2-4：随包字体换成 Noto OFL 子集（原 msyh.ttc / simkai.ttf 为微软授权字体）
        "fonts/NotoSansSC-subset.ttf",
        "fonts/NotoSerifSC-subset.ttf",
        "fonts/OFL.txt",
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


# ---------------------------------------------------------------------------
# S2-4：随包字体必须是可再分发的开源字体
# ---------------------------------------------------------------------------
def test_bundled_fonts_are_open_licensed() -> None:
    """防线回归：不允许再把系统/商用字体拷进仓库。

    msyh.ttc（微软雅黑）与 simkai.ttf（楷体）随安装包分发需要微软单独授权，
    曾是 1.6.0 的分发风险点。这里同时断言：
    - 旧文件不存在；
    - 仓库里有 OFL 许可证文本（OFL 条件 2：分发时必须随附许可证）；
    - 当前 family 名不是 Reserved Font Name 的原始名（OFL 条件 3：子集属
      Modified Version，不得沿用 "Noto Sans SC" 原名）。
    """
    font_dir = theme.resources_dir() / "fonts"
    for legacy in ("msyh.ttc", "simkai.ttf"):
        assert not (font_dir / legacy).exists(), f"微软授权字体仍在随包资源里：{legacy}"
    license_text = (font_dir / "OFL.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in license_text.upper()
    assert theme.UI_FONT.endswith(" Subset"), theme.UI_FONT
    assert theme.PIECE_FONT.endswith(" Subset"), theme.PIECE_FONT


def test_bundled_fonts_cover_all_piece_glyphs() -> None:
    """棋子字形不能被字体子集裁掉 —— 少了就是方块（tofu），且只在对局时可见。"""
    from fontTools.ttLib import TTFont

    font_dir = theme.resources_dir() / "fonts"
    needed = {name for side in theme.NAMES.values() for name in side.values()}
    needed |= {"汉", "象", "棋", "残", "局"}
    for filename in ("NotoSansSC-subset.ttf", "NotoSerifSC-subset.ttf"):
        cmap = set(TTFont(font_dir / filename).getBestCmap())
        missing = {ch for ch in needed if ord(ch) not in cmap}
        assert not missing, f"{filename} 缺少字形：{''.join(sorted(missing))}"


# ---------------------------------------------------------------------------
# P1-Q：没有 QGuiApplication 时，字体加载必须是安全 no-op
# ---------------------------------------------------------------------------
def test_load_bundled_fonts_is_noop_without_gui_application(monkeypatch: pytest.MonkeyPatch) -> None:
    """打桩掉应用实例后调用，不能抛异常、也不能改动字体名。"""
    before = (theme.UI_FONT, theme.PIECE_FONT)
    monkeypatch.setattr(theme, "_gui_application", lambda: None)
    theme.load_bundled_fonts()
    assert (theme.UI_FONT, theme.PIECE_FONT) == before


def test_load_bundled_fonts_does_not_crash_the_process_without_qapplication() -> None:
    """子进程里裸调一次：没有 QGuiApplication 时必须正常退出。

    为什么用子进程：`QFontDatabase.addApplicationFont()` 在没有 GUI 应用时是
    **段错误**（本机实测 exit 139），不是抛异常。进程内跑会把 pytest 一起带走，
    所以只能另起一个进程看退出码。
    """
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    code = (
        "import sys; sys.path.insert(0, 'src')\n"
        "from xionghan_chess.desktop.ui import theme\n"
        "theme.load_bundled_fonts()\n"
        "print('NOOP_OK')\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True,
                          text=True, timeout=120)
    assert proc.returncode == 0, f"退出码 {proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
    assert "NOOP_OK" in proc.stdout
