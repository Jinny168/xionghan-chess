from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from typing import Any, Iterator


class AccountError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Account:
    id: int
    username: str
    display_name: str
    created_at: int

    def public(self) -> dict[str, Any]:
        return {"id": self.id, "username": self.username, "displayName": self.display_name,
                "createdAt": self.created_at}


class AccountStore:
    def __init__(self, path: str | Path | None = None):
        default_root = Path(os.getenv("XIONGHAN_DATA_DIR", Path.home() / ".xionghan-chess"))
        self.path = Path(path) if path else default_root / "cloud.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    preferences TEXT NOT NULL DEFAULT '{}',
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions(
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cloud_games(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    document TEXT NOT NULL,
                    favorite INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cloud_games_user_updated
                    ON cloud_games(user_id, updated_at DESC);
            """)

    def register(self, username: str, password: str, display_name: str = "") -> tuple[Account, str]:
        username = username.strip()
        if not (3 <= len(username) <= 32) or not all(ch.isalnum() or ch in "_-" for ch in username):
            raise AccountError("用户名须为 3-32 位字母、数字、下划线或连字符")
        if len(password) < 8:
            raise AccountError("密码至少需要 8 个字符")
        salt = secrets.token_hex(16)
        password_hash = self._password_hash(password, salt)
        now = int(time.time())
        try:
            with self._lock, self.connect() as db:
                cursor = db.execute(
                    "INSERT INTO users(username,display_name,password_hash,salt,created_at) VALUES(?,?,?,?,?)",
                    (username, display_name.strip() or username, password_hash, salt, now),
                )
                account = Account(cursor.lastrowid, username, display_name.strip() or username, now)
        except sqlite3.IntegrityError as exc:
            raise AccountError("用户名已存在") from exc
        return account, self._create_session(account.id)

    def login(self, username: str, password: str) -> tuple[Account, str]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        if row is None or not hmac.compare_digest(row["password_hash"],
                                                   self._password_hash(password, row["salt"])):
            raise AccountError("用户名或密码错误")
        account = self._account(row)
        return account, self._create_session(account.id)

    def authenticate(self, token: str) -> Account:
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            row = db.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
                "WHERE s.token_hash=? AND s.expires_at>?", (digest, int(time.time())),
            ).fetchone()
        if row is None:
            raise AccountError("登录已过期，请重新登录")
        return self._account(row)

    def logout(self, token: str) -> None:
        with self._lock, self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?",
                       (hashlib.sha256(token.encode()).hexdigest(),))

    def preferences(self, user_id: int) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT preferences FROM users WHERE id=?", (user_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    def save_preferences(self, user_id: int, preferences: dict[str, Any]) -> dict[str, Any]:
        clean = json.loads(json.dumps(preferences))
        with self._lock, self.connect() as db:
            row = db.execute("SELECT preferences FROM users WHERE id=?", (user_id,)).fetchone()
            current = json.loads(row[0]) if row and row[0] else {}
            current.update(clean)
            db.execute("UPDATE users SET preferences=? WHERE id=?",
                       (json.dumps(current, ensure_ascii=False), user_id))
        return current

    def list_games(self, user_id: int, favorite: bool | None = None) -> list[dict[str, Any]]:
        query = "SELECT id,title,favorite,created_at,updated_at FROM cloud_games WHERE user_id=?"
        params: list[Any] = [user_id]
        if favorite is not None:
            query += " AND favorite=?"
            params.append(int(favorite))
        query += " ORDER BY updated_at DESC"
        with self.connect() as db:
            rows = db.execute(query, params).fetchall()
        return [self._game_summary(row) for row in rows]

    def save_game(self, user_id: int, document: dict[str, Any], title: str = "",
                  game_id: int | None = None) -> dict[str, Any]:
        encoded = json.dumps(document, ensure_ascii=False)
        now = int(time.time())
        with self._lock, self.connect() as db:
            if game_id is None:
                cursor = db.execute(
                    "INSERT INTO cloud_games(user_id,title,document,created_at,updated_at) VALUES(?,?,?,?,?)",
                    (user_id, title.strip() or "匈汉棋局", encoded, now, now),
                )
                game_id = cursor.lastrowid
            else:
                cursor = db.execute(
                    "UPDATE cloud_games SET title=?,document=?,updated_at=? WHERE id=? AND user_id=?",
                    (title.strip() or "匈汉棋局", encoded, now, game_id, user_id),
                )
                if not cursor.rowcount:
                    raise AccountError("云端棋局不存在")
        return self.get_game(user_id, game_id)

    def get_game(self, user_id: int, game_id: int) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM cloud_games WHERE id=? AND user_id=?",
                             (game_id, user_id)).fetchone()
        if row is None:
            raise AccountError("云端棋局不存在")
        return self._game_summary(row) | {"document": json.loads(row["document"])}

    def favorite_game(self, user_id: int, game_id: int, favorite: bool) -> dict[str, Any]:
        with self._lock, self.connect() as db:
            cursor = db.execute("UPDATE cloud_games SET favorite=?,updated_at=? WHERE id=? AND user_id=?",
                                (int(favorite), int(time.time()), game_id, user_id))
            if not cursor.rowcount:
                raise AccountError("云端棋局不存在")
        return self.get_game(user_id, game_id)

    def delete_game(self, user_id: int, game_id: int) -> None:
        with self._lock, self.connect() as db:
            db.execute("DELETE FROM cloud_games WHERE id=? AND user_id=?", (game_id, user_id))

    def _create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self._lock, self.connect() as db:
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (int(time.time()),))
            db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                       (digest, user_id, int(time.time()) + 30 * 24 * 3600))
        return token

    @staticmethod
    def _password_hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 310_000).hex()

    @staticmethod
    def _account(row: sqlite3.Row) -> Account:
        return Account(int(row["id"]), str(row["username"]), str(row["display_name"]),
                       int(row["created_at"]))

    @staticmethod
    def _game_summary(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": int(row["id"]), "title": str(row["title"]),
                "favorite": bool(row["favorite"]), "createdAt": int(row["created_at"]),
                "updatedAt": int(row["updated_at"])}
