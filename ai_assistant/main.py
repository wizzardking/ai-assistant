from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication

from ai_assistant.app_controller import AppController

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("AI Assistant")
    app.setQuitOnLastWindowClosed(False)

    AppController(app)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
