"""
DRAVION v.9 — Screen Agent (Vision-Guided GUI Automation)

JARVIS-level autonomous screen control. Dravion sees the screen,
understands UI elements, clicks, types, scrolls — and narrates
everything it does in real time.

Architecture:
  OBSERVE → THINK → ACT → VERIFY → NARRATE → repeat

Uses Gemini 2.5 Flash for vision (screenshot → coordinate detection).
Uses pyautogui for actual mouse/keyboard control.

Example:
  "Open YouTube and play lofi hip hop"
  → Dravion opens Chrome, navigates to YouTube, searches, clicks play.
  → Narrates each step: "Opening Chrome... Navigating to YouTube..."
  → Final walkthrough: "Done, Boss. Opened Chrome, went to YouTube..."
"""
import asyncio
import base64
import io
import json
import time
import os
from datetime import datetime
from typing import Callable, Optional, List, Tuple
from core.logger import log
from core.config import config

# ANSI colors for terminal narration
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


class ScreenAction:
    """A single GUI action taken by the screen agent."""

    def __init__(self, step: int, action_type: str, observation: str = "",
                 reasoning: str = "", narration: str = "",
                 coordinates: tuple = None, text: str = None,
                 key: str = None, keys: list = None, direction: str = None,
                 summary: str = None):
        self.step = step
        self.action_type = action_type   # click, type, press, hotkey, scroll, wait, done
        self.observation = observation
        self.reasoning = reasoning
        self.narration = narration       # Casual update for Boss
        self.coordinates = coordinates   # (x_fraction, y_fraction) 0.0-1.0
        self.text = text
        self.key = key
        self.keys = keys
        self.direction = direction
        self.summary = summary
        self.timestamp = datetime.now()
        self.pixel_coords = None         # Actual pixels used
        self.success = True
        self.error = None


