import logging

__all__ = ["setup_logging", "SILENCE_LOGGERS"]

import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path

SILENCE_LOGGERS = [
    "httpx",
    "httpcore",
    "httpcore.connection",
    "httpcore.http11",
    "anyio",
    "h11",
    "hishel",
    "urllib3",
    "asyncio",
]


def setup_logging(
    level: str = "INFO",
    file: str = "",
    message_format: str = "simple",
    show_timestamp: bool = True,
    silence_loggers: list[str] = SILENCE_LOGGERS,
    config: dict | None = None,
):
    """
    Configure stdlib logging.

    Params:
        level (str): Console log level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        file (str): Optional path to a file to append logs to (file always uses DEBUG)
        message_format (str): "simple", "detailed", or "debug" (affects console)
        show_timestamp (bool): If False, omit timestamps from console output
        config (logging.dictConfig): Optional dictConfig; if provided, other params are ignored
        silence_loggers (list[str]): iterable of logger names to silence (set to WARNING & stop propagation)
    """

    if config:
        logging.config.dictConfig(config)
        return

    ## normalize requested console level
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    console_level = level_map.get(level.lower(), logging.INFO)

    ## root logger: let handlers decide filtering, so use NOTSET
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)

    root.setLevel(logging.NOTSET)

    ## Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)

    ## File handler (always DEBUG if present)
    file_handler = None
    if file:
        Path(file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

    ## timestamp format used when timestamps are enabled
    timestamp_fmt = "%Y-%m-%d %H:%M:%S"

    ## Build console format depending on options:
    #    - If console_level is DEBUG -> always include logger name and line
    #    - else respect message_format and show_timestamp
    if console_level == logging.DEBUG:
        ## detailed with logger name for debug sessions
        console_fmt_core = "%(name)s:%(lineno)d :: %(message)s"
        prefix = (
            "%(asctime)s [%(levelname)s] " if show_timestamp else "[%(levelname)s] "
        )
        console_fmt = prefix + console_fmt_core
    else:
        if message_format == "debug":
            core = "%(name)s:%(lineno)d :: %(message)s"
            prefix = (
                "%(asctime)s [%(levelname)s] " if show_timestamp else "[%(levelname)s] "
            )
            console_fmt = prefix + core
        elif message_format == "detailed":
            core = "(%(filename)s:%(lineno)d) :: %(message)s"
            prefix = (
                "%(asctime)s | [%(levelname)s] | "
                if show_timestamp
                else "[%(levelname)s] | "
            )
            console_fmt = prefix + core
        else:
            if show_timestamp:
                console_fmt = "%(asctime)s [%(levelname)s] :: %(message)s"
            else:
                console_fmt = "[%(levelname)s] :: %(message)s"

    console_formatter = logging.Formatter(
        console_fmt, datefmt=timestamp_fmt if show_timestamp else None
    )
    console_handler.setFormatter(console_formatter)

    root.addHandler(console_handler)

    if file_handler:
        ## file always detailed and timestamped
        file_fmt = (
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)-3d :: %(message)s"
        )
        file_formatter = logging.Formatter(file_fmt, datefmt=timestamp_fmt)
        file_handler.setFormatter(file_formatter)

        root.addHandler(file_handler)

    ## Silence noisy third-party loggers by setting them WARNING and stopping propagation.
    #  This prevents their DEBUG messages from reaching the root handlers.
    for lib in silence_loggers:
        if not isinstance(lib, str):
            raise TypeError(
                f"Invalid type for silence_logger item: {type(lib).__name__}. Expected a string."
            )

        lg = logging.getLogger(lib)
        lg.setLevel(logging.WARNING)

        ## don't propagate to root (prevents double-logging if they have their own handlers)
        lg.propagate = False
