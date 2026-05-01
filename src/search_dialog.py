"""Full-text search across all .md files in the current root directory."""
from __future__ import annotations
import os
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QCheckBox, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QFont


class _Worker(QObject):
    result = pyqtSignal(str, int, str)   # path, lineno, snippet
    finished = pyqtSignal()

    def __init__(self, root: str, query: str, case: bool, regex: bool) -> None:
        super().__init__()
        self._root = root
        self._query = query
        self._case = case
        self._regex = regex

    def run(self) -> None:
        flags = 0 if self._case else re.IGNORECASE
        try:
            if self._regex:
                pattern = re.compile(self._query, flags)
            else:
                pattern = re.compile(re.escape(self._query), flags)
        except re.error:
            self.finished.emit()
            return

        for dirpath, _dirs, files in os.walk(self._root):
            for fname in files:
                if not fname.lower().endswith((".md", ".markdown", ".txt")):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for lineno, line in enumerate(f, 1):
                            if pattern.search(line):
                                snippet = line.strip()[:120]
                                self.result.emit(fpath, lineno, snippet)
                except OSError:
                    pass
        self.finished.emit()


class SearchDialog(QDialog):
    open_file_at_line = pyqtSignal(str, int)

    def __init__(self, root: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._root = root
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self.setWindowTitle("全文検索")
        self.resize(680, 500)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Search bar
        bar = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("検索キーワード…")
        self._input.returnPressed.connect(self._start_search)
        bar.addWidget(self._input, 1)

        self._btn_search = QPushButton("検索")
        self._btn_search.clicked.connect(self._start_search)
        bar.addWidget(self._btn_search)
        layout.addLayout(bar)

        # Options
        opts = QHBoxLayout()
        self._chk_case = QCheckBox("大文字小文字を区別")
        self._chk_regex = QCheckBox("正規表現")
        opts.addWidget(self._chk_case)
        opts.addWidget(self._chk_regex)
        opts.addStretch()
        self._status_label = QLabel("")
        self._status_label.setFont(QFont("Segoe UI", 9))
        opts.addWidget(self._status_label)
        layout.addLayout(opts)

        # Results
        self._results = QListWidget()
        self._results.setFont(QFont("Consolas", 10))
        self._results.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._results)

        info = QLabel("ダブルクリックでファイルを開きます")
        info.setFont(QFont("Segoe UI", 8))
        info.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(info)

    def set_root(self, root: str) -> None:
        self._root = root

    def _start_search(self) -> None:
        query = self._input.text().strip()
        if not query:
            return
        self._results.clear()
        self._status_label.setText("検索中…")
        self._btn_search.setEnabled(False)

        self._worker = _Worker(
            self._root, query,
            self._chk_case.isChecked(),
            self._chk_regex.isChecked()
        )
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.result.connect(self._add_result)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _add_result(self, path: str, lineno: int, snippet: str) -> None:
        rel = os.path.relpath(path, self._root)
        label = f"{rel}:{lineno}  {snippet}"
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, (path, lineno))
        self._results.addItem(item)
        self._status_label.setText(f"{self._results.count()} 件")

    def _on_finished(self) -> None:
        self._btn_search.setEnabled(True)
        count = self._results.count()
        self._status_label.setText(f"{count} 件" if count else "見つかりませんでした")

    def _on_double_click(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            path, lineno = data
            self.open_file_at_line.emit(path, lineno)
