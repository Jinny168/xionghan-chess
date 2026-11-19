"""I/J 批：棋子徽记「默认关 / 开启」两组对照证据离屏拍摄脚本。

## 用途

为 `docs/visual_manual_check_record.md` 的 VA-14 徽记开关目检点补拍静态 PNG，
落到 `benchmarks/visual_evidence/`（**untracked，不入库**）：

- 默认态（`pieceBadges === false`，三端默认值）：盘面只画棋子本体，无星 / 杠 /
  横 / 方徽记描边、无半透明残影；同时盘面不出现已移除的吃子图例卡片。
- 开启态（`pieceBadges === true`）：既有特色子徽记仍画出，几何口径不变
  （orbit 0.86 / size 0.26 / stroke 0.055，间隙由 `test_badge_clearance` 静态复算兜底）。

## 运行口径

- Playwright 复用 `.venv` 内已装版本（未进依赖清单），`channel="chrome"` 连系统 Chrome，
  不下载 Chromium；两个本地 `http.server` 分别托管 `web/`（旧树）与 `webapp/`。
- web 旧树沿用 G 批离屏桥：加载模块前置 `window.__XH_DEBUG__='offscreen'`，
  才挂 `window.__xh={app,draw,resizeBoard,geometry}`（生产路径不启用）。
- webapp 启动后 `window.__xh=app`；开启态通过点击 `#optPieceBadges` 复选框走既有
  onchange 链路（写偏好 → `render()`），不直接闭包内调未暴露的 render。
- 初始局双方棋子在位，足以核对徽记有无；注入/切换的只是徽记偏好，不作规则正确性依据。

## 退出码

四张全部拍出 0；任一目检点失败 1（失败项在 stdout 写明卡点，不回灌代码批）。
"""

from __future__ import annotations

import hashlib
import http.server
import shutil
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xionghan_chess.core.game import Game  # noqa: E402

WEB_DIR = ROOT / "web"
WEBAPP_DIR = ROOT / "webapp"
EVIDENCE_DIR = ROOT / "benchmarks" / "visual_evidence"


def _build_staging_state() -> dict:
    """core 初始局序列化成 web 旧树 `app.state` 形状（补 profile 包装）。"""
    game = Game("desktop_complete")
    state = game.state.to_dict()
    state["profile"] = {
        "id": game.profile.id,
        "title": game.profile.title,
        "rows": 13,
        "cols": 13,
        "options": {},
        "archerStarPoints": [],
    }
    state["check"] = False
    return state

# 四张证据文件名（与 `docs/visual_manual_check_record.md` 模板索引逐字一致）。
SHOTS = (
    "i_default_no_badges_web.png",
    "i_badges_on_web.png",
    "i_default_no_badges_webapp.png",
    "i_badges_on_webapp.png",
)


def _http_server(directory: Path, locales_root: Path | None = None) -> tuple[socketserver.ThreadingTCPServer, str]:
    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def translate_path(self, path: str) -> str:
            if locales_root is not None and path.startswith("/locales/"):
                return str(locales_root / path[len("/locales/") :])
            return super().translate_path(path)

        def log_message(self, *_args) -> None:  # 静音访问日志
            return

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/index.html"


# web 旧树：注入初始局、读取/写入偏好并重绘。
_WEB_JS = """
({ state, badges }) => {
  const xh = window.__xh;
  if (!xh) return { ok: false, reason: 'window.__xh 未挂载（__XH_DEBUG__ 标记缺失？）' };
  const app = xh.app;
  app.state = state;
  app.preferences.boardTheme = 'classic';
  app.preferences.systemTheme = 'light';
  document.body.dataset.boardTheme = 'classic';
  document.body.dataset.systemTheme = 'light';
  app.preferences.pieceBadges = badges === true;
  app.selected = null;
  app.legal = [];
  app.capturable = [];
  app.victims = [];
  app.state.check = false;
  xh.resizeBoard();
  xh.draw();
  return { ok: true, badges: app.preferences.pieceBadges === true,
           checked: !!document.querySelector('#pieceBadgesEnabled')?.checked,
           types: [...new Set(app.state.pieces.map(p => p.type))] };
}
"""

# webapp：开启态点复选框走既有链路；默认态只回读偏好与复选框状态。
_WEBAPP_ON_JS = """
() => {
  const app = window.__xh;
  if (!app) return { ok: false, reason: 'window.__xh 未挂载' };
  const box = document.querySelector('#optPieceBadges');
  if (box && !box.checked) box.click();
  return { ok: true, badges: app.prefs.pieceBadges === true, checked: !!box?.checked };
}
"""

_WEBAPP_READ_JS = """
() => {
  const app = window.__xh;
  if (!app) return { ok: false, reason: 'window.__xh 未挂载' };
  const box = document.querySelector('#optPieceBadges');
  return { ok: true, badges: app.prefs.pieceBadges === true, checked: !!box?.checked };
}
"""


