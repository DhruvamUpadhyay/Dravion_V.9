"""
DRAVION v.9 — Cortex (The Brain)

Architecture (local-first):
  - LOCAL (primary): Ollama — fast, private, no API limits. Full tool access.
    Handles everything: conversation, knowledge, tool-calling, actions.
    Data never leaves the machine.
  - CLOUD (backup): Groq (Llama 3.3 70B) — used when local is down.
  - PREMIUM: Gemini 2.5 Flash — smarter, vision. Limited daily quota.

Modes:
  - auto:   Local first → Cloud fallback → Gemini fallback
  - local:  Local only (cloud rescue if Ollama is down)
  - cloud:  Groq only → Gemini fallback
  - gemini: Gemini only
"""
import re
import json
import asyncio
from datetime import datetime
from openai import AsyncOpenAI
from core.config import config
from core.logger import log
from core.system_prompt import get_system_prompt
from memory.memory_manager import MemoryManager
from skills.builtins import TOOL_DEFINITIONS, execute_tool

SYSTEM_PROMPT = get_system_prompt()

# Timeout for API calls (seconds)
API_TIMEOUT = 25
LOCAL_TIMEOUT = 60


class Cortex:
    def __init__(self):
        self.mode = "auto"  # "auto", "cloud", "local", "gemini"
        self.memory = MemoryManager()
        self._last_brain = "groq"  # Track which brain answered last
        self._local_supports_tools = True  # Will be set to False if model rejects tools

        # Local brain — fallback, conversation only (no tool calling)
        self.local_client = AsyncOpenAI(
            base_url=config.ollama_base_url,
            api_key="ollama",
        )
        self.local_model = config.ollama_model

        # Primary brain — Groq (fast, 14,400 RPD, 131K TPM)
        self.cloud_client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=config.groq_api_key,
        )
        self.cloud_model = "llama-3.1-8b-instant"

        # Backup brain — Gemini 2.0 Flash (1,500 RPD free tier, 15 RPM)
        self.gemini_client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=config.gemini_api_key or config.google_api_key,
        )
        self.gemini_model = "gemini-2.0-flash"

        log.info("cortex_online",
                 mode=self.mode,
                 local=self.local_model,
                 primary="Gemini 2.0 Flash",
                 fallback="Local (Gemma)")

    def switch_mode(self, mode: str):
        self.mode = mode
        log.info("brain_switched", mode=mode)

    def _needs_tools(self, user_input: str) -> bool:
        """Detect if user input likely requires tool execution.
        Uses specific action phrases to avoid false positives on normal conversation."""
        action_phrases = [
            # App / system control
            "open chrome", "open browser", "open notepad", "open app",
            "close window", "close app", "minimize", "maximize",
            "shutdown computer", "restart computer", "lock screen",
            "set volume", "turn volume", "mute", "unmute",
            # Email
            "read email", "read my email", "check email", "send email",
            "read gmail", "check gmail", "send gmail", "draft email",
            # Screenshots / vision
            "take screenshot", "take a screenshot", "screenshot",
            "analyze screen", "what's on screen", "capture screen",
            # Time / weather / info
            "what time", "what's the time", "what date", "what day",
            "weather in", "what's the weather", "check weather",
            # Reminders / tasks
            "set reminder", "set a reminder", "remind me",
            "set timer", "set alarm", "add task",
            # Desktop automation
            "move mouse", "click on", "press key", "hotkey",
            "copy clipboard", "paste clipboard",
            # Files / documents
            "read pdf", "read document", "open file", "read file",
            "scan document", "extract text from",
            # Navigation / web
            "search for", "search google", "browse to", "navigate to",
            "give me directions", "directions to",
            # System
            "system info", "wifi status", "check wifi",
            "run python", "execute code", "run command",
            # Screen Agent (vision-guided GUI automation)
            "go to youtube", "go to gmail", "go to website",
            "play on youtube", "reply to email", "fill the form",
            "use the screen", "screen agent", "automate this",
            "do it on screen", "operate the", "navigate the app",
            "stop screen agent", "stop automation",
        ]
        lower = user_input.lower().strip()
        return any(phrase in lower for phrase in action_phrases)

    def _needs_vision(self, user_input: str) -> bool:
        """Detect if user input requires visual/camera capabilities (Gemini only)."""
        vision_phrases = [
            "what am i holding", "what do you see", "what's in front",
            "look at me", "look at this", "look through camera",
            "use camera", "use webcam", "see webcam", "see camera",
            "what's on screen", "what's on my screen", "analyze screen",
            "take a look", "can you see", "describe what",
            "read my screen", "read the screen", "show me",
            "am i holding", "what is this", "identify this",
            "recognize", "what color", "how many fingers",
            "capture", "what do i look like",
        ]
        lower = user_input.lower().strip()
        return any(phrase in lower for phrase in vision_phrases)

    async def think(self, user_input: str) -> str:
        # ── Intercept mode-switch commands ──
        lower = user_input.lower().strip()
        mode_map = {
            "go local": "local", "go offline": "local", "use local brain": "local",
            "local mode": "local", "switch to local": "local",
            "go cloud": "cloud", "go groq": "cloud", "use groq": "cloud",
            "cloud mode": "cloud", "go online": "auto",
            "go gemini": "gemini", "use gemini": "gemini", "premium mode": "gemini",
            "gemini mode": "gemini", "switch to gemini": "gemini",
            "go auto": "auto", "auto mode": "auto", "smart mode": "auto",
        }
        for trigger, mode in mode_map.items():
            if lower == trigger or lower.startswith(trigger):
                old = self.mode
                self.switch_mode(mode)
                brain_names = {"local": "Local (Ollama)", "cloud": "Groq (Llama 3.1 8B)",
                               "gemini": "Gemini 2.5 Flash-Lite", "auto": "Auto (Cloud-first)"}
                return f"Switched from {brain_names.get(old, old)} to {brain_names.get(mode, mode)}, Boss."

        messages = self._build_messages(user_input)
        needs_vision = self._needs_vision(user_input)

        # ── Route based on mode ──
        if self.mode == "local":
            reply, brain = await self._try_local(messages)
            if brain == "local-error":
                reply_gemini, brain_gemini = await self._try_gemini(messages)
                if reply_gemini:
                    reply = reply_gemini
                    brain = brain_gemini

        elif self.mode == "cloud" or self.mode == "gemini":
            reply, brain = await self._try_gemini(messages)
            if reply is None:
                log.info("auto_fallback", to="local")
                reply, brain = await self._try_local(messages)
            if reply is None:
                reply = "Gemini is down, Boss. Try again in a minute."
                brain = "none"

        else:
            # AUTO MODE — Gemini first, local fallback
            log.info("auto_route", destination="gemini")
            reply, brain = await self._try_gemini(messages)
            if reply is None:
                log.info("auto_fallback", to="local")
                reply, brain = await self._try_local(messages)
            if reply is None:
                reply = "All brains are down, Boss."
                brain = "none"

        reply = self._clean_response(reply)
        self._last_brain = brain
        self.memory.remember_conversation(user_input, reply)

        # Background: learn about Boss
        asyncio.create_task(self._learn_background(user_input, reply))

        return reply

    # ─── Brain Attempts (each returns (reply, brain_name) or (None, None) on failure) ───

    async def _try_groq(self, messages: list, retries: int = 2) -> tuple:
        """Try Groq with tools. Auto-retries on rate limit (429). Returns (reply, "groq") or (None, None)."""
        for attempt in range(retries + 1):
            try:
                reply = await asyncio.wait_for(
                    self._think_with_tools(messages, self.cloud_client, self.cloud_model),
                    timeout=API_TIMEOUT
                )
                log.info("brain_responded", brain="groq")
                return (reply, "groq")
            except asyncio.TimeoutError:
                log.warning("groq_timeout", timeout=API_TIMEOUT)
                return (None, None)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < retries:
                    wait = 3 * (attempt + 1)
                    log.info("groq_rate_limited_retrying", wait=wait, attempt=attempt+1)
                    await asyncio.sleep(wait)
                    continue
                elif "429" in error_str:
                    log.warning("groq_rate_limited", attempts_exhausted=True)
                else:
                    print(f"\n\033[91m[GROQ ERROR]: {error_str}\033[0m")
                    log.warning("groq_error", error=error_str[:100])
                return (None, None)
        return (None, None)

    async def _try_gemini(self, messages: list) -> tuple:
        """Try Gemini with tools. Returns (reply, "gemini") or (None, None)."""
        try:
            reply = await asyncio.wait_for(
                self._think_with_tools(messages, self.gemini_client, self.gemini_model),
                timeout=API_TIMEOUT
            )
            log.info("brain_responded", brain="gemini")
            return (reply, "gemini")
        except asyncio.TimeoutError:
            log.warning("gemini_timeout", timeout=API_TIMEOUT)
            return (None, None)
        except Exception as e:
            print(f"\n\033[91m[GEMINI ERROR]: {e}\033[0m")
            log.warning("gemini_error", error=str(e)[:100])
            return (None, None)

    async def _try_local(self, messages: list) -> tuple:
        """Try local Ollama — the primary brain, with graceful tool fallback."""
        try:
            if self._local_supports_tools:
                # Try with tools first
                try:
                    reply = await asyncio.wait_for(
                        self._think_with_tools(messages, self.local_client, self.local_model),
                        timeout=LOCAL_TIMEOUT
                    )
                    log.info("brain_responded", brain="local")
                    return (reply, "local")
                except Exception as tool_err:
                    err_str = str(tool_err)
                    if "400" in err_str and ("does not su" in err_str or "tool" in err_str.lower()):
                        # Model doesn't support tools — remember this and fall through
                        self._local_supports_tools = False
                        log.info("local_tools_disabled", reason="model does not support tool calling")
                    else:
                        raise  # Re-raise non-tool errors

            # Simple mode (no tools) — conversation only
            reply = await asyncio.wait_for(
                self._think_simple(self.local_client, self.local_model, messages),
                timeout=LOCAL_TIMEOUT
            )
            log.info("brain_responded", brain="local")
            return (reply, "local")
        except asyncio.TimeoutError:
            log.warning("local_timeout", timeout=LOCAL_TIMEOUT)
            return ("Local brain timed out, Boss. Model might be too heavy.", "local-error")
        except Exception as e:
            err = str(e).lower()
            if "connect" in err or "refused" in err or "unreachable" in err:
                log.warning("local_offline", error=str(e)[:100])
                return ("Ollama isn't running, Boss.", "local-error")
            log.warning("local_error", error=str(e)[:100])
            return (f"Local brain error: {str(e)[:80]}", "local-error")

    # ─── Core LLM Calls ───

    async def _think_with_tools(self, messages: list, client, model) -> str:
        """LLM call with tool-calling support."""
        # For Groq (tiny TPM limit) — send only relevant tools to save tokens
        tools = TOOL_DEFINITIONS
        if client == self.cloud_client:
            tools = self._filter_tools_for_query(messages)

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
        )

        msg = response.choices[0].message

        if msg.tool_calls:
            messages.append(msg)

            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

                log.info("tool_call", tool=fn_name, args=str(fn_args)[:80])
                result = await execute_tool(fn_name, fn_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            final = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
            )
            return final.choices[0].message.content

        return msg.content

    async def _think_simple(self, client, model, messages: list) -> str:
        """Simple LLM call without tools."""
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content

    # ─── Background Learning ───

    async def _learn_background(self, user_input: str, reply: str):
        try:
            await self.memory.learn_from_conversation(user_input, reply)
        except Exception as e:
            log.debug("background_learning_failed", error=str(e))

    # ─── Tool Filtering (for Groq's tiny TPM limit) ───

    # Tools always sent regardless of query
    _ALWAYS_SEND = {"open_app", "open_url", "run_shell_command", "get_time", "screen_do"}

    # Keyword → tool name mapping for smart filtering
    _TOOL_KEYWORDS = {
        "email": ["read_email", "send_email"],
        "gmail": ["read_email", "send_email"],
        "screenshot": ["take_screenshot", "analyze_screenshot"],
        "screen": ["take_screenshot", "analyze_screenshot", "screen_do", "screen_stop"],
        "weather": ["get_weather"],
        "remind": ["set_reminder", "list_reminders"],
        "timer": ["set_timer"],
        "volume": ["set_volume"],
        "mute": ["set_volume"],
        "shutdown": ["power_control"],
        "restart": ["power_control"],
        "lock": ["lock_screen"],
        "wifi": ["wifi_status"],
        "system": ["system_info", "wifi_status"],
        "youtube": ["youtube_play"],
        "play": ["youtube_play", "open_app"],
        "search": ["web_search", "google_search"],
        "browse": ["open_url"],
        "file": ["read_file", "write_file", "list_directory"],
        "folder": ["list_directory"],
        "copy": ["clipboard_read", "clipboard_write"],
        "clipboard": ["clipboard_read", "clipboard_write"],
        "mouse": ["mouse_click", "mouse_move"],
        "click": ["mouse_click", "screen_do"],
        "type": ["keyboard_type", "keyboard_press"],
        "key": ["keyboard_press", "keyboard_hotkey"],
        "hotkey": ["keyboard_hotkey"],
        "pdf": ["read_document"],
        "document": ["read_document"],
        "python": ["run_python", "run_shell_command"],
        "code": ["run_python", "run_shell_command"],
        "direction": ["get_directions"],
        "navigate": ["get_directions", "screen_do"],
        "security": ["security_scan", "osint_lookup"],
        "scan": ["security_scan"],
        "memory": ["consolidate_memory"],
        "audit": ["activity_report"],
        "automate": ["screen_do"],
    }

    def _filter_tools_for_query(self, messages: list) -> list:
        """Select only relevant tools based on the user's message to save tokens."""
        # Get the last user message
        user_msg = ""
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "user":
                user_msg = m.get("content", "").lower()
                break

        # Collect relevant tool names
        relevant = set(self._ALWAYS_SEND)
        for keyword, tools in self._TOOL_KEYWORDS.items():
            if keyword in user_msg:
                relevant.update(tools)

        # If nothing matched, send a broader set
        if len(relevant) <= len(self._ALWAYS_SEND):
            return TOOL_DEFINITIONS  # Fall back to all tools

        # Filter tool definitions
        filtered = [t for t in TOOL_DEFINITIONS if t["function"]["name"] in relevant]
        return filtered if filtered else TOOL_DEFINITIONS

    # ─── Helpers ───

    @staticmethod
    def _clean_response(text: str) -> str:
        if not text:
            return "..."
        text = re.sub(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
            r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251'
            r'\U0001f900-\U0001f9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF'
            r'\U00002600-\U000026FF\U0000FE0F]+',
            '', text
        )
        text = re.sub(r'\b(\w+)\b(?:\s+\1\b){1,}', r'\1', text)
        for g in ['confirme', '\n confirme', ' confirme']:
            text = text.replace(g, '')
        text = text.replace("(local fallback)", "")
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    def _build_messages(self, user_input: str) -> list:
        now = datetime.now()
        time_context = f"\nCurrent date: {now.strftime('%A, %d %B %Y')}. Current time: {now.strftime('%I:%M %p')}."

        adaptive_ctx = self.memory.get_adaptive_context()
        system_content = SYSTEM_PROMPT + time_context
        if adaptive_ctx:
            system_content += f"\n\n{adaptive_ctx}"

        messages = [{"role": "system", "content": system_content}]

        history = self.memory.get_conversation_history(n=6)
        for turn in history:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["agent"]})

        knowledge = self.memory.search_knowledge(user_input)
        if knowledge:
            memory_text = "\n".join(f"- {item['document']}" for item in knowledge)
            messages[0]["content"] += f"\n\nRelevant memories:\n{memory_text}"

        messages.append({"role": "user", "content": user_input})
        return messages
