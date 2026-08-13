from __future__ import annotations

import random
from typing import Literal

TauntScene = Literal["opening", "check", "victory", "defeat", "random"]

TAUNTS: dict[str, tuple[str, ...]] = {
    "opening": ("请多指教", "先行一步，静观其变。", "棋局方始，莫急。", "让我们看看谁更稳。"),
    "check": ("将军，留神脚下。", "这一手可不轻松。", "王前有变，慎之。", "请接招。"),
    "victory": ("承让，这局棋妙在收官。", "胜负已分，再来一局？", "多谢指教。", "这一局我先取胜。"),
    "defeat": ("好棋，我记下了。", "此局受教，再战。", "胜负常事，下一局见。", "这一手确实漂亮。"),
}


def taunts(scene: TauntScene = "random") -> list[str]:
    if scene == "random":
        return [item for values in TAUNTS.values() for item in values]
    return list(TAUNTS.get(scene, TAUNTS["opening"]))


def choose_taunt(scene: TauntScene = "random", seed: int | None = None) -> str:
    return random.Random(seed).choice(taunts(scene))
