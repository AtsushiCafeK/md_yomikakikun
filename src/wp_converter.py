"""Markdown → WordPress Gutenberg / HTML converter."""
from __future__ import annotations
import re

# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------

def _inline(text: str) -> str:
    """Apply inline Markdown → HTML conversion (safe order)."""
    # 1. Protect code spans from further processing
    placeholders: dict[str, str] = {}
    counter = 0

    def _save(m: re.Match) -> str:
        nonlocal counter
        key = f"\x00{counter}\x00"
        placeholders[key] = f"<code>{_esc(m.group(1))}</code>"
        counter += 1
        return key

    text = re.sub(r"`([^`]+)`", _save, text)

    # 2. Images before links
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}"/>',
        text,
    )
    # 3. Links
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        text,
    )
    # 4. Bold (** before *)
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", text)
    text = re.sub(r"__(.+?)__",     lambda m: f"<strong>{m.group(1)}</strong>", text)
    # 5. Italic
    text = re.sub(r"\*(.+?)\*",    lambda m: f"<em>{m.group(1)}</em>", text)
    text = re.sub(r"_(.+?)_",      lambda m: f"<em>{m.group(1)}</em>", text)
    # 6. Strikethrough
    text = re.sub(r"~~(.+?)~~",    lambda m: f"<s>{m.group(1)}</s>", text)

    # Restore code spans
    for key, val in placeholders.items():
        text = text.replace(key, val)
    return text


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Block renderers — Gutenberg
# ---------------------------------------------------------------------------

def _wp_heading(level: int, text: str) -> str:
    return (
        f'<!-- wp:heading {{"level":{level}}} -->\n'
        f'<h{level} class="wp-block-heading">{text}</h{level}>\n'
        f'<!-- /wp:heading -->'
    )

def _wp_paragraph(text: str) -> str:
    return f"<!-- wp:paragraph -->\n<p>{text}</p>\n<!-- /wp:paragraph -->"