class ScreenAgent:
    """
    Autonomous vision-guided GUI automation agent with live narration.

    Features:
      - Multi-step ReAct loop (Observe → Think → Act → Verify)
      - Proactive mid-task narration via speaker/terminal
      - Completion walkthrough summary
      - Screenshot logging at every step for debugging
      - Smart UI stabilization waits
      - Safety limits (max steps, timeout, interruptible)
    """

    MAX_STEPS = 15
    OVERALL_TIMEOUT = 180        # 3 minutes max per task
    ACTION_COOLDOWN = 1.5        # seconds between actions for UI to settle
    SCREENSHOT_LOG_DIR = None    # Set to a path to save step screenshots

    def __init__(self):
        self._action_log: List[ScreenAction] = []
        self._running = False
        self._speak_fn = None      # async fn(text) -> None
        log.info("screen_agent_ready")

        # Create screenshot log directory
        self.SCREENSHOT_LOG_DIR = os.path.join(config.data_dir, "screen_agent_logs")
        os.makedirs(self.SCREENSHOT_LOG_DIR, exist_ok=True)

    def set_speaker(self, speak_fn):
        """Set the TTS callback. Called from CLI after speaker init."""
        self._speak_fn = speak_fn

    # ─────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────

    async def execute(self, instruction: str) -> str:
        """
        Execute a GUI automation task from natural language.

        Args:
            instruction: e.g. "Open YouTube and play lofi music"

        Returns:
            Walkthrough summary string
        """
        self._action_log = []
        self._running = True
        start_time = time.time()
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        await self._narrate(f"On it, Boss.", speak=True)

        try:
            screen_w, screen_h = self._get_screen_size()

            for step in range(1, self.MAX_STEPS + 1):
                elapsed = time.time() - start_time
                if elapsed > self.OVERALL_TIMEOUT:
                    await self._narrate("Took too long. Stopping.", speak=True)
                    break

                if not self._running:
                    await self._narrate("Stopped.", speak=True)
                    break

                # ── OBSERVE ──
                await self._narrate(f"Step {step}: scanning...")
                screenshot = self._take_screenshot()
                if not screenshot:
                    await self._narrate("Can't see screen. Aborting.", speak=True)
                    break

                self._save_debug_screenshot(screenshot, task_id, step, "before")

                # ── THINK ──
                action = await self._think(
                    instruction=instruction,
                    screenshot=screenshot,
                    screen_size=(screen_w, screen_h),
                    step=step,
                    history=self._action_log
                )

                if not action:
                    await self._narrate("Lost visual. Stopping.", speak=True)
                    break

                # ── DONE? ──
                if action.action_type == "done":
                    self._action_log.append(action)
                    break

                # ── ACT ──
                # Only speak the FIRST action and every 4th — rest is terminal only
                action_desc = action.narration or self._describe_action(action)
                should_speak = (step == 1 or step % 4 == 0)
                await self._narrate(action_desc, speak=should_speak)

                success = self._execute_action(action, screen_w, screen_h)
                action.success = success
                self._action_log.append(action)

                if not success:
                    await self._narrate(f"Hiccup: {action.error}")

                await asyncio.sleep(self.ACTION_COOLDOWN)

                # ── VERIFY ──
                verify_shot = self._take_screenshot()
                if verify_shot:
                    self._save_debug_screenshot(verify_shot, task_id, step, "after")

            # ── SMART RESULT (not a full walkthrough for simple stuff) ──
            result = self._build_smart_result(instruction)
            await self._narrate(result, speak=True)
            return result

        except Exception as e:
            error_msg = f"Screen agent hit a wall: {e}"
            log.error("screen_agent_error", error=str(e))
            await self._narrate(error_msg, speak=True)
            return error_msg
        finally:
            self._running = False

    def stop(self):
        """Emergency stop — cancel the current task."""
        self._running = False

    # ─────────────────────────────────────────────
    # OBSERVE
    # ─────────────────────────────────────────────

    def _take_screenshot(self) -> Optional[bytes]:
        """Capture screen as PNG bytes, resized for Gemini."""
        try:
            import pyautogui
            from PIL import Image

            img = pyautogui.screenshot()

            # Resize for Gemini (saves tokens, faster upload)
            w, h = img.size
            if w > 1280:
                ratio = 1280 / w
                img = img.resize((1280, int(h * ratio)), Image.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()
        except Exception as e:
            log.error("screenshot_failed", error=str(e))
            return None

    def _get_screen_size(self) -> Tuple[int, int]:
        """Get actual screen resolution."""
        try:
            import pyautogui
            return pyautogui.size()
        except Exception:
            return (1920, 1080)

    # ─────────────────────────────────────────────
    # THINK (Gemini Vision)
    # ─────────────────────────────────────────────

    async def _think(self, instruction: str, screenshot: bytes,
                     screen_size: tuple, step: int,
                     history: list) -> Optional[ScreenAction]:
        """Send screenshot to Gemini, get the next action as structured JSON."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=config.gemini_api_key or config.google_api_key,
            )

            b64 = base64.b64encode(screenshot).decode("utf-8")

            # Build concise history
            history_text = self._format_history(history)

            prompt = self._build_vision_prompt(
                instruction, screen_size, step, history_text
            )

            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gemini-2.0-flash",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/png;base64,{b64}"
                            }},
                        ],
                    }],
                    temperature=0.2,
                    max_tokens=500,
                ),
                timeout=30
            )

            result_text = response.choices[0].message.content.strip()
            return self._parse_action_response(result_text, step)

        except asyncio.TimeoutError:
            log.warning("screen_think_timeout")
            return None
        except Exception as e:
            log.error("screen_think_error", error=str(e))
            return None

    def _build_vision_prompt(self, instruction: str, screen_size: tuple,
                             step: int, history_text: str) -> str:
        """Build the structured prompt for Gemini vision analysis."""
        return f"""You are DRAVION's Screen Agent — an autonomous GUI automation AI on a Windows PC.

GOAL: {instruction}
STEP: {step} of {self.MAX_STEPS}
SCREEN: {screen_size[0]}x{screen_size[1]} pixels
{history_text}
Analyze the screenshot. Decide the ONE next action to progress toward the goal.

COORDINATE RULES:
- Express as fractions 0.0 to 1.0 of screen width/height.
- Top-left = [0.0, 0.0], center = [0.5, 0.5], bottom-right = [1.0, 1.0].
- Aim for the CENTER of the target element (button, link, field).

BEHAVIOR RULES:
- After typing a URL or search query, press "enter" as the NEXT step.
- Wait for pages to fully load before clicking new elements.
- If the goal is achieved, return action "done" with a summary.
- One action per step. Be precise.

Return ONLY valid JSON — no markdown fences, no extra text:
{{
  "observation": "What is currently visible on screen",
  "reasoning": "Why this specific action moves toward the goal",
  "action": "click|double_click|right_click|type|press|hotkey|scroll|wait|done",
  "coordinates": [0.5, 0.5],
  "text": "only for type action",
  "key": "only for press action (enter, tab, escape, etc.)",
  "keys": ["ctrl", "t"],
  "direction": "up|down (scroll only)",
  "narration": "Short casual update for Boss, like a buddy telling you what he's doing",
  "summary": "only for done — what was accomplished"
}}

Only include fields relevant to your chosen action. Omit null fields."""

    def _format_history(self, history: List[ScreenAction]) -> str:
        """Format action history for the prompt."""
        if not history:
            return ""
        lines = ["PREVIOUS ACTIONS:"]
        for a in history[-6:]:  # Last 6 steps max to save tokens
            tag = "OK" if a.success else "FAIL"
            if a.action_type == "click":
                lines.append(f"  Step {a.step}: Clicked at {a.pixel_coords} [{tag}]")
            elif a.action_type == "type":
                lines.append(f"  Step {a.step}: Typed '{a.text}' [{tag}]")
            elif a.action_type == "press":
                lines.append(f"  Step {a.step}: Pressed {a.key} [{tag}]")
            elif a.action_type == "hotkey":
                lines.append(f"  Step {a.step}: Hotkey {'+'.join(a.keys or [])} [{tag}]")
            elif a.action_type == "scroll":
                lines.append(f"  Step {a.step}: Scrolled {a.direction} [{tag}]")
            else:
                lines.append(f"  Step {a.step}: {a.action_type} [{tag}]")
        return "\n".join(lines)

    def _parse_action_response(self, text: str, step: int) -> Optional[ScreenAction]:
        """Parse Gemini's JSON response into a ScreenAction."""
        try:
            # Strip markdown fences
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
            # Sometimes Gemini wraps in ```json ... ```
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

            data = json.loads(cleaned)

            coords = None
            if data.get("coordinates"):
                c = data["coordinates"]
                if isinstance(c, list) and len(c) == 2:
                    coords = (float(c[0]), float(c[1]))

            return ScreenAction(
                step=step,
                action_type=data.get("action", "done"),
                observation=data.get("observation", ""),
                reasoning=data.get("reasoning", ""),
                narration=data.get("narration", ""),
                coordinates=coords,
                text=data.get("text"),
                key=data.get("key"),
                keys=data.get("keys"),
                direction=data.get("direction"),
                summary=data.get("summary"),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            log.warning("screen_parse_failed", error=str(e), raw=text[:200])
            return None

    # ─────────────────────────────────────────────
    # ACT (pyautogui execution)
    # ─────────────────────────────────────────────

    def _execute_action(self, action: ScreenAction,
                        screen_w: int, screen_h: int) -> bool:
        """Execute a single GUI action. Returns True on success."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = True  # Move mouse to corner to abort

            at = action.action_type

            if at in ("click", "double_click", "right_click"):
                if not action.coordinates:
                    action.error = "No coordinates for click"
                    return False

                x = int(action.coordinates[0] * screen_w)
                y = int(action.coordinates[1] * screen_h)
                # Clamp to screen bounds
                x = max(0, min(x, screen_w - 1))
                y = max(0, min(y, screen_h - 1))
                action.pixel_coords = (x, y)

                if at == "click":
                    pyautogui.click(x, y)
                elif at == "double_click":
                    pyautogui.doubleClick(x, y)
                elif at == "right_click":
                    pyautogui.rightClick(x, y)

            elif at == "type":
                if not action.text:
                    action.error = "No text to type"
                    return False
                # pyautogui.typewrite only handles ASCII — use clipboard
                # paste for non-ASCII text (Hindi, emoji, special chars)
                if action.text.isascii():
                    pyautogui.typewrite(action.text, interval=0.03)
                else:
                    import pyperclip
                    pyperclip.copy(action.text)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.2)

            elif at == "press":
                if not action.key:
                    action.error = "No key specified"
                    return False
                pyautogui.press(action.key)

            elif at == "hotkey":
                if not action.keys or len(action.keys) < 2:
                    action.error = "Need at least 2 keys for hotkey"
                    return False
                pyautogui.hotkey(*action.keys)

            elif at == "scroll":
                direction = action.direction or "down"
                amount = -5 if direction == "down" else 5
                if action.coordinates:
                    x = int(action.coordinates[0] * screen_w)
                    y = int(action.coordinates[1] * screen_h)
                    pyautogui.scroll(amount, x=x, y=y)
                else:
                    pyautogui.scroll(amount)

            elif at == "wait":
                pass  # Cooldown handles the wait

            else:
                action.error = f"Unknown action: {at}"
                return False

            return True

        except Exception as e:
            action.error = str(e)
            log.error("screen_act_failed", action=action.action_type, error=str(e))
            return False

    # ─────────────────────────────────────────────
    # NARRATE (proactive updates)
    # ─────────────────────────────────────────────

    async def _narrate(self, message: str, speak: bool = False):
        """
        Proactive narration — print to terminal, optionally speak.

        Args:
            message: What to say
            speak: If True, also speak via TTS (for milestones)
        """
        # Always print to terminal
        print(f"  {MAGENTA}[SCREEN]{RESET} {message}")
        log.info("screen_narrate", msg=message[:100])

        # Speak key milestones (short, punchy updates)
        if speak and self._speak_fn:
            try:
                # Truncate for TTS — keep it snappy
                speak_text = message[:150]
                await self._speak_fn(speak_text)
            except Exception as e:
                log.debug("screen_speak_failed", error=str(e))

    def _describe_action(self, action: ScreenAction) -> str:
        """Generate a human-readable description of an action."""
        at = action.action_type
        if at == "click":
            return f"Clicking at target..."
        elif at == "double_click":
            return f"Double-clicking target..."
        elif at == "type":
            preview = action.text[:40] + "..." if len(action.text or "") > 40 else action.text
            return f"Typing: '{preview}'"
        elif at == "press":
            return f"Pressing {action.key}..."
        elif at == "hotkey":
            return f"Hotkey: {'+'.join(action.keys or [])}"
        elif at == "scroll":
            return f"Scrolling {action.direction}..."
        elif at == "wait":
            return "Waiting for UI to settle..."
        return f"Action: {at}"

    # ─────────────────────────────────────────────
    # WALKTHROUGH (completion summary)
    # ─────────────────────────────────────────────

    def _build_smart_result(self, instruction: str) -> str:
        """
        Context-aware result reporting.
        Simple tasks → one-liner. Complex/failed tasks → detailed breakdown.
        """
        if not self._action_log:
            return "Couldn't do anything, Boss."

        total = len(self._action_log)
        failed = sum(1 for a in self._action_log if not a.success)
        last = self._action_log[-1]

        # ── Simple success: just tell Boss the result ──
        if failed == 0 and total <= 6:
            if last.action_type == "done" and last.summary:
                return last.summary
            return "Done."

        # ── Complex or had failures: give a brief breakdown ──
        elapsed = (last.timestamp - self._action_log[0].timestamp).total_seconds()
        lines = []

        if failed > 0:
            lines.append(f"Ran into {failed} issue{'s' if failed > 1 else ''} but pushed through.")

        if total > 6:
            lines.append(f"Took {total} steps over {elapsed:.0f}s.")

        # Only list failed steps (successes don't need explaining)
        for a in self._action_log:
            if not a.success:
                lines.append(f"  Failed: {a.action_type} — {a.error or 'unknown'}")

        if last.action_type == "done" and last.summary:
            lines.append(last.summary)
        elif failed == 0:
            lines.append("Done.")
        else:
            lines.append("Finished with issues. Check the screen.")

        return " ".join(lines) if len(lines) <= 2 else "\n".join(lines)

    # ─────────────────────────────────────────────
    # DEBUG (screenshot logging)
    # ─────────────────────────────────────────────

    def _save_debug_screenshot(self, img_bytes: bytes,
                               task_id: str, step: int, phase: str):
        """Save step screenshots for debug review."""
        if not self.SCREENSHOT_LOG_DIR:
            return
        try:
            path = os.path.join(
                self.SCREENSHOT_LOG_DIR,
                f"{task_id}_step{step:02d}_{phase}.png"
            )
            with open(path, "wb") as f:
                f.write(img_bytes)
        except Exception:
            pass  # Non-critical


# ─── Singleton ───
screen_agent = ScreenAgent()
