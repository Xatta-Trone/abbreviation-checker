from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from filelock import FileLock

from app_config import INACTIVITY_TIMEOUT_SECONDS, MAX_ACTIVE_USERS
from file_manager import BASE_DIR, delete_user_files


RUNTIME_DIR = BASE_DIR / "runtime"
ACTIVE_USERS_PATH = RUNTIME_DIR / "active_users.json"
QUEUE_PATH = RUNTIME_DIR / "queue.json"
LOCK_PATH = RUNTIME_DIR / "session.lock"

def ensure_runtime_files() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if not ACTIVE_USERS_PATH.exists():
        ACTIVE_USERS_PATH.write_text("{}", encoding="utf-8")
    if not QUEUE_PATH.exists():
        QUEUE_PATH.write_text("[]", encoding="utf-8")


def new_user_id() -> str:
    return uuid.uuid4().hex


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _drop_expired(active_users: dict[str, dict[str, Any]], queue: list[dict[str, Any]], now: float) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    expired_user_ids = [
        user_id
        for user_id, state in active_users.items()
        if now - float(state.get("last_active", 0)) > INACTIVITY_TIMEOUT_SECONDS
    ]

    for user_id in expired_user_ids:
        active_users.pop(user_id, None)
        delete_user_files(user_id)

    queue = [
        entry
        for entry in queue
        if now - float(entry.get("last_active", entry.get("joined_at", 0))) <= INACTIVITY_TIMEOUT_SECONDS
    ]
    return active_users, queue


def _promote_queue(active_users: dict[str, dict[str, Any]], queue: list[dict[str, Any]], now: float) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    while len(active_users) < MAX_ACTIVE_USERS and queue:
        entry = queue.pop(0)
        user_id = entry["user_id"]
        active_users[user_id] = {
            "status": "active",
            "last_active": now,
            "current_run_dir": None,
            "excel_path": None,
            "pdf_path": None,
            "processing": False,
            "completed": False,
            "error": None,
        }
    return active_users, queue


def get_or_create_user_state(user_id: str) -> tuple[str, dict[str, Any] | None, int | None]:
    ensure_runtime_files()
    now = time.time()

    with FileLock(str(LOCK_PATH)):
        active_users = _read_json(ACTIVE_USERS_PATH, {})
        queue = _read_json(QUEUE_PATH, [])
        active_users, queue = _drop_expired(active_users, queue, now)

        if user_id in active_users:
            active_users[user_id]["last_active"] = now
            status = "active"
            state = active_users[user_id]
            queue_position = None
        else:
            existing_queue_ids = [entry["user_id"] for entry in queue]
            if len(active_users) < MAX_ACTIVE_USERS and user_id not in existing_queue_ids:
                active_users[user_id] = {
                    "status": "active",
                    "last_active": now,
                    "current_run_dir": None,
                    "excel_path": None,
                    "pdf_path": None,
                    "processing": False,
                    "completed": False,
                    "error": None,
                }
                status = "active"
                state = active_users[user_id]
                queue_position = None
            else:
                if user_id not in existing_queue_ids:
                    queue.append({"user_id": user_id, "joined_at": now, "last_active": now})
                else:
                    for entry in queue:
                        if entry["user_id"] == user_id:
                            entry["last_active"] = now
                            break
                status = "queued"
                state = None
                queue_position = [entry["user_id"] for entry in queue].index(user_id) + 1

        active_users, queue = _promote_queue(active_users, queue, now)
        _write_json(ACTIVE_USERS_PATH, active_users)
        _write_json(QUEUE_PATH, queue)

    return status, state, queue_position


def update_user_state(user_id: str, **updates: Any) -> dict[str, Any]:
    ensure_runtime_files()
    now = time.time()

    with FileLock(str(LOCK_PATH)):
        active_users = _read_json(ACTIVE_USERS_PATH, {})
        state = active_users.setdefault(user_id, {})
        state.update(updates)
        state["last_active"] = now
        active_users[user_id] = state
        _write_json(ACTIVE_USERS_PATH, active_users)
        return state


def get_usage_summary() -> dict[str, int]:
    ensure_runtime_files()

    with FileLock(str(LOCK_PATH)):
        active_users = _read_json(ACTIVE_USERS_PATH, {})
        queue = _read_json(QUEUE_PATH, [])

    return {
        "active_users": len(active_users),
        "queued_users": len(queue),
        "max_active_users": MAX_ACTIVE_USERS,
    }


def clear_user_state(user_id: str) -> None:
    ensure_runtime_files()
    with FileLock(str(LOCK_PATH)):
        active_users = _read_json(ACTIVE_USERS_PATH, {})
        queue = _read_json(QUEUE_PATH, [])
        active_users.pop(user_id, None)
        queue = [entry for entry in queue if entry.get("user_id") != user_id]
        _write_json(ACTIVE_USERS_PATH, active_users)
        _write_json(QUEUE_PATH, queue)
    delete_user_files(user_id)
