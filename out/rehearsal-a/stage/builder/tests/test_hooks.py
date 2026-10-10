"""Identity answer cleaning, run the way the platform runs a pre-hook. Test inputs are invented."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib.hooks import identity_parser_source, identity_pre_source  # noqa: E402

CFG = {"question_field": "field", "answer_field": "answer", "numeric_date_order": "dmy",
       "kinds": {"dob": "date", "last4": "digits:4", "born": "year", "zip": "text"}}


def norm():
    ns: dict = {}
    exec(identity_parser_source(CFG), ns)
    return ns["norm"]


def run_pre(body: dict, cfg: dict = CFG) -> dict:
    config = {"body": dict(body)}
    exec(identity_pre_source(cfg), {"config": config, "vars": {}})
    return config["body"]


class TestIdentity(unittest.TestCase):
    def test_dates(self):
        n = norm()
        self.assertEqual(n("date", "2001-02-03"), "2001-02-03")
        self.assertEqual(n("date", "03/02/2001"), "2001-02-03")          # numbers only: day, month, year
        self.assertEqual(n("date", "2001.2.3"), "2001-02-03")
        self.assertEqual(n("date", "3 February 2001"), "2001-02-03")
        self.assertEqual(n("date", "February 3rd, 2001"), "2001-02-03")
        self.assertEqual(n("date", "the third of February 2001"), "2001-02-03")
        self.assertEqual(n("date", "twenty-first of June 1999"), "1999-06-21")

    def test_month_first_order(self):
        ns: dict = {}
        exec(identity_parser_source(dict(CFG, numeric_date_order="mdy")), ns)
        self.assertEqual(ns["norm"]("date", "03/02/2001"), "2001-03-02")

    def test_digits(self):
        n = norm()
        self.assertEqual(n("digits:4", "it's 4 4 1 0"), "4410")
        self.assertEqual(n("digits:4", "eight eight four six"), "8846")
        self.assertEqual(n("digits:4", "double five oh two"), "5502")
        self.assertEqual(n("digits:4", "+34 600 123 456"), "3456")

    def test_year_and_text(self):
        n = norm()
        self.assertEqual(n("year", "I was born in 1987"), "1987")
        self.assertEqual(n("text", "  sw1a 1aa "), "sw1a 1aa")

    def test_pre_hook_rewrites_only_known_questions(self):
        self.assertEqual(run_pre({"field": "last4", "answer": "four four one zero"})["answer"], "4410")
        self.assertEqual(run_pre({"field": "other", "answer": "four"})["answer"], "four")

    def test_pre_hook_uses_configured_field_names(self):
        cfg = dict(CFG, question_field="q", answer_field="a")
        self.assertEqual(run_pre({"q": "born", "a": "1975, I think"}, cfg)["a"], "1975")

    def test_pre_hook_never_raises(self):
        self.assertEqual(run_pre({"field": "dob"}), {"field": "dob"})
        config = {"body": "not a dict"}
        exec(identity_pre_source(CFG), {"config": config, "vars": {}})
        self.assertEqual(config["body"], "not a dict")


if __name__ == "__main__":
    unittest.main()
