from __future__ import annotations

import json
from pathlib import Path

from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Move, Position
from xionghan_chess.i18n import t


ROOT = Path(__file__).resolve().parents[1]


def flattened_keys(value: object, prefix: str = "") -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, item in value.items():
            keys |= flattened_keys(item, f"{prefix}.{key}" if prefix else key)
        return keys
    return {prefix}


def test_locale_keys_are_paired() -> None:
    zh = json.loads((ROOT / "locales" / "zh-CN.json").read_text(encoding="utf-8"))
    en = json.loads((ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
    assert flattened_keys(zh) == flattened_keys(en)


def test_translation_falls_back_to_chinese() -> None:
    assert t("app.name", "fr-FR") == "匈汉象棋"
    assert t("missing.key", "en") == "missing.key"


def test_game_error_and_notation_can_use_english() -> None:
    game = Game("web", language="en")
    try:
        game.move(Move(Position(0, 0), Position(0, 1)))
    except GameError as exc:
        assert str(exc) == "Illegal move"
