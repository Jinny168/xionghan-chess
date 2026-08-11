from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_LANGUAGE = "zh-CN"
SUPPORTED_LANGUAGES = ("zh-CN", "en")


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    normalized = language.replace("_", "-")
    if normalized.lower().startswith("zh"):
        return "zh-CN"
    if normalized.lower().startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE


def _locale_dir() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "locales",
        here.parents[2] / "locales",
        here.parents[3] / "locales",
        Path.cwd() / "locales",
    ]
    for candidate in candidates:
        if (candidate / f"{DEFAULT_LANGUAGE}.json").exists():
            return candidate
    return candidates[0]


@lru_cache(maxsize=None)
def catalog(language: str = DEFAULT_LANGUAGE) -> dict[str, Any]:
    lang = normalize_language(language)
    path = _locale_dir() / f"{lang}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        if lang != DEFAULT_LANGUAGE:
            return catalog(DEFAULT_LANGUAGE)
        return {}


def _lookup(data: dict[str, Any], key: str) -> Any:
    current: Any = data
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def t(key: str, language: str = DEFAULT_LANGUAGE, **params: object) -> str:
    value = _lookup(catalog(language), key)
    if value is None and normalize_language(language) != DEFAULT_LANGUAGE:
        value = _lookup(catalog(DEFAULT_LANGUAGE), key)
    if value is None:
        return key
    text = str(value)
    for name, param in params.items():
        text = text.replace("{" + name + "}", str(param))
    return text
