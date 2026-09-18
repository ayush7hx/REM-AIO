from __future__ import annotations

import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from colorama import Fore, Style, init

init(autoreset=True)

CREATOR = "devrock"
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "rem.log"

_RESET = Style.RESET_ALL
_BRIGHT = Style.BRIGHT

_PALETTE = {
    "time": Fore.LIGHTBLACK_EX,
    "info": Fore.CYAN,
    "success": Fore.GREEN,
    "warn": Fore.YELLOW,
    "error": Fore.RED,
    "cog": Fore.LIGHTMAGENTA_EX,
    "shard": Fore.MAGENTA,
    "ready": Fore.LIGHTGREEN_EX + _BRIGHT,
    "accent": Fore.LIGHTMAGENTA_EX + _BRIGHT,
    "pink": Fore.LIGHTMAGENTA_EX,
    "muted": Fore.LIGHTBLACK_EX,
    "label": Fore.WHITE + _BRIGHT,
    "creator": Fore.LIGHTCYAN_EX,
}

_KAOMOJI = (
    "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧",
    "(◕‿◕✿)",
    "♡(˶ᵔ ᵕ ᵔ˶)♡",
    "✧(≧◡≦)✧",
    "(๑˃ᴗ˂)ﻭ",
    "ʕ•ᴥ•ʔ✧",
)

_READY_LINES = (
    "REM is online — go say hi!",
    "All systems cute and operational ✧",
    "Ready to serve your guilds, senpai~",
    "Boot complete. Time to be awesome.",
)

_QUIET_LOGGERS = (
    "discord",
    "discord.gateway",
    "discord.http",
    "discord.client",
    "werkzeug",
    "asyncio",
)


class RemConsoleFormatter(logging.Formatter):
    """Cute anime-styled console formatter for REM."""

    LEVEL_STYLES = {
        logging.DEBUG: ("✧ DBG ", "muted"),
        logging.INFO: ("✧ INFO", "info"),
        logging.WARNING: ("⚠ WARN", "warn"),
        logging.ERROR: ("✖ FAIL", "error"),
        logging.CRITICAL: ("☠ CRIT", "error"),
    }

    def format(self, record: logging.LogRecord) -> str:
        stamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_name, level_key = self.LEVEL_STYLES.get(record.levelno, ("✧ LOG ", "muted"))
        logger_name = record.name.replace("rem.", "").replace("core.", "")
        if logger_name in {"rem", "__main__"}:
            logger_name = "rem-chan"
        if len(logger_name) > 16:
            logger_name = logger_name[:15] + "…"

        message = record.getMessage()
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        lines = [message]
        if record.exc_text:
            lines.append(record.exc_text)

        output = []
        for line in lines:
            output.append(
                f"{_PALETTE['time']}{stamp}{_RESET} "
                f"{_PALETTE['pink']}♡{_RESET} "
                f"{_PALETTE[level_key]}{level_name}{_RESET} "
                f"{_PALETTE['muted']}{logger_name:<16}{_RESET} "
                f"{_PALETTE['label']}{line}{_RESET}"
            )
        return "\n".join(output)


class RemFileFormatter(logging.Formatter):
    """Clean plain-text formatter for log files."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class RemConsoleHandler(logging.StreamHandler):
    """Console handler that skips duplicate noisy boot messages."""

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith("discord.") and record.levelno < logging.WARNING:
            return
        super().emit(record)


def setup_console_logging(level: str = "INFO", *, log_to_file: bool = True) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    console_handler = RemConsoleHandler(sys.stdout)
    console_handler.setFormatter(RemConsoleFormatter())
    root.addHandler(console_handler)

    if log_to_file:
        LOG_DIR.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(RemFileFormatter())
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)

    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def print_banner(bot_name: str = "DARK INFINITE") -> None:
    art = r"""
    ♡ ╭──────────────────────────────────────────────╮ ♡
      │                                              │
      │   レム  ✧  R E M   A I O   B O T  ✧  レム   │
      │                                              │
    ♡ ╰──────────────────────────────────────────────╯ ♡
