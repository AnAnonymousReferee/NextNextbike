"""SQL-backed user store for BonnBike."""

import json
import sqlite3
from datetime import datetime, timedelta

from backend.security import (
    generate_api_key,
    generate_reset_token,
    hash_password,
    verify_password,
)

RESET_TOKEN_EXPIRE_HOURS = 1


class SQLiteUserStore:
    """Persist users in SQLite with hashed passwords only."""

    def __init__(self, db_path):
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
        self.initialize_schema()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def initialize_schema(self):
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL UNIQUE,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                favourites_json TEXT NOT NULL DEFAULT '[]',
                password_reset_token TEXT UNIQUE,
                password_reset_expires_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()

    def authenticate(self, username, password):
        row = self._user_by_username(username)
        return bool(row and verify_password(password, row["password_hash"]))

    def api_key_for(self, username):
        row = self._user_by_username(username)
        if row is None:
            return None
        return row["api_key"]

    def username_for_api_key(self, api_key):
        row = self.connection.execute(
            "SELECT username FROM users WHERE api_key = ?",
            (api_key,),
        ).fetchone()
        if row is None:
            return None
        return row["username"]

    def favourites_for_api_key(self, api_key):
        row = self.connection.execute(
            "SELECT favourites_json FROM users WHERE api_key = ?",
            (api_key,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["favourites_json"])

    def user_exists(self, username):
        return self._user_by_username(username) is not None

    def email_exists(self, email):
        row = self.connection.execute(
            "SELECT 1 FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        return row is not None

    def register(self, username, password, email):
        password_hash = hash_password(password)
        api_key = generate_api_key()
        try:
            self.connection.execute(
                """
                INSERT INTO users (api_key, username, password_hash, email)
                VALUES (?, ?, ?, ?)
                """,
                (api_key, username, password_hash, email),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("duplicate user or email") from exc
        return api_key

    def request_password_reset(self, email):
        row = self.connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if row is None:
            return None

        token = generate_reset_token()
        expires_at = (datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)).isoformat()
        self.connection.execute(
            "UPDATE users SET password_reset_token = ?, password_reset_expires_at = ? WHERE email = ?",
            (token, expires_at, email),
        )
        self.connection.commit()
        return token

    def reset_password(self, token, password):
        row = self.connection.execute(
            "SELECT id, password_reset_expires_at FROM users WHERE password_reset_token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return False

        expires_at = row["password_reset_expires_at"]
        if expires_at is None:
            return False

        try:
            expires = datetime.fromisoformat(expires_at)
        except (TypeError, ValueError):
            return False

        if expires < datetime.utcnow():
            return False

        password_hash = hash_password(password)
        self.connection.execute(
            "UPDATE users SET password_hash = ?, password_reset_token = NULL, password_reset_expires_at = NULL WHERE id = ?",
            (password_hash, row["id"]),
        )
        self.connection.commit()
        return True

    def add_favourite(self, api_key, bike_number):
        favourites = self.favourites_for_api_key(api_key)
        if favourites is None:
            return False
        if bike_number not in favourites:
            favourites.append(bike_number)
            self.connection.execute(
                "UPDATE users SET favourites_json = ? WHERE api_key = ?",
                (json.dumps(favourites), api_key),
            )
            self.connection.commit()
        return True

    def remove_favourite(self, api_key, bike_number):
        favourites = self.favourites_for_api_key(api_key)
        if favourites is None:
            return False
        if bike_number in favourites:
            favourites.remove(bike_number)
            self.connection.execute(
                "UPDATE users SET favourites_json = ? WHERE api_key = ?",
                (json.dumps(favourites), api_key),
            )
            self.connection.commit()
        return True

    def _user_by_username(self, username):
        return self.connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
