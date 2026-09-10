"""Assemble docs/thesis/*.md into one Markdown file, a .docx and a self-contained .html.

    uv run --with pypandoc_binary python scripts/build_thesis.py

Free. Reads nothing but the chapter files, the bibliography and data/figures/.
Run scripts/make_figures.py first so the figures match the database.

Why pandoc via pypandoc_binary: it is the one tool that turns the same source
into Word (for submission), HTML (for reading and sharing) and Markdown (for
version control) with tables, LaTeX maths and a real bibliography, and the
binary wheel means nothing has to be installed system-wide.
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "thesis"
OUT = SRC / "build"

CHAPTERS = [
    "00-front.md", "01-introduction.md", "02-background.md", "03-method.md",
    "04-validity.md", "05-results.md", "06-frontier.md", "07-abort.md",
    "08-limitations.md", "09-conclusion.md", "10-appendices.md",
]


def assemble() -> Path:
    OUT.mkdir(exist_ok=True)
    parts = [(SRC / name).read_text() for name in CHAPTERS]
    combined = OUT / "CARR-thesis.md"
    combined.write_text("\n\n".join(parts))
    return combined


def to_docx(md: Path) -> Path:
    import pypandoc

    out = OUT / "CARR-thesis.docx"
    pypandoc.convert_file(
        str(md), "docx", outputfile=str(out),
        extra_args=["--citeproc", f"--bibliography={SRC / 'references.bib'}",
                    "--number-sections", "--toc", "--toc-depth=2",
                    f"--resource-path={SRC}", "--from=markdown+tex_math_dollars"],
    )
    return out


def to_html(md: Path) -> Path:
    """A body fragment with figures inlined as data URIs, for the artifact."""
    import pypandoc

    html = pypandoc.convert_file(
        str(md), "html", extra_args=[
            "--citeproc", f"--bibliography={SRC / 'references.bib'}",
            "--number-sections", "--toc", "--toc-depth=2", "--mathml",
            f"--resource-path={SRC}", "--from=markdown+tex_math_dollars"],
    )

    def inline(match: re.Match) -> str:
        rel = match.group(1)
        path = (SRC / rel).resolve()
        if not path.exists():
            return match.group(0)
        data = base64.b64encode(path.read_bytes()).decode()
        return f'src="data:image/png;base64,{data}"'

    html = re.sub(r'src="([^"]+\.png)"', inline, html)
    out = OUT / "CARR-thesis.html"
    out.write_text(html)
    return out


def main() -> None:
    md = assemble()
    words = len(md.read_text().split())
    print(f"  {md.relative_to(ROOT)}   ({words:,} words)")
    try:
        docx = to_docx(md)
        print(f"  {docx.relative_to(ROOT)}   ({docx.stat().st_size // 1024} KB)")
        html = to_html(md)
        print(f"  {html.relative_to(ROOT)}   ({html.stat().st_size // 1024} KB)")
    except ImportError:
        sys.exit("  pypandoc not available: run with  uv run --with pypandoc_binary ...")


if __name__ == "__main__":
    main()
