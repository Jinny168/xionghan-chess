"""把 webapp 的 ES 模块打包成单文件 HTML。

为什么需要它
------------
WorkBuddy「发布为网站」的分享链接在首次访问时只授权 HTML 文档本身，
子资源（CSS / 多个 JS 模块）会拿到 403，要等 Cookie 落地后刷新才正常。
把整个应用内联进一个 HTML，就能让评审第一次点开即可游玩，同时也把
首屏请求数从 12 个降到 1 个。

产物（5 类，全部由本脚本同步）：
  1. webapp/dist/index.html              自包含单文件
  2. online/public/index.html            联机静态页（与 1 逐字节相同）
  3. online/public/record.html           棋谱页副本
  4. online/core/*.js                    联机端规则内核（模块化）
  5. webapp/.edgeone/assets/...          EdgeOne Makers **部署源**（引用式加载活体 js/core/*.js）
       - assets/js/core/profiles.js
       - assets/js/core/rules.js
       - assets/js/core/movegen.js
       - assets/tests/fixtures/rules.json

⚠️ 第 5 类是本轮补上的（主理人 U4′）：`.edgeone/assets/index.html:333` 是
`<script type="module" src="./js/ui/app.js">` —— **引用式加载活体 js/core/*.js**。
旧脚本的产物清单不写它，于是「补完 webapp 源码，线上 EdgeOne 页面仍跑旧引擎」。
本轮不做部署/发布动作，只做源码同步与校验。

用法：
    python scripts/build_webapp_bundle.py            # 同步 5 类产物
    python scripts/build_webapp_bundle.py --check   # 重算 + 逐字节比对，漂移 exit 1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "webapp"
OUT = WEB / "dist"
ONLINE = WEB.parent / "online"
EDGEONE = WEB / ".edgeone" / "assets"
MANIFEST = WEB / "js" / "core" / "profiles.manifest.json"

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
        pieces.append(source[cursor : match.start()])
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
        chunks.append(f"__mods[{json.dumps(key)}] = (function () {{\n{body}\nreturn {{ {exported} }};\n}})();")
    return "\n\n".join(chunks)


def build_html() -> str:
    """重算完整单文件 HTML（含 __WORKER_SRC 与 app_src 两份内嵌规则内核）。"""
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
    return html


def _write(path: Path, text: str) -> None:
    """统一 LF：Windows 上 Path.write_text 默认会把 \\n 转 \\r\\n，
    造成 online/core/profiles.js 与 webapp 源逐字节分叉（实测差 260 个 CR）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _edgeone_targets() -> dict[Path, Path]:
    """EdgeOne 部署源 → webapp 唯一源的映射（只列本轮明确纳入清单的文件）。"""
    return {
        EDGEONE / "js" / "core" / "profiles.js": WEB / "js" / "core" / "profiles.js",
        EDGEONE / "js" / "core" / "rules.js": WEB / "js" / "core" / "rules.js",
        # movegen.js 本轮也改了（rules.js 的配套快速生成器），不同步会让部署源 AI 与主规则分叉
        EDGEONE / "js" / "core" / "movegen.js": WEB / "js" / "core" / "movegen.js",
        EDGEONE / "tests" / "fixtures" / "rules.json": WEB / "tests" / "fixtures" / "rules.json",
    }


def sync(html: str) -> None:
    _write(OUT / "index.html", html)
    if ONLINE.exists():
        _write(ONLINE / "public" / "index.html", html)
        record = WEB / "dist" / "record.html"
        if record.exists():
            _write(ONLINE / "public" / "record.html", record.read_text(encoding="utf-8"))
        core_dst = ONLINE / "core"
        core_dst.mkdir(parents=True, exist_ok=True)
        for item in (WEB / "js" / "core").glob("*.js"):
            _write(core_dst / item.name, item.read_text(encoding="utf-8"))
        print(f"已同步到 {ONLINE}")
    # 第五类：EdgeOne Makers 部署源（引用式加载活体 js/core/*.js）
    if EDGEONE.exists():
        for target, source in _edgeone_targets().items():
            if source.exists():
                _write(target, source.read_text(encoding="utf-8"))
        print(f"已同步到 {EDGEONE}")

    size_kb = (OUT / "index.html").stat().st_size / 1024
    print(f"写入 {OUT / 'index.html'}")
    print(f"体积 {size_kb:.1f} KB（内联 CSS + 全部模块 + Worker）")
    assert '<script type="module"' not in html, "仍有外部模块引用"
    assert "./css/app.css" not in html, "样式未内联"


def _normalize(text: str) -> str:
    """CRLF/LF 归一化，用于 --check 的行尾符无关比对。"""
    return text.replace("\r\n", "\n")


def _embedded_body(html: str, key: str) -> str | None:
    """从 bundle HTML 抠出 `__mods["<key>"] = (function () {\\n<body>\\nreturn {...};`。

    chunk 拼接格式是 `... (function () {\\n{body}\\nreturn {...};\\n})();`，
    故 body 前后各带一个换行；比对时去掉这两个换行即可与 `transform()` 结果逐字相等。
    """
    marker = f"__mods[{json.dumps(key)}] = (function () {{"
    start = html.find(marker)
    if start < 0:
        return None
    body_start = start + len(marker)
    tail_at = html.find("\nreturn {", body_start)
    if tail_at < 0:
        return None
    body = html[body_start:tail_at]
    return body[1:] if body.startswith("\n") else body


