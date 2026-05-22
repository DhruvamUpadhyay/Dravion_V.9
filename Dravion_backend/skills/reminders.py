"""
DRAVION v.9 — Reminder & Alarm System

Background scheduler for time-based triggers:
  - Set reminders ("remind me in 30 minutes to call mom")
  - Set alarms ("wake me up at 7 AM")
  - List/cancel pending reminders
  - Persistent across restarts (SQLite backed)
"""
import asyncio
import sqlite3
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from core.config import config
from core.logger import log


class ReminderSystem:
    def __init__(self):
        self.db_path = os.path.join(config.data_dir, "reminders.db")
        self._init_db()
        self._running = False
        self._callbacks = []  # [(callback_fn)] called when reminder fires
        log.info("reminder_system_ready")

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        c = self._conn()
        c.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                fire_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                fired INTEGER DEFAULT 0,
                type TEXT DEFAULT 'reminder'
            )
        """)
        c.commit()
        c.close()

    def on_fire(self, callback):
        """Register a callback for when a reminder fires."""
        self._callbacks.append(callback)

    def add_reminder(self, message: str, fire_at: datetime, rtype: str = "reminder") -> str:
        c = self._conn()
        c.execute(
            "INSERT INTO reminders (message, fire_at, type) VALUES (?, ?, ?)",
            (message, fire_at.strftime("%Y-%m-%d %H:%M:%S"), rtype)
        )
        c.commit()
        rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        c.close()
        time_str = fire_at.strftime("%I:%M %p on %b %d")
        return f"Reminder #{rid} set for {time_str}: {message}"

    def add_relative(self, message: str, minutes: int = 0, hours: int = 0) -> str:
        """Add a reminder relative to now."""
        fire_at = datetime.now() + timedelta(minutes=minutes, hours=hours)
        return self.add_reminder(message, fire_at)

    def parse_and_add(self, text: str) -> str:
        """
        Parse natural-ish time expressions:
          "in 30 minutes", "in 2 hours", "at 7:30 PM", "at 14:00"
        """
        now = datetime.now()

        # "in X minutes/hours"
        m = re.search(r'in\s+(\d+)\s*(min|minute|minutes|hr|hour|hours)', text, re.I)
        if m:
            val = int(m.group(1))
            unit = m.group(2).lower()
            if 'min' in unit:
                fire_at = now + timedelta(minutes=val)
            else:
                fire_at = now + timedelta(hours=val)
            msg = re.sub(r'in\s+\d+\s*\w+', '', text).strip()
            msg = re.sub(r'^(to|that|about)\s+', '', msg, flags=re.I).strip()
            return self.add_reminder(msg or "Reminder", fire_at)

        # "at HH:MM AM/PM" or "at HH:MM"
        m = re.search(r'at\s+(\d{1,2}):(\d{2})\s*(am|pm)?', text, re.I)
        if m:
            h, mn = int(m.group(1)), int(m.group(2))
            ampm = (m.group(3) or "").lower()
            if ampm == "pm" and h < 12:
                h += 12
            elif ampm == "am" and h == 12:
                h = 0
            fire_at = now.replace(hour=h, minute=mn, second=0, microsecond=0)
            if fire_at <= now:
                fire_at += timedelta(days=1)
            msg = re.sub(r'at\s+\d{1,2}:\d{2}\s*(?:am|pm)?', '', text, flags=re.I).strip()
            msg = re.sub(r'^(to|that|about)\s+', '', msg, flags=re.I).strip()
            return self.add_reminder(msg or "Alarm", fire_at, rtype="alarm")

        return "Couldn't parse the time. Try: 'in 30 minutes' or 'at 7:30 PM'."

    def list_pending(self) -> str:
        c = self._conn()
        rows = c.execute(
            "SELECT id, message, fire_at, type FROM reminders WHERE fired=0 ORDER BY fire_at"
        ).fetchall()
        c.close()
        if not rows:
            return "No pending reminders."
        lines = []
        for r in rows:
            try:
                dt = datetime.strptime(r[2], "%Y-%m-%d %H:%M:%S")
                time_str = dt.strftime("%I:%M %p, %b %d")
            except:
                time_str = r[2]
            lines.append(f"  #{r[0]} [{r[3].upper()}] {r[1]} — {time_str}")
        return "Pending reminders:\n" + "\n".join(lines)

    def cancel(self, reminder_id: int) -> str:
        c = self._conn()
        r = c.execute("SELECT message FROM reminders WHERE id=? AND fired=0", (reminder_id,)).fetchone()
        if not r:
            return f"No active reminder #{reminder_id}."
        c.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
        c.commit()
        c.close()
        return f"Cancelled reminder #{reminder_id}: {r[0]}"

    # ── Background Checker ──

    async def start_checker(self):
        """Run in background — checks every 30 seconds for due reminders."""
        self._running = True
        log.info("reminder_checker_started")
        while self._running:
            try:
                self._check_and_fire()
            except Exception as e:
                log.error("reminder_check_error", error=str(e))
            await asyncio.sleep(30)

    def _check_and_fire(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c = self._conn()
        due = c.execute(
            "SELECT id, message, type FROM reminders WHERE fired=0 AND fire_at <= ?", (now,)
        ).fetchall()
        for r in due:
            c.execute("UPDATE reminders SET fired=1 WHERE id=?", (r[0],))
            log.info("reminder_fired", id=r[0], message=r[1])
            for cb in self._callbacks:
                try:
                    cb(r[1], r[2])
                except:
                    pass
        c.commit()
        c.close()

    def stop(self):
        self._running = False


reminder_system = ReminderSystem()
