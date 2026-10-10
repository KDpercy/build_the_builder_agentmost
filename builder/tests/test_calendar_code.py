"""The generated calendar source, executed the way a code node runs it, on many dates.

The holiday dates below are test inputs invented for the tests, not taken from any brief.
"""
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib.calendar_code import calendar_source  # noqa: E402

D = datetime.date


def env(config: dict) -> dict:
    ns: dict = {}
    exec(calendar_source(config), ns)
    return ns


class TestCalendar(unittest.TestCase):
    def setUp(self):
        # 2030-03-01 is a Friday. Invented holidays: Monday 2030-03-04 and Friday 2030-03-15.
        self.c = env({"holidays": ["2030-03-04", "2030-03-15"], "weekend": [5, 6]})

    def test_triple_closing_brace_is_split(self):
        src = calendar_source({"a": {"b": {"c": 1}}})
        self.assertNotIn("}}", src)
        self.assertEqual(env({"a": {"b": {"c": 1}}})["CAL"]["a"]["b"]["c"], 1)

    def test_no_double_braces_even_with_nested_config(self):
        src = calendar_source({"bands": [{"a": {"b": 1}}], "holidays": []})
        self.assertNotIn("}}", src)
        self.assertNotIn("{{", src)
        self.assertEqual(env({"bands": [{"a": {"b": 1}}]})["CAL"]["bands"][0]["a"]["b"], 1)

    def test_weekend_and_holiday_are_not_business_days(self):
        c = self.c
        self.assertFalse(c["isbiz"](D(2030, 3, 2)))   # Saturday
        self.assertFalse(c["isbiz"](D(2030, 3, 3)))   # Sunday
        self.assertFalse(c["isbiz"](D(2030, 3, 4)))   # holiday
        self.assertTrue(c["isbiz"](D(2030, 3, 5)))

    def test_holiday_after_weekend(self):
        self.assertEqual(self.c["nextbiz"](D(2030, 3, 1)), D(2030, 3, 5))

    def test_nth_business_day_skips_weekend_and_holidays(self):
        nth = self.c["nth_biz_after"]
        self.assertEqual(nth(D(2030, 3, 1), 1), D(2030, 3, 5))
        self.assertEqual(nth(D(2030, 3, 1), 5), D(2030, 3, 11))
        self.assertEqual(nth(D(2030, 3, 1), 10), D(2030, 3, 19))  # 5,6,7,8,11,12,13,14,(15 holiday),18,19

    def test_count_today_option(self):
        c = env({"holidays": [], "count_today": True})
        self.assertEqual(c["nth_biz_after"](D(2030, 3, 5), 1), D(2030, 3, 5))

    def test_other_weekend(self):
        c = env({"holidays": [], "weekend": [4, 5]})  # Friday and Saturday off
        self.assertFalse(c["isbiz"](D(2030, 3, 1)))
        self.assertTrue(c["isbiz"](D(2030, 3, 3)))

    def test_week_end_business_day(self):
        web = self.c["week_end_biz"]
        self.assertEqual(web(D(2030, 3, 11)), D(2030, 3, 14))   # Friday 15th is a holiday
        self.assertEqual(web(D(2030, 3, 1)), D(2030, 3, 1))

    def test_this_and_next_weekday(self):
        c = self.c
        fri = D(2030, 3, 1)
        self.assertEqual(c["this_weekday"](fri, 4), fri)
        self.assertEqual(c["next_weekday"](fri, 4), D(2030, 3, 8))   # "next Friday" said on a Friday
        self.assertEqual(c["this_weekday"](D(2030, 3, 6), 0), D(2030, 3, 4))

    def test_spoken_date(self):
        self.assertEqual(self.c["sp"](D(2030, 3, 5)), "Tuesday 5 March 2030")

    def test_many_dates_never_land_on_a_non_business_day(self):
        c = self.c
        for offset in range(60):
            now = D(2030, 2, 20) + datetime.timedelta(days=offset)
            for n in (1, 7, 12):
                self.assertTrue(c["isbiz"](c["nth_biz_after"](now, n)), (now, n))
            self.assertTrue(c["isbiz"](c["nextbiz"](now)), now)


if __name__ == "__main__":
    unittest.main()
