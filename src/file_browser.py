"""Sidebar file browser backed by QFileSystemModel."""
from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QLabel,
    QHBoxLayout, QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt, QDir, pyqtSignal, QModelIndex
from PyQt6.QtGui import QFileSystemModel, QFont


class FileBrowser(QWidget):
    file_open_requested = pyqtSignal(str)

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._root: str = settings.get("last_directory", str(Path.home()))
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setObjectName("fb_header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 4, 4, 4)
        self._path_label = QLabel()
        self._path_label.setFont(QFont("Segoe UI", 9))
        self._path_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._path_label.setToolTip(self._root)
        hl.addWidget(self._path_label, 1)

        btn_change = QPushButton("…")
        btn_change.setFixedWidth(26)
        btn_change.setToolTip("フォルダを変更")
        btn_change.clicked.connect(self._pick_root)
        hl.addWidget(btn_change)
        layout.addWidget(header)

        # File tree
        self._model = QFileSystemModel()
        self._model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.Files | QDir.Filter.Dirs)
        self._model.setNameFilters(["*.md", "*.markdown", "*.txt"])
        self._model.setNameFilterDisables(False)

        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setRootIndex(self._model.setRootPath(self._root))
        self._tree.setHeaderHidden(True)
        self._tree.setColumnHidden(1, True)
        self._tree.setColumnHidden(2, True)
        self._tree.setColumnHidden(3, True)
        self._tree.setAnimated(False)
        self._tree.setIndentation(16)
        self._tree.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._tree)

        self._update_label()

    def set_root(self, path: str) -> None:
        self._root = path
        self._model.setRootPath(path)
        self._tree.setRootIndex(self._model.index(path))
        self._update_label()
        self._settings.set("last_directory", path)

    def get_root(self) -> str:
        return self._root

    def _pick_root(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "フォルダを選択", self._root)
        if d:
            self.set_root(d)

    def _on_double_click(self, index: QModelIndex) -> None:
        path = self._model.filePath(index)
        if Path(path).is_file():
            self.file_open_requested.emit(path)

    def _update_label(self) -> None:
        name = Path(self._root).name or self._root
        self._path_label.setText(name)
        self._path_label.setToolTip(self._root)
