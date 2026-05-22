"""
DRAVION v.9 — Memory Consolidation Pipeline

Promotes important episodic memories → semantic memory.
Runs periodically (or on demand) to:
  1. Scan recent episodic conversations
  2. Extract key facts/decisions using LLM
  3. Store in ChromaDB if not already present
  4. Decay old mood entries in adaptive memory
  5. Report what was consolidated
"""
import asyncio
from datetime import datetime
from core.logger import log
from core.config import config


async def consolidate_memories(memory_manager) -> str:
    """
    Run memory consolidation:
      episodic (recent conversations) → semantic (long-term vector store)
      + adaptive mood decay
    """
    log.info("consolidation_started")

    episodic = memory_manager.episodic
    semantic = memory_manager.semantic
    adaptive = memory_manager.adaptive

    # 1. Get recent conversations not yet consolidated
    recent = episodic.get_recent(n=20)
    if not recent:
        return "No conversations to consolidate."

    # 2. Build a summary prompt for the LLM
    convo_text = "\n".join(f"User: {t['user']}\nDRAVION: {t['agent']}" for t in recent)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=config.groq_api_key,
        )

        prompt = f"""Analyze these recent conversations between Dhruvam (Boss) and DRAVION.
Extract ONLY genuinely important information worth remembering long-term.

Conversations:
{convo_text[:4000]}

Extract into categories. One fact per line. Only extract if genuinely important:
- KEY_FACT: important factual information
- DECISION: decisions that were made
- PREFERENCE: preferences expressed
- PROJECT: project/work information
- RELATIONSHIP: people mentioned and their relation

If nothing important, return: NOTHING_NEW

Format:
CATEGORY: fact content"""

        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
        )

        result = response.choices[0].message.content.strip()

        if result == "NOTHING_NEW":
            log.info("consolidation_nothing_new")
            return "Consolidation complete. No new important memories to store."

        stored = 0
        for line in result.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                parts = line.split(":", 1)
                content = parts[1].strip()
                if len(content) > 10:
                    semantic.store(content, metadata={
                        "source": "consolidation",
                        "category": parts[0].strip(),
                        "consolidated_at": datetime.now().isoformat()
                    })
                    stored += 1

        # 3. Decay old moods
        adaptive.decay_old_moods(days=7)

        report = f"Consolidation complete. {stored} facts promoted to long-term memory."
        log.info("consolidation_done", stored=stored)
        return report

    except Exception as e:
        log.error("consolidation_failed", error=str(e))
        return f"Consolidation failed: {e}"
