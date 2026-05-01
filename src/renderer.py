"""Markdown → HTML renderer with GitHub-style CSS, MathJax, Mermaid."""
from __future__ import annotations
import re
import yaml
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.toc import TocExtension
from pygments.formatters import HtmlFormatter

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
_LIGHT_CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;font-size:16px;line-height:1.6;color:#24292f;background:#fff;max-width:900px;margin:0 auto;padding:32px 40px;word-wrap:break-word;}
h1,h2,h3,h4,h5,h6{margin-top:24px;margin-bottom:16px;font-weight:600;line-height:1.25;}
h1{font-size:2em;border-bottom:1px solid #d0d7de;padding-bottom:.3em;}
h2{font-size:1.5em;border-bottom:1px solid #d0d7de;padding-bottom:.3em;}
h3{font-size:1.25em;}h4{font-size:1em;}h5{font-size:.875em;}h6{font-size:.85em;color:#57606a;}
p{margin-top:0;margin-bottom:16px;}
a{color:#0969da;text-decoration:none;}a:hover{text-decoration:underline;}
code{font-family:'Cascadia Code',Consolas,'Courier New',monospace;background:#f6f8fa;padding:.2em .4em;border-radius:3px;font-size:85%;}
pre{background:#f6f8fa;border-radius:6px;padding:16px;overflow:auto;line-height:1.45;margin-bottom:16px;}
pre code{background:none;padding:0;font-size:100%;border-radius:0;}
blockquote{margin:0 0 16px;padding:0 1em;color:#57606a;border-left:.25em solid #d0d7de;}
table{border-collapse:collapse;width:100%;margin:0 0 16px;}
th,td{border:1px solid #d0d7de;padding:6px 13px;text-align:left;}
th{background:#f6f8fa;font-weight:600;}tr:nth-child(2n){background:#f6f8fa;}
img{max-width:100%;height:auto;border-radius:4px;}
hr{border:none;border-top:1px solid #d0d7de;margin:24px 0;}
ul,ol{margin-top:0;margin-bottom:16px;padding-left:2em;}
li+li{margin-top:.25em;}
.task-list-item{list-style:none;}.task-list-item input{margin:-3px .5em 0 -1.6em;}
.toc{background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;padding:12px 24px;margin:0 0 24px;display:inline-block;min-width:200px;}
.toc ul{margin:4px 0;}
.footnote{font-size:85%;color:#57606a;border-top:1px solid #d0d7de;margin-top:24px;padding-top:8px;}
.admonition{border:1px solid #d0d7de;border-radius:6px;padding:12px 16px;margin:16px 0;}
.admonition-title{font-weight:600;margin:0 0 8px;}
.frontmatter{font-size:.85em;background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;margin-bottom:24px;}
.frontmatter td,.frontmatter th{padding:4px 10px;}
"""

_DARK_CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;font-size:16px;line-height:1.6;color:#e6edf3;background:#0d1117;max-width:900px;margin:0 auto;padding:32px 40px;word-wrap:break-word;}
h1,h2,h3,h4,h5,h6{margin-top:24px;margin-bottom:16px;font-weight:600;line-height:1.25;}
h1{font-size:2em;border-bottom:1px solid #30363d;padding-bottom:.3em;}
h2{font-size:1.5em;border-bottom:1px solid #30363d;padding-bottom:.3em;}
h3{font-size:1.25em;}h4{font-size:1em;}h5{font-size:.875em;}h6{font-size:.85em;color:#8b949e;}
p{margin-top:0;margin-bottom:16px;}
a{color:#58a6ff;text-decoration:none;}a:hover{text-decoration:underline;}
code{font-family:'Cascadia Code',Consolas,'Courier New',monospace;background:#161b22;padding:.2em .4em;border-radius:3px;font-size:85%;}
pre{background:#161b22;border-radius:6px;padding:16px;overflow:auto;line-height:1.45;margin-bottom:16px;}
pre code{background:none;padding:0;font-size:100%;border-radius:0;}
blockquote{margin:0 0 16px;padding:0 1em;color:#8b949e;border-left:.25em solid #30363d;}
table{border-collapse:collapse;width:100%;margin:0 0 16px;}
th,td{border:1px solid #30363d;padding:6px 13px;text-align:left;}
th{background:#161b22;font-weight:600;}tr:nth-child(2n){background:#161b22;}
img{max-width:100%;height:auto;border-radius:4px;}
hr{border:none;border-top:1px solid #30363d;margin:24px 0;}
ul,ol{margin-top:0;margin-bottom:16px;padding-left:2em;}
li+li{margin-top:.25em;}
.task-list-item{list-style:none;}.task-list-item input{margin:-3px .5em 0 -1.6em;}
.toc{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px 24px;margin:0 0 24px;display:inline-block;min-width:200px;}
.toc ul{margin:4px 0;}
.footnote{font-size:85%;color:#8b949e;border-top:1px solid #30363d;margin-top:24px;padding-top:8px;}
.admonition{border:1px solid #30363d;border-radius:6px;padding:12px 16px;margin:16px 0;}
.admonition-title{font-weight:600;margin:0 0 8px;}
.frontmatter{font-size:.85em;background:#161b22;border:1px solid #30363d;border-radius:6px;margin-bottom:24px;}
.frontmatter td,.frontmatter th{padding:4px 10px;}
"""

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{theme_css}</style>
<style>{pygments_css}</style>
<!-- MathJax -->
<script>
MathJax = {{
  tex: {{ inlineMath: [['$','$'],['\\\\(','\\\\)']], displayMath: [['$$','$$'],['\\\\[','\\\\]']] }},
  svg: {{ fontCache: 'global' }}
}};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js" async></script>
<!-- Mermaid -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>document.addEventListener('DOMContentLoaded',()=>mermaid.initialize({{startOnLoad:true,theme:'{mermaid_theme}'}}));</script>
</head>
<body>
{frontmatter_html}
{toc_html}
{body_html}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Front-matter extraction
# ---------------------------------------------------------------------------
_FM_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)


def extract_frontmatter(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if m:
        try:
            meta = yaml.safe_load(m.group(1)) or {}
            return meta, text[m.end():]
        except yaml.YAMLError:
            pass
    return {}, text


# ---------------------------------------------------------------------------
# Mermaid custom fence handler
# ---------------------------------------------------------------------------
def _mermaid_fence(source, language, class_name, options, md, **kwargs):  # noqa: ARG001
    return f'<div class="mermaid">{source}</div>'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def render_html(text: str, dark_mode: bool = False) -> str:
    meta, content = extract_frontmatter(text)

    pygments_style = "monokai" if dark_mode else "friendly"
    pygments_css = HtmlFormatter(style=pygments_style).get_style_defs(".highlight")

    extensions = [
        "tables",
        "fenced_code",
        CodeHiliteExtension(css_class="highlight", guess_lang=False),
        TocExtension(permalink=True, toc_depth="1-3"),
        "nl2br",
        "attr_list",
        "footnotes",
        "abbr",
        "def_list",
        "admonition",
        "sane_lists",
    ]

    # pymdownx extensions (optional – fall back gracefully)
    try:
        import pymdownx.superfences  # noqa: F401
        extensions += [
            "pymdownx.tasklist",
            "pymdownx.tilde",
        ]
        # superfences with Mermaid support
        from markdown import Extension as MdExt
        extensions.append(
            __import__(
                "pymdownx.superfences",
                fromlist=["SuperFencesCodeExtension"],
            ).SuperFencesCodeExtension(
                custom_fences=[
                    {"name": "mermaid", "class": "mermaid", "format": _mermaid_fence}
                ]
            )
        )
        extensions.remove("fenced_code")
    except Exception:
        pass

    md_proc = markdown.Markdown(extensions=extensions)
    body = md_proc.convert(content)
    toc: str = getattr(md_proc, "toc", "")

    # Front matter table
    fm_html = ""
    if meta:
        rows = "".join(
            f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in meta.items()
        )
        fm_html = f'<table class="frontmatter">{rows}</table>'

    toc_html = ""
    if toc and toc.strip() not in ("", "<div class=\"toc\"></div>"):
        toc_html = f'<nav class="toc"><strong>目次</strong>{toc}</nav>'

    theme_css = _DARK_CSS if dark_mode else _LIGHT_CSS
    mermaid_theme = "dark" if dark_mode else "default"

    return _HTML_TEMPLATE.format(
        theme_css=theme_css,
        pygments_css=pygments_css,
        frontmatter_html=fm_html,
        toc_html=toc_html,
        body_html=body,
        mermaid_theme=mermaid_theme,
    )
