from __future__ import annotations

import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app_config import BASE_DIR, CLEANUP_MAX_FILE_AGE_SECONDS


TEMP_OUTPUTS_DIR = BASE_DIR / "temp_outputs"


def ensure_storage_dirs() -> None:
    TEMP_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def safe_folder_name(filename: str, max_length: int = 50) -> str:
    base = Path(filename).stem
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", base).strip("_")
    return (safe or "uploaded_pdf")[:max_length]


def safe_user_id(user_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", user_id)


def get_user_dir(user_id: str) -> Path:
    return TEMP_OUTPUTS_DIR / f"user_{safe_user_id(user_id)}"


def create_run_dir(user_id: str, filename: str, timestamp: str | None = None) -> Path:
    ensure_storage_dirs()
    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = get_user_dir(user_id) / f"{safe_folder_name(filename)}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def path_belongs_to_user(path: str | Path, user_id: str) -> bool:
    try:
        resolved_path = Path(path).resolve()
        resolved_user_dir = get_user_dir(user_id).resolve()
        return resolved_path == resolved_user_dir or resolved_user_dir in resolved_path.parents
    except OSError:
        return False


def delete_user_files(user_id: str) -> None:
    user_dir = get_user_dir(user_id)
    if user_dir.exists():
        shutil.rmtree(user_dir, ignore_errors=True)


def cleanup_old_files(max_age_seconds: int = CLEANUP_MAX_FILE_AGE_SECONDS) -> None:
    ensure_storage_dirs()
    now = datetime.now(timezone.utc).timestamp()

    for user_dir in TEMP_OUTPUTS_DIR.glob("user_*"):
        if not user_dir.is_dir():
            continue

        newest_mtime = max(
            (p.stat().st_mtime for p in user_dir.rglob("*") if p.exists()),
            default=user_dir.stat().st_mtime,
        )
        if now - newest_mtime > max_age_seconds:
            shutil.rmtree(user_dir, ignore_errors=True)


def save_uploaded_file(uploaded_file, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        handle.write(uploaded_file.getbuffer())
    return destination
