"""Main application window."""
from __future__ import annotations
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QStatusBar,
    QLabel, QMenuBar, QFileDialog, QMessageBox,
    QInputDialog, QApplication, QDialog, QVBoxLayout,
    QFormLayout, QComboBox, QSpinBox, QLineEdit,
    QDialogButtonBox, QCheckBox, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QSize, QMimeData
from PyQt6.QtGui import QAction, QKeySequence, QPalette, QColor, QFont, QCloseEvent, QDragEnterEvent, QDropEvent

from .settings import Settings
from .tab_widget import TabWidget
from .preview import PreviewWidget
from .file_browser import FileBrowser
from .toolbar import MarkdownToolBar
from .search_dialog import SearchDialog
from .renderer import render_html, render_content
from . import exporter


_MD_EXTS = {".md", ".markdown", ".txt"}


def _has_md_urls(mime: QMimeData) -> bool:
    if not mime or not mime.hasUrls():
        return False
    return any(
        Path(u.toLocalFile()).suffix.lower() in _MD_EXTS
        and Path(u.toLocalFile()).is_file()
        for u in mime.urls()
    )


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings
        self._dark_mode = False
        self._preview_visible = True
        self._sidebar_visible = True
        self._sync_scroll = self._settings.get("sync_scroll", False)
        self._word_wrap = self._settings.get("word_wrap", True)
        self._toc_visible = self._settings.get("toc_visible", True)

        # Status bar must be created before _setup_ui so that _update_status()
        # can safely be called from signal handlers triggered during widget init.
        self.setAcceptDrops(True)
        self._lbl_path = self._lbl_cursor = self._lbl_words = self._lbl_mode = None
        self._setup_status_bar()
        self._setup_ui()
        self._setup_menus()
        self._restore_geometry()
        self._detect_os_theme()

    # ------------------------------------------------------------------
    # UI assembly
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        self.setWindowTitle("MD読み書き君")
        self.setMinimumSize(800, 600)

        # Toolbar
        self._toolbar = MarkdownToolBar(self._settings, self)
        self.addToolBar(self._toolbar)

        # Central splitter: sidebar | editor | preview
        self._outer_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self._outer_splitter)

        # File browser
        self._file_browser = FileBrowser(self._settings)
        self._file_browser.file_open_requested.connect(self._open_file)
        self._outer_splitter.addWidget(self._file_browser)

        # Tab widget (editor area)
        self._tabs = TabWidget(self._settings)
        # QueuedConnection defers the slot to the next event-loop iteration,
        # preventing Qt re-entrancy crash when setCurrentIndex fires during init.
        self._tabs.current_editor_changed.connect(
            self._on_editor_changed, Qt.ConnectionType.QueuedConnection
        )
        self._outer_splitter.addWidget(self._tabs)

        # Preview
        self._preview = PreviewWidget()
        self._preview.file_open_requested.connect(self._open_file)
        self._outer_splitter.addWidget(self._preview)

        # Splitter sizes
        sidebar_w = self._settings.get("window.splitter_sidebar", 220)
        editor_w  = self._settings.get("window.splitter_editor", 550)
        self._outer_splitter.setSizes([sidebar_w, editor_w, 600])
        self._outer_splitter.setCollapsible(0, True)
        self._outer_splitter.setCollapsible(2, True)

        # Auto-save timer
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._auto_save)

        # Preview update timer (debounce)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview_incremental)

        # Open one blank tab to start
        self._tabs.new_tab()
        self._toolbar.set_editor(self._tabs.current_editor())

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------
    def _setup_menus(self) -> None:
        mb = self.menuBar()
        sc = self._settings.get("shortcuts", {})

        # --- File ---
        file_menu = mb.addMenu("ファイル(&F)")
        self._add_action(file_menu, "新規(&N)", self._new_file, sc.get("new", "Ctrl+N"))
        self._add_action(file_menu, "開く(&O)…", self._open_file_dialog, sc.get("open", "Ctrl+O"))

        recent_menu = file_menu.addMenu("最近のファイル")
        self._recent_menu = recent_menu
        self._rebuild_recent_menu()

        file_menu.addSeparator()
        self._add_action(file_menu, "保存(&S)", self._save, sc.get("save", "Ctrl+S"))
        self._add_action(file_menu, "名前を付けて保存…", self._save_as, "Ctrl+Shift+S")
        self._add_action(file_menu, "すべて保存", self._save_all, None)
        file_menu.addSeparator()
        self._add_action(file_menu, "HTMLとして書き出し…", self._export_html,
                         sc.get("export_html", "Ctrl+Shift+H"))
        self._add_action(file_menu, "PDFとして書き出し…", self._export_pdf,
                         sc.get("export_pdf", "Ctrl+Shift+X"))
        file_menu.addSeparator()
        self._add_action(file_menu, "終了(&Q)", self.close, "Ctrl+Q")

        # --- Edit ---
        edit_menu = mb.addMenu("編集(&E)")
        self._add_action(edit_menu, "元に戻す", lambda: self._ed() and self._ed().undo(), "Ctrl+Z")
        self._add_action(edit_menu, "やり直し", lambda: self._ed() and self._ed().redo(), "Ctrl+Y")
        edit_menu.addSeparator()
        self._add_action(edit_menu, "切り取り", lambda: self._ed() and self._ed().cut(), "Ctrl+X")
        self._add_action(edit_menu, "コピー",   lambda: self._ed() and self._ed().copy(), "Ctrl+C")
        self._add_action(edit_menu, "貼り付け", lambda: self._ed() and self._ed().paste(), "Ctrl+V")
        edit_menu.addSeparator()
        self._add_action(edit_menu, "全選択",   lambda: self._ed() and self._ed().selectAll(), "Ctrl+A")
        edit_menu.addSeparator()
        self._add_action(edit_menu, "検索…(&F)", self._show_search, sc.get("find", "Ctrl+F"))

        # --- View ---
        view_menu = mb.addMenu("表示(&V)")
        self._add_action(view_menu, "プレビュー表示切替",
                         self._toggle_preview,
                         sc.get("toggle_preview", "Ctrl+Shift+P"))
        self._add_action(view_menu, "サイドバー表示切替",
                         self._toggle_sidebar,
                         sc.get("toggle_sidebar", "Ctrl+Shift+E"))
        # スクロール同期トグル（チェックマーク付き）
        self._sync_scroll_action = QAction("スクロール同期", self)
        self._sync_scroll_action.setCheckable(True)
        self._sync_scroll_action.setChecked(self._sync_scroll)
        self._sync_scroll_action.triggered.connect(self._toggle_sync_scroll)
        view_menu.addAction(self._sync_scroll_action)

        # ワードラップトグル（チェックマーク付き）
        self._word_wrap_action = QAction("ワードラップ", self)
        self._word_wrap_action.setCheckable(True)
        self._word_wrap_action.setChecked(self._word_wrap)
        self._word_wrap_action.triggered.connect(self._toggle_word_wrap)
        view_menu.addAction(self._word_wrap_action)

        # 目次トグル（チェックマーク付き）
        self._toc_action = QAction("目次", self)
        self._toc_action.setCheckable(True)
        self._toc_action.setChecked(self._toc_visible)
        self._toc_action.triggered.connect(self._toggle_toc)
        view_menu.addAction(self._toc_action)

        view_menu.addSeparator()
        self._add_action(view_menu, "ダークモード切替", self._toggle_dark, None)

        # --- Tools ---
        tools_menu = mb.addMenu("ツール(&T)")
        self._add_action(tools_menu, "設定…", self._show_preferences, "Ctrl+,")

        # --- Help ---
        help_menu = mb.addMenu("ヘルプ(&H)")
        self._add_action(help_menu, "キーボードショートカット", self._show_shortcuts, None)
        self._add_action(help_menu, "バージョン情報", self._show_about, None)

    def _add_action(self, menu, label: str, slot, shortcut: str | None) -> QAction:
        a = QAction(label, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(slot)
        menu.addAction(a)
        return a

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------
    def _setup_status_bar(self) -> None:
        sb = self.statusBar()
        self._lbl_path   = QLabel()
        self._lbl_cursor = QLabel()
        self._lbl_words  = QLabel()
        self._lbl_mode   = QLabel()
        for w in (self._lbl_path, self._lbl_cursor, self._lbl_words, self._lbl_mode):
            w.setFont(QFont("Segoe UI", 9))
        sb.addWidget(self._lbl_path, 1)
        sb.addPermanentWidget(self._lbl_words)
        sb.addPermanentWidget(self._lbl_cursor)
        sb.addPermanentWidget(self._lbl_mode)

    def _update_status(self) -> None:
        if self._lbl_cursor is None:
            return
        ed = self._ed()
        if ed is None:
            return
        cursor = ed.textCursor()
        line = cursor.blockNumber() + 1
        col  = cursor.positionInBlock() + 1
        self._lbl_cursor.setText(f"行 {line}, 列 {col}")
        text = ed.toPlainText()
        words = len(text.split())
        chars = len(text)
        self._lbl_words.setText(f"{words} 語  {chars} 文字")
        path = ed.file_path or "無題"
        self._lbl_path.setText(path)
        self._lbl_mode.setText("🌙" if self._dark_mode else "☀")

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------
    def _restore_geometry(self) -> None:
        w = self._settings.get("window.width", 1400)
        h = self._settings.get("window.height", 900)
        self.resize(w, h)
        if self._settings.get("window.maximized", False):
            self.showMaximized()

    def _save_geometry(self) -> None:
        if self.isMaximized():
            self._settings.set("window.maximized", True)
        else:
            self._settings.set("window.maximized", False)
            self._settings.set("window.width", self.width())
            self._settings.set("window.height", self.height())
        sizes = self._outer_splitter.sizes()
        if len(sizes) >= 3:
            self._settings.set("window.splitter_sidebar", sizes[0])
            self._settings.set("window.splitter_editor", sizes[1])
        self._settings.save()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def _detect_os_theme(self) -> None:
        theme = self._settings.get("theme", "system")
        if theme == "dark":
            self._apply_dark(True)
        elif theme == "light":
            self._apply_dark(False)
        else:
            app = QApplication.instance()
            try:
                hints = app.styleHints()
                dark = hints.colorScheme().name.lower() == "dark"
            except Exception:
                dark = False
            self._apply_dark(dark)

    def _apply_dark(self, dark: bool) -> None:
        self._dark_mode = dark
        app = QApplication.instance()
        if dark:
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#d4d4d4"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#252526"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#d4d4d4"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#3c3c3c"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#d4d4d4"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#264f78"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Link, QColor("#58a6ff"))
            app.setPalette(palette)
        else:
            app.setPalette(QPalette())
        self._tabs.set_dark(dark)
        self._preview.set_dark(dark)
        self._update_preview()
        self._update_status()

    def _toggle_dark(self) -> None:
        new_dark = not self._dark_mode
        self._settings.set("theme", "dark" if new_dark else "light")
        self._apply_dark(new_dark)

    # ------------------------------------------------------------------
    # Editor slot
    # ------------------------------------------------------------------
    def _ed(self):
        return self._tabs.current_editor()

    def _on_editor_changed(self, editor) -> None:
        self._toolbar.set_editor(editor)
        if editor is not None:
            editor.textChanged.connect(self._on_text_changed)
            editor.cursorPositionChanged.connect(self._update_status)
            editor.file_open_requested.connect(self._open_file)
            editor.scroll_ratio_changed.connect(self._on_editor_scroll)
            if editor.file_path:
                self._preview.set_base_dir(
                    os.path.dirname(editor.file_path)
                )
                self._file_browser.set_root(
                    os.path.dirname(editor.file_path)
                )
        self._update_preview()
        self._update_status()

    def _on_editor_scroll(self, ratio: float) -> None:
        if self._sync_scroll:
            self._preview.apply_scroll_ratio(ratio)

    def _toggle_sync_scroll(self) -> None:
        self._sync_scroll = self._sync_scroll_action.isChecked()
        self._settings.set("sync_scroll", self._sync_scroll)

    def _toggle_toc(self) -> None:
        self._toc_visible = self._toc_action.isChecked()
        self._settings.set("toc_visible", self._toc_visible)
        self._update_preview()

    def _toggle_word_wrap(self) -> None:
        self._word_wrap = self._word_wrap_action.isChecked()
        self._settings.set("word_wrap", self._word_wrap)
        self._apply_word_wrap()

    def _apply_word_wrap(self) -> None:
        from PyQt6.QtWidgets import QPlainTextEdit
        mode = (QPlainTextEdit.LineWrapMode.WidgetWidth if self._word_wrap
                else QPlainTextEdit.LineWrapMode.NoWrap)
        for i in range(self._tabs.count()):
            ed = self._tabs.editor_at(i)
            if ed:
                ed.setLineWrapMode(mode)

    def _on_text_changed(self) -> None:
        self._preview_timer.start(300)
        interval = self._settings.get("auto_save_interval", 2000)
        if self._settings.get("auto_save", True):
            self._save_timer.start(interval)

    def _update_preview(self) -> None:
        """ページ全体を再レンダリング（テーマ切替・ファイル切替・TOC切替時）。"""
        if not self._preview_visible:
            return
        ed = self._ed()
        text = ed.toPlainText() if ed else ""
        html = render_html(text, dark_mode=self._dark_mode, show_toc=self._toc_visible)
        self._preview.render(html)

    def _update_preview_incremental(self) -> None:
        """本文のみJS差し替え（テキスト入力時 — ちらつきなし）。"""
        if not self._preview_visible:
            return
        ed = self._ed()
        text = ed.toPlainText() if ed else ""
        content = render_content(text, dark_mode=self._dark_mode, show_toc=self._toc_visible)
        self._preview.update_content(content)

    def _auto_save(self) -> None:
        ed = self._ed()
        if ed and ed.is_dirty and ed.file_path:
            self._tabs.save_current()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def _new_file(self) -> None:
        self._tabs.new_tab()
        self._apply_word_wrap()

    def _open_file_dialog(self) -> None:
        last = self._settings.get("last_directory", str(Path.home()))
        paths, _ = QFileDialog.getOpenFileNames(
            self, "ファイルを開く", last,
            "Markdown (*.md *.markdown);;Text (*.txt);;All (*)"
        )
        for p in paths:
            self._open_file(p)

    def _open_file(self, path: str) -> None:
        existing = self._tabs.find_tab_for_path(path)
        if existing >= 0:
            self._tabs.setCurrentIndex(existing)
            return
        ed = self._tabs.new_tab(path)
        self._apply_word_wrap()
        self._settings.set("last_directory", os.path.dirname(path))
        self._settings.add_recent(path)
        self._rebuild_recent_menu()
        self._preview.set_base_dir(os.path.dirname(path))
        self._update_preview()

    def _open_file_at_line(self, path: str, lineno: int) -> None:
        self._open_file(path)
        ed = self._ed()
        if ed:
            doc = ed.document()
            block = doc.findBlockByNumber(lineno - 1)
            if block.isValid():
                cursor = ed.textCursor()
                cursor.setPosition(block.position())
                ed.setTextCursor(cursor)
                ed.ensureCursorVisible()

    def _save(self) -> None:
        self._tabs.save_current()

    def _save_as(self) -> None:
        ed = self._ed()
        if ed is None:
            return
        ed.file_path = None
        self._tabs.save_current()

    def _save_all(self) -> None:
        self._tabs.save_all()

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        files = [p for p in self._settings.get("recent_files", []) if os.path.exists(p)]
        for path in files:
            a = self._recent_menu.addAction(Path(path).name)
            a.setToolTip(path)
            a.triggered.connect(lambda checked, p=path: self._open_file(p))
        if not files:
            self._recent_menu.addAction("（なし）").setEnabled(False)
        self._recent_menu.addSeparator()
        clear_a = self._recent_menu.addAction("履歴を消去")
        clear_a.triggered.connect(self._clear_recent_files)

    def _clear_recent_files(self) -> None:
        self._settings.set("recent_files", [])
        self._rebuild_recent_menu()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def _export_html(self) -> None:
        ed = self._ed()
        if ed is None:
            return
        exporter.export_html(ed.toPlainText(), ed.file_path,
                              self._dark_mode, self)

    def _export_pdf(self) -> None:
        ed = self._ed()
        if ed is None:
            return
        exporter.export_pdf(self._preview, ed.file_path, self)

    # ------------------------------------------------------------------
    # View toggles
    # ------------------------------------------------------------------
    def _toggle_preview(self) -> None:
        self._preview_visible = not self._preview_visible
        self._preview.setVisible(self._preview_visible)
        if self._preview_visible:
            self._update_preview()

    def _toggle_sidebar(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        self._file_browser.setVisible(self._sidebar_visible)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def _show_search(self) -> None:
        dlg = SearchDialog(self._file_browser.get_root(), self)
        dlg.open_file_at_line.connect(self._open_file_at_line)
        dlg.exec()

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def _show_preferences(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("設定")
        dlg.resize(400, 300)
        layout = QVBoxLayout(dlg)
        form = QFormLayout()

        # Theme
        theme_box = QComboBox()
        theme_box.addItems(["system", "light", "dark"])
        theme_box.setCurrentText(self._settings.get("theme", "system"))
        form.addRow("テーマ:", theme_box)

        # Font family
        font_edit = QLineEdit(self._settings.get("font_family", "Consolas"))
        form.addRow("エディタフォント:", font_edit)

        # Font size
        font_size = QSpinBox()
        font_size.setRange(8, 32)
        font_size.setValue(self._settings.get("font_size", 14))
        form.addRow("フォントサイズ:", font_size)

        # Auto-save
        auto_save = QCheckBox()
        auto_save.setChecked(self._settings.get("auto_save", True))
        form.addRow("自動保存:", auto_save)

        layout.addLayout(form)
        layout.addSpacing(8)

        # --- Danger zone ---
        from PyQt6.QtWidgets import QFrame, QHBoxLayout
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        danger_row = QHBoxLayout()
        btn_clear_recent = QPushButton("最近のファイル履歴を消去")
        btn_clear_recent.setToolTip("ファイルは削除されません")
        btn_reset = QPushButton("設定を初期化")
        btn_reset.setToolTip("すべての設定をデフォルトに戻します")
        danger_row.addWidget(btn_clear_recent)
        danger_row.addWidget(btn_reset)
        layout.addLayout(danger_row)
        layout.addSpacing(4)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        # Danger zone handlers (execute immediately, don't need OK)
        def _do_clear_recent() -> None:
            self._settings.set("recent_files", [])
            self._rebuild_recent_menu()
            btn_clear_recent.setText("消去しました ✓")
            btn_clear_recent.setEnabled(False)

        def _do_reset() -> None:
            resp = QMessageBox.question(
                dlg, "確認",
                "すべての設定をデフォルトに戻しますか？\n（最近のファイル履歴も消去されます）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                return
            from .settings import DEFAULTS, _deep_merge
            self._settings._data = _deep_merge({}, DEFAULTS)
            self._settings.save()
            self._rebuild_recent_menu()
            # Reflect new values in the dialog widgets
            theme_box.setCurrentText(self._settings.get("theme", "system"))
            font_edit.setText(self._settings.get("font_family", "Consolas"))
            font_size.setValue(self._settings.get("font_size", 14))
            auto_save.setChecked(self._settings.get("auto_save", True))
            btn_reset.setText("初期化しました ✓")
            btn_reset.setEnabled(False)

        btn_clear_recent.clicked.connect(_do_clear_recent)
        btn_reset.clicked.connect(_do_reset)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._settings.set("theme", theme_box.currentText())
            self._settings.set("font_family", font_edit.text())
            self._settings.set("font_size", font_size.value())
            self._settings.set("auto_save", auto_save.isChecked())
            self._settings.save()
            # Apply
            self._detect_os_theme()
            for i in range(self._tabs.count()):
                ed = self._tabs.editor_at(i)
                if ed:
                    ed.refresh_font()

    # ------------------------------------------------------------------
    # Shortcuts info
    # ------------------------------------------------------------------
    def _show_shortcuts(self) -> None:
        sc = self._settings.get("shortcuts", {})
        lines = [f"  {k}: {v}" for k, v in sc.items()]
        QMessageBox.information(self, "キーボードショートカット",
                                "\n".join(lines))

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "MD読み書き君",
            "MD読み書き君 v1.0\n\nPython 3.12 / PyQt6 製 Markdown エディタ"
        )

    # ------------------------------------------------------------------
    # Window-level file drag & drop (fallback for areas not covered by filter)
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _has_md_urls(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if _has_md_urls(event.mimeData()):
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in _MD_EXTS and p.is_file():
                    self._open_file(str(p))
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._tabs.ask_save_all_before_close():
            event.ignore()
            return
        self._save_geometry()
        event.accept()
