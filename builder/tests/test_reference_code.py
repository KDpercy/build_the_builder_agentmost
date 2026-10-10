"""Per-product debt facts from an invented spec and an invented account."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from reference.code import debt_source  # noqa: E402

SPEC = {
    "calendar": {"holidays": ["2030-03-04"], "weekend": [5, 6]},
    "bands": [{"name": "mild", "min_days": 1, "max_days": 9, "deadline": "business_days_after_today:10", "attempts": 1},
              {"name": "severe", "min_days": 10, "max_days": 90, "deadline": "business_days_after_today:3", "attempts": 2}],
    "products": {"type_field": "kind", "fields": {"id": "ref", "past_due": "owed", "days_late": "late"},
                 "types": {"overdraft": {"spoken": "overdraft on account {acct}", "floor_field": "min_due"},
                           "mortgage": {"spoken": "mortgage", "floor_field": "monthly"}}},
    "persuasion": {"attempts": [{"amount": "full_or_floor_if_too_much", "date": "last_business_day_this_week_or_next_if_today"},
                                {"amount": "floor", "date": "deadline"}]},
    "debt_statement": "We are calling about money owed",
    "first_ask": "Could you settle it today?",
    "first_ask_all": "Could you settle all of them today?",
}
ACCOUNT = [{"ref": "a1", "kind": "overdraft", "acct": "77", "owed": 500, "late": 3, "min_due": 50},
           {"ref": "a2", "kind": "mortgage", "owed": 1200, "late": 30, "monthly": 400}]


def run(products: list, now: str = "2030-03-05T10:00") -> dict:
    v = {"now": now, "account_products": json.dumps(products)}
    exec(debt_source(SPEC), {"vars": v})
    return v


class TestDebtFacts(unittest.TestCase):
    def test_one_product_line(self):
        v = run(ACCOUNT[:1])
        self.assertEqual(v["debt_state"], "ok")
        self.assertEqual(v["debt_line"], "Thank you, you are verified. We are calling about money owed on your overdraft on account 77. "
                                         "The past-due amount is 500.00, and it is 3 days late. Could you settle it today?")

    def test_bands_floors_and_attempts_per_product(self):
        v = run(ACCOUNT)
        self.assertEqual(v["n_products"], "2")
        self.assertIn("band: mild", v["p1_block"])
        self.assertIn("Floor, the lowest amount you may record: 50.00", v["p1_block"])
        self.assertIn("band: severe", v["p2_block"])
        self.assertNotIn("Attempt 2", v["p1_attempts"])
        self.assertIn("Attempt 2: propose 400.00 on Friday 8 March 2030", v["p2_attempts"])   # 3 business days after Tue 5th
        self.assertIn("Could you settle all of them today?", v["debt_line"])
        self.assertEqual(json.loads(v["deadlines_json"])["a2"], "2030-03-08")

    def test_products_from_flattened_response_variables(self):
        v = {"now": "2030-03-05T10:00", "load_x_response.data.products.0.ref": "a1", "load_x_response.data.products.0.kind": "mortgage",
             "load_x_response.data.products.0.owed": 1200, "load_x_response.data.products.0.late": 30,
             "load_x_response.data.products.0.monthly": 400}
        exec(debt_source(SPEC), {"vars": v})
        self.assertEqual(v["debt_state"], "ok")
        self.assertEqual(v["product_ids"], "a1")

    def test_bad_account_reports_error(self):
        self.assertEqual(run([])["debt_state"], "error")
        self.assertEqual(run([{"kind": "overdraft"}])["debt_state"], "error")


class TestPromiseRetryFill(unittest.TestCase):
    def test_missing_amount_and_date_come_from_stored_args(self):
        from reference import hooks as RH
        spec = dict(SPEC, tool_names={"promise": "make_deal"}, tool_fields={"product": "item", "amount": "sum", "date": "day"})
        v = {"make_deal_args.make_deal_sum": 120, "make_deal_args.make_deal_day": "2030-03-06", "product_ids": "a1"}
        cfg = {"body": {"item": "a1"}}
        exec(RH.promise_pre(spec), {"config": cfg, "vars": v})
        self.assertEqual(cfg["body"]["sum"], 120.0)
        self.assertEqual(cfg["body"]["day"], "2030-03-06")


if __name__ == "__main__":
    unittest.main()
