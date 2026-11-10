"""`ruleVersion`：走法语义的版本号，与容器格式/重复局面键**正交**。

## 为什么需要第三个版本号

2.0.0 改的是**走法**（巡禁竖移、兵底线开关默认关），存档结构一个字节没动 ——
所以 `formatVersion` 不 bump，`positionKeyVersion` 也不 bump。但两端如果各跑一套
走法，症状不是"打不开文件"，而是"同一张盘上我这能走、服务器说非法"：
这种报告最难查，因为两边的日志都是合法的。

于是分三层各管一件事：
- `formatVersion`       —— 容器结构（能不能打开）；
- `positionKeyVersion`  —— 重复局面键（三次重复判得对不对）；
- `ruleVersion`         —— 走法语义（这步棋合不合法、房间能不能一起下）。

## 三条硬口径

1. 棋谱**写入** `ruleVersion`；旧档缺省 1；比当前**更新**的档拒绝载入
   （读不懂就别硬读），比当前更旧的照常载入（局面是局面，合法着法是算出来的）。
2. 联机建房/加入必须与服务器一致；不一致给**专用错误码**（HTTP 409 +
   `code="rule_version_mismatch"`），不是通用 400。
3. 远端客户端**不声明**版本 = 声明 1（2.0.0 之前所有构建都是 1），照样拒绝 ——
   旧缓存网页正好走这条路，它必须被拦在建房那一刻。

## 为什么"同进程调用不校验"

`RoomManager.create(rule_version=None)` 是同进程调用方（单测、内部脚本、AI 房自建），
它跟服务器是同一份代码同一个常量，不可能不一致。远端客户端的"没声明"由 HTTP 层
翻译成 1 再传进来，两者不是一回事 —— 这是本节最容易看错的地方。
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from xionghan_chess.core.game import Game
from xionghan_chess.core.profiles import RULE_VERSION
from xionghan_chess.core.storage import game_document, game_from_document
from xionghan_chess.service.app import app


def test_document_carries_the_rule_version_but_not_a_new_format_version() -> None:
    document = game_document(Game("web"))
    assert document["ruleVersion"] == RULE_VERSION == 2
    # 本轮只改走法语义：容器结构与重复局面键都不该动
    assert document["formatVersion"] == 1
    assert document["positionKeyVersion"] >= 1


def test_older_document_still_loads_and_newer_document_is_refused() -> None:
    """旧档（缺 ruleVersion 或 =1）能读；来自更新版本的档不能硬读。"""
    document = game_document(Game("web"))

    legacy = dict(document)
    legacy.pop("ruleVersion")
    assert game_from_document(legacy).profile.id == "web", "旧档（无字段 = 1）必须照常载入"

    from_the_future = dict(document, ruleVersion=RULE_VERSION + 1)
    with pytest.raises(ValueError, match="更新的规则版本"):
        game_from_document(from_the_future)


def _create(client: TestClient, **overrides):
    payload = {"profileId": "web", "mode": "online", "playerName": "red"}
    payload.update(overrides)
    return client.post("/api/rooms", json=payload)


def test_mismatched_rule_version_is_refused_with_a_dedicated_code() -> None:
    with TestClient(app) as client:
        stale = _create(client, ruleVersion=RULE_VERSION - 1)
        assert stale.status_code == 409, stale.text
        assert stale.json()["detail"]["code"] == "rule_version_mismatch"
        assert stale.json()["detail"]["serverRuleVersion"] == RULE_VERSION

        # 旧客户端根本不发这个字段 → HTTP 层按 1 处理 → 同样拒绝（这是这道门的意义）
        silent = _create(client)
        assert silent.status_code == 409, silent.text
        assert silent.json()["detail"]["code"] == "rule_version_mismatch"

        fresh = _create(client, ruleVersion=RULE_VERSION)
        assert fresh.status_code == 200, fresh.text
        assert fresh.json()["ruleVersion"] == RULE_VERSION


def test_join_checks_the_rule_version_too() -> None:
    with TestClient(app) as client:
        created = _create(client, ruleVersion=RULE_VERSION).json()
        room_id = created["roomId"]
        stale = client.post(f"/api/rooms/{room_id}/join", json={"playerName": "black", "ruleVersion": RULE_VERSION - 1})
        assert stale.status_code == 409, stale.text
        assert stale.json()["detail"]["code"] == "rule_version_mismatch"
        ok = client.post(f"/api/rooms/{room_id}/join", json={"playerName": "black", "ruleVersion": RULE_VERSION})
        assert ok.status_code == 200, ok.text


def test_protocol_version_has_a_single_definition() -> None:
    """`core/protocol.py` 与 `desktop/net.py` 曾各写一份 `PROTOCOL_VERSION = 1`。

    两份同名常量分居两处，改一处另一处悄悄留在旧版本 —— 症状是"首帧就被判协议不符"，
    而两边代码都"写着 1"。现在只认 protocol 那一份。
    """
    from xionghan_chess.core import protocol
    from xionghan_chess.desktop import net

    assert net.PROTOCOL_VERSION == protocol.PROTOCOL_VERSION
    with open(net.__file__, encoding="utf-8") as handle:
        code_lines = [line for line in handle.read().splitlines() if not line.lstrip().startswith("#")]
    assert not any(re.match(r"\s*PROTOCOL_VERSION\s*=", line) for line in code_lines), (
        "net.py 又写死了一份协议版本（注释里提到可以，赋值不行）"
    )


def test_position_key_version_is_4_and_the_digest_names_the_rule_set() -> None:
    """硬规则没有开关，只能靠 key 里的 `rs{规则集版本}-` 前缀进账本。

    不加前缀的话，同一盘面在 1.9 与 2.0 下会算出**完全相同的 key** ——
    升级用户的中途局会带着旧规则的计数继续跑，三次重复判和就会误判。
    """
    from xionghan_chess.core.profiles import RULE_VERSION
    from xionghan_chess.core.rules import POSITION_KEY_VERSION

    assert POSITION_KEY_VERSION == 4
    key = Game("web").rules.position_key(Game("web").state)
    assert f"||opt:rs{RULE_VERSION}-" in key, key


def test_upgrade_rebuilds_the_old_ledger_instead_of_reusing_it() -> None:
    """升级验收：打开旧存档时，`positionCounts` 必须**重算**而不是原样带过来。

    `GAME_BREAKING_KEYS` 只管配置，管不到硬规则 —— 升级后 config 一字未变，
    不会触发"改规则须重开对局"，于是中途局会带着旧规则的账本继续跑。
    `game_from_document` 里"键版本落后就按当前键重算"的机制就是为这一刻准备的，
    这条测试钉住它：旧键（v3，没有 `rs` 前缀）必须被丢掉，账本按新键重建。
    """
    game = Game("web")
    document = game_document(game)
    document["positionKeyVersion"] = 3  # 旧键格式（无 rs 前缀）
    document["state"]["positionCounts"] = {"stale|old-format||opt:p3l0-promo1-self1": 2}

    loaded = game_from_document(document)
    keys = set(loaded.state.position_counts)
    assert not any("stale" in key for key in keys), "旧账本被原样带过来了 —— 会误判三次重复"
    assert keys == {loaded.rules.position_key(loaded.state)}, "账本应按当前键重建"
