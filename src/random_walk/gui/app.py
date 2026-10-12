"""Application setup and the GUI entry point."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from random_walk.gui.main_window import MainWindow


def create_app(argv: list[str] | None = None) -> QApplication:
    """The QApplication, in the light colour scheme regardless of the OS setting."""
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    assert isinstance(app, QApplication)
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    return app


def run() -> int:
    """Open the main window and run the event loop until it closes."""
    app = create_app()
    window = MainWindow()
    window.show()
    return app.exec()
