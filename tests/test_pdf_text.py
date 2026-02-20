from __future__ import annotations

from pathlib import Path
import tempfile

import fitz  # PyMuPDF

from app.worker.pdf_text import extract_text_from_pdf


def _make_test_pdf(path: Path) -> None:
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "თებერვალი, 2026")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "17 თებერვალი")
    doc.save(str(path))
    doc.close()


def test_extracts_text_from_first_two_pages():
    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "sample.pdf"
        _make_test_pdf(pdf_path)

        text = extract_text_from_pdf(pdf_path, pages=(0, 1))
        assert "თებერვალი, 2026" in text
        assert "17 თებერვალი" in text


def test_extracts_only_first_page_when_requested():
    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "sample.pdf"
        _make_test_pdf(pdf_path)

        text = extract_text_from_pdf(pdf_path, pages=(0,))
        assert "თებერვალი, 2026" in text
        assert "17 თებერვალი" not in text
