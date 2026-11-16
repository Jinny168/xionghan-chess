"""webapp/css/app.css 的声明快照守卫。

与 web/css 那套并行，但**不能照抄**：webapp 只有 `:root` 一处作用域，没有
`data-system-theme` / `data-board-theme` 覆写，三份快照除 scope 后缀外完全相同。
所以这里守的是"除了后缀别无差异" —— 若照搬 web 的 `light != dark`，
后缀本身就足以让断言永远通过，那是假守卫。

基线由 `python scripts/css_snapshot.py --webapp --write` 生成，禁止手写。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "css_snapshot.py"
SCOPES = ("light", "dark", "board-dark")
BASELINES = {
    "light": ROOT / "benchmarks" / "css_snapshot_webapp_light.txt",
    "dark": ROOT / "benchmarks" / "css_snapshot_webapp_dark.txt",
    "board-dark": ROOT / "benchmarks" / "css_snapshot_webapp_board-dark.txt",
}


def _module():
    spec = importlib.util.spec_from_file_location("css_snapshot_webapp", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snapshots() -> dict[str, bytes]:
    module = _module()
    snaps = module.snapshots(module.WEBAPP_CSS)
    return {name: snaps[name].encode("utf-8") for name in SCOPES}


def _first_mismatch(got: bytes, want: bytes) -> str:
    got_lines, want_lines = got.split(b"\n"), want.split(b"\n")
    for index, (a, b) in enumerate(zip(got_lines, want_lines), 1):
        if a != b:
            return (
                f"首个差异在第 {index} 行\n"
                f"  基线：{b.decode('utf-8', 'replace')[:200]}\n"
                f"  现在：{a.decode('utf-8', 'replace')[:200]}"
            )
    if len(got_lines) != len(want_lines):
        return f"行数不同：基线 {len(want_lines)} 行 / 现在 {len(got_lines)} 行"
    return "内容完全相同（不该走到这条断言）"


def test_webapp_snapshots_match_baseline_bytes() -> None:
    got = _snapshots()
    for name, path in BASELINES.items():
        assert path.is_file(), f"缺少 webapp {name} 基线，先跑 python scripts/css_snapshot.py --webapp --write"
        want = path.read_bytes()
        assert got[name] == want, (
            f"webapp {name} 快照变了：基线 {len(want)} 字节 / 现在 {len(got[name])} 字节\n"
            + _first_mismatch(got[name], want)
        )


def test_webapp_snapshot_is_stable_across_runs() -> None:
    assert _snapshots() == _snapshots()


def test_webapp_snapshot_has_no_cr() -> None:
    for name, body in _snapshots().items():
        assert b"\r" not in body, f"webapp {name} 快照含 CR"


def test_webapp_scopes_differ_only_by_suffix() -> None:
    """三份除 scope 后缀外必须逐字相同。

    webapp 没有暗色覆写 —— 这是与 web 的 `test_dark_snapshot_differs_from_light`
    恰好相反的契约。若哪天 webapp 多了暗色作用域，这条会先红，提醒同步基线口径。
    """
    snaps = _snapshots()
    light = snaps["light"].decode("utf-8")
    dark = snaps["dark"].decode("utf-8")
    board = snaps["board-dark"].decode("utf-8")
    assert dark.replace("@dark|", "|") == light, "暗色快照出现 :root 之外的覆写（webapp 不该有）"
    assert board.replace("@board-dark|", "|") == light, "棋盘暗色快照出现 :root 之外的覆写（webapp 不该有）"
