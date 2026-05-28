from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SERVICE_NAME = "ai-assistant"
OPENAI_KEY_ATTR = "openai-api-key"


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


def get_openai_api_key() -> str | None:
    collection = _get_collection()
    if collection is None:
        return None

    try:
        items = list(collection.search_items({"application": SERVICE_NAME, "key": OPENAI_KEY_ATTR}))
        if items:
            return items[0].get_secret().decode("utf-8")
    except Exception:
        logger.exception("Failed to read OpenAI API key from keyring")

    return None


def set_openai_api_key(api_key: str) -> None:
    collection = _get_collection()
    if collection is None:
        raise RuntimeError("Secret service not available. Install libsecret and ensure gnome-keyring is running.")

    existing = list(collection.search_items({"application": SERVICE_NAME, "key": OPENAI_KEY_ATTR}))
    for item in existing:
        item.delete()

    collection.create_item(
        f"{SERVICE_NAME}/{OPENAI_KEY_ATTR}",
        {"application": SERVICE_NAME, "key": OPENAI_KEY_ATTR},
        api_key.encode("utf-8"),
    )


def delete_openai_api_key() -> None:
    collection = _get_collection()
    if collection is None:
        return

    existing = list(collection.search_items({"application": SERVICE_NAME, "key": OPENAI_KEY_ATTR}))
    for item in existing:
        item.delete()
