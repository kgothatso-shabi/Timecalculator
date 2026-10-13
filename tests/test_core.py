import unittest
from datetime import date

from timecalc import core
from timecalc.core import DateOptions, HoursOptions, ValidationError


class SumTests(unittest.TestCase):
    def test_screenshot_example(self):
        rows = [("00", "31"), ("00", "48"), ("00", "55"), ("00", "53"), ("00", "43"), ("01", "54"),
                ("00", "00"), ("00", "00"), ("00", "00"), ("00", "00")]
        total = core.sum_rows(rows)
        self.assertEqual(core.split_hm(total), (5, 44))
        self.assertEqual(core.format_decimal(total), "5.73")

    def test_blank_is_zero(self):
        self.assertEqual(core.sum_rows([("", ""), ("1", "")]), 60)

    def test_minutes_over_59_rejected_with_field(self):
        with self.assertRaises(ValidationError) as cm:
            core.sum_rows([("0", "10"), ("0", "75")])
        self.assertEqual(cm.exception.field, (1, "m"))

    def test_non_numeric_rejected(self):
        with self.assertRaises(ValidationError):
            core.sum_rows([("1x", "00")])
        with self.assertRaises(ValidationError):
            core.sum_rows([("-1", "00")])

    def test_rounding_half_up(self):
        self.assertEqual(core.format_decimal(3), "0.05")     # 0.05 exactly
        self.assertEqual(core.format_decimal(1), "0.02")     # 0.0166..
        self.assertEqual(core.format_decimal(90), "1.50")


class HoursTests(unittest.TestCase):
    def mod(self, h, m, ap):
        return core.to_minute_of_day(h, m, ap, "T", "from")

    def test_clock_conversion(self):
        self.assertEqual(self.mod("12", "00", "AM"), 0)
        self.assertEqual(self.mod("0", "00", "AM"), 0)
        self.assertEqual(self.mod("12", "00", "PM"), 720)
        self.assertEqual(self.mod("5", "30", "PM"), 17 * 60 + 30)

    def test_invalid_hour(self):
        with self.assertRaises(ValidationError):
            self.mod("13", "00", "AM")

    def test_simple_and_overnight(self):
        nine, five = self.mod("9", "00", "AM"), self.mod("5", "30", "PM")
        self.assertEqual(core.time_between(nine, five), 510)
        ten_pm, six_am = self.mod("10", "00", "PM"), self.mod("6", "00", "AM")
        self.assertEqual(core.time_between(ten_pm, six_am), 480)
        with self.assertRaises(ValidationError):
            core.time_between(ten_pm, six_am, HoursOptions(overnight=False))

    def test_break(self):
        self.assertEqual(core.time_between(0, 480, HoursOptions(break_minutes=30)), 450)
        with self.assertRaises(ValidationError):
            core.time_between(0, 20, HoursOptions(break_minutes=30))

    def test_formats(self):
        self.assertEqual(core.format_hours_result(450, "decimal"), "07.50")
        self.assertEqual(core.format_hours_result(450, "hhmm"), "07:30")
        self.assertEqual(core.format_hours_result(0, "decimal"), "00.00")
        self.assertEqual(core.format_clock(0), "12:00 AM")
        self.assertEqual(core.format_clock(17 * 60 + 5), "5:05 PM")


class DateTests(unittest.TestCase):
    START, END = date(2026, 10, 13), date(2026, 11, 13)      # Tue -> Fri

    def days(self, **kw):
        return core.date_difference(self.START, self.END, DateOptions(**kw))

    def test_inclusive_rules(self):
        self.assertEqual(self.days().days, 31)
        self.assertEqual(self.days(include_start=False).days, 30)
        self.assertEqual(self.days(include_end=True).days, 32)
        self.assertEqual(self.days(include_start=False, include_end=True).days, 31)

    def test_working_days(self):
        self.assertEqual(self.days(mode="working").days, 23)
        self.assertEqual(self.days(mode="working", include_end=True).days, 24)
        # Friday-only weekend: 31 calendar days minus 4 Fridays (Oct 16, 23, 30, Nov 6) = 27
        self.assertEqual(self.days(mode="working", weekend_days=frozenset({4})).days, 27)

    def test_holidays(self):
        hol = frozenset({date(2026, 11, 2)})                  # a Monday
        self.assertEqual(self.days(mode="working", holidays=hol).days, 22)
        self.assertEqual(self.days(mode="working", holidays=hol, skip_holidays=False).days, 23)
        weekend_hol = frozenset({date(2026, 10, 17)})         # Saturday: counted once, as weekend
        r = self.days(mode="working", holidays=weekend_hol)
        self.assertEqual((r.days, r.holidays_skipped), (23, 0))

    def test_same_day_and_reversed(self):
        d = date(2026, 1, 5)
        self.assertEqual(core.date_difference(d, d, DateOptions()).days, 0)
        self.assertEqual(core.date_difference(d, d, DateOptions(include_end=True)).days, 1)
        self.assertEqual(core.date_difference(d, d, DateOptions(include_start=False)).days, 0)
        with self.assertRaises(ValidationError):
            core.date_difference(date(2026, 1, 6), d)

    def test_ymd(self):
        self.assertEqual(core.ymd_between(date(2026, 1, 31), date(2026, 3, 1)), (0, 1, 1))
        self.assertEqual(core.ymd_between(date(2024, 2, 29), date(2025, 2, 28)), (1, 0, 0))
        r = self.days()
        self.assertEqual((r.years, r.months, r.month_days), (0, 1, 0))
        self.assertEqual((r.weeks, r.week_days), (4, 3))

    def test_formatting(self):
        o = DateOptions()
        r = core.date_difference(self.START, self.END, o)
        self.assertEqual(core.format_date_result(r, o), "31 days")
        self.assertEqual(core.format_date_result(r, DateOptions(output="weeks_days")), "4 weeks, 3 days")
        self.assertEqual(core.format_date_result(r, DateOptions(output="ymd")), "1 month")
        one = core.date_difference(self.START, self.START.replace(day=14), o)
        self.assertEqual(core.format_date_result(one, o), "1 day")
        zero = core.date_difference(self.START, self.START, o)
        self.assertEqual(core.format_date_result(zero, DateOptions(output="ymd")), "0 days")

    def test_make_date_validation(self):
        self.assertEqual(core.make_date(2, "28", "2026", "Start", "from"), date(2026, 2, 28))
        with self.assertRaises(ValidationError) as cm:
            core.make_date(2, "30", "2026", "Start", "from")
        self.assertEqual(cm.exception.field, ("from", "d"))
        with self.assertRaises(ValidationError):
            core.make_date(2, "1", "", "Start", "from")
        with self.assertRaises(ValidationError):
            core.make_date(2, "1", "1500", "Start", "from")
        self.assertEqual(core.make_date(2, "29", "2028", "Start", "from"), date(2028, 2, 29))

    def test_parse_holidays(self):
        got = core.parse_holidays("2026-12-25\n2026-12-26, 2027-01-01;\n\n")
        self.assertEqual(len(got), 3)
        with self.assertRaises(ValidationError):
            core.parse_holidays("25/12/2026")


if __name__ == "__main__":
    unittest.main()
