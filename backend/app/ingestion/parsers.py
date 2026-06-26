"""Document parsers for supported file formats.

Supported: PDF, Markdown, Plain Text, DOCX.
Each parser returns a list of (text, metadata) segments preserving section headings.
"""

from __future__ import annotations

import re
from pathlib import Path


def parse_document(file_path: str | Path) -> list[tuple[str, dict]]:
    """Parse a document and return (text, metadata) segments.

    Metadata includes source, section_heading, and page_number (if available).
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(path)
    elif ext == ".md":
        return _parse_markdown(path)
    elif ext == ".txt":
        return _parse_text(path)
    elif ext == ".docx":
        return _parse_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _parse_pdf(path: Path) -> list[tuple[str, dict]]:
    """Parse a PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    segments: list[tuple[str, dict]] = []
    doc = fitz.open(str(path))
    current_heading = ""

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") != 0:  # skip images
                continue
            text = "".join(
                span["text"]
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            ).strip()
            if not text:
                continue

            # Detect headings by font size (simple heuristic)
            first_span = block.get("lines", [{}])[0].get("spans", [{}])[0]
            font_size = first_span.get("size", 12)
            is_bold = any(
                "Bold" in span.get("font", "")
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            )

            if is_bold or font_size > 14:
                current_heading = text
            else:
                segments.append(
                    (
                        text,
                        {
                            "source": path.name,
                            "section_heading": current_heading,
                            "page_number": page_num,
                        },
                    )
                )

    doc.close()
    return segments


def _parse_markdown(path: Path) -> list[tuple[str, dict]]:
    """Parse a Markdown file, preserving heading structure."""
    segments: list[tuple[str, dict]] = []
    current_heading = ""
    content_buffer: list[str] = []

    text = path.read_text(encoding="utf-8")

    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            # Flush previous content buffer
            if content_buffer:
                para = "\n".join(content_buffer).strip()
                if para:
                    segments.append(
                        (
                            para,
                            {
                                "source": path.name,
                                "section_heading": current_heading,
                            },
                        )
                    )
                content_buffer = []

            current_heading = heading_match.group(2).strip()
        elif line.strip():
            content_buffer.append(line)
        else:
            # Blank line — flush paragraph
            if content_buffer:
                para = "\n".join(content_buffer).strip()
                if para:
                    segments.append(
                        (
                            para,
                            {
                                "source": path.name,
                                "section_heading": current_heading,
                            },
                        )
                    )
                content_buffer = []

    # Flush remaining content
    if content_buffer:
        para = "\n".join(content_buffer).strip()
        if para:
            segments.append(
                (
                    para,
                    {
                        "source": path.name,
                        "section_heading": current_heading,
                    },
                )
            )

    return segments


def _parse_text(path: Path) -> list[tuple[str, dict]]:
    """Parse a plain text file by paragraph breaks."""
    segments: list[tuple[str, dict]] = []
    text = path.read_text(encoding="utf-8")
    paragraphs = re.split(r"\n\s*\n", text.strip())

    for para in paragraphs:
        para = para.strip()
        if para:
            segments.append(
                (
                    para,
                    {
                        "source": path.name,
                        "section_heading": "",
                    },
                )
            )

    return segments


def _parse_docx(path: Path) -> list[tuple[str, dict]]:
    """Parse a DOCX file using python-docx."""
    from docx import Document

    segments: list[tuple[str, dict]] = []
    doc = Document(str(path))
    current_heading = ""

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if para.style.name.startswith("Heading"):
            current_heading = text
        else:
            segments.append(
                (
                    text,
                    {
                        "source": path.name,
                        "section_heading": current_heading,
                    },
                )
            )

    return segments
