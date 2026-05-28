from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

SERVICE_NAME = "ai-assistant"
OPENAI_KEY_ATTR = "openai-api-key"

FALLBACK_PATH = Path.home() / ".config" / "ai-assistant" / "secrets.json"


# ---------------------------------------------------------------------------
# Fallback file storage (used when libsecret / gnome-keyring is unavailable
# or stays locked). Permissions are restricted to the owner (chmod 600).
# ---------------------------------------------------------------------------
def _load_fallback() -> dict[str, str]:
    if not FALLBACK_PATH.is_file():
        return {}
    try:
        return json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read fallback secrets file")
        return {}


def _save_fallback(data: dict[str, str]) -> None:
    FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    FALLBACK_PATH.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(FALLBACK_PATH, 0o600)
    except OSError:
        logger.warning("Could not chmod 600 on %s", FALLBACK_PATH)


# ---------------------------------------------------------------------------
# libsecret / gnome-keyring helpers
# ---------------------------------------------------------------------------
def _get_collection():
    try:
        import secretstorage
    except ImportError:
        logger.warning("secretstorage not available")
        return None

    try:
        bus = secretstorage.dbus_init()
        return secretstorage.get_default_collection(bus)
    except Exception:
        logger.exception("Failed to connect to secret service")
        return None


def _try_unlock(collection) -> bool:
    """Best-effort unlock; returns True if the collection is usable."""
    try:
        if collection.is_locked():
            collection.unlock()
        return not collection.is_locked()
    except Exception:
        logger.exception("Failed to unlock keyring collection")
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_openai_api_key() -> str | None:
    collection = _get_collection()
    if collection is not None and _try_unlock(collection):
        try:
            items = list(collection.search_items(
                {"application": SERVICE_NAME, "key": OPENAI_KEY_ATTR}
            ))
            for item in items:
                try:
                    if item.is_locked():
                        item.unlock()
                    return item.get_secret().decode("utf-8")
                except Exception:
                    logger.exception("Failed to read item from keyring")
        except Exception:
            logger.exception("Failed to search keyring for OpenAI key")

    return _load_fallback().get(OPENAI_KEY_ATTR)


def set_openai_api_key(api_key: str) -> None:
    """Store the key in the keyring; fall back to a chmod-600 file on failure."""
    collection = _get_collection()
    if collection is not None and _try_unlock(collection):
        try:
            existing = list(collection.search_items(
                {"application": SERVICE_NAME, "key": OPENAI_KEY_ATTR}
            ))
            for item in existing:
                try:
                    if item.is_locked():
                        item.unlock()
                    item.delete()
                except Exception:
                    logger.exception("Failed to delete existing keyring item")
            collection.create_item(
                f"{SERVICE_NAME}/{OPENAI_KEY_ATTR}",
                {"application": SERVICE_NAME, "key": OPENAI_KEY_ATTR},
                api_key.encode("utf-8"),
            )
            # Clean up any stale fallback entry
            fallback = _load_fallback()
            if OPENAI_KEY_ATTR in fallback:
                fallback.pop(OPENAI_KEY_ATTR, None)
                _save_fallback(fallback)
            logger.info("Stored OpenAI API key in system keyring")
            return
        except Exception:
            logger.exception("Keyring write failed – falling back to file")

    fallback = _load_fallback()
    fallback[OPENAI_KEY_ATTR] = api_key
    _save_fallback(fallback)
    logger.info("Stored OpenAI API key in fallback file: %s", FALLBACK_PATH)


def delete_openai_api_key() -> None:
    collection = _get_collection()
    if collection is not None and _try_unlock(collection):
        try:
            existing = list(collection.search_items(
                {"application": SERVICE_NAME, "key": OPENAI_KEY_ATTR}
            ))
            for item in existing:
                try:
                    if item.is_locked():
                        item.unlock()
                    item.delete()
                except Exception:
                    logger.exception("Failed to delete keyring item")
        except Exception:
            logger.exception("Keyring delete failed")

    fallback = _load_fallback()
    if OPENAI_KEY_ATTR in fallback:
        fallback.pop(OPENAI_KEY_ATTR, None)
        _save_fallback(fallback)
