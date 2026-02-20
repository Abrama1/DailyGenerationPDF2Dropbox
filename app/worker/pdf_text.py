from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz  # PyMuPDF


@dataclass(frozen=True)
class PdfTextExtractError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def extract_text_from_pdf(
    pdf_path: str | Path,
    *,
    pages: Iterable[int] = (0, 1),
) -> str:
    """
    Extracts plain text from selected pages of a PDF using PyMuPDF.

    - `pages` are 0-based page indices.
    - Missing page indices are ignored.
    - Returns a single combined string (pages separated by blank lines).

    Raises PdfTextExtractError for IO/corrupted PDF issues.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise PdfTextExtractError(f"PDF not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise PdfTextExtractError(f"Failed to open PDF: {e}") from e

    try:
        parts: list[str] = []
        total_pages = doc.page_count

        for idx in pages:
            if idx < 0 or idx >= total_pages:
                continue
            page = doc.load_page(idx)
            text = page.get_text("text") or ""
            text = text.strip()
            if text:
                parts.append(text)

        return "\n\n".join(parts).strip()
    except Exception as e:
        raise PdfTextExtractError(f"Failed to extract text: {e}") from e
    finally:
        doc.close()
