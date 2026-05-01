"""Formatting toolbar that operates on the currently active MarkdownEditor."""
from __future__ import annotations
from PyQt6.QtWidgets import QToolBar, QWidget, QComboBox, QLabel, QSizePolicy
from PyQt6.QtGui import QAction, QIcon, QFont
from PyQt6.QtCore import Qt


def _act(toolbar: QToolBar, label: str, tooltip: str,
         shortcut: str | None = None) -> QAction:
    a = QAction(label, toolbar)
    a.setToolTip(tooltip)
    if shortcut:
        a.setShortcut(shortcut)
    toolbar.addAction(a)
    return a


class MarkdownToolBar(QToolBar):
    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__("書式", parent)
        self._settings = settings
        self._editor = None
        self.setMovable(False)
        self.setFloatable(False)
        self._build()

    def set_editor(self, editor) -> None:
        self._editor = editor

    def _ed(self):
        return self._editor

    def _build(self) -> None:
        sc = self._settings.get("shortcuts", {})

        # Heading selector
        self.addWidget(QLabel(" "))
        self._heading_combo = QComboBox()
        self._heading_combo.addItems(["本文", "H1", "H2", "H3", "H4", "H5", "H6"])
        self._heading_combo.setFixedWidth(70)
        self._heading_combo.setToolTip("見出しレベル")
        self._heading_combo.activated.connect(self._on_heading)
        self.addWidget(self._heading_combo)
        self.addSeparator()

        # Bold / Italic / Strike
        a_bold = _act(self, "B", "太字 (Ctrl+B)", sc.get("bold", "Ctrl+B"))
        a_bold.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        a_bold.triggered.connect(lambda: self._ed() and self._ed().wrap_selection("**"))

        a_italic = _act(self, "I", "斜体 (Ctrl+I)", sc.get("italic", "Ctrl+I"))
        f = QFont("Segoe UI", 10)
        f.setItalic(True)
        a_italic.setFont(f)
        a_italic.triggered.connect(lambda: self._ed() and self._ed().wrap_selection("*"))

        a_strike = _act(self, "S̶", "打ち消し線", None)
        a_strike.triggered.connect(lambda: self._ed() and self._ed().wrap_selection("~~"))

        self.addSeparator()

        # Code
        _act(self, "`", "インラインコード", None).triggered.connect(
            lambda: self._ed() and self._ed().wrap_selection("`"))
        _act(self, "```", "コードブロック", None).triggered.connect(
            lambda: self._ed() and self._ed().insert_code_block())

        self.addSeparator()

        # Link / Image
        a_link = _act(self, "🔗 リンク", "リンク挿入", sc.get("insert_link", "Ctrl+K"))
        a_link.triggered.connect(lambda: self._ed() and self._ed().insert_link())

        a_img = _act(self, "🖼 画像", "画像挿入 (ファイル選択)", sc.get("insert_image", "Ctrl+Shift+I"))
        a_img.triggered.connect(self._insert_image_dialog)

        self.addSeparator()

        # Lists
        _act(self, "• リスト", "箇条書きリスト", None).triggered.connect(
            lambda: self._ed() and self._ed().textCursor().insertText("- "))
        _act(self, "1. リスト", "番号付きリスト", None).triggered.connect(
            lambda: self._ed() and self._ed().textCursor().insertText("1. "))
        _act(self, "☑ タスク", "タスクリスト", None).triggered.connect(
            lambda: self._ed() and self._ed().textCursor().insertText("- [ ] "))

        self.addSeparator()

        # Blockquote / HR / Table
        _act(self, "> 引用", "引用", None).triggered.connect(
            lambda: self._ed() and self._ed().textCursor().insertText("> "))
        _act(self, "― HR", "水平線", None).triggered.connect(
            lambda: self._ed() and self._ed().textCursor().insertText("\n---\n"))
        _act(self, "⊞ 表", "テーブル挿入", None).triggered.connect(
            lambda: self._ed() and self._ed().insert_table())

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

    def _on_heading(self, index: int) -> None:
        if self._ed() is None:
            return
        if index == 0:
            return
        self._ed().insert_heading(index)
        self._heading_combo.setCurrentIndex(0)

    def _insert_image_dialog(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        if self._ed() is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "画像を選択", "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp *.svg *.bmp);;All (*)"
        )
        if path:
            self._ed().insert_image(path)
