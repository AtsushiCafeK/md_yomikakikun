"""Multi-tab manager pairing each tab with a MarkdownEditor."""
from __future__ import annotations
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QMessageBox, QApplication
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence
from .editor import MarkdownEditor

_UNTITLED = "無題"


class TabWidget(QTabWidget):
    current_editor_changed = pyqtSignal(object)  # MarkdownEditor | None
    tab_title_changed = pyqtSignal(int, str)

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.tabCloseRequested.connect(self._close_tab)
        self.currentChanged.connect(lambda _: self.current_editor_changed.emit(self.current_editor()))

    # ------------------------------------------------------------------
    def new_tab(self, path: str | None = None) -> MarkdownEditor:
        editor = MarkdownEditor(self._settings)
        editor.textChanged.connect(lambda: self._on_text_changed(editor))

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(editor)

        title = Path(path).name if path else _UNTITLED
        idx = self.addTab(container, title)
        self.setCurrentIndex(idx)

        if path and Path(path).exists():
            try:
                editor.file_path = path          # パスを先に設定してから内容をセット
                with open(path, "r", encoding="utf-8") as f:
                    editor.setPlainText(f.read())
                editor.mark_clean()
                self._update_tab_title(idx, editor)   # dirty フラグ解除後にタイトルを確定
            except OSError as e:
                QMessageBox.warning(self, "エラー", str(e))
        return editor

    def current_editor(self) -> MarkdownEditor | None:
        w = self.currentWidget()
        if w is None:
            return None
        return w.findChild(MarkdownEditor)

    def editor_at(self, index: int) -> MarkdownEditor | None:
        w = self.widget(index)
        if w is None:
            return None
        return w.findChild(MarkdownEditor)

    def find_tab_for_path(self, path: str) -> int:
        for i in range(self.count()):
            ed = self.editor_at(i)
            if ed and ed.file_path == path:
                return i
        return -1

    def save_current(self) -> bool:
        ed = self.current_editor()
        if ed is None:
            return False
        return self._save_editor(ed)

    def save_all(self) -> None:
        for i in range(self.count()):
            ed = self.editor_at(i)
            if ed and ed.is_dirty:
                self._save_editor(ed)

    def _save_editor(self, ed: MarkdownEditor) -> bool:
        if not ed.file_path:
            from PyQt6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(
                self, "名前を付けて保存", "", "Markdown (*.md *.markdown);;All (*)"
            )
            if not path:
                return False
            ed.file_path = path
        try:
            with open(ed.file_path, "w", encoding="utf-8") as f:
                f.write(ed.toPlainText())
            ed.mark_clean()
            idx = self.find_tab_for_path(ed.file_path)
            if idx >= 0:
                self._update_tab_title(idx, ed)
            self._settings.add_recent(ed.file_path)
            return True
        except OSError as e:
            QMessageBox.warning(self, "保存エラー", str(e))
            return False

    def _close_tab(self, index: int) -> None:
        ed = self.editor_at(index)
        if ed and ed.is_dirty:
            name = Path(ed.file_path).name if ed.file_path else _UNTITLED
            resp = QMessageBox.question(
                self, "保存確認",
                f"「{name}」は変更されています。保存しますか？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if resp == QMessageBox.StandardButton.Cancel:
                return
            if resp == QMessageBox.StandardButton.Save:
                if not self._save_editor(ed):
                    return
        self.removeTab(index)
        if self.count() == 0:
            self.new_tab()

    def _on_text_changed(self, editor: MarkdownEditor) -> None:
        idx = -1
        for i in range(self.count()):
            if self.editor_at(i) is editor:
                idx = i
                break
        if idx >= 0:
            editor._is_dirty = True
            self._update_tab_title(idx, editor)

    def _update_tab_title(self, idx: int, editor: MarkdownEditor) -> None:
        name = Path(editor.file_path).name if editor.file_path else _UNTITLED
        title = ("● " if editor.is_dirty else "") + name
        self.setTabText(idx, title)
        self.setTabToolTip(idx, editor.file_path or "")

    def set_dark(self, dark: bool) -> None:
        for i in range(self.count()):
            ed = self.editor_at(i)
            if ed:
                ed.set_dark(dark)

    def ask_save_all_before_close(self) -> bool:
        """Returns False if user cancels."""
        for i in range(self.count()):
            ed = self.editor_at(i)
            if ed and ed.is_dirty:
                name = Path(ed.file_path).name if ed.file_path else _UNTITLED
                resp = QMessageBox.question(
                    self, "保存確認",
                    f"「{name}」は変更されています。保存しますか？",
                    QMessageBox.StandardButton.Save |
                    QMessageBox.StandardButton.Discard |
                    QMessageBox.StandardButton.Cancel
                )
                if resp == QMessageBox.StandardButton.Cancel:
                    return False
                if resp == QMessageBox.StandardButton.Save:
                    if not self._save_editor(ed):
                        return False
        return True
