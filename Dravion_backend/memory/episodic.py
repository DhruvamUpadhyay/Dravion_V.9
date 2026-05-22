"""
DRAVION v.9 — Episodic Memory (SQLite)

Stores recent conversation turns. No external services required.
Redis can replace this later if sub-millisecond latency matters.
"""
import sqlite3
import json
import os
from typing import List, Dict, Any
from core.config import config
from core.logger import log


class EpisodicMemory:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        db_path = os.path.join(config.data_dir, "episodic.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()
        log.info("episodic_memory_ready", backend="sqlite", path=db_path)

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_text TEXT NOT NULL,
                agent_text TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def add_interaction(self, user_text: str, agent_text: str):
        try:
            self.conn.execute(
                "INSERT INTO turns (user_text, agent_text) VALUES (?, ?)",
                (user_text, agent_text)
            )
            # Prune old turns beyond max
            self.conn.execute("""
                DELETE FROM turns WHERE id NOT IN (
                    SELECT id FROM turns ORDER BY id DESC LIMIT ?
                )
            """, (self.max_turns,))
            self.conn.commit()
        except Exception as e:
            log.error("episodic_write_error", error=str(e))

    def get_recent(self, n: int = 10) -> List[Dict[str, str]]:
        try:
            cursor = self.conn.execute(
                "SELECT user_text, agent_text FROM turns ORDER BY id DESC LIMIT ?",
                (n,)
            )
            rows = cursor.fetchall()
            # Reverse so oldest is first (chronological order)
            return [{"user": r[0], "agent": r[1]} for r in reversed(rows)]
        except Exception as e:
            log.error("episodic_read_error", error=str(e))
            return []

    def clear(self):
        self.conn.execute("DELETE FROM turns")
        self.conn.commit()
