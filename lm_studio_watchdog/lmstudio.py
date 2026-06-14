from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


_BACKED_UP_PATHS: set[Path] = set()
_BACKUP_LOCK = threading.Lock()


class LMStudioConversationError(RuntimeError):
    pass


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def create_backup_once(path: Path, logger: Callable[[str], None] | None = None) -> Path | None:
    resolved = path.resolve()
    with _BACKUP_LOCK:
        if resolved in _BACKED_UP_PATHS:
            return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".backup_{timestamp}")
    shutil.copy2(path, backup_path)

    with _BACKUP_LOCK:
        _BACKED_UP_PATHS.add(resolved)

    if logger:
        logger(f"Backup created: {backup_path}")
    return backup_path


def replace_first_message(conversation: dict[str, Any], new_text: str) -> None:
    messages = conversation.get("messages")
    if not isinstance(messages, list) or not messages:
        raise LMStudioConversationError("Conversation JSON has no messages array.")

    first_message = messages[0]
    if not isinstance(first_message, dict):
        raise LMStudioConversationError("First message is not an object.")

    new_content = [{"type": "text", "text": new_text}]
    new_preprocessed = {"role": "user", "content": new_content}

    versions = first_message.get("versions")
    if isinstance(versions, list):
        if not versions:
            first_message["versions"] = [{}]
            versions = first_message["versions"]

        first_version = versions[0]
        if not isinstance(first_version, dict):
            raise LMStudioConversationError("First message version is not an object.")

        first_version["role"] = "user"
        first_version["content"] = new_content
        # ✅ Fix: update preprocessed so the model actually receives the new context
        first_version["preprocessed"] = new_preprocessed
        first_message["currentlySelected"] = 0
        return

    first_message["role"] = "user"
    first_message["content"] = new_content
    # ✅ Fix: same for flat structure
    first_message["preprocessed"] = new_preprocessed


def sync_first_message(
    merged_text: str,
    conversation_path: Path,
    backup: bool = True,
    logger: Callable[[str], None] | None = None,
) -> None:
    if not conversation_path.exists():
        raise LMStudioConversationError(f"Conversation file not found: {conversation_path}")

    if backup:
        create_backup_once(conversation_path, logger)

    try:
        conversation = json.loads(conversation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LMStudioConversationError(f"Conversation JSON is invalid: {exc}") from exc

    if not isinstance(conversation, dict):
        raise LMStudioConversationError("Conversation JSON root is not an object.")

    replace_first_message(conversation, merged_text)
    atomic_write_json(conversation_path, conversation)