from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    try:
        parsed = int(value)
    except ValueError:
        return default

    return parsed if parsed > 0 else default


APP_TITLE = os.getenv("APP_TITLE", "Abbreviation Checker")
MAX_ACTIVE_USERS = _get_int("MAX_ACTIVE_USERS", 5)
MAX_PDF_SIZE_MB = _get_int("MAX_PDF_SIZE_MB", 20)
MAX_PAGES = _get_int("MAX_PAGES", 100)
INACTIVITY_TIMEOUT_MINUTES = _get_int("INACTIVITY_TIMEOUT_MINUTES", 30)
CLEANUP_MAX_FILE_AGE_MINUTES = _get_int("CLEANUP_MAX_FILE_AGE_MINUTES", INACTIVITY_TIMEOUT_MINUTES)
QUEUE_POLL_SECONDS = _get_int("QUEUE_POLL_SECONDS", 60)
ACTIVE_HEARTBEAT_SECONDS = _get_int("ACTIVE_HEARTBEAT_SECONDS", 60)

MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024
INACTIVITY_TIMEOUT_SECONDS = INACTIVITY_TIMEOUT_MINUTES * 60
CLEANUP_MAX_FILE_AGE_SECONDS = CLEANUP_MAX_FILE_AGE_MINUTES * 60
