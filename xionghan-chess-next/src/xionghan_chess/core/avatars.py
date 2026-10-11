from __future__ import annotations

import re


BUILTIN_AVATARS = tuple(f"avatar-{index:02d}" for index in range(1, 10))
_BUILTIN_PATTERN = re.compile(r"^builtin:(avatar-\d{2})$")


def normalize_avatar(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    match = _BUILTIN_PATTERN.fullmatch(value)
    if match and match.group(1) in BUILTIN_AVATARS:
        return value
    if value.startswith(("https://", "http://")) and len(value) <= 500:
        return value
    raise ValueError("头像须选择内置头像或使用 http/https URL")


def avatar_asset_name(value: str) -> str | None:
    match = _BUILTIN_PATTERN.fullmatch(value.strip())
    return f"{match.group(1)}.webp" if match and match.group(1) in BUILTIN_AVATARS else None
