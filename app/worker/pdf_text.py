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


def _normalize_pdf_text(s: str) -> str:
    # Replace non-breaking spaces and collapse weird whitespace into normal spaces
    return " ".join((s or "").replace("\xa0", " ").split())


def extract_text_from_pdf(
    pdf_path: str | Path,
    *,
    pages: Iterable[int] = (0, 1),
) -> str:
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
            text = _normalize_pdf_text(text)
            if text:
                parts.append(text)

        return "\n\n".join(parts).strip()
    except Exception as e:
        raise PdfTextExtractError(f"Failed to extract text: {e}") from e
    finally:
        doc.close()
