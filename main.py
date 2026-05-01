import sys
import os

# QtWebEngineWidgets MUST be imported before QApplication is created
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-logging")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

# This import order is required on Windows
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401 – must precede QApplication
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.settings import Settings
from src.main_window import MainWindow


def main() -> None:
    # High-DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("MD読み書き君")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("local")

    settings = Settings()
    window = MainWindow(settings)
    window.show()

    # Open files passed as CLI arguments
    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            window._open_file(arg)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
