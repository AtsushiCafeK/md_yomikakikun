"""HTML / PDF export."""
from __future__ import annotations
import os
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget
from .renderer import render_html


def export_html(text: str, parent_path: str | None, dark: bool,
                parent_widget: QWidget | None = None) -> None:
    default_dir = str(Path(parent_path).parent) if parent_path else str(Path.home())
    default_name = (Path(parent_path).stem + ".html") if parent_path else "export.html"
    out_path, _ = QFileDialog.getSaveFileName(
        parent_widget, "HTMLとして保存",
        os.path.join(default_dir, default_name),
        "HTML (*.html *.htm)"
    )
    if not out_path:
        return
    try:
        html = render_html(text, dark_mode=dark)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        QMessageBox.information(parent_widget, "完了",
                                f"HTMLを保存しました:\n{out_path}")
    except OSError as e:
        QMessageBox.warning(parent_widget, "エラー", str(e))


def export_pdf(preview_widget, parent_path: str | None,
               parent_widget: QWidget | None = None) -> None:
    """Use QWebEnginePage.printToPdf (async)."""
    default_dir = str(Path(parent_path).parent) if parent_path else str(Path.home())
    default_name = (Path(parent_path).stem + ".pdf") if parent_path else "export.pdf"
    out_path, _ = QFileDialog.getSaveFileName(
        parent_widget, "PDFとして保存",
        os.path.join(default_dir, default_name),
        "PDF (*.pdf)"
    )
    if not out_path:
        return

    def _on_done(success: bool) -> None:
        if success:
            QMessageBox.information(parent_widget, "完了",
                                    f"PDFを保存しました:\n{out_path}")
        else:
            QMessageBox.warning(parent_widget, "エラー", "PDF出力に失敗しました")

    preview_widget.page().printToPdf(out_path)
    # printToPdf is fire-and-forget; connect pdfPrintingFinished for feedback
    try:
        preview_widget.page().pdfPrintingFinished.connect(_on_done)
    except Exception:
        pass
