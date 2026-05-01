"""QSyntaxHighlighter for Markdown source with multi-line block support."""
from __future__ import annotations
import re
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextDocument
)

# Block states
_STATE_NORMAL    = 0
_STATE_CODEBLOCK = 1
_STATE_FRONTMATTER = 2


def _fmt(color: str | None = None, bold=False, italic=False,
         underline=False, strike=False, bg: str | None = None) -> QTextCharFormat:
    f = QTextCharFormat()
    if color:
        f.setForeground(QColor(color))
    if bg:
        f.setBackground(QColor(bg))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    if underline:
        f.setFontUnderline(True)
    if strike:
        f.setFontStrikeOut(True)
    return f


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument, dark: bool = False) -> None:
        super().__init__(document)
        self._dark = dark
        self._build_formats()

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        self._build_formats()
        self.rehighlight()

    def _build_formats(self) -> None:
        d = self._dark
        # colours differ by theme
        self.fmt_h1      = _fmt("#569cd6" if d else "#0550ae", bold=True)
        self.fmt_h2      = _fmt("#569cd6" if d else "#0550ae", bold=True)
        self.fmt_h3      = _fmt("#4ec9b0" if d else "#116329", bold=True)
        self.fmt_h456    = _fmt("#9cdcfe" if d else "#0969da", bold=True)
        self.fmt_bold    = _fmt(bold=True)
        self.fmt_italic  = _fmt(italic=True)
        self.fmt_boldital= _fmt(bold=True, italic=True)
        self.fmt_strike  = _fmt(strike=True, color="#6e7681" if d else "#57606a")
        self.fmt_code    = _fmt(color="#ce9178" if d else "#953800",
                                bg="#1e1e1e" if d else "#f6f8fa")
        self.fmt_codeblk = _fmt(color="#b5cea8" if d else "#116329",
                                bg="#1a1a1a" if d else "#f0f4f8")
        self.fmt_link    = _fmt(color="#4ec9b0" if d else "#0969da", underline=True)
        self.fmt_linkurl = _fmt(color="#6a9955" if d else "#6e7781")
        self.fmt_image   = _fmt(color="#c586c0" if d else "#8250df")
        self.fmt_list    = _fmt(color="#ce9178" if d else "#cf222e", bold=True)
        self.fmt_quote   = _fmt(color="#6a9955" if d else "#57606a", italic=True)
        self.fmt_hr      = _fmt(color="#6e7681")
        self.fmt_fm      = _fmt(color="#9cdcfe" if d else "#0550ae",
                                bg="#1e1e2e" if d else "#f0f5ff")
        self.fmt_fmdelim = _fmt(color="#c586c0" if d else "#8250df", bold=True)
        self.fmt_codefence = _fmt(color="#569cd6" if d else "#0550ae", bold=True)

        # Inline rules as (compiled_regex, format or list-of-formats)
        self._inline_rules: list[tuple[re.Pattern, list[tuple[int, int, QTextCharFormat]]]] = []

        def add(pattern: str, groups: list[tuple[int, QTextCharFormat]]) -> None:
            self._inline_rules.append((re.compile(pattern), groups))

        # Bold+Italic
        add(r"(\*\*\*|___)(.*?)\1",        [(0, self.fmt_boldital)])
        # Bold
        add(r"(\*\*|__)(.*?)\1",           [(0, self.fmt_bold)])
        # Italic
        add(r"(?<!\*)(\*|_)(?!\s)(.*?)(?<!\s)\1(?!\*)", [(0, self.fmt_italic)])
        # Strikethrough
        add(r"(~~)(.*?)\1",                [(0, self.fmt_strike)])
        # Inline code
        add(r"(`+)(.+?)\1",                [(0, self.fmt_code)])
        # Image  ![alt](url)
        add(r"(!\[.*?\])(\(.*?\))",        [(0, self.fmt_image), (1, self.fmt_linkurl)])
        # Link [text](url)
        add(r"(\[.*?\])(\(.*?\))",         [(0, self.fmt_link), (1, self.fmt_linkurl)])
        # Autolink <url>
        add(r"<(https?://[^>]+)>",         [(0, self.fmt_link)])

    # ------------------------------------------------------------------
    def highlightBlock(self, text: str) -> None:
        prev = self.previousBlockState()
        block_num = self.currentBlock().blockNumber()

        # --- Front matter ---
        if block_num == 0 and text.strip() == "---":
            self.setFormat(0, len(text), self.fmt_fmdelim)
            self.setCurrentBlockState(_STATE_FRONTMATTER)
            return
        if prev == _STATE_FRONTMATTER:
            if text.strip() == "---":
                self.setFormat(0, len(text), self.fmt_fmdelim)
                self.setCurrentBlockState(_STATE_NORMAL)
            else:
                self.setFormat(0, len(text), self.fmt_fm)
                self.setCurrentBlockState(_STATE_FRONTMATTER)
            return

        # --- Code fence ---
        if prev == _STATE_CODEBLOCK:
            if re.match(r"^```", text):
                self.setFormat(0, len(text), self.fmt_codefence)
                self.setCurrentBlockState(_STATE_NORMAL)
            else:
                self.setFormat(0, len(text), self.fmt_codeblk)
                self.setCurrentBlockState(_STATE_CODEBLOCK)
            return

        if re.match(r"^```", text):
            self.setFormat(0, len(text), self.fmt_codefence)
            self.setCurrentBlockState(_STATE_CODEBLOCK)
            return

        self.setCurrentBlockState(_STATE_NORMAL)

        # --- Headings ---
        m = re.match(r"^(#{1,6})\s", text)
        if m:
            level = len(m.group(1))
            fmt = (self.fmt_h1 if level == 1 else
                   self.fmt_h2 if level == 2 else
                   self.fmt_h3 if level == 3 else
                   self.fmt_h456)
            self.setFormat(0, len(text), fmt)
            return

        # --- Horizontal rule ---
        if re.match(r"^(\*{3,}|-{3,}|_{3,})\s*$", text):
            self.setFormat(0, len(text), self.fmt_hr)
            return

        # --- Blockquote ---
        if text.startswith(">"):
            self.setFormat(0, len(text), self.fmt_quote)
            return

        # --- List ---
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s", text)
        if m:
            bullet_end = m.end(2) + 1
            self.setFormat(m.start(2), bullet_end - m.start(2), self.fmt_list)

        # --- Inline rules ---
        for pattern, group_fmts in self._inline_rules:
            for match in pattern.finditer(text):
                if len(group_fmts) == 1 and group_fmts[0][0] == 0:
                    self.setFormat(match.start(), match.end() - match.start(),
                                   group_fmts[0][1])
                else:
                    for grp_idx, fmt in group_fmts:
                        if grp_idx < len(match.groups()):
                            g = grp_idx + 1
                            if match.start(g) >= 0:
                                self.setFormat(match.start(g),
                                               match.end(g) - match.start(g),
                                               fmt)
