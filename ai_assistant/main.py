from __future__ import annotations

import logging
import sys
import traceback

from PyQt6.QtWidgets import QApplication

from ai_assistant.app_controller import AppController

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _global_exception_hook(exc_type, exc_value, exc_tb) -> None:
    """Log uncaught exceptions but keep the application running."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.error(
        "Uncaught exception:\n%s",
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
    )


def main() -> None:
    sys.excepthook = _global_exception_hook

    app = QApplication(sys.argv)
    app.setApplicationName("AI Assistant")
    app.setQuitOnLastWindowClosed(False)

    AppController(app)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
