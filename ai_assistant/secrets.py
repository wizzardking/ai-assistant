from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from ai_assistant.config import CONFIG_DIR

logger = logging.getLogger(__name__)

SERVICE_NAME = "ai-assistant"
OPENAI_KEY_ATTR = "openai-api-key"

FALLBACK_PATH = CONFIG_DIR / "secrets.json"

# When set to "1"/"true"/"yes", the OS keyring is bypassed entirely and the
# API key is stored in the chmod-600 fallback file. Useful on systems where
# the keyring keeps prompting for an unlock password (e.g. auto-login).
ENV_USE_FILE = "AI_ASSISTANT_USE_FILE_SECRETS"


def _file_only() -> bool:
    return os.environ.get(ENV_USE_FILE, "").strip().lower() in ("1", "true", "yes", "on")


def _env_api_key() -> str | None:
    """Allow OPENAI_API_KEY to override anything else."""
    value = os.environ.get("OPENAI_API_KEY")
    return value.strip() if value else None


# ---------------------------------------------------------------------------
# Fallback file storage (used when the OS keyring is unavailable). On POSIX
# we restrict permissions to the owner; on Windows the file lives in
# %APPDATA% which is per-user.
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
    if os.name == "posix":
        try:
            os.chmod(FALLBACK_PATH, 0o600)
        except OSError:
            logger.warning("Could not chmod 600 on %s", FALLBACK_PATH)


# ---------------------------------------------------------------------------
# Keyring helpers (cross-platform via the `keyring` package).
# ---------------------------------------------------------------------------
def _keyring():
    if _file_only():
        return None
    try:
        import keyring  # type: ignore
        # Detect the "fail" backend (no real keyring backend available) so we
        # don't block the UI with broken Secret Service round-trips.
        try:
            backend = keyring.get_keyring()
            if backend.__class__.__module__.endswith(".fail"):
                logger.info("No usable keyring backend – using fallback file only")
                return None
        except Exception:
            pass
        return keyring
    except Exception:
        logger.warning("keyring package not available – using fallback file only")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_openai_api_key() -> str | None:
    env_key = _env_api_key()
    if env_key:
        return env_key

    if _file_only():
        return _load_fallback().get(OPENAI_KEY_ATTR)

    keyring = _keyring()
    if keyring is not None:
        try:
            value = keyring.get_password(SERVICE_NAME, OPENAI_KEY_ATTR)
            if value:
                return value
        except Exception:
            logger.exception("Keyring read failed – trying fallback file")

    return _load_fallback().get(OPENAI_KEY_ATTR)


def set_openai_api_key(api_key: str) -> None:
    """Store the key.

    Behaviour:
      - If ``AI_ASSISTANT_USE_FILE_SECRETS`` is set, write directly to
        ``secrets.json`` (chmod 600) and skip the OS keyring.
      - Otherwise try the OS keyring first; on failure fall back to the file.
    """
    if _file_only():
        fallback = _load_fallback()
        fallback[OPENAI_KEY_ATTR] = api_key
        _save_fallback(fallback)
        logger.info("Stored OpenAI API key in file (keyring bypassed): %s", FALLBACK_PATH)
        return

    keyring = _keyring()
    if keyring is not None:
        try:
            keyring.set_password(SERVICE_NAME, OPENAI_KEY_ATTR, api_key)
            # Clean up any stale fallback entry so we don't keep two copies.
            fallback = _load_fallback()
            if OPENAI_KEY_ATTR in fallback:
                fallback.pop(OPENAI_KEY_ATTR, None)
                _save_fallback(fallback)
            logger.info("Stored OpenAI API key in OS keyring")
            return
        except Exception:
            logger.exception("Keyring write failed – falling back to file")

    fallback = _load_fallback()
    fallback[OPENAI_KEY_ATTR] = api_key
    _save_fallback(fallback)
    logger.info("Stored OpenAI API key in fallback file: %s", FALLBACK_PATH)


def delete_openai_api_key() -> None:
    if not _file_only():
        keyring = _keyring()
        if keyring is not None:
            try:
                keyring.delete_password(SERVICE_NAME, OPENAI_KEY_ATTR)
            except Exception:
                # Most likely the key didn't exist – treat as best effort.
                logger.debug("Keyring delete failed (ignored)", exc_info=True)

    fallback = _load_fallback()
    if OPENAI_KEY_ATTR in fallback:
        fallback.pop(OPENAI_KEY_ATTR, None)
        _save_fallback(fallback)


def storage_mode() -> str:
    """Diagnostic helper: returns where the key would be read from."""
    if _env_api_key():
        return "env:OPENAI_API_KEY"
    if _file_only():
        return f"file:{FALLBACK_PATH}"
    if _keyring() is not None:
        return f"keyring:{SERVICE_NAME}"
    return f"file:{FALLBACK_PATH}"


def fallback_path() -> Path:
    """Public accessor (e.g. for diagnostics)."""
    return FALLBACK_PATH
