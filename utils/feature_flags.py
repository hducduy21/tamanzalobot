import sqlite3
import threading

_DB_PATH = 'database/database.sql'
_lock = threading.Lock()

_DEFAULTS = {
    'notify_sync_pass': True,
    'notify_edit_pass': True,
}

DESCRIPTIONS = {
    'notify_sync_pass': 'Gửi thông báo Zalo khi sync pass từ sheet nguồn -> quản lý',
    'notify_edit_pass': 'Gửi thông báo Zalo khi có cập nhật pass ở file quản lý',
}


def _connect():
    return sqlite3.connect(_DB_PATH, check_same_thread=False)


def _init():
    with _lock:
        conn = _connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feature_flags (
                    name  TEXT PRIMARY KEY,
                    value INTEGER NOT NULL DEFAULT 1
                )
            """)
            for name, default in _DEFAULTS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO feature_flags (name, value) VALUES (?, ?)",
                    (name, 1 if default else 0),
                )
            conn.commit()
        finally:
            conn.close()


def get_flag(name: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT value FROM feature_flags WHERE name = ?", (name,)
            ).fetchone()
        finally:
            conn.close()
    if row is None:
        return _DEFAULTS.get(name, False)
    return bool(row[0])


def set_flag(name: str, value: bool) -> bool:
    """Returns False if flag name is unknown."""
    if name not in _DEFAULTS:
        return False
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO feature_flags (name, value) VALUES (?, ?)",
                (name, 1 if value else 0),
            )
            conn.commit()
        finally:
            conn.close()
    return True


def get_all_flags() -> dict:
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute("SELECT name, value FROM feature_flags").fetchall()
        finally:
            conn.close()
    result = {name: _DEFAULTS[name] for name in _DEFAULTS}
    for name, value in rows:
        if name in result:
            result[name] = bool(value)
    return result


_init()
