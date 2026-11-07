"""把 webapp 的 ES 模块打包成单文件 HTML。

为什么需要它
------------
WorkBuddy「发布为网站」的分享链接在首次访问时只授权 HTML 文档本身，
子资源（CSS / 多个 JS 模块）会拿到 403，要等 Cookie 落地后刷新才正常。
把整个应用内联进一个 HTML，就能让评审第一次点开即可游玩，同时也把
首屏请求数从 12 个降到 1 个。

产物：webapp/dist/index.html（自包含，无外部依赖）

用法：
    python scripts/build_webapp_bundle.py
"""

from __future__ import annotations

import json
import posixpath
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "webapp"
OUT = WEB / "dist"

IMPORT_RE = re.compile(
    r"import\s+(?P<clause>\*\s+as\s+\w+|\{[\s\S]*?\})\s+from\s+['\"](?P<spec>[^'\"]+)['\"];?",
)
EXPORT_DECL_RE = re.compile(
    r"^export\s+(?P<async>async\s+)?(?P<kind>const|let|var|function|class)\s+(?P<name>\w+)",
    re.MULTILINE,
)
EXPORT_LIST_RE = re.compile(r"^export\s*\{(?P<names>[^}]*)\}\s*;?\s*$", re.MULTILINE)


def module_key(path: str) -> str:
    return posixpath.normpath(path)


def resolve(base: str, spec: str) -> str:
    return module_key(posixpath.join(posixpath.dirname(base), spec))


def read_source(key: str) -> str:
    return (WEB / key).read_text(encoding="utf-8")


def scan_imports(source: str) -> list[str]:
    return [match.group("spec") for match in IMPORT_RE.finditer(source)]


def collect_modules(entry: str) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()

    def visit(key: str) -> None:
        if key in seen:
            return
        seen.add(key)
        for spec in scan_imports(read_source(key)):
            visit(resolve(key, spec))
        order.append(key)

    visit(module_key(entry))
    return order


def transform(key: str, source: str) -> tuple[str, list[str]]:
    names: list[str] = []
    pieces: list[str] = []
    cursor = 0

    # 1. import 语句 → 从模块表里解构
    for match in IMPORT_RE.finditer(source):
        pieces.append(source[cursor:match.start()])
        clause = match.group("clause")
        dep = module_key(resolve(key, match.group("spec")))
        if clause.startswith("*"):
            alias = clause.split("as")[1].strip()
            pieces.append(f"const {alias} = __mods[{json.dumps(dep)}];")
        else:
            inner = clause.strip()[1:-1]
            binding = ", ".join(part.strip() for part in inner.split(",") if part.strip())
            pieces.append(f"const {{ {binding} }} = __mods[{json.dumps(dep)}];")
        cursor = match.end()
    pieces.append(source[cursor:])
    body = "".join(pieces)

    # 2. export 声明 → 记录导出名并去掉关键字
    for match in EXPORT_DECL_RE.finditer(body):
        names.append(match.group("name"))
    body = EXPORT_DECL_RE.sub(lambda m: f"{m.group('async') or ''}{m.group('kind')} {m.group('name')}", body)

    # 3. export { a, b } → 记录并删除
    for match in EXPORT_LIST_RE.finditer(body):
        for part in match.group("names").split(","):
            part = part.strip()
            if not part:
                continue
            names.append(part.split(" as ")[-1].strip())
    body = EXPORT_LIST_RE.sub("", body)

    return body, names


def bundle(entry: str) -> str:
    order = collect_modules(entry)
    chunks = []
    for key in order:
        body, names = transform(key, read_source(key))
        exported = ", ".join(dict.fromkeys(names))
        chunks.append(
            f"__mods[{json.dumps(key)}] = (function () {{\n{body}\n"
            f"return {{ {exported} }};\n}})();"
        )
    return "\n\n".join(chunks)


def main() -> None:
    css = (WEB / "css" / "app.css").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")

    worker_src = "var __mods = {};\n" + bundle("js/ai-worker.js")
    app_src = bundle("js/ui/app.js")

    prelude = (
        "/* 单文件构建：模块表 + Worker 由 Blob 创建，避免额外网络请求 */\n"
        "var __mods = {};\n"
        "globalThis.__xhBundled = true;\n"
        f"var __WORKER_SRC = {json.dumps(worker_src)};\n"
        "globalThis.__xhCreateWorker = function () {\n"
        "  var blob = new Blob([__WORKER_SRC], { type: 'text/javascript' });\n"
        "  return new Worker(URL.createObjectURL(blob));\n"
        "};\n"
    )

    favicon = (
        "data:image/svg+xml,"
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
        "%3Ccircle cx='32' cy='32' r='30' fill='%239c2b22'/%3E"
        "%3Ccircle cx='32' cy='32' r='25.5' fill='none' stroke='%23f6e7c8' stroke-width='1.6' opacity='.7'/%3E"
        "%3Ctext x='32' y='43' text-anchor='middle' font-family='KaiTi,STKaiti,serif' font-size='34' fill='%23fdf3e4'%3E"
        "%E6%BC%A2%3C/text%3E%3C/svg%3E"
    )

    html = html.replace('  <link rel="icon" href="./favicon.svg" type="image/svg+xml">\n', "")
    html = html.replace('<link rel="icon" href="./favicon.svg" type="image/svg+xml">', "")
    html = html.replace('<link rel="manifest" href="./manifest.webmanifest">', "")
    html = html.replace(
        '<link rel="stylesheet" href="./css/app.css">',
        f'<link rel="icon" href="{favicon}">\n  <style>\n{css}\n  </style>',
    )
    html = html.replace(
        '<script type="module" src="./js/ui/app.js"></script>',
        f"<script>\n{prelude}\n{app_src}\n</script>",
    )

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "index.html"
    target.write_text(html, encoding="utf-8")

    # 同步到联机应用：静态页与规则内核都从这里取，避免两处不一致
    online_dir = WEB.parent / "online"
    if online_dir.exists():
        public = online_dir / "public"
        public.mkdir(parents=True, exist_ok=True)
        (public / "index.html").write_text(html, encoding="utf-8")
        record = WEB / "dist" / "record.html"
        if record.exists():
            (public / "record.html").write_text(record.read_text(encoding="utf-8"), encoding="utf-8")
        core_dst = online_dir / "core"
        core_dst.mkdir(exist_ok=True)
        for item in (WEB / "js" / "core").glob("*.js"):
            (core_dst / item.name).write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"已同步到 {online_dir}")

    size_kb = target.stat().st_size / 1024
    print(f"写入 {target}")
    print(f"体积 {size_kb:.1f} KB（内联 CSS + 全部模块 + Worker）")
    assert "<script type=\"module\"" not in html, "仍有外部模块引用"
    assert "./css/app.css" not in html, "样式未内联"


if __name__ == "__main__":
    main()
