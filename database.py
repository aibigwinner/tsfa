import json
import sqlite3
import threading
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


class SQLiteStorage:
    def __init__(self, table_name):
        self.table = table_name
        self._lock = threading.Lock()
        DATA_DIR.mkdir(exist_ok=True)
        self._db_path = DATA_DIR / "bot.db"
        conn = sqlite3.connect(str(self._db_path))
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} ("
            "  id TEXT PRIMARY KEY,"
            "  data TEXT NOT NULL"
            ")"
        )
        conn.commit()
        conn.close()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, key, default=None):
        conn = self._connect()
        try:
            c = conn.execute(f"SELECT data FROM {self.table} WHERE id = ?", (key,))
            row = c.fetchone()
            if row:
                return json.loads(row["data"])
            return default
        finally:
            conn.close()

    def set(self, key, value):
        data = json.dumps(value, ensure_ascii=False)
        conn = self._connect()
        try:
            with self._lock:
                conn.execute(
                    f"INSERT OR REPLACE INTO {self.table} (id, data) VALUES (?, ?)",
                    (key, data),
                )
                conn.commit()
        finally:
            conn.close()

    def delete(self, key):
        conn = self._connect()
        try:
            conn.execute(f"DELETE FROM {self.table} WHERE id = ?", (key,))
            conn.commit()
        finally:
            conn.close()

    def all(self):
        conn = self._connect()
        try:
            c = conn.execute(f"SELECT id, data FROM {self.table}")
            return {row["id"]: json.loads(row["data"]) for row in c.fetchall()}
        finally:
            conn.close()

    def filter(self, predicate):
        return {k: v for k, v in self.all().items() if predicate(k, v)}


def get_db_path():
    return DATA_DIR / "bot.db"


def migrate_from_json():
    """Migrate existing JSON data to SQLite on first run."""
    for name in ("players", "battles", "tournaments", "challenges", "polls"):
        json_path = DATA_DIR / f"{name}.json"
        if json_path.exists():
            store = SQLiteStorage(name)
            if not store.all():
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, value in data.items():
                    store.set(key, value)
