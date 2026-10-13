"""Load/save user options as JSON in %APPDATA%\\TimeCalculator\\settings.json."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .core import DateOptions, HoursOptions

APP_NAME = "TimeCalculator"


@dataclass
class AppSettings:
    hours: HoursOptions = field(default_factory=HoursOptions)
    dates: DateOptions = field(default_factory=DateOptions)


def settings_path() -> Path:
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / APP_NAME / "settings.json"


def _hours_from(d: dict) -> HoursOptions:
    default = HoursOptions()
    output = d.get("output", default.output)
    brk = d.get("break_minutes", 0)
    return HoursOptions(
        output=output if output in ("decimal", "hhmm") else default.output,
        overnight=bool(d.get("overnight", default.overnight)),
        break_minutes=brk if isinstance(brk, int) and 0 <= brk <= 1440 else 0,
    )


def _dates_from(d: dict) -> DateOptions:
    default = DateOptions()
    holidays = set()
    for item in d.get("holidays", []):
        try:
            holidays.add(date.fromisoformat(item))
        except (TypeError, ValueError):
            pass
    weekend = {x for x in d.get("weekend_days", [5, 6]) if isinstance(x, int) and 0 <= x <= 6}
    mode = d.get("mode", default.mode)
    output = d.get("output", default.output)
    return DateOptions(
        mode=mode if mode in ("calendar", "working") else default.mode,
        include_start=bool(d.get("include_start", default.include_start)),
        include_end=bool(d.get("include_end", default.include_end)),
        weekend_days=frozenset(weekend),
        holidays=frozenset(holidays),
        skip_holidays=bool(d.get("skip_holidays", default.skip_holidays)),
        output=output if output in ("days", "weeks_days", "ymd") else default.output,
    )


def load() -> AppSettings:
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        return AppSettings(_hours_from(data.get("hours", {})), _dates_from(data.get("dates", {})))
    except (OSError, ValueError, AttributeError):
        return AppSettings()


def save(s: AppSettings) -> None:
    h, d = s.hours, s.dates
    data = {
        "hours": {"output": h.output, "overnight": h.overnight, "break_minutes": h.break_minutes},
        "dates": {
            "mode": d.mode, "include_start": d.include_start, "include_end": d.include_end,
            "weekend_days": sorted(d.weekend_days),
            "holidays": sorted(x.isoformat() for x in d.holidays),
            "skip_holidays": d.skip_holidays, "output": d.output,
        },
    }
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # a read-only profile must never crash the app
