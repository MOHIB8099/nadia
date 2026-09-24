"""Small SQLite chat history used by Luna V14."""

import sqlite3


class LunaMemory:
    def __init__(self, path="luna_memory.db"):
        self.path = path
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)")

    def save(self, role, content):
        if role not in ("user", "assistant"):
            raise ValueError("Invalid chat role")
        with sqlite3.connect(self.path, timeout=10) as connection:
            connection.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))

    def get_history(self, limit=6):
        with sqlite3.connect(self.path, timeout=10) as connection:
            rows = connection.execute("SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?", (max(0, int(limit)),)).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]