def _worker_source(html: str) -> str | None:
    """解码 `var __WORKER_SRC = ("...");` 转义串，得到 Worker 模块源码。"""
    match = re.search(r"var __WORKER_SRC = (\"(?:[^\"\\]|\\.)*\");", html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _rules_snapshot_count(html: str) -> int:
    """`js/core/rules.js` 引擎快照数：主 inline 明文 1 + WORKER_SRC 解码后 1 = 2。"""
    marker = '__mods["js/core/rules.js"] = (function () {'
    plain = html.count(marker)
    worker = _worker_source(html)
    in_worker = worker.count(marker) if worker else 0
    return plain + in_worker


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(html: str) -> int:
    """重算 + 逐字节比对 + 哨兵；任一漂移 exit 1。"""
    problems: list[str] = []

    # 前置断言：rulesHash == sha256(webapp/js/core/rules.js)（Step1 manifest 链）
    if not MANIFEST.exists():
        print("[manifest] profiles.manifest.json 缺失 —— 先跑 Step1", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rules_js = WEB / "js" / "core" / "rules.js"
    if manifest.get("rulesHash") != _sha256(rules_js):
        problems.append("[rules-hash] manifest.rulesHash != sha256(webapp/js/core/rules.js) —— 先跑 Step1")

    # ① 重算 html 与两处产物逐字节比对（归一化行尾符）
    for path in (OUT / "index.html", ONLINE / "public" / "index.html"):
        if not path.exists():
            problems.append(f"[html-missing] {path} 不存在 —— 跑 build_webapp_bundle.py")
        elif _normalize(path.read_text(encoding="utf-8")) != _normalize(html):
            problems.append(f"[html-drift] {path} 与重算结果不一致")

    # ② online/core/*.js 归一化行尾后与 webapp/js/core/*.js 逐字相同
    for item in (WEB / "js" / "core").glob("*.js"):
        dst = ONLINE / "core" / item.name
        if not dst.exists():
            problems.append(f"[online-core] {dst} 缺失")
        elif _normalize(dst.read_text(encoding="utf-8")) != _normalize(item.read_text(encoding="utf-8")):
            problems.append(f"[online-core] {item.name} 与 webapp 源不一致")

    # ③ 内嵌 __mods["js/core/rules.js"] / ["js/core/profiles.js"] 文本 == transform(源文件)
    disk_html = OUT / "index.html"
    if disk_html.exists():
        raw = disk_html.read_text(encoding="utf-8")
        for key in ("js/core/rules.js", "js/core/profiles.js"):
            expected_body, _ = transform(key, read_source(key))
            actual_body = _embedded_body(raw, key)
            if actual_body is None:
                problems.append(f"[embedded] 缺 __mods[{json.dumps(key)}] 内嵌块")
            elif _normalize(actual_body) != _normalize(expected_body):
                problems.append(f"[embedded] __mods[{json.dumps(key)}] 内嵌文本与源文件漂移")

    # ④ 第五类：EdgeOne 部署源漂移
    for target, source in _edgeone_targets().items():
        if not source.exists():
            continue
        if not target.exists():
            problems.append(f"[edgeone] {target} 缺失 —— 跑 build_webapp_bundle.py")
        elif _normalize(target.read_text(encoding="utf-8")) != _normalize(source.read_text(encoding="utf-8")):
            problems.append(f"[edgeone] {target.name} 与 webapp 唯一源漂移")

    # ⑤ 哨兵（严过关 M26）：`js/core/rules.js` 在 HTML 里真正的
    #    `__mods[...] = (function` 引擎快照只有 **2 份**（1 份主 inline script、
    #    1 份 `__WORKER_SRC` 转义串）。只更新一份时 `≥1` 会假绿，故阈值一律 ≥2。
    #    判据按两份快照取，不按全文（app.js 的 UI 文案按 §0 本轮不动，不该计入）。
    for path in (OUT / "index.html", ONLINE / "public" / "index.html"):
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        assignment_count = _rules_snapshot_count(raw)
        if assignment_count != 2:
            problems.append(f"[sentinel] {path.name} rules.js 引擎快照数={assignment_count}，期望恰好 2（主inline+WORKER_SRC）")
        # 主理人裁决：不写死 `rs3-` 字面量（§2.2(c) 防复发优先）。
        # 文本哨兵认 `rs${RULE_VERSION}-`（≥2）；运行时串由 T14 的 Q-PK 全等覆盖。
        sentinels = [
            ("threeLineCaptures", 2),
            ("pawn_three_line_capture", 2),
            ("p3l", 2),
            ("rs${RULE_VERSION}-", 2),
            ("||opt:", 2),
            ("||pool:", 2),
        ]
        for token, minimum in sentinels:
            count = raw.count(token)
            if count < minimum:
                problems.append(f"[sentinel] {path.name} {token} 计数={count} < {minimum}")
        # 内嵌规则内核快照不得残留 1.9.x 死开关
        block = _embedded_body(raw, "js/core/rules.js")
        if block is not None and "pawn_full_movement_at_base" in block:
            problems.append(f"[sentinel] {path.name} 内嵌 rules.js 残留 pawn_full_movement_at_base")
        # `_armorCaptures`：§0/§2.2(d) 要求保留软删甲分支，按「与唯一源计数一致」
        # 判定（详见交付报告未闭环项），而非字面 ==0。
        source_rules = read_source("js/core/rules.js")
        if block is not None and block.count("_armorCaptures") != source_rules.count("_armorCaptures"):
            problems.append(f"[sentinel] {path.name} 内嵌 rules.js 的 _armorCaptures 计数与唯一源不一致")

    if problems:
        for line in problems:
            print(line, file=sys.stderr)
        print("\n下一步：python scripts/build_webapp_bundle.py", file=sys.stderr)
        return 1
    print("bundle ok: 5 类产物同步 / 内嵌块 / 哨兵")
    print(f"  rulesHash={_sha256(rules_js)[:12]}… / html={len(html.encode('utf-8'))} B")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    html = build_html()
    if args.check:
        return check(html)
    sync(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
