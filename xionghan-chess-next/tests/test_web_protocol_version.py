r"""网页客户端的 `protocolVersion` 必须等于 `core/protocol.py::PROTOCOL_VERSION`。

## 为什么只能靠一个测试守着，而不是"收成一处常量"

`web/js/app.js` 里那一处 `protocolVersion:1` 是**手写死的**，不改的原因是两条替代
方案都不成立（都已论证过）：

- **构建期注入**：网页端是纯静态文件，直接由服务端原样下发，没有打包/预编译步骤，
  没有任何地方能"注入"一个数字进去；为一个常量引入构建链，代价远大于收益。
- **服务端下发**：`protocolVersion` 是**每条消息的封包字段**，服务端要先收到一条消息
  才知道对面是谁；让客户端"先问一次版本再发消息"等于给握手加第二次往返，还会在
  旧服务端上直接失效。版本号必须客户端自带。

所以口径是：**允许硬编码，但必须被一条测试盯着**。

也不建"跨语言常量登记表"：`tests/test_offline_rule_version.py` 的写法是"从两边各自
读出值再比"，不是"在第三个文件里再抄一份"。本文件同理 —— 值从 `protocol.PROTOCOL_VERSION`
读，字面量从 `web/js/app.js` 扫，两边直接比，没有第三份真相源。

## 扫的是什么

`protocolVersion\s*:\s*(\d+)` —— 只认**调用点**写法（`protocolVersion:1` /
`protocolVersion : 1`）。整行注释（`//` 开头）跳过；**引号内的字符串与行尾
`//` 注释也要先剥掉**：实测 `console.warn('… protocolVersion:9 …')` 与
`x = 1; // protocolVersion:9` 都会被光正则误判成调用点（假红），而它们不参与封包。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from xionghan_chess.core.protocol import PROTOCOL_VERSION

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "js" / "app.js"

# 只看"值"的写法：`protocolVersion:1`（冒号前后可有空格）
_CALL_SITE = re.compile(r"protocolVersion\s*:\s*(\d+)")
# 引号内的字符串（单/双引号，含转义）：先整段抹掉，避免把提示文案当调用点
_STRING = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")
# 行尾 `//` 注释：字符串已被抹掉，所以剩下的 `//` 都是注释（不会误伤 http://）
_TRAILING_COMMENT = re.compile(r"//.*$")


def _strip_noise(line: str) -> str:
    """抹掉引号内文本与行尾注释，只留代码骨架。

    为什么不是"跳过 `//` 开头的行"就够：质检实测过 `console.warn('… protocolVersion:9 …')`
    与 `x = 1; // protocolVersion:9` 两种写法都会被判成调用点（报第 420 行）——
    它们不参与封包，却是合法 JS。假红比不测更糟：会逼着后来人删断言。
    """
    return _TRAILING_COMMENT.sub("", _STRING.sub("''", line))


def _occurrences() -> list[tuple[int, int]]:
    """`(行号, 值)` 列表；整行注释跳过，字符串与行尾注释先剥掉。"""
    text = APP_JS.read_text(encoding="utf-8")
    found: list[tuple[int, int]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("//"):
            continue
        found.extend((number, int(match.group(1)))
                     for match in _CALL_SITE.finditer(_strip_noise(line)))
    return found


def test_app_js_has_at_least_one_protocol_version_call_site() -> None:
    """至少一处 —— 常量被删掉/改名/挪走时，下面的断言会"空集合对比"假绿。"""
    found = _occurrences()
    assert found, (
        f"{APP_JS} 里找不到任何 `protocolVersion: <n>` 调用点。\n"
        "  → 若只是改了写法：请同步更新 tests/test_web_protocol_version.py 的正则\n"
        "  → 若真的不再发这个字段：core/protocol.py::Envelope 会拒收，先改协议再删测试"
    )


def test_every_hardcoded_protocol_version_matches_python() -> None:
    """`web/js/app.js` 里所有 `protocolVersion: <n>` 都必须等于 `PROTOCOL_VERSION`。"""
    found = _occurrences()
    values = {value for _number, value in found}
    offenders = [(number, value) for number, value in found if value != PROTOCOL_VERSION]
    if offenders:
        where = "\n".join(f"  第 {number} 行：protocolVersion:{value}"
                          for number, value in offenders)
        pytest.fail(
            f"网页端写死的协议版本与 Python 不一致（Python 是 {PROTOCOL_VERSION}）：\n"
            f"{where}\n"
            "  → 改哪一行：上面列出的行\n"
            f"  → 改什么：`protocolVersion:<n>` → `protocolVersion:{PROTOCOL_VERSION}`\n"
            "  → 为什么：服务端按 `Envelope.protocol_version`（Literal）校验，"
            "版本对不上会以 1002 关闭连接；客户端自己发错版本时，报错现场在服务端，"
            "很难回溯到这里。",
            pytrace=False,
        )
    assert values == {PROTOCOL_VERSION}, (
        f"扫描结果异常：{sorted(values)} != {{{PROTOCOL_VERSION}}}（共 {len(found)} 处）"
    )
