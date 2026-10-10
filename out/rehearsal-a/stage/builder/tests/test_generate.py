"""The reference generator on an invented bank: other field names, values, questions and calendar.
The workflow must pass the validator and must not contain any value the spec did not give it."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import validate as V  # noqa: E402
from reference.generate import build  # noqa: E402


def op(props: dict, required: list) -> dict:
    return {"post": {"requestBody": {"content": {"application/json": {"schema": {
        "type": "object", "properties": props, "required": required}}}}}}


S = {"type": "string"}
API = {"servers": [{"url": "https://other-bank.example/api"}], "paths": {
    "/verify_identity": op({"client": S, "question": {"type": "string", "enum": ["postcode", "birth_year"]}, "value": S},
                           ["client", "question", "value"]),
    "/get_account": op({"client": S}, ["client"]),
    "/create_promise": op({"client": S, "item": S, "sum": {"type": "number"}, "day": S}, ["client", "item", "sum", "day"]),
    "/add_note": op({"client": S, "item": S, "why": {"type": "string", "enum": ["declined", "settled"]}}, ["client", "item", "why"]),
    "/schedule_callback": op({"client": S, "day": S, "hour": S}, ["client", "day", "hour"]),
    "/transfer_to_agent": op({"client": S, "desk": {"type": "string", "enum": ["arrears", "people"]}}, ["client", "desk"]),
    "/close_call": op({"client": S, "result": {"type": "string", "enum": ["agreed", "none", "moved", "unconfirmed", "missed"]},
                       "why": S}, ["client", "result"]),
}}

SPEC = {
    "agent_identity": "the Northwind Credit assistant",
    "opening": {"first_sentence": "Good morning, this is an automated assistant from Northwind Credit.", "ask": "Is this {{title}} {{last_name}}?"},
    "forbidden_before_verification": ["arrears", "balance"],
    "confirmation_words": {"confirms": ["yes"], "does_not_confirm": ["hi"], "asks": 2, "close_if_unclear": ["missed", "unclear"]},
    "identity": {"questions": [{"value": "postcode", "ask": "what is your postcode?", "kind": "text"},
                               {"value": "birth_year", "ask": "what year were you born?", "kind": "year"}],
                 "question_field": "question", "answer_field": "value", "numeric_date_order": "mdy", "wrong_answer_limit": 2,
                 "first_line": "Thanks. First, what is your postcode?",
                 "response": {"ok": "ok", "verified": "match", "all_verified": "passed", "left": "tries_left", "hint": "hint"},
                 "on_failed": {"say": "suggest visiting a branch", "close": ["unconfirmed", "failed"]},
                 "on_declined": {"explain_once": "the questions keep their money safe", "close": ["unconfirmed", "declined"]}},
    "calendar": {"holidays": ["2030-01-01"], "weekend": [4, 5]},
    "bands": [{"name": "any", "min_days": 1, "max_days": 99, "deadline": "business_days_after_today:5", "attempts": 1}],
    "products": {"type_field": "kind", "fields": {"id": "item", "past_due": "due", "days_late": "late"},
                 "types": {"cardx": {"spoken": "card {last}", "floor_field": "min"}}},
    "debt_statement": "I am calling about your overdue balance",
    "first_ask": "Can you settle it today?",
    "persuasion": {"attempts": [{"amount": "full", "date": "deadline"}], "floor_offer": {"once": True, "say_with_offer": "the remainder stays open"},
                   "close_refused": ["none", "declined"]},
    "callback": {"days": ["next_business_day"], "from": "09:00", "to": "17:00", "close_booked": ["missed", "rebook"], "close_none": ["missed", "none"]},
    "special_cases": [{"name": "people", "trigger": "asks for a person", "action": "ask once if you can help", "transfer": "people", "close": ["moved", "person"]}],
    "third_party": {"wrong_number": ["missed", "wrong"], "deceased": {"say": "My condolences.", "close": ["missed", "deceased"]}},
    "outcome_logic": {"on_transfer": "moved", "reason_by_queue": {"people": "person", "arrears": "plan"}, "on_promise": "agreed",
                      "no_promise": "none", "verify_failed": ["unconfirmed", "failed"], "promise_failed": ["none", "error"]},
    "notes": {"used": False},
    "sentences": {"after_promise": "A letter will confirm this arrangement."},
    "read_back": {"ask": "Is that right?"},
    "tool_names": {"verify": "verify_identity", "account": "get_account", "promise": "create_promise", "callback": "schedule_callback",
                   "transfer": "transfer_to_agent", "note": "add_note", "close": "close_call"},
    "tool_fields": {"customer": "client", "product": "item", "amount": "sum", "date": "day", "queue": "desk", "note_reason": "why",
                    "outcome": "result", "reason": "why"},
    "never_offer": ["a fee waiver"],
}


class TestGenerate(unittest.TestCase):
    def setUp(self):
        self.wf = build(SPEC, API)
        self.text = json.dumps(self.wf)

    def test_passes_the_validator(self):
        rules = {"forbidden_before_verification": SPEC["forbidden_before_verification"],
                 "required_sentences": [SPEC["sentences"]["after_promise"], "My condolences."]}
        errors = [m for level, m in V.validate(self.wf, API, rules) if level == V.ERROR]
        self.assertEqual(errors, [])

    def test_uses_the_tool_api_and_spec_names(self):
        self.assertIn("https://other-bank.example/api/verify_identity", self.text)
        self.assertIn('"client"', self.text)
        self.assertIn("Northwind Credit", self.text)

    def test_product_steps_cannot_close_the_call(self):
        for name, n in self.wf["nodes"].items():
            if name.startswith("product_") and n["node_type"] == "conversation":
                self.assertNotIn("close_call", [t["function"]["name"] for t in n.get("tools", [])], name)

    def test_no_note_tool_when_notes_are_not_used(self):
        tools = {t["function"]["name"] for n in self.wf["nodes"].values() for t in n.get("tools", [])}
        self.assertNotIn("add_note", tools)

    def test_no_value_from_any_practice_brief(self):
        for word in ("Freya Bank", "collections", "minimum_payment", "instalment", "2026", "customer_id\": {\"type\": \"string\", \"default\": \"{{customer_id}}\"}, \"field"):
            self.assertNotIn(word, self.text, word)


if __name__ == "__main__":
    unittest.main()