def main() -> int:
    if shutil.which("node") is None:
        print("[capture] 提示：PATH 无 node（不影响本脚本出图）")

    from playwright.sync_api import sync_playwright

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    results: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        # ---------- web 旧树 ----------
        web_server, web_url = _http_server(WEB_DIR, locales_root=ROOT / "locales")
        page = browser.new_page(viewport={"width": 1280, "height": 960}, device_scale_factor=2)
        page.on("pageerror", lambda err: failures.append(f"web pageerror: {err}"))
        page.add_init_script(
            "try{localStorage.setItem('xh-onboarded','1')}catch(e){}"
            "window.__XH_DEBUG__ = 'offscreen';"
        )
        page.goto(web_url, wait_until="networkidle")
        page.wait_for_timeout(600)
        staging = _build_staging_state()

        # 默认态全景；开启态放大盘缘特色子行裁切（既突出徽记与邻子间隙，
        # 又避免与 H 批已入库的全景 M1 逐字节重复 —— M1 拍于开关落地前，本身带徽记）。
        web_scenes = {
            "i_default_no_badges_web.png": {"badges": False, "clip": None},
            "i_badges_on_web.png": {"badges": True, "clip": "clip-top"},
        }
        for filename, scene in web_scenes.items():
            try:
                injected = page.evaluate(_WEB_JS, {"state": staging, "badges": scene["badges"]})
                if not injected.get("ok"):
                    raise RuntimeError(injected.get("reason", "注入失败"))
                page.wait_for_function(
                    "[...window.__xh.app.pieceImages.values()].every(img => !img || img.complete)",
                    timeout=3000,
                )
                page.evaluate("window.__xh.draw()")
                page.wait_for_timeout(200)
                page.evaluate("document.querySelector('#boardShell').style.zoom = ''")
                shell = page.locator("#boardShell")
                if scene["clip"] == "clip-top":
                    # 200% 上缘裁切：放大棋盘后只取首行一带，露出盘缘徽记与邻子间隙。
                    page.evaluate("document.querySelector('#boardShell').style.zoom = '2'")
                    page.wait_for_timeout(150)
                    box = shell.bounding_box()
                    clip_box = {
                        "x": box["x"],
                        "y": box["y"],
                        "width": box["width"],
                        "height": box["height"] * 0.32,
                    }
                    page.screenshot(path=str(EVIDENCE_DIR / filename), clip=clip_box)
                else:
                    shell.screenshot(path=str(EVIDENCE_DIR / filename))
                data = (EVIDENCE_DIR / filename).read_bytes()
                results.append({"file": filename, "bytes": len(data),
                                "sha256": hashlib.sha256(data).hexdigest()[:12],
                                "badges": injected.get("badges"),
                                "types": injected.get("types")})
            except Exception as exc:  # noqa: BLE001 —— 失败只记待办，不回灌代码批
                failures.append(f"{filename}: {exc}")
        page.close()
        web_server.shutdown()

        # ---------- webapp ----------
        app_server, app_url = _http_server(WEBAPP_DIR)
        page = browser.new_page(viewport={"width": 1280, "height": 960}, device_scale_factor=2)
        page.on("pageerror", lambda err: failures.append(f"webapp pageerror: {err}"))
        page.goto(app_url, wait_until="networkidle")
        page.wait_for_timeout(700)

        # 默认态：回读偏好（应为 false / 未勾）。
        try:
            read = page.evaluate(_WEBAPP_READ_JS)
            if not read.get("ok"):
                raise RuntimeError(read.get("reason", "读取失败"))
            page.wait_for_timeout(200)
            page.locator("#boardHolder").screenshot(path=str(EVIDENCE_DIR / "i_default_no_badges_webapp.png"))
            data = (EVIDENCE_DIR / "i_default_no_badges_webapp.png").read_bytes()
            results.append({"file": "i_default_no_badges_webapp.png", "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()[:12],
                            "badges": read.get("badges")})
        except Exception as exc:  # noqa: BLE001
            failures.append(f"i_default_no_badges_webapp.png: {exc}")

        # 开启态：点复选框走既有 onchange 链路。
        try:
            injected = page.evaluate(_WEBAPP_ON_JS)
            if not injected.get("ok"):
                raise RuntimeError(injected.get("reason", "开启失败"))
            page.wait_for_timeout(300)
            page.locator("#boardHolder").screenshot(path=str(EVIDENCE_DIR / "i_badges_on_webapp.png"))
            data = (EVIDENCE_DIR / "i_badges_on_webapp.png").read_bytes()
            results.append({"file": "i_badges_on_webapp.png", "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()[:12],
                            "badges": injected.get("badges")})
        except Exception as exc:  # noqa: BLE001
            failures.append(f"i_badges_on_webapp.png: {exc}")
        page.close()
        app_server.shutdown()

        browser.close()

    for result in results:
        print(f"[capture] {result['file']}  {result['bytes']} B  sha256={result['sha256']}  badges={result.get('badges')}  types={result.get('types')}")
    if failures:
        print("[capture] 失败项：")
        for fail in failures:
            print("  ✗ " + fail)
        return 1
    print("[capture] 四张徽记对照证据全部拍出")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
