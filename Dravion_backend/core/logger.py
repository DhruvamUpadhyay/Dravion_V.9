"""
DRAVION v.9 — Logger

Pretty colored console output. No JSON spam in terminal.
"""
import structlog
import logging
import sys

# ANSI
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
RESET = "\033[0m"


class DravionConsoleRenderer:
    """Custom renderer that prints clean colored lines instead of JSON."""

    LEVEL_COLORS = {
        "debug": DIM,
        "info": GREEN,
        "warning": YELLOW,
        "error": RED,
        "critical": RED,
    }

    def __call__(self, logger, method_name, event_dict):
        level = event_dict.pop("level", method_name)
        event = event_dict.pop("event", "")
        color = self.LEVEL_COLORS.get(level, RESET)

        # Build extra info string
        extras = " | ".join(f"{k}={v}" for k, v in event_dict.items()
                           if k not in ("logger", "timestamp"))

        line = f"{DIM}[{level.upper():>5}]{RESET} {color}{event}{RESET}"
        if extras:
            line += f" {DIM}({extras}){RESET}"
        return line


def setup_logger():
    # Suppress noisy libs
    for name in ["httpx", "chromadb", "sentence_transformers", "urllib3",
                  "posthog", "openai", "httpcore"]:
        logging.getLogger(name).setLevel(logging.ERROR)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            DravionConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


setup_logger()
log = structlog.get_logger("dravion.core")
