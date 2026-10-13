"""Pure calculation and validation logic. No GUI imports, fully unit-testable."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional, Sequence, Tuple

MIN_YEAR, MAX_YEAR = 1900, 2200


class ValidationError(ValueError):
    """Raised for bad user input. `field` tells the UI which control to highlight."""

    def __init__(self, message: str, field: Optional[tuple] = None):
        super().__init__(message)
        self.field = field


# --------------------------------------------------------------------------- #
# Generic helpers
# --------------------------------------------------------------------------- #
def parse_field(text: str, label: str, lo: int, hi: int,
                field: Optional[tuple] = None, blank_ok: bool = True) -> int:
    """Parse a whole-number text box and range-check it. Blank means 0 if allowed."""
    t = (text or "").strip()
    if t == "":
        if blank_ok:
            return 0
        raise ValidationError(f"{label} is required.", field)
    if not (t.isascii() and t.isdigit()):
        raise ValidationError(f"{label} must be a whole number.", field)
    value = int(t)
    if not lo <= value <= hi:
        raise ValidationError(f"{label} must be between {lo} and {hi}.", field)
    return value


def plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


# --------------------------------------------------------------------------- #
# 1. Adding up durations  (left-hand "Enter Time" list)
# --------------------------------------------------------------------------- #
def parse_rows(rows: Sequence[Tuple[str, str]]) -> list:
    """Each row is (hours_text, minutes_text). Returns minutes per row.

    Hours 0-99, minutes 0-59. Blank boxes count as 0.
    The error `field` is (row_index, "h" | "m").
    """
    result = []
    for i, (h_text, m_text) in enumerate(rows):
        h = parse_field(h_text, f"Line {i + 1} hours", 0, 99, (i, "h"))
        m = parse_field(m_text, f"Line {i + 1} minutes", 0, 59, (i, "m"))
        result.append(h * 60 + m)
    return result


def sum_rows(rows: Sequence[Tuple[str, str]]) -> int:
    return sum(parse_rows(rows))


def split_hm(total_minutes: int) -> Tuple[int, int]:
    return divmod(total_minutes, 60)


def format_decimal(total_minutes: int, places: int = 2) -> str:
    """Decimal hours, rounded half-up (5h44m -> '5.73')."""
    q = Decimal(1).scaleb(-places)
    return str((Decimal(total_minutes) / Decimal(60)).quantize(q, rounding=ROUND_HALF_UP))


# --------------------------------------------------------------------------- #
# 2. Time between two clock times  ("Time Between Hours")
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class HoursOptions:
    output: str = "decimal"      # "decimal" (7.50) or "hhmm" (07:30)
    overnight: bool = True       # end earlier than start => next day
    break_minutes: int = 0       # unpaid break subtracted from the result


def to_minute_of_day(hour_text: str, minute_text: str, meridiem: str,
                     label: str, prefix: str) -> int:
    """12-hour clock -> minutes since midnight. Hour 0 or 12 both mean 12."""
    h = parse_field(hour_text, f"{label} hour", 0, 12, (prefix, "h"))
    m = parse_field(minute_text, f"{label} minutes", 0, 59, (prefix, "m"))
    if meridiem not in ("AM", "PM"):
        raise ValidationError(f"{label}: choose AM or PM.", (prefix, "m"))
    return ((h % 12) + (12 if meridiem == "PM" else 0)) * 60 + m


def time_between(start_min: int, end_min: int, opts: HoursOptions = HoursOptions()) -> int:
    diff = end_min - start_min
    if diff < 0:
        if not opts.overnight:
            raise ValidationError("The 'To' time is earlier than the 'From' time.", ("to",))
        diff += 24 * 60
    diff -= opts.break_minutes
    if diff < 0:
        raise ValidationError("The break is longer than the time between the two times.", ("to",))
    return diff


def format_clock(minute_of_day: int) -> str:
    h, m = divmod(minute_of_day, 60)
    suffix = "AM" if h < 12 else "PM"
    return f"{(h % 12) or 12}:{m:02d} {suffix}"


def format_hours_result(minutes: int, output: str) -> str:
    if output == "hhmm":
        h, m = split_hm(minutes)
        return f"{h:02d}:{m:02d}"
    value = Decimal(minutes) / Decimal(60)
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):05}"   # 07.50


# --------------------------------------------------------------------------- #
# 3. Time between dates  ("Time Between Dates")
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DateOptions:
    mode: str = "calendar"                       # "calendar" or "working"
    include_start: bool = True                   # count the From date itself
    include_end: bool = False                    # count the To date itself
    weekend_days: frozenset = frozenset({5, 6})  # Monday=0 ... Sunday=6
    holidays: frozenset = frozenset()            # set of datetime.date
    skip_holidays: bool = True
    output: str = "days"                         # "days", "weeks_days", "ymd"


@dataclass(frozen=True)
class DateResult:
    days: int              # calendar or working days, depending on mode
    calendar_days: int     # always the plain calendar count for the same rule
    weekend_skipped: int
    holidays_skipped: int
    weeks: int
    week_days: int
    years: int
    months: int
    month_days: int


def make_date(month: int, day_text: str, year_text: str, label: str, prefix: str) -> date:
    year = parse_field(year_text, f"{label} year", MIN_YEAR, MAX_YEAR, (prefix, "y"), blank_ok=False)
    day = parse_field(day_text, f"{label} day", 1, 31, (prefix, "d"), blank_ok=False)
    try:
        return date(year, month, day)
    except ValueError:
        raise ValidationError(
            f"{label} date does not exist ({calendar.month_name[month]} has "
            f"{calendar.monthrange(year, month)[1]} days in {year}).", (prefix, "d")) from None


def add_months(d: date, n: int) -> date:
    idx = d.year * 12 + d.month - 1 + n
    y, m0 = divmod(idx, 12)
    m = m0 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def ymd_between(a: date, b: date) -> Tuple[int, int, int]:
    """Whole years, months and leftover days from a to b (a <= b)."""
    months = (b.year - a.year) * 12 + b.month - a.month
    if add_months(a, months) > b:
        months -= 1
    return months // 12, months % 12, (b - add_months(a, months)).days


def date_difference(start: date, end: date, opts: DateOptions = DateOptions()) -> DateResult:
    """Count days using a half-open window [first, last).

    first = start date if include_start else start + 1 day
    last  = end date + 1 day if include_end else end date
    e.g. Oct 13 -> Nov 13 gives 31 (default), 30 (neither), 32 (both).
    """
    if end < start:
        raise ValidationError("The 'To' date must not be before the 'From' date.", ("to",))
    first = start + timedelta(days=0 if opts.include_start else 1)
    last = end + timedelta(days=1 if opts.include_end else 0)
    if last < first:
        last = first
    total = (last - first).days

    working = total
    weekend_skipped = holiday_skipped = 0
    if opts.mode == "working":
        working = 0
        d = first
        one = timedelta(days=1)
        for _ in range(total):
            if d.weekday() in opts.weekend_days:
                weekend_skipped += 1
            elif opts.skip_holidays and d in opts.holidays:
                holiday_skipped += 1
            else:
                working += 1
            d += one

    weeks, week_days = divmod(total, 7)
    y, mo, md = ymd_between(first, last)
    return DateResult(working, total, weekend_skipped, holiday_skipped,
                      weeks, week_days, y, mo, md)


def format_date_result(res: DateResult, opts: DateOptions) -> str:
    if opts.mode == "working":
        return plural(res.days, "working day")
    if opts.output == "weeks_days":
        return f"{plural(res.weeks, 'week')}, {plural(res.week_days, 'day')}"
    if opts.output == "ymd":
        parts = [plural(res.years, "year") if res.years else "",
                 plural(res.months, "month") if res.months else "",
                 plural(res.month_days, "day") if res.month_days or not (res.years or res.months) else ""]
        return ", ".join(p for p in parts if p)
    return plural(res.days, "day")


def describe_rules(opts: DateOptions) -> str:
    kind = "working days" if opts.mode == "working" else "calendar days"
    start = "start date included" if opts.include_start else "start date excluded"
    end = "end date included" if opts.include_end else "end date excluded"
    return f"{kind}; {start}; {end}"


def parse_holidays(text: str) -> frozenset:
    """Parse one YYYY-MM-DD date per line (commas/semicolons also accepted)."""
    found = set()
    for raw in text.replace(",", "\n").replace(";", "\n").splitlines():
        item = raw.strip()
        if not item:
            continue
        try:
            found.add(date.fromisoformat(item))
        except ValueError:
            raise ValidationError(f"'{item}' is not a valid holiday date. Use YYYY-MM-DD.") from None
    return frozenset(found)


def format_holidays(holidays: Iterable[date]) -> str:
    return "\n".join(d.isoformat() for d in sorted(holidays))
