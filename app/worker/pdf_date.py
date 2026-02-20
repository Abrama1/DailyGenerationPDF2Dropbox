from __future__ import annotations

import re
from dataclasses import dataclass


GE_MONTHS = {
    "იანვარი": 1,
    "თებერვალი": 2,
    "მარტი": 3,
    "აპრილი": 4,
    "მაისი": 5,
    "ივნისი": 6,
    "ივლისი": 7,
    "აგვისტო": 8,
    "სექტემბერი": 9,
    "ოქტომბერი": 10,
    "ნოემბერი": 11,
    "დეკემბერი": 12,
}


@dataclass(frozen=True)
class DateParseError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


_month_year_re = re.compile(r"([ა-ჰ]+)\s*,?\s*(\d{4})")
_day_month_re = re.compile(r"(\d{1,2})\s+([ა-ჰ]+)")


def _normalize_month_name(raw: str) -> str:
    # Keep it simple: lower + strip whitespace.
    return raw.strip().lower()


def _month_to_number(month_name: str) -> int | None:
    return GE_MONTHS.get(_normalize_month_name(month_name))


def parse_date_key_from_text(text: str) -> str:
    """
    Extracts date from Georgian PDF text and returns YYYYMMDD string.
    Expected stable patterns:
      - Header: "თებერვალი, 2026" (month-year)
      - Table:  "17 თებერვალი"   (day-month)

    Strategy:
      1) Find first recognized month-year => (month, year)
      2) Find all recognized day-month occurrences
      3) Prefer day-months matching header month
      4) Choose the maximum day among candidates (safe if multiple rows exist)

    Raises DateParseError with a clear code if parsing fails.
    """
    if not text or not text.strip():
        raise DateParseError("empty_text", "No text provided for date parsing")

    # 1) Month + year (header-like)
    header_month = None
    header_year = None
    for m_name, y in _month_year_re.findall(text):
        m_num = _month_to_number(m_name)
        if m_num is not None:
            header_month = m_num
            header_year = int(y)
            break

    if header_month is None or header_year is None:
        raise DateParseError(
            "missing_month_year",
            "Could not find a recognizable Georgian month+year (e.g., 'თებერვალი, 2026')",
        )

    # 2) Day + month (table-like)
    candidates: list[tuple[int, int]] = []  # (day, month_num)
    for d_str, m_name in _day_month_re.findall(text):
        m_num = _month_to_number(m_name)
        if m_num is None:
            continue
        day = int(d_str)
        if 1 <= day <= 31:
            candidates.append((day, m_num))

    if not candidates:
        raise DateParseError(
            "missing_day_month",
            "Could not find a recognizable Georgian day+month (e.g., '17 თებერვალი')",
        )

    # 3) Prefer same-month candidates
    same_month = [(d, m) for (d, m) in candidates if m == header_month]
    final_candidates = same_month if same_month else candidates

    # 4) Pick the max day (robust if multiple rows exist)
    day, month = max(final_candidates, key=lambda x: x[0])

    # Build YYYYMMDD
    return f"{header_year:04d}{month:02d}{day:02d}"