def _wp_list(items: list[str], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    attr = ' {"ordered":true}' if ordered else ""
    inner = "\n".join(
        f"<!-- wp:list-item -->\n<li>{_inline(it)}</li>\n<!-- /wp:list-item -->"
        for it in items
    )
    return f"<!-- wp:list{attr} -->\n<{tag}>\n{inner}\n</{tag}>\n<!-- /wp:list -->"

def _wp_quote(lines: list[str]) -> str:
    content = " ".join(lines)
    return (
        f"<!-- wp:quote -->\n"
        f'<blockquote class="wp-block-quote">\n'
        f"<p>{_inline(content)}</p>\n"
        f"</blockquote>\n<!-- /wp:quote -->"
    )

def _wp_code(code: str, lang: str) -> str:
    # WordPress コアの wp:code ブロックは <code> に属性を許可しないため
    # class="language-xxx" を付けるとブロック検証エラーになる
    return (
        f"<!-- wp:code -->\n"
        f'<pre class="wp-block-code"><code>{_esc(code)}</code></pre>\n'
        f"<!-- /wp:code -->"
    )

def _wp_table(rows: list[list[str]]) -> str:
    header = rows[0]
    body   = rows[2:]  # rows[1] is separator
    thead = "<tr>" + "".join(f"<th>{_inline(h)}</th>" for h in header) + "</tr>"
    tbody = "".join(
        "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>"
        for row in body
    )
    return (
        '<!-- wp:table {"hasFixedLayout":true} -->\n'
        '<figure class="wp-block-table">'
        '<table class="has-fixed-layout">'
        f"<thead>{thead}</thead>"
        f"<tbody>{tbody}</tbody>"
        "</table></figure>\n"
        "<!-- /wp:table -->"
    )

def _wp_image(alt: str, src: str) -> str:
    return (
        "<!-- wp:image -->\n"
        f'<figure class="wp-block-image"><img src="{src}" alt="{alt}"/></figure>\n'
        "<!-- /wp:image -->"
    )

def _wp_separator() -> str:
    return (
        "<!-- wp:separator -->\n"
        '<hr class="wp-block-separator has-alpha-channel-opacity"/>\n'
        "<!-- /wp:separator -->"
    )


# ---------------------------------------------------------------------------
# Block renderers — plain HTML
# ---------------------------------------------------------------------------

def _html_heading(level: int, text: str) -> str:
    return f"<h{level}>{text}</h{level}>"

def _html_paragraph(text: str) -> str:
    return f"<p>{text}</p>"

def _html_list(items: list[str], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    inner = "\n".join(f"  <li>{_inline(it)}</li>" for it in items)
    return f"<{tag}>\n{inner}\n</{tag}>"

def _html_quote(lines: list[str]) -> str:
    return f"<blockquote><p>{_inline(' '.join(lines))}</p></blockquote>"

def _html_code(code: str, lang: str) -> str:
    cls = f' class="language-{lang}"' if lang else ""
    return f"<pre><code{cls}>{_esc(code)}</code></pre>"

def _html_table(rows: list[list[str]]) -> str:
    header = rows[0]
    body   = rows[2:]
    thead = "<tr>" + "".join(f"<th>{_inline(h)}</th>" for h in header) + "</tr>"
    tbody = "".join(
        "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>"
        for row in body
    )
    return f"<table>\n<thead>{thead}</thead>\n<tbody>{tbody}</tbody>\n</table>"

def _html_image(alt: str, src: str) -> str:
    return f'<img src="{src}" alt="{alt}"/>'

def _html_separator() -> str:
    return "<hr/>"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---[ \t]*\n.*?\n---[ \t]*\n", re.DOTALL)
_HEADING_RE     = re.compile(r"^(#{1,6})\s+(.*)")
_HR_RE          = re.compile(r"^(-{3,}|\*{3,}|_{3,})\s*$")
_UL_RE          = re.compile(r"^\s*[-*+]\s+(.*)")
_OL_RE          = re.compile(r"^\s*\d+\.\s+(.*)")
_TABLE_SEP_RE   = re.compile(r"^\|?[\s:\-|]+\|")
_BLOCKQUOTE_RE  = re.compile(r"^>\s?(.*)")
_IMAGE_LINE_RE  = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
_FENCE_RE       = re.compile(r"^```(\w*)")


def _parse_table_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_block_start(s: str) -> bool:
    return bool(
        _HEADING_RE.match(s)
        or _HR_RE.match(s)
        or _UL_RE.match(s)
        or _OL_RE.match(s)
        or _FENCE_RE.match(s)
        or _BLOCKQUOTE_RE.match(s)
        or ("|" in s)
    )


def _parse(text: str) -> list[tuple]:
    """Return a list of (type, ...) tuples representing Markdown blocks."""
    text = _FM_RE.sub("", text, count=1)
    lines = text.splitlines()
    blocks: list[tuple] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Fenced code block
        m = _FENCE_RE.match(stripped)
        if m:
            lang = m.group(1)
            i += 1
            code_lines: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            blocks.append(("code", lang, "\n".join(code_lines)))
            continue

        # Heading
        m = _HEADING_RE.match(stripped)
        if m:
            blocks.append(("heading", len(m.group(1)), _inline(m.group(2).strip())))
            i += 1
            continue

        # Horizontal rule (must come before ul check since --- could match)
        if _HR_RE.match(stripped):
            blocks.append(("hr",))
            i += 1
            continue

        # Table (current line has | and next line is separator)
        if "|" in stripped:
            next_s = lines[i + 1].strip() if i + 1 < n else ""
            if _TABLE_SEP_RE.match(next_s):
                table_lines: list[str] = []
                while i < n and "|" in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                rows = [_parse_table_row(l) for l in table_lines]
                blocks.append(("table", rows))
                continue

        # Blockquote
        if _BLOCKQUOTE_RE.match(stripped):
            q_lines: list[str] = []
            while i < n and _BLOCKQUOTE_RE.match(lines[i].strip()):
                q_lines.append(_BLOCKQUOTE_RE.match(lines[i].strip()).group(1))
                i += 1
            blocks.append(("quote", q_lines))
            continue

        # Unordered list
        if _UL_RE.match(stripped):
            items: list[str] = []
            while i < n:
                s = lines[i].strip()
                mm = _UL_RE.match(s)
                if mm:
                    items.append(mm.group(1))
                    i += 1
                elif not s:
                    break
                else:
                    break
            blocks.append(("ul", items))
            continue

        # Ordered list
        if _OL_RE.match(stripped):
            items = []
            while i < n:
                s = lines[i].strip()
                mm = _OL_RE.match(s)
                if mm:
                    items.append(mm.group(1))
                    i += 1
                elif not s:
                    break
                else:
                    break
            blocks.append(("ol", items))
            continue

        # Standalone image
        m = _IMAGE_LINE_RE.match(stripped)
        if m:
            blocks.append(("image", m.group(1), m.group(2)))
            i += 1
            continue

        # Paragraph — accumulate until blank line or new block start
        para_lines: list[str] = []
        while i < n:
            s = lines[i].strip()
            if not s:
                break
            if para_lines and _is_block_start(s):
                break
            para_lines.append(s)
            i += 1
        if para_lines:
            blocks.append(("para", " ".join(para_lines)))
        continue

    return blocks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_gutenberg(text: str) -> str:
    """Convert Markdown to WordPress Gutenberg block format."""
    out: list[str] = []
    for block in _parse(text):
        kind = block[0]
        if kind == "heading":
            out.append(_wp_heading(block[1], block[2]))
        elif kind == "para":
            out.append(_wp_paragraph(_inline(block[1])))
        elif kind == "ul":
            out.append(_wp_list(block[1], ordered=False))
        elif kind == "ol":
            out.append(_wp_list(block[1], ordered=True))
        elif kind == "quote":
            out.append(_wp_quote(block[1]))
        elif kind == "code":
            out.append(_wp_code(block[2], block[1]))
        elif kind == "table":
            out.append(_wp_table(block[1]))
        elif kind == "image":
            out.append(_wp_image(block[1], block[2]))
        elif kind == "hr":
            out.append(_wp_separator())
    return "\n\n".join(out)


def convert_html(text: str) -> str:
    """Convert Markdown to plain HTML."""
    out: list[str] = []
    for block in _parse(text):
        kind = block[0]
        if kind == "heading":
            out.append(_html_heading(block[1], block[2]))
        elif kind == "para":
            out.append(_html_paragraph(_inline(block[1])))
        elif kind == "ul":
            out.append(_html_list(block[1], ordered=False))
        elif kind == "ol":
            out.append(_html_list(block[1], ordered=True))
        elif kind == "quote":
            out.append(_html_quote(block[1]))
        elif kind == "code":
            out.append(_html_code(block[2], block[1]))
        elif kind == "table":
            out.append(_html_table(block[1]))
        elif kind == "image":
            out.append(_html_image(block[1], block[2]))
        elif kind == "hr":
            out.append(_html_separator())
    return "\n\n".join(out)
