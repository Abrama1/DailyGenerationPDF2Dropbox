import pytest

from app.worker.pdf_date import DateParseError, parse_date_key_from_text


def test_parses_simple_february_example():
    text = "თებერვალი, 2026\nცხრილი\n17 თებერვალი"
    assert parse_date_key_from_text(text) == "20260217"


def test_parses_without_comma_in_header():
    text = "თებერვალი 2026\n2 თებერვალი"
    assert parse_date_key_from_text(text) == "20260202"


def test_picks_max_day_if_multiple_rows_same_month():
    text = "თებერვალი, 2026\n1 თებერვალი\n17 თებერვალი\n3 თებერვალი"
    assert parse_date_key_from_text(text) == "20260217"


def test_prefers_header_month_over_other_months():
    text = "მარტი, 2026\n27 თებერვალი\n3 მარტი"
    assert parse_date_key_from_text(text) == "20260303"


def test_missing_month_year_raises():
    text = "2026\n17 თებერვალი"
    with pytest.raises(DateParseError) as e:
        parse_date_key_from_text(text)
    assert e.value.code == "missing_month_year"


def test_missing_day_month_raises():
    text = "თებერვალი, 2026\nარ არის დღე"
    with pytest.raises(DateParseError) as e:
        parse_date_key_from_text(text)
    assert e.value.code == "missing_day_month"


def test_empty_text_raises():
    with pytest.raises(DateParseError) as e:
        parse_date_key_from_text("   ")
    assert e.value.code == "empty_text"
