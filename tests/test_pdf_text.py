from __future__ import annotations

from pathlib import Path
import tempfile

import fitz  # PyMuPDF

from app.worker.pdf_text import extract_text_from_pdf


def _find_unicode_font() -> Path | None:
    candidates = [
        # Windows (often contains Georgian-capable fonts)
        Path(r"C:\Windows\Fonts\sylfaen.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\seguisym.ttf"),
        Path(r"C:\Windows\Fonts\tahoma.ttf"),
        # Linux
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        # macOS
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _make_test_pdf(path: Path) -> tuple[str, str]:
    """
    Creates a 2-page PDF and returns (expected_page1_text, expected_page2_text).

    If a Unicode font is available, writes Georgian strings.
    Otherwise falls back to ASCII so extraction tests still validate behavior.
    """
    doc = fitz.open()

    font_path = _find_unicode_font()
    if font_path:
        expected1 = "თებერვალი, 2026"
        expected2 = "17 თებერვალი"
        fontname = "u"

        p1 = doc.new_page()
        p1.insert_font(fontname=fontname, fontfile=str(font_path))
        p1.insert_text((72, 72), expected1, fontname=fontname, fontsize=12)

        p2 = doc.new_page()
        p2.insert_font(fontname=fontname, fontfile=str(font_path))
        p2.insert_text((72, 72), expected2, fontname=fontname, fontsize=12)
    else:
        expected1 = "FEBRUARY, 2026"
        expected2 = "17 FEBRUARY"

        p1 = doc.new_page()
        p1.insert_text((72, 72), expected1)

        p2 = doc.new_page()
        p2.insert_text((72, 72), expected2)

    doc.save(str(path))
    doc.close()
    return expected1, expected2


def test_extracts_text_from_first_two_pages():
    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "sample.pdf"
        expected1, expected2 = _make_test_pdf(pdf_path)

        text = extract_text_from_pdf(pdf_path, pages=(0, 1))
        assert expected1 in text
        assert expected2 in text


def test_extracts_only_first_page_when_requested():
    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "sample.pdf"
        expected1, expected2 = _make_test_pdf(pdf_path)

        text = extract_text_from_pdf(pdf_path, pages=(0,))
        assert expected1 in text
        assert expected2 not in text
