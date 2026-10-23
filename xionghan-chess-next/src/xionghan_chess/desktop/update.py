"""版本检查：判断远端是否有新版本，并把「下载页」交给浏览器。

设计取舍（迭代计划 S2-3 / 问题 P1-H）：
- **只做「检查 + 打开下载页」，不做静默自更新。** 自动下载并替换可执行文件需要
  代码签名与回滚机制，二者都还没有（S2-1 尚未落地）；在没有签名的前提下做自更新，
  等于给用户装了一条可被中间人替换的更新通道。
- **不需要 PySide6。** 版本比较、清单解析、网络请求都在这里，UI 只负责展示，
  这样这些逻辑能被普通单测覆盖（与 `net.py` 同一分工）。
- **失败不抛异常。** 检查更新是「顺手看一眼」，离线/被墙/限流都属常态，
  统一折成 `CheckResult(status="error")` 由界面用一句话说明。
"""

from __future__ import annotations

from dataclasses import dataclass

from . import net

# GitHub Releases 是当前唯一的分发出口（打包产物由 CI 上传）。
# 用 latest（不含预发布）而不是列表接口：语义就是「最新正式版」。
RELEASES_URL = "https://api.github.com/repos/Jinny168/xionghan-chess/releases/latest"
DOWNLOAD_PAGE = "https://github.com/Jinny168/xionghan-chess/releases/latest"

STATUS_UPDATE = "update"
STATUS_LATEST = "latest"
STATUS_ERROR = "error"


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    """远端最新版本的描述。`url` 是给用户点开的网页，不是 API 地址。"""

    version: str
    url: str
    notes: str = ""
    published_at: str = ""

    @property
    def label(self) -> str:
        """给人看的版本号。GitHub tag 普遍带 `v` 前缀，直接显示会变成「最新 v9.9.9」。"""
        return self.version.strip().lstrip("vV")


@dataclass(frozen=True, slots=True)
class CheckResult:
    status: str
    info: UpdateInfo | None = None
    error: str = ""


def parse_version(text: str) -> tuple[int, ...]:
    """把 `v1.7.1` / `1.7` / `1.7.0-rc1` 折成可比较的数字元组。

    预发布与构建元数据（`-rc1`、`+build5`）一律丢掉：本函数只回答
    「谁的版本号更大」，不回答「这个预发布能不能装」。遇到无法解析的段
    就地截断，避免 `int("")` 抛异常把整个检查流程打断。
    """
    core = str(text).strip().lstrip("vV").split("-")[0].split("+")[0]
    parts: list[int] = []
    for chunk in core.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def is_newer(remote: str, local: str) -> bool:
    """远端是否比本地新。位数不同时右侧补 0，`1.7` 与 `1.7.0` 视为相同。"""
    left, right = parse_version(remote), parse_version(local)
    if not left or not right:
        return False
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) > right + (0,) * (width - len(right))


def parse_release(payload: object) -> UpdateInfo | None:
    """解析 GitHub Releases 响应，也兼容自建静态清单。

    自建清单形如 `{"version": "1.7.1", "url": "https://…", "notes": "…"}`，
    将来换分发渠道不必改客户端。草稿/预发布返回 None —— 它们不该推给普通用户。
    """
    if not isinstance(payload, dict):
        return None
    if payload.get("draft") or payload.get("prerelease"):
        return None
    raw_version = payload.get("version") or payload.get("tag_name") or ""
    if not isinstance(raw_version, str) or not parse_version(raw_version):
        return None
    url = ""
    for key in ("html_url", "download_url", "url"):
        candidate = payload.get(key)
        if not isinstance(candidate, str) or not candidate.startswith("http"):
            continue
        # GitHub API 的 `url` 字段指向 api.github.com，点开是一坨 JSON，不是下载页。
        if "api.github.com" in candidate:
            continue
        url = candidate
        break
    notes = payload.get("notes") or payload.get("body") or ""
    published = payload.get("published_at") or payload.get("publishedAt") or ""
    return UpdateInfo(
        version=str(raw_version).strip(),
        url=url or DOWNLOAD_PAGE,
        notes=str(notes)[:2000],
        published_at=str(published),
    )


def evaluate(payload: object, current: str) -> CheckResult:
    """把「已拿到的清单」折成结论。

    单独拆出来是因为桌面端走的是异步链路：HTTP 由 `HttpWorker` 取回、回调里只剩
    解析后的 JSON，`check_for_update` 那条同步路径不适用。两处共用本函数，
    保证界面显示的结论与单测断言的结论是同一条代码算出来的。
    """
    info = parse_release(payload)
    if info is None:
        return CheckResult(STATUS_ERROR, error="更新信息格式无法识别")
    status = STATUS_UPDATE if is_newer(info.version, current) else STATUS_LATEST
    return CheckResult(status, info)


def check_for_update(current: str, *, transport: net.Transport | None = None,
                     url: str = RELEASES_URL) -> CheckResult:
    """查询远端最新版并与 `current` 比较。任何失败都折成 error，不抛。"""
    try:
        payload = net.request_json(url, transport=transport)
    except Exception as exc:  # noqa: BLE001 —— 网络层异常种类多，界面只关心"没查到"
        return CheckResult(STATUS_ERROR, error=str(exc) or exc.__class__.__name__)
    return evaluate(payload, current)
