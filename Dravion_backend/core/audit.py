"""
DRAVION v.9 — Audit Logger

Immutable append-only log of every action DRAVION takes.
Query: "what did you do today?" → full activity report.
"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict
from core.config import config
from core.logger import log


class AuditLogger:
    def __init__(self):
        self.db_path = os.path.join(config.data_dir, "audit.db")
        self._init_db()
        log.info("audit_logger_ready")

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        c = self._conn()
        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action_type TEXT NOT NULL,
                tool_name TEXT,
                input_summary TEXT,
                output_summary TEXT,
                status TEXT DEFAULT 'success'
            )
        """)
        c.commit()
        c.close()

    def log_action(self, action_type: str, tool_name: str = None,
                   input_summary: str = "", output_summary: str = "", status: str = "success"):
        """Log an action. Called from execute_tool."""
        c = self._conn()
        c.execute(
            "INSERT INTO audit_log (action_type, tool_name, input_summary, output_summary, status) VALUES (?,?,?,?,?)",
            (action_type, tool_name, input_summary[:200], output_summary[:200], status)
        )
        c.commit()
        c.close()

    def get_today(self) -> str:
        """Get all actions from today."""
        today = datetime.now().strftime("%Y-%m-%d")
        c = self._conn()
        rows = c.execute(
            "SELECT timestamp, action_type, tool_name, input_summary, status FROM audit_log WHERE DATE(timestamp) = ? ORDER BY id",
            (today,)
        ).fetchall()
        c.close()
        if not rows:
            return "No actions logged today."
        lines = [f"Activity Report — {today} ({len(rows)} actions):"]
        for r in rows:
            time_str = r[0].split(" ")[1][:5] if " " in r[0] else r[0]
            tool = f" [{r[2]}]" if r[2] else ""
            lines.append(f"  {time_str} — {r[1]}{tool}: {r[3]}")
        return "\n".join(lines)

    def get_recent(self, hours: int = 24) -> str:
        """Get actions from the last N hours."""
        since = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        c = self._conn()
        rows = c.execute(
            "SELECT timestamp, action_type, tool_name, input_summary FROM audit_log WHERE timestamp >= ? ORDER BY id",
            (since,)
        ).fetchall()
        c.close()
        if not rows:
            return f"No actions in the last {hours} hours."
        lines = [f"Last {hours}h — {len(rows)} actions:"]
        for r in rows:
            tool = f" [{r[2]}]" if r[2] else ""
            lines.append(f"  {r[0]} — {r[1]}{tool}: {r[3]}")
        return "\n".join(lines)

    def get_stats(self) -> Dict:
        c = self._conn()
        total = c.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        today_count = c.execute(
            "SELECT COUNT(*) FROM audit_log WHERE DATE(timestamp) = DATE('now')"
        ).fetchone()[0]
        by_type = c.execute(
            "SELECT action_type, COUNT(*) FROM audit_log GROUP BY action_type ORDER BY COUNT(*) DESC LIMIT 10"
        ).fetchall()
        c.close()
        return {
            "total_actions": total,
            "today": today_count,
            "top_actions": {r[0]: r[1] for r in by_type}
        }


audit = AuditLogger()