"""
    print(f"{_PALETTE['pink']}{art}{_RESET}", flush=True)
    print(
        f"  {_PALETTE['accent']}✦{_RESET} {_PALETTE['label']}{bot_name}{_RESET}  "
        f"{_PALETTE['muted']}│{_RESET}  "
        f"{_PALETTE['creator']}created by {CREATOR}{_RESET}  "
        f"{_PALETTE['pink']}♡{random.choice(_KAOMOJI)}{_RESET}\n",
        flush=True,
    )


def section(title: str) -> None:
    print(
        f"{_PALETTE['pink']}  ✧ {_RESET}{_PALETTE['label']}{title}{_RESET}",
        flush=True,
    )


def info(message: str) -> None:
    _emit("info", "✧ INFO", message)


def success(message: str) -> None:
    _emit("success", "♡ OK  ", message)


def warn(message: str) -> None:
    _emit("warn", "⚠ WARN", message)


def error(message: str) -> None:
    _emit("error", "✖ FAIL", message)


def cog_progress(name: str, *, index: int, total: int) -> None:
    bar = _progress_bar(index, total, width=28)
    stamp = datetime.now().strftime("%H:%M:%S")
    line = (
        f"{_PALETTE['time']}{stamp}{_RESET} "
        f"{_PALETTE['pink']}♡{_RESET} "
        f"{_PALETTE['cog']}◈ COG {_RESET}"
        f"{_PALETTE['muted']}{bar}{_RESET} "
        f"{_PALETTE['label']}{name:<20}{_RESET}"
    )
    end = "\n" if index >= total else ""
    print(f"\r{line}", end=end, flush=True)


def cog_loaded(name: str, *, index: int | None = None, total: int | None = None) -> None:
    if index is not None and total is not None:
        cog_progress(name, index=index, total=total)
        return
    _emit("cog", "◈ COG ", name)


def ready(
    username: str,
    *,
    guilds: int,
    users: int,
    prefix_commands: int | None = None,
    slash_commands: int | None = None,
) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    stats = f"{guilds} guilds · {users:,} users"
    if prefix_commands is not None and slash_commands is not None:
        stats += f" · {prefix_commands} prefix · {slash_commands} slash"

    kaomoji = random.choice(_KAOMOJI)
    quote = random.choice(_READY_LINES)

    print(
        f"\n{_PALETTE['pink']}  ╭{'─' * 46}╮{_RESET}\n"
        f"{_PALETTE['pink']}  │{_RESET} {_PALETTE['ready']}♡ READY{_RESET} "
        f"{_PALETTE['label']}{username}{_RESET}\n"
        f"{_PALETTE['pink']}  │{_RESET} {_PALETTE['muted']}{stats}{_RESET}\n"
        f"{_PALETTE['pink']}  │{_RESET} {_PALETTE['creator']}{quote}{_RESET}\n"
        f"{_PALETTE['pink']}  ╰{'─' * 46}╯{_RESET} "
        f"{_PALETTE['pink']}{kaomoji}{_RESET}\n",
        flush=True,
    )


def shard_connected(shard_id: int) -> None:
    _emit("shard", f"✦ SH#{shard_id}", "connected to gateway ✧")


def goodbye() -> None:
    kaomoji = random.choice(("(｡•́︿•̀｡)", "(╯︵╰,)", "♡ see you soon~"))
    print(
        f"\n{_PALETTE['pink']}  ♡ REM is shutting down... {kaomoji}{_RESET}\n",
        flush=True,
    )


def summary(title: str, message: str) -> None:
    print(
        f"  {_PALETTE['success']}♡ {title:<5}{_RESET} "
        f"{_PALETTE['label']}{message}{_RESET}",
        flush=True,
    )


class LoadTimer:
    def __init__(self, label: str) -> None:
        self.label = label
        self._start = time.perf_counter()

    def finish(self, detail: str) -> None:
        elapsed = time.perf_counter() - self._start
        summary(self.label, f"{detail} in {elapsed:.2f}s ✧")


def _progress_bar(current: int, total: int, *, width: int = 28) -> str:
    if total <= 0:
        return f"[{'░' * width}]"
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current:>3}/{total}"


def _emit(color_key: str, badge: str, message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    print(
        f"{_PALETTE['time']}{stamp}{_RESET} "
        f"{_PALETTE['pink']}♡{_RESET} "
        f"{_PALETTE[color_key]}{badge}{_RESET} "
        f"{_PALETTE['label']}{message}{_RESET}",
        flush=True,
    )