"""Date facts from an invented spec, executed like a code node. No brief values."""
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib.date_facts import date_facts_source  # noqa: E402

D = datetime.date
SPEC = {
    "calendar": {"holidays": ["2030-03-04", "2030-03-15"], "weekend": [5, 6]},
    "bands": [{"name": "soft", "min_days": 1, "max_days": 10, "deadline": "business_days_after_today:9", "attempts": 1},
              {"name": "hard", "min_days": 11, "max_days": 60, "deadline": "business_days_after_today:4", "attempts": 2}],
    "callback": {"days": ["today", "next_business_day"], "from": "09:30", "to": "18:00", "later_than_now": True},
}


def run(now: str) -> tuple:
    v = {"now": now}
    ns = {"vars": v}
    exec(date_facts_source(SPEC), ns)
    return v, ns


class TestDateFacts(unittest.TestCase):
    def test_basic_facts(self):
        v, _ = run("2030-03-01T12:15")   # a Friday
        self.assertEqual(v["date_state"], "ok")
        self.assertEqual(v["today_spoken"], "Friday 1 March 2030")
        self.assertIn('"next Friday" = Friday 8 March 2030', v["week_table"])

    def test_callback_window_today_and_next_business_day(self):
        v, _ = run("2030-03-01T12:15")
        self.assertIn("any time later than 12:15 up to 18:00", v["callback_facts"])
        self.assertIn("Tuesday 5 March 2030", v["callback_facts"])   # Monday 4th is a holiday
        v, _ = run("2030-03-01T19:00")
        self.assertIn("no longer possible", v["callback_facts"])
        v, _ = run("2030-03-01T08:00")
        self.assertIn("from 09:30 up to 18:00", v["callback_facts"])

    def test_bands_and_deadlines(self):
        _, ns = run("2030-03-01T12:00")
        today = D(2030, 3, 1)
        self.assertEqual(ns["band_for"](3)["name"], "soft")
        self.assertEqual(ns["band_for"](11)["name"], "hard")
        self.assertIsNone(ns["band_for"](0))
        self.assertEqual(ns["date_expr"]("business_days_after_today:4", today), D(2030, 3, 8))

    def test_last_business_day_of_week(self):
        _, ns = run("2030-03-01T12:00")
        de = ns["date_expr"]
        self.assertEqual(de("last_business_day_this_week_or_next_if_today", D(2030, 3, 1)), D(2030, 3, 8))
        self.assertEqual(de("last_business_day_this_week", D(2030, 3, 1)), D(2030, 3, 1))
        self.assertEqual(de("last_business_day_this_week_or_next_if_today", D(2030, 3, 11)), D(2030, 3, 14))  # 15th holiday
        self.assertEqual(de("last_business_day_this_week_or_next_if_today", D(2030, 3, 11), D(2030, 3, 12)), D(2030, 3, 12))

    def test_calendar_day_expressions(self):
        _, ns = run("2030-03-01T12:00")   # Friday; 2030-03-04 is a holiday
        de = ns["date_expr"]
        self.assertEqual(de("calendar_days_after_today:2", D(2030, 3, 1)), D(2030, 3, 3))           # Sunday, as is
        self.assertEqual(de("calendar_days_after_today:2:back", D(2030, 3, 1)), D(2030, 3, 1))      # back to Friday
        self.assertEqual(de("calendar_days_after_today:2:forward", D(2030, 3, 1)), D(2030, 3, 5))   # past the holiday

    def test_calendar_lines(self):
        _, ns = run("2030-03-01T12:00")
        text = ns["calendar_lines"](D(2030, 3, 1), D(2030, 3, 14), 2)
        self.assertIn("Monday 4 March 2030 (2030-03-04): NOT allowed, a bank holiday. Offer the next business day, Tuesday 5 March 2030.", text)
        self.assertIn("Friday 15 March 2030 (2030-03-15): AFTER the deadline", text)
        self.assertIn("Can you pay on that day?", text)

    def test_now_variable_name_comes_from_the_spec(self):
        v = {"stamp": "2030-03-01T12:15"}
        exec(date_facts_source(dict(SPEC, now_variable="stamp")), {"vars": v})
        self.assertEqual(v["today_spoken"], "Friday 1 March 2030")

    def test_bad_now_never_raises(self):
        v, _ = run("not a date")
        self.assertTrue(v["date_state"].startswith("error"))


if __name__ == "__main__":
    unittest.main()
