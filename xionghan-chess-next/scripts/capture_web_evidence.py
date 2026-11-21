"""web 旧树（`web/`，**不是 webapp**）四张目检证据离屏拍摄脚本。

## 用途

为 `docs/visual_manual_check_record.md` 的 M-1 / M-2 / M-4 / M-7 四个目检点补拍
静态证据 PNG，落到 `benchmarks/visual_evidence/`（**untracked，不入库**）。

## 运行口径

- Playwright 复用 `.venv` 内已装版本（未进依赖清单），`channel="chrome"` 连系统 Chrome，
  不下载 Chromium；本地 `http.server` 只托管 `web/` 目录。
- 页面在加载模块**之前**由 `evaluateOnNewDocument` 置 `window.__XH_DEBUG__='offscreen'`，
  才会挂上 `window.__xh` 离屏桥（见 `web/js/app.js` 末尾；生产路径不启用）。
- 注入的是 **staging 局面**（core 初始局 + 脚本强制的选中/标记/将军态），只用于核对
  标记层级与形态，不作为规则正确性依据；M-7 将军环为会话内临时置 `check`，非真实将军局。

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
EVIDENCE_DIR = ROOT / "benchmarks" / "visual_evidence"

# 四张证据文件名（与 `docs/visual_manual_check_record.md` 模板索引逐字一致）。
SHOTS = (
    "web_m1_glyph_weight.png",
    "web_m2_shadow_soft.png",
    "web_m4_dark_markers.png",
    "web_m7_state_layers.png",
)


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


def _piece(pieces: list[dict], color: str, ptype: str) -> dict | None:
    return next((p for p in pieces if p["color"] == color and p["type"] == ptype), None)


def _http_server() -> tuple[socketserver.ThreadingTCPServer, str]:
    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(WEB_DIR), **kwargs)

        def translate_path(self, path: str) -> str:
            # 离屏适配：`web/` 静态子集不带 locales，把 /locales/ 映射回仓库根 locales/。
            if path.startswith("/locales/"):
                return str(ROOT / "locales" / path[len("/locales/") :])
            return super().translate_path(path)

        def log_message(self, *_args) -> None:  # 静音访问日志
            return

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/index.html"


# 浏览器内注入：把 staging 局面 / 主题 / 标记塞进离屏桥暴露的成员并重绘。
_INJECT_JS = """
({ state, boardTheme, systemTheme, selected, legal, capturable, victims, check }) => {
  const xh = window.__xh;
  if (!xh) return { ok: false, reason: 'window.__xh 未挂载（__XH_DEBUG__ 标记缺失？）' };
  const app = xh.app;
  app.state = state;
  app.preferences.boardTheme = boardTheme;
  app.preferences.systemTheme = systemTheme;
  document.body.dataset.boardTheme = boardTheme;
  document.body.dataset.systemTheme = systemTheme;
  app.selected = selected || null;
  app.legal = legal || [];
  app.capturable = capturable || [];
  app.victims = victims || [];
  app.state.check = !!check;
  xh.resizeBoard();
  xh.draw();
  return { ok: true, pieces: app.state.pieces.length };
}
"""


def _markers_for(state: dict, scene: str) -> dict:
    pieces = state["pieces"]
    red_horse = _piece(pieces, "red", "horse") or _piece(pieces, "red", "rook")
    black_pawn = _piece(pieces, "black", "pawn") or _piece(pieces, "black", "rook")
    black_rook = _piece(pieces, "black", "rook") or black_pawn

    if scene == "m4":
        # 选中红马；legal 含一枚空格（可走点）+ 一枚占子（可吃盘）；叉=落点可吃，环=旁吃受害。
        legal = []
        if red_horse:
            legal.append({"row": red_horse["row"] - 1, "col": red_horse["col"]})
        if black_pawn:
            legal.append({"row": black_pawn["row"], "col": black_pawn["col"]})
        return {
            "selected": red_horse,
            "legal": legal,
            "capturable": [black_rook] if black_rook else [],
            "victims": [black_pawn] if black_pawn else [],
            "check": False,
        }

    if scene == "m7":
        # 四态同屏：上一步起讫格 + 将军环 + 选择 + 可走点。将军为临时置位，非真实将军。
        legal = []
        if red_horse:
            legal.append({"row": red_horse["row"] - 1, "col": red_horse["col"]})
        history = []
        if red_horse:
            history.append(
                {
                    "move": {
                        "from": {"row": red_horse["row"] + 1, "col": red_horse["col"]},
                        "to": {"row": red_horse["row"], "col": red_horse["col"]},
                    },
                    "captured": [],
                    "notation": "马",
                }
            )
        state["history"] = history
        return {
            "selected": red_horse,
            "legal": legal,
            "capturable": [],
            "victims": [],
            "check": True,
        }

    return {"selected": None, "legal": [], "capturable": [], "victims": [], "check": False}


def main() -> int:
    if shutil.which("node") is None:
        # 不阻塞拍摄：仅记录；真正依赖 node 的门禁在 pytest 侧。
        print("[capture] 提示：PATH 无 node（不影响本脚本出图）")

    from playwright.sync_api import sync_playwright

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    staging = _build_staging_state()

    server, base_url = _http_server()
    failures: list[str] = []
    results: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 960}, device_scale_factor=2)
        page.on("pageerror", lambda err: failures.append(f"pageerror: {err}"))
        page.add_init_script(
            "try{localStorage.setItem('xh-onboarded','1')}catch(e){}"
            "window.__XH_DEBUG__ = 'offscreen';"
        )
        page.goto(base_url, wait_until="networkidle")
        page.wait_for_timeout(600)

        scenes = {
            "web_m1_glyph_weight.png": ("m1", "classic", "light", None),
            "web_m2_shadow_soft.png": ("m2", "classic", "light", "clip-lower"),
            "web_m4_dark_markers.png": ("m4", "dark", "light", None),
            "web_m7_state_layers.png": ("m7", "classic", "light", None),
        }

        for filename, (scene, board_theme, system_theme, clip) in scenes.items():
            try:
                # 每张前复位上一张可能残留的 zoom，避免布局/几何被上一张污染。
                page.evaluate("document.querySelector('#boardShell').style.zoom = ''")
                markers = _markers_for(staging, scene)
                injected = page.evaluate(
                    _INJECT_JS,
                    {
                        "state": staging,
                        "boardTheme": board_theme,
                        "systemTheme": system_theme,
                        **markers,
                    },
                )
                if not injected.get("ok"):
                    raise RuntimeError(injected.get("reason", "注入失败"))
                # 等棋子位图 onload 完成，避免截到回退画圆字形。
                page.wait_for_function(
                    "[...window.__xh.app.pieceImages.values()].every(img => !img || img.complete)",
                    timeout=3000,
                )
                page.evaluate("window.__xh.draw()")
                page.wait_for_timeout(200)

                shell = page.locator("#boardShell")
                if clip == "clip-lower":
                    # 200% 下缘裁切：放大棋盘后只取下缘一带，露出盘边棋子投影柔边。
                    page.evaluate("document.querySelector('#boardShell').style.zoom = '2'")
                    page.wait_for_timeout(150)
                    box = shell.bounding_box()
                    clip_box = {
                        "x": box["x"],
                        "y": box["y"] + box["height"] * 0.5,
                        "width": box["width"],
                        "height": box["height"] * 0.5,
                    }
                    page.screenshot(path=str(EVIDENCE_DIR / filename), clip=clip_box)
                else:
                    shell.screenshot(path=str(EVIDENCE_DIR / filename))

                data = (EVIDENCE_DIR / filename).read_bytes()
                results.append(
                    {
                        "file": filename,
                        "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()[:12],
                    }
                )
            except Exception as exc:  # noqa: BLE001 —— 失败只记待办，不回灌代码批
                failures.append(f"{filename}: {exc}")

        browser.close()

    server.shutdown()

    for result in results:
        print(f"[capture] {result['file']}  {result['bytes']} B  sha256={result['sha256']}")
    if failures:
        print("[capture] 失败项：")
        for fail in failures:
            print("  ✗ " + fail)
        return 1
    print("[capture] 四张证据全部拍出")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
