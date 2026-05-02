"""WebEngine-based Markdown preview panel."""
from __future__ import annotations
from pathlib import Path
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent

_MD_EXTS = {".md", ".markdown", ".txt"}


class PreviewWidget(QWebEngineView):
    file_open_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self._base_dir: str = ""
        self._pending_html: str = ""
        self._restore_y: int = 0
        self.setAcceptDrops(True)
        self.loadFinished.connect(self._on_load_finished)

    def set_base_dir(self, directory: str) -> None:
        self._base_dir = directory

    def render(self, html: str) -> None:
        """HTMLをレンダリングする。スクロール位置を保持して更新する。"""
        self._pending_html = html
        # 現在のスクロール位置を JS で取得してからレンダリング
        self.page().runJavaScript("window.scrollY", self._do_render)

    def _do_render(self, scroll_y) -> None:
        self._restore_y = int(scroll_y or 0)
        if self._base_dir:
            base_url = QUrl.fromLocalFile(
                self._base_dir.rstrip("/\\") + "/"
            )
        else:
            base_url = QUrl()
        self.setHtml(self._pending_html, base_url)

    def _on_load_finished(self, ok: bool) -> None:
        """ページ読み込み完了後にスクロール位置を復元する。"""
        if self._restore_y > 0:
            self.page().runJavaScript(f"window.scrollTo(0, {self._restore_y})")

    def apply_scroll_ratio(self, ratio: float) -> None:
        """エディタのスクロール比率に合わせてプレビューをスクロールする。"""
        js = (
            f"(function(){{"
            f"  var r = {ratio};"
            f"  var max = document.documentElement.scrollHeight"
            f"          - document.documentElement.clientHeight;"
            f"  window.scrollTo(0, r * max);"
            f"}})();"
        )
        self.page().runJavaScript(js)

    def export_pdf(self, output_path: str) -> None:
        self.page().printToPdf(output_path)

    # ------------------------------------------------------------------
    # File drag & drop (intercept before Chromium where possible)
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._has_md_urls(event):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self._has_md_urls(event):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if self._has_md_urls(event):
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in _MD_EXTS and p.is_file():
                    self.file_open_requested.emit(str(p))
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    @staticmethod
    def _has_md_urls(event) -> bool:
        mime = event.mimeData()
        if not mime.hasUrls():
            return False
        return any(
            Path(u.toLocalFile()).suffix.lower() in _MD_EXTS
            and Path(u.toLocalFile()).is_file()
            for u in mime.urls()
        )
