"""
DRAVION v.9 — Main Entry Point

Boot sequence: Config → Logger → Memory → Cortex → Interface
"""
import asyncio
import sys
import os
import warnings
import logging
import time
import threading
import uvicorn

# ── Suppress ALL noise before any imports ──
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["POSTHOG_DISABLED"] = "true"
warnings.filterwarnings("ignore")

# Mock posthog before chromadb imports it (kills the telemetry error)
import types
posthog_mock = types.ModuleType("posthog")
posthog_mock.capture = lambda *a, **kw: None
posthog_mock.Posthog = type("Posthog", (), {"capture": lambda *a, **kw: None})
import sys as _sys
_sys.modules["posthog"] = posthog_mock

for lib in ["httpx", "chromadb", "sentence_transformers", "urllib3",
            "posthog", "openai._base_client", "httpcore"]:
    logging.getLogger(lib).setLevel(logging.CRITICAL)

# ── Terminal Theme: Sci-fi Blue Techie ──
# Core palette
BG        = ""           # terminal default bg
BLUE      = "\033[38;5;33m"   # primary accent — electric blue
CYAN      = "\033[38;5;51m"   # secondary — bright cyan
ICE       = "\033[38;5;117m"  # subtle info — ice blue
STEEL     = "\033[38;5;244m"  # dim text — steel gray
WHITE     = "\033[97m"        # bright white
GREEN     = "\033[38;5;48m"   # success — mint green
RED       = "\033[38;5;196m"  # errors — vivid red
YELLOW    = "\033[38;5;220m"  # warnings — amber
MAGENTA   = "\033[38;5;135m"  # mode changes — purple
BOLD      = "\033[1m"
DIM       = "\033[2m"
RESET     = "\033[0m"


def boot_line(label: str, status: str = "OK", color: str = GREEN):
    """Print a boot subsystem status."""
    print(f"  {STEEL}├─{RESET} {color}[{status}]{RESET} {ICE}{label}{RESET}")


def boot_last(label: str, status: str = "OK", color: str = GREEN):
    """Print the final boot subsystem status."""
    print(f"  {STEEL}└─{RESET} {color}[{status}]{RESET} {ICE}{label}{RESET}")


def banner():
    """Futuristic sci-fi boot banner."""
    os.system("")  # Enable ANSI on Windows
    print()
    # Clear-line effect
    print(f"{STEEL}  {'─' * 56}{RESET}")
    print()
    # ASCII art — compact, sharp, futuristic
    art = f"""{BOLD}{CYAN}\
  ██████╗ ██████╗  █████╗ ██╗   ██╗██╗ ██████╗ ███╗   ██╗
  ██╔══██╗██╔══██╗██╔══██╗██║   ██║██║██╔═══██╗████╗  ██║
  ██║  ██║██████╔╝███████║██║   ██║██║██║   ██║██╔██╗ ██║
  ██║  ██║██╔══██╗██╔══██║╚██╗ ██╔╝██║██║   ██║██║╚██╗██║
  ██████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║╚██████╔╝██║ ╚████║
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝{RESET}"""
    print(art)
    print()
    print(f"  {BLUE}{BOLD}          ╔═══════════════════════╗{RESET}")
    print(f"  {BLUE}{BOLD}          ║   {WHITE}D R A V I O N  v.9{BLUE}   ║{RESET}")
    print(f"  {BLUE}{BOLD}          ╚═══════════════════════╝{RESET}")
    print(f"  {STEEL}          Autonomous Intelligence System{RESET}")
    print()
    print(f"  {STEEL}{'─' * 56}{RESET}")
    print(f"  {STEEL}  SYSTEM BOOT SEQUENCE{RESET}")
    print(f"  {STEEL}{'─' * 56}{RESET}")


async def main():
    banner()
    time.sleep(0.2)

    # 1. Config
    from core.config import config
    boot_line("Configuration loaded")

    # 2. Logger
    from core.logger import log
    boot_line("Logger initialized")

    # 3. Brain
    from brain.cortex import Cortex
    from skills.builtins import TOOL_DEFINITIONS
    cortex = Cortex()
    brain_label = {"auto": "Gemini 2.0 Flash + Local", "cloud": "Gemini 2.0 Flash", "gemini": "Gemini 2.0 Flash", "local": f"{cortex.local_model} (local)"}.get(cortex.mode, cortex.mode)
    boot_line(f"Cortex online — {brain_label}")
    boot_line(f"Arsenal loaded: {len(TOOL_DEFINITIONS)} tools")

    # 4. Interface
    from interfaces.cli import CLI
    cli = CLI(cortex)
    input_label = "Voice (Google STT)" if cli.input_mode == "voice" else "Text"
    boot_line(f"Input: {input_label}")
    boot_line("TTS: Google Journey-D")

    # 4b. Wire Screen Agent to speaker (so it can narrate GUI automation)
    from skills.screen_agent import screen_agent
    screen_agent.set_speaker(cli.speaker.speak)
    boot_line("Screen Agent online (vision-guided GUI)")

    # 5. UI Web Server
    import sys as _sys
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in _sys.path:
        _sys.path.insert(0, root_dir)
    from web_server import app as web_app
    web_app.state.cortex = cortex
    web_app.state.speaker = cli.speaker
    web_app.state.main_loop = asyncio.get_running_loop()
    def run_ui():
        uvicorn.run(web_app, host="127.0.0.1", port=8000, log_level="critical")
    threading.Thread(target=run_ui, daemon=True).start()
    
    # Give the web server a second to bind the port before popping the browser
    import webbrowser
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000")
    threading.Thread(target=open_browser, daemon=True).start()
    
    boot_last("Web UI live → 127.0.0.1:8000")

    # 6. Ready
    print()
    print(f"  {STEEL}{'─' * 56}{RESET}")
    print()
    print(f"  {CYAN}{BOLD}       ■ D R A V I O N   I S   A C T I V E ■{RESET}")
    print()
    print(f"  {STEEL}{'─' * 56}{RESET}")
    print(f"  {ICE}  'text mode'{STEEL} │ {ICE}'go local'{STEEL} │ {ICE}'voice mode'{STEEL} │ {ICE}'exit'{RESET}")
    print(f"  {STEEL}{'─' * 56}{RESET}")
    print()

    await cli.run()

    print(f"\n  {DIM}[SHUTDOWN] DRAVION v.9 offline.{RESET}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n  {DIM}[SHUTDOWN] Interrupted.{RESET}")
