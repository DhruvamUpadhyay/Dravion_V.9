"""
DRAVION v.9 — CLI Interface

Voice-first. Always listening by default.
Mode switching via voice commands:
  - "text mode"   → switches to keyboard input
  - "voice mode"  → switches back to mic input
  - "go local"    → switches brain to Gemma (offline)
  - "go online"   → switches brain to Auto (cloud)
  - "exit/sleep"  → shutdown
"""
import asyncio
import random
import time
import sqlite3
import os
from brain.cortex import Cortex
from voice.speaker import Speaker
from core.logger import log
from core.config import config

# ── Sci-Fi Terminal Theme (matches main.py palette) ──
BLUE      = "\033[38;5;33m"    # electric blue
CYAN      = "\033[38;5;51m"    # bright cyan — Dravion's voice
ICE       = "\033[38;5;117m"   # ice blue — subtle info
STEEL     = "\033[38;5;244m"   # steel gray — dim/system
WHITE     = "\033[97m"         # bright white
GREEN     = "\033[38;5;48m"    # mint green — success
RED       = "\033[38;5;196m"   # vivid red — errors
YELLOW    = "\033[38;5;220m"   # amber — user input
MAGENTA   = "\033[38;5;135m"   # purple — mode changes
BOLD      = "\033[1m"
DIM       = "\033[2m"
RESET     = "\033[0m"

WAKE_REPLIES = [
    "Yes Boss, I'm up.",
    "At your service.",
    "Listening, Boss.",
    "Go ahead.",
    "Systems online.",
    "I'm all ears.",
    "Ready for instructions.",
]

SLEEP_RESPONSES = [
    "Alright Boss, going to sleep. Wake me when you need me.",
    "Going into power-saving mode. I'll be back faster than you can say DRAVION.",
    "Off to recharge my neural networks. See you soon, Boss.",
    "Sleep mode activated. Don't miss me too much.",
    "Shutting down the think-tank. But I'm just one command away.",
    "Taking a breather. Don't do anything stupid without me, Boss.",
    "Going dark. But I'm never really gone.",
]


