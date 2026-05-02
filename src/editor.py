"""Markdown plain-text editor with auto-continuation, drag & drop, and toolbar actions."""
from __future__ import annotations
import os
import re
from pathlib import Path
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import (
    QFont, QKeyEvent, QTextCursor, QDropEvent, QDragEnterEvent,
    QDragMoveEvent, QPalette, QColor
)
from .highlighter import MarkdownHighlighter

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
_MD_EXTS    = {".md", ".markdown", ".txt"}

_LIST_PREFIX_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s")
_ORDERED_RE = re.compile(r"^(\s*)(\d+)\.\s")

# Task list detection
_TASK_RE = re.compile(r"^(\s*[-*+]\s)\[[ xX]\]\s")


class MarkdownEditor(QPlainTextEdit):
    file_path_changed   = pyqtSignal(str)
    file_open_requested = pyqtSignal(str)   # emitted when .md file is dropped
    scroll_ratio_changed = pyqtSignal(float) # 0.0〜1.0 のスクロール比率

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._file_path: str | None = None
        self._is_dirty = False

        self._apply_font()
        self._highlighter = MarkdownHighlighter(self.document())
        self.setAcceptDrops(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.verticalScrollBar().valueChanged.connect(self._emit_scroll_ratio)

    def _emit_scroll_ratio(self, value: int) -> None:
        sb = self.verticalScrollBar()
        maximum = sb.maximum()
        ratio = value / maximum if maximum > 0 else 0.0
        self.scroll_ratio_changed.emit(ratio)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def file_path(self) -> str | None:
        return self._file_path

    @file_path.setter
    def file_path(self, path: str | None) -> None:
        self._file_path = path
        self.file_path_changed.emit(path or "")

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    def mark_clean(self) -> None:
        self._is_dirty = False

    def set_dark(self, dark: bool) -> None:
        self._highlighter.set_dark(dark)
        p = self.palette()
        if dark:
            p.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
            p.setColor(QPalette.ColorRole.Text, QColor("#d4d4d4"))
        else:
            p.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            p.setColor(QPalette.ColorRole.Text, QColor("#1f1f1f"))
        self.setPalette(p)

    def _apply_font(self) -> None:
        family = self._settings.get("font_family", "Consolas")
        size = self._settings.get("font_size", 14)
        font = QFont(family, size)
        font.setFixedPitch(True)
        self.setFont(font)

    def refresh_font(self) -> None:
        self._apply_font()

    # ------------------------------------------------------------------
    # Toolbar helpers
    # ------------------------------------------------------------------
    def wrap_selection(self, prefix: str, suffix: str | None = None) -> None:
        suffix = suffix if suffix is not None else prefix
        cursor = self.textCursor()
        selected = cursor.selectedText()
        cursor.beginEditBlock()
        if selected:
            cursor.insertText(f"{prefix}{selected}{suffix}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{prefix}{suffix}")
            cursor.setPosition(pos + len(prefix))
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def insert_heading(self, level: int) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        line = self.textCursor().block().text()
        m = re.match(r"^(#{1,6})\s", line)
        if m:
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                QTextCursor.MoveMode.KeepAnchor)
            new_text = re.sub(r"^#{1,6}\s", "#" * level + " ", line)
            cursor.insertText(new_text)
        else:
            cursor.insertText("#" * level + " ")
        cursor.endEditBlock()

    def insert_link(self) -> None:
        cursor = self.textCursor()
        selected = cursor.selectedText()
        cursor.beginEditBlock()
        if selected:
            cursor.insertText(f"[{selected}](url)")
        else:
            pos = cursor.position()
            cursor.insertText("[text](url)")
            cursor.setPosition(pos + 1)
            cursor.setPosition(pos + 5, QTextCursor.MoveMode.KeepAnchor)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def insert_image(self, path: str = "") -> None:
        rel = self._to_relative(path)
        cursor = self.textCursor()
        cursor.insertText(f"![alt]({rel})\n")

    def insert_code_block(self) -> None:
        cursor = self.textCursor()
        selected = cursor.selectedText()
        cursor.beginEditBlock()
        if selected:
            cursor.insertText(f"```\n{selected}\n```\n")
        else:
            pos = cursor.position()
            cursor.insertText("```\n\n```\n")
            cursor.setPosition(pos + 4)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def insert_table(self) -> None:
        cursor = self.textCursor()
        cursor.insertText(
            "| 列1 | 列2 | 列3 |\n"
            "| --- | --- | --- |\n"
            "| セル | セル | セル |\n"
        )

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Return and not event.modifiers():
            self._handle_return(event)
            return
        if event.key() == Qt.Key.Key_Tab and not event.modifiers():
            self.textCursor().insertText("    ")
            return
        if event.key() == Qt.Key.Key_Backtab:
            self._dedent()
            return
        super().keyPressEvent(event)
        self._is_dirty = True

    def _handle_return(self, event: QKeyEvent) -> None:
        cursor = self.textCursor()
        line = cursor.block().text()

        m = _LIST_PREFIX_RE.match(line)
        if m:
            # Empty list item → break out of the list
            prefix_full = m.group(0)
            rest = line[len(prefix_full):]
            if not rest.strip():
                cursor.beginEditBlock()
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                    QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                cursor.endEditBlock()
                self._is_dirty = True
                return

            indent = m.group(1)
            bullet = m.group(2)
            # Auto-increment ordered lists
            om = _ORDERED_RE.match(line)
            if om:
                next_num = int(om.group(2)) + 1
                next_prefix = f"{indent}{next_num}. "
            else:
                next_prefix = f"{indent}{bullet} "
                # Carry over task list checkbox
                if _TASK_RE.match(line):
                    next_prefix += "[ ] "
            cursor.insertText(f"\n{next_prefix}")
            self._is_dirty = True
            return

        super().keyPressEvent(
            QKeyEvent(
                event.type(), Qt.Key.Key_Return, event.modifiers()
            )
        )
        self._is_dirty = True

    def _dedent(self) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        line = cursor.block().text()
        if line.startswith("    "):
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            for _ in range(4):
                cursor.deleteChar()
        elif line.startswith("\t"):
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.deleteChar()
        cursor.endEditBlock()

    # ------------------------------------------------------------------
    # Drag & drop images
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._has_image_urls(event.mimeData()) or self._has_md_urls(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self._has_image_urls(event.mimeData()) or self._has_md_urls(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if self._has_image_urls(event.mimeData()):
            for url in event.mimeData().urls():
                local = url.toLocalFile()
                if Path(local).suffix.lower() in _IMAGE_EXTS:
                    self.insert_image(local)
            event.acceptProposedAction()
        elif self._has_md_urls(event.mimeData()):
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in _MD_EXTS and p.is_file():
                    self.file_open_requested.emit(str(p))
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    @staticmethod
    def _has_image_urls(mime: QMimeData) -> bool:
        if not mime.hasUrls():
            return False
        return any(Path(u.toLocalFile()).suffix.lower() in _IMAGE_EXTS
                   for u in mime.urls())

    @staticmethod
    def _has_md_urls(mime: QMimeData) -> bool:
        if not mime.hasUrls():
            return False
        return any(Path(u.toLocalFile()).suffix.lower() in _MD_EXTS
                   for u in mime.urls())

    def _to_relative(self, abs_path: str) -> str:
        if not abs_path or not self._file_path:
            return abs_path
        try:
            base = os.path.dirname(self._file_path)
            rel = os.path.relpath(abs_path, base)
            return rel.replace("\\", "/")
        except ValueError:
            return abs_path.replace("\\", "/")
