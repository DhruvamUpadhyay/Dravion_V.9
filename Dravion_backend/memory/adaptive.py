"""
DRAVION v.9 — Adaptive Memory

DRAVION's personality memory. This is NOT chat history — this is
how DRAVION learns who Boss IS. Preferences, behaviors, habits,
likes, dislikes, patterns. All extracted automatically from
conversations and reinforced over time.

Storage: SQLite (lightweight, persistent, no external deps)
Extraction: LLM-powered (runs after each conversation turn)
Injection: Top-K relevant facts injected into system prompt
"""
import sqlite3
import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from core.config import config
from core.logger import log


class AdaptiveMemory:
    """
    Learns about the user over time. Categories:
      - preference: "Boss prefers dark mode", "Boss likes Python over JS"
      - behavior:   "Boss is a night owl, active 10PM-2AM"
      - fact:       "Boss's brother is Riyansh, age 4"
      - dislike:    "Boss hates verbose responses"
      - habit:      "Boss usually asks for weather in the morning"
      - mood:       "Boss seems stressed about exams"
      - project:    "Boss is working on AlgoPilot crypto platform"
    """

    CATEGORIES = ["preference", "behavior", "fact", "dislike", "habit", "mood", "project"]

    def __init__(self):
        self.db_path = os.path.join(config.data_dir, "adaptive_memory.db")
        self._init_db()
        self._extract_queue: list = []
        log.info("adaptive_memory_ready", path=self.db_path)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        c = self._conn()
        c.execute("""
            CREATE TABLE IF NOT EXISTS learned_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL UNIQUE,
                confidence REAL DEFAULT 0.5,
                times_reinforced INTEGER DEFAULT 1,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'conversation'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS personality_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.commit()
        c.close()

    # ─── Store ───

    def store_fact(self, category: str, content: str, source: str = "conversation"):
        """Store a learned fact. If it already exists, reinforce it."""
        if category not in self.CATEGORIES:
            category = "fact"

        c = self._conn()
        existing = c.execute(
            "SELECT id, confidence, times_reinforced FROM learned_facts WHERE content = ?",
            (content,)
        ).fetchone()

        if existing:
            # Reinforce — increase confidence
            new_conf = min(1.0, existing[1] + 0.1)
            new_count = existing[2] + 1
            c.execute(
                "UPDATE learned_facts SET confidence=?, times_reinforced=?, last_seen=CURRENT_TIMESTAMP WHERE id=?",
                (new_conf, new_count, existing[0])
            )
            log.debug("fact_reinforced", content=content[:60], confidence=new_conf)
        else:
            c.execute(
                "INSERT INTO learned_facts (category, content, source) VALUES (?, ?, ?)",
                (category, content, source)
            )
            log.debug("fact_learned", category=category, content=content[:60])

        c.commit()
        c.close()

    def store_profile(self, key: str, value: str):
        """Update a top-level personality profile entry."""
        c = self._conn()
        c.execute(
            "INSERT OR REPLACE INTO personality_profile (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )
        c.commit()
        c.close()

    # ─── Recall ───

    def get_all_facts(self, min_confidence: float = 0.3) -> List[Dict]:
        """Get all learned facts above a confidence threshold."""
        c = self._conn()
        rows = c.execute(
            "SELECT category, content, confidence, times_reinforced FROM learned_facts WHERE confidence >= ? ORDER BY confidence DESC, times_reinforced DESC",
            (min_confidence,)
        ).fetchall()
        c.close()
        return [{"category": r[0], "content": r[1], "confidence": r[2], "reinforced": r[3]} for r in rows]

    def get_facts_by_category(self, category: str) -> List[Dict]:
        c = self._conn()
        rows = c.execute(
            "SELECT content, confidence, times_reinforced FROM learned_facts WHERE category=? ORDER BY confidence DESC",
            (category,)
        ).fetchall()
        c.close()
        return [{"content": r[0], "confidence": r[1], "reinforced": r[2]} for r in rows]

    def get_profile(self) -> Dict[str, str]:
        c = self._conn()
        rows = c.execute("SELECT key, value FROM personality_profile").fetchall()
        c.close()
        return {r[0]: r[1] for r in rows}

    def get_context_injection(self, max_facts: int = 15) -> str:
        """
        Build a context string to inject into the system prompt.
        This is how DRAVION 'remembers' who Boss is.
        """
        facts = self.get_all_facts(min_confidence=0.4)[:max_facts]
        if not facts:
            return ""

        lines = ["Things I know about Boss (learned from conversations):"]
        for f in facts:
            tag = f["category"].upper()
            lines.append(f"  [{tag}] {f['content']}")

        profile = self.get_profile()
        if profile:
            lines.append("\nBoss's profile summary:")
            for k, v in profile.items():
                lines.append(f"  {k}: {v}")

        return "\n".join(lines)

    # ─── Decay ───

    def decay_old_moods(self, days: int = 7):
        """Moods older than N days lose confidence — they're transient."""
        c = self._conn()
        c.execute("""
            UPDATE learned_facts
            SET confidence = MAX(0, confidence - 0.2)
            WHERE category = 'mood'
            AND julianday('now') - julianday(last_seen) > ?
        """, (days,))
        c.execute("DELETE FROM learned_facts WHERE confidence <= 0")
        c.commit()
        c.close()

    # ─── LLM-Powered Extraction ───

    _turn_counter = 0  # Class-level counter to throttle extraction

    async def extract_from_conversation(self, user_msg: str, agent_msg: str):
        """
        After each conversation turn, ask the LLM to extract any
        learnable facts about the user. Uses LOCAL model first to save API quota.
        Runs in background — never blocks.

        Throttled: only runs every 3rd turn, and skips short messages.
        """
        # Skip short messages — greetings, confirmations, etc. have no signal
        if len(user_msg.strip()) < 15:
            return

        # Only extract every 3rd turn to reduce noise and save compute
        AdaptiveMemory._turn_counter += 1
        if AdaptiveMemory._turn_counter % 3 != 0:
            return

        try:
            from openai import AsyncOpenAI

            extraction_prompt = f"""You are a fact extraction module for an AI assistant named DRAVION. The user is called "Boss" or "Dhruvam" — he is a human, the owner and operator.

USER said: "{user_msg}"
ASSISTANT (DRAVION) replied: "{agent_msg}"

Extract ONLY facts about the USER (Dhruvam/Boss), NOT about the assistant. Categories:
- preference: what Boss likes/prefers
- behavior: patterns in how Boss acts
- fact: concrete personal facts about Boss (people, places, dates)
- dislike: things Boss dislikes or avoids
- habit: recurring behaviors of Boss
- mood: Boss's current emotional state (transient)
- project: what Boss is actively working on (MUST be explicitly stated by Boss, never inferred)

CRITICAL RULES:
- ONLY extract facts the USER explicitly stated. NEVER infer or guess.
- Do NOT extract facts about the ASSISTANT. "Boss" refers to the user, not the assistant.
- Do NOT fabricate projects or tasks that weren't clearly mentioned.
- If the conversation is just small talk, greetings, or complaints, return: NONE
- If unsure, return: NONE
- Most messages have NOTHING learnable. Be extremely conservative.

Format (if facts exist):
category: fact content

Example:
preference: Boss prefers Python for backend work
mood: Boss seems tired tonight
project: Boss is building a crypto trading platform called AlgoPilot"""

            messages = [{"role": "user", "content": extraction_prompt}]
            result = None

            # Try local Ollama first (free, unlimited)
            try:
                local_client = AsyncOpenAI(
                    base_url=config.ollama_base_url,
                    api_key="ollama",
                )
                response = await local_client.chat.completions.create(
                    model=config.ollama_model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=300,
                )
                result = response.choices[0].message.content.strip()
                log.debug("adaptive_extraction_via", source="local")
            except Exception:
                # Local failed — fall back to Gemini
                try:
                    cloud_client = AsyncOpenAI(
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                        api_key=config.gemini_api_key or config.google_api_key,
                    )
                    response = await cloud_client.chat.completions.create(
                        model="gemini-2.5-flash",
                        messages=messages,
                        temperature=0.3,
                        max_tokens=300,
                    )
                    result = response.choices[0].message.content.strip()
                    log.debug("adaptive_extraction_via", source="gemini")
                except Exception:
                    return  # Both failed — skip silently

            if not result or result == "NONE":
                return

            # Parse and store
            for line in result.split("\n"):
                line = line.strip()
                if ":" in line and not line.startswith("#"):
                    parts = line.split(":", 1)
                    cat = parts[0].strip().lower()
                    content = parts[1].strip()
                    if cat in self.CATEGORIES and len(content) > 5:
                        self.store_fact(cat, content)

        except Exception as e:
            # Never crash the main flow for memory extraction
            log.debug("adaptive_extraction_failed", error=str(e))

    def get_stats(self) -> Dict:
        """Get memory statistics."""
        c = self._conn()
        total = c.execute("SELECT COUNT(*) FROM learned_facts").fetchone()[0]
        by_cat = c.execute(
            "SELECT category, COUNT(*), AVG(confidence) FROM learned_facts GROUP BY category"
        ).fetchall()
        c.close()
        return {
            "total_facts": total,
            "by_category": {r[0]: {"count": r[1], "avg_confidence": round(r[2], 2)} for r in by_cat}
        }


# Singleton
adaptive_memory = AdaptiveMemory()