class CLI:
    def __init__(self, cortex: Cortex):
        self.cortex = cortex
        self.speaker = Speaker(voice_name="en-US-Journey-D")
        self.running = True
        self.input_mode = "voice"  # "voice" or "text"
        self.listener = None

        # Try to init voice listener
        try:
            from voice.listener import Listener
            self.listener = Listener()
        except Exception as e:
            log.error("listener_init_failed", error=str(e))
            print(f"  {YELLOW}Voice input unavailable: {e}{RESET}")
            print(f"  {YELLOW}Starting in text mode.{RESET}\n")
            self.input_mode = "text"

    def log_to_ui_db(self, role: str, content: str):
        db_path = os.path.join(config.data_dir, "chat_sessions.db")
        try:
            c = sqlite3.connect(db_path)
            c.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, title TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
            c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE)")
            
            sid = "terminal_cli"
            # Ensure session exists
            c.execute("INSERT OR IGNORE INTO sessions (id, title) VALUES (?, ?)", (sid, "Terminal Session"))
            
            c.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (sid, role, content))
            c.execute("UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (sid,))
            c.commit()
            c.close()
        except Exception as e:
            pass # Non-critical if UI DB fails

    async def run(self):
        # Boot greeting (banner is already displayed by main.py)
        greeting = random.choice(WAKE_REPLIES)
        print(f"  {CYAN}{BOLD}DRAVION{RESET}{STEEL} ▸{RESET} {ICE}{greeting}{RESET}\n")
        await self.speaker.speak(greeting)

        # Main loop
        while self.running:
            try:
                user_input = await self._get_input()

                if not user_input:
                    continue

                # Check for mode switch commands BEFORE sending to brain
                handled = await self._handle_command(user_input)
                if handled:
                    continue

                self.log_to_ui_db("user", user_input)
                # Send to brain
                response = await self.cortex.think(user_input)
                print(f"\n  {CYAN}{BOLD}DRAVION{RESET}{STEEL} ▸{RESET} {ICE}{response}{RESET}\n")
                self.log_to_ui_db("assistant", response)
                await self.speaker.speak(response)

            except (KeyboardInterrupt, EOFError):
                print(f"\n  {STEEL}[SHUTDOWN] DRAVION offline.{RESET}\n")
                break
            except Exception as e:
                log.error("cli_error", error=str(e))
                print(f"\n  {RED}[ERROR]{RESET} {RED}{e}{RESET}\n")

    async def _get_input(self) -> str | None:
        """Get input from current mode (voice or text)."""
        if self.input_mode == "voice" and self.listener:
            user_input = await self.listener.listen(timeout=8)
            if user_input:
                print(f"  {YELLOW}YOU{RESET}{STEEL} ▸{RESET} {WHITE}{user_input}{RESET}")
            return user_input
        else:
            # Text mode — use thread to avoid blocking event loop
            try:
                import sys
                sys.stdout.write(f"  {YELLOW}YOU{RESET}{STEEL} ▸ {RESET}")
                sys.stdout.flush()
                line = await asyncio.to_thread(sys.stdin.readline)
                return line.strip() if line else None
            except EOFError:
                return None

    async def _handle_command(self, text: str) -> bool:
        """Handle mode-switching voice commands. Returns True if handled."""
        lower = text.strip().lower()

        # Exit commands
        if any(w in lower for w in ["exit", "quit", "shutdown", "sleep", "goodbye"]):
            farewell = random.choice(SLEEP_RESPONSES)
            print(f"\n  {CYAN}{BOLD}DRAVION{RESET}{STEEL} ▸{RESET} {ICE}{farewell}{RESET}\n")
            await self.speaker.speak(farewell)
            self.running = False
            return True

        # Text mode
        if lower in ("text mode", "switch to text", "type mode"):
            self.input_mode = "text"
            msg = "Switched to text mode, Boss. Type away."
            print(f"\n  {MAGENTA}⚡{RESET} {ICE}{msg}{RESET}\n")
            await self.speaker.speak(msg)
            await asyncio.sleep(0.5)  # Let voice thread settle
            return True

        # Voice mode
        if lower in ("voice mode", "switch to voice", "listen mode"):
            if self.listener:
                self.input_mode = "voice"
                msg = "Switched to voice mode. I'm listening."
                print(f"\n  {MAGENTA}⚡{RESET} {ICE}{msg}{RESET}\n")
                await self.speaker.speak(msg)
            else:
                msg = "Voice input isn't available right now, Boss."
                print(f"\n  {RED}✗{RESET} {ICE}{msg}{RESET}\n")
                await self.speaker.speak(msg)
            return True

        # Local brain
        if lower in ("go local", "local mode", "go offline", "switch to local"):
            self.cortex.switch_mode("local")
            msg = "Switched to local brain. Running on Gemma, fully offline."
            print(f"\n  {MAGENTA}⚡{RESET} {ICE}{msg}{RESET}\n")
            await self.speaker.speak(msg)
            return True

        # Cloud brain
        if lower in ("go online", "cloud mode", "go cloud"):
            self.cortex.switch_mode("auto")
            msg = "Back online, Boss. Gemini 2.0 Flash active."
            print(f"\n  {MAGENTA}⚡{RESET} {ICE}{msg}{RESET}\n")
            await self.speaker.speak(msg)
            return True

        # Gemini-only mode
        if lower in ("go gemini", "switch to gemini", "gemini mode", "premium mode"):
            self.cortex.switch_mode("gemini")
            msg = "Gemini-only mode. 1500 requests per day."
            print(f"\n  {MAGENTA}⚡{RESET} {ICE}{msg}{RESET}\n")
            await self.speaker.speak(msg)
            return True

        # Auto mode
        if lower in ("auto mode", "smart mode", "auto", "go auto"):
            self.cortex.switch_mode("auto")
            msg = "Auto mode. Gemini first, local fallback."
            print(f"\n  {MAGENTA}⚡{RESET} {ICE}{msg}{RESET}\n")
            await self.speaker.speak(msg)
            return True

        # Screen Agent emergency stop
        if any(w in lower for w in ["stop screen", "abort screen", "screen stop",
                                     "stop automation", "cancel screen"]):
            from skills.screen_agent import screen_agent
            screen_agent.stop()
            msg = "Screen Agent halted. All automation stopped."
            print(f"\n  {MAGENTA}⚡{RESET} {ICE}{msg}{RESET}\n")
            await self.speaker.speak(msg)
            return True

        return False

    def stop(self):
        self.running = False
