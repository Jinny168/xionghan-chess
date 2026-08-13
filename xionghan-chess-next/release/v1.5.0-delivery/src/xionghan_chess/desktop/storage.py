from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from xionghan_chess.core.game import Game
from xionghan_chess.core.storage import game_document, game_from_content, game_from_document

from .config import config_path


def save_game(game: Game, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(game_document(game), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_game(path: str | Path) -> Game:
    return game_from_content(Path(path).read_text(encoding="utf-8"))


def autosave_game(game: Game) -> Path:
    folder = config_path().parent / "games"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return save_game(game, folder / f"xionghan_{stamp}.xhgame")


def statistics_path() -> Path:
    return config_path().parent / "statistics.json"


def _statistics_defaults() -> dict[str, Any]:
    return {
        "games": 0, "wins": 0, "losses": 0, "draws": 0, "moves": 0,
        "totalTimeMs": 0, "fastestWinMs": 0,
        "winStreak": {"current": 0, "max": 0},
        "perColor": {
            "red": {"games": 0, "wins": 0},
            "black": {"games": 0, "wins": 0},
        },
    }


def load_statistics() -> dict[str, Any]:
    defaults = _statistics_defaults()
    try:
        data = json.loads(statistics_path().read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return defaults
        result = defaults | {key: int(data.get(key, defaults[key])) for key in (
            "games", "wins", "losses", "draws", "moves", "totalTimeMs", "fastestWinMs"
        )}
        streak = data.get("winStreak", {})
        if isinstance(streak, dict):
            result["winStreak"] = {
                "current": int(streak.get("current", 0)),
                "max": int(streak.get("max", 0)),
            }
        per_color = data.get("perColor", {})
        if isinstance(per_color, dict):
            for color in ("red", "black"):
                values = per_color.get(color, {})
                if isinstance(values, dict):
                    result["perColor"][color] = {
                        "games": int(values.get("games", 0)),
                        "wins": int(values.get("wins", 0)),
                    }
        return result
    except (OSError, ValueError, TypeError):
        return defaults


def record_result(game: Game, human_color: str) -> dict[str, Any]:
    stats = load_statistics()
    duration_ms = sum(max(0, record.elapsed_ms) for record in game.state.history)
    won = bool(game.state.winner and game.state.winner.value == human_color)
    stats["games"] += 1
    stats["moves"] += len(game.state.history)
    stats["totalTimeMs"] += duration_ms
    color_stats = stats["perColor"].setdefault(human_color, {"games": 0, "wins": 0})
    color_stats["games"] += 1
    if game.state.draw:
        stats["draws"] += 1
        stats["winStreak"]["current"] = 0
    elif won:
        stats["wins"] += 1
        color_stats["wins"] += 1
        stats["winStreak"]["current"] += 1
        stats["winStreak"]["max"] = max(stats["winStreak"]["max"], stats["winStreak"]["current"])
        if duration_ms and (not stats["fastestWinMs"] or duration_ms < stats["fastestWinMs"]):
            stats["fastestWinMs"] = duration_ms
    else:
        stats["losses"] += 1
        stats["winStreak"]["current"] = 0
    statistics_path().parent.mkdir(parents=True, exist_ok=True)
    statistics_path().write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def reset_statistics() -> None:
    statistics_path().parent.mkdir(parents=True, exist_ok=True)
    statistics_path().write_text(json.dumps(_statistics_defaults(), ensure_ascii=False, indent=2), encoding="utf-8")
