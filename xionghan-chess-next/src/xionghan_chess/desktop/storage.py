from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from xionghan_chess.core.game import Game
from xionghan_chess.core.storage import FORMAT_VERSION, game_document, game_from_document

from .config import config_path


def save_game(game: Game, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(game_document(game), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_game(path: str | Path) -> Game:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("棋谱文件内容无效")
    return game_from_document(data)


def autosave_game(game: Game) -> Path:
    folder = config_path().parent / "games"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return save_game(game, folder / f"xionghan_{stamp}.xhgame")


def statistics_path() -> Path:
    return config_path().parent / "statistics.json"


def load_statistics() -> dict[str, int]:
    defaults = {"games": 0, "wins": 0, "losses": 0, "draws": 0, "moves": 0}
    try:
        data = json.loads(statistics_path().read_text(encoding="utf-8"))
        return {key: int(data.get(key, value)) for key, value in defaults.items()}
    except (OSError, ValueError, TypeError):
        return defaults


def record_result(game: Game, human_color: str) -> dict[str, int]:
    stats = load_statistics()
    stats["games"] += 1
    stats["moves"] += len(game.state.history)
    if game.state.draw:
        stats["draws"] += 1
    elif game.state.winner and game.state.winner.value == human_color:
        stats["wins"] += 1
    else:
        stats["losses"] += 1
    statistics_path().write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def reset_statistics() -> None:
    statistics_path().write_text(json.dumps(load_statistics() | {"games": 0, "wins": 0, "losses": 0, "draws": 0, "moves": 0}, ensure_ascii=False, indent=2), encoding="utf-8")
