"""One failing fixture per validator check, plus a clean workflow that must pass.

    python3 -m unittest discover -s builder/tests -v
"""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import validate as V  # noqa: E402

API = {"paths": {
    "/verify_identity": {"post": {"requestBody": {"content": {"application/json": {"schema": {
        "properties": {"customer_id": {}, "field": {"enum": ["date_of_birth", "phone_last4"]}, "answer": {}},
        "required": ["customer_id", "field", "answer"]}}}}}},
    "/close_call": {"post": {"requestBody": {"content": {"application/json": {"schema": {
        "properties": {"customer_id": {}, "outcome": {"enum": ["promise", "no_promise"]}, "reason": {}},
        "required": ["customer_id", "outcome"]}}}}}},
}}


def api_tool(name: str, body: dict) -> dict:
    return {"type": "function", "function": {"name": name, "handler": "__function__:api_call", "parameters": {
        "type": "object", "properties": {"body": {"type": "object", "properties": body}}}}}


VERIFY = api_tool("verify_identity", {"customer_id": {"default": "{{customer_id}}"},
                                      "field": {"enum": ["date_of_birth", "phone_last4"]}, "answer": {}})
CLOSE = api_tool("close_call", {"customer_id": {"default": "{{customer_id}}"}, "outcome": {"enum": ["promise", "no_promise"]}})


def route(target: str, variable: str, values: list) -> dict:
    return {"target_node": target, "condition": {"logic": "or", "conditions": [
        {"variable": variable, "operator": "equals", "operand": v} for v in values]}}


CLEAN = {
    "initial_node": "setup",
    "system_prompt": "Today is {{today_spoken}}.",
    "nodes": {
        "setup": {"node_type": "code", "passthrough": True, "passthrough_default_transition": "opening",
                  "pre_actions": [{"function": {"name": "code_exec", "handler": "__function__:code_exec", "parameters": {
                      "properties": {"code": {"default": "vars['today_spoken'] = 'Monday'\nvars['p' + '1' + '_line'] = 'x'"}}}}}],
                  "transitions": [{"target_node": "opening", "condition": {"operator": "always"}}]},
        "opening": {"node_type": "conversation", "on_enter": {"type": "tts", "text": "Hello, is this {{title}} {{last_name}}?"},
                    "task_message": "Say {{p1_line}}.", "tools": [VERIFY, CLOSE],
                    "transitions": [route("end", "close_call_response.data.ok", ["true", "True"]),
                                    route("debt", "verify_identity_response.data.all_verified", ["true", "True"])]},
        "debt": {"node_type": "conversation", "on_enter": {"type": "tts", "text": "About your debt."},
                 "task_message": "", "tools": [CLOSE],
                 "transitions": [route("end", "close_call_response.data.ok", ["true", "True"])]},
        "end": {"node_type": "end_call", "transitions": []},
    },
}
RULES = {"forbidden_before_verification": ["debt"], "restricted_words": ["recorded"],
         "required_sentences": ["About your debt."]}


def errors(wf: dict, rules: dict = RULES) -> list:
    return [m for level, m in V.validate(wf, API, rules) if level == V.ERROR]


def mutate(fn) -> dict:
    wf = copy.deepcopy(CLEAN)
    fn(wf)
    return wf


class TestValidate(unittest.TestCase):
    def assertCaught(self, wf: dict, fragment: str, rules: dict = RULES) -> None:
        found = errors(wf, rules)
        self.assertTrue(any(fragment in m for m in found), f"expected an error with {fragment!r}, got {found}")

    def test_clean_workflow_passes(self):
        self.assertEqual(errors(CLEAN), [])

    def test_null(self):
        self.assertCaught(mutate(lambda w: w["nodes"]["debt"].update(task_message=None)), "is null")

    def test_missing_initial_node(self):
        self.assertCaught(mutate(lambda w: w.update(initial_node="nope")), "initial_node")

    def test_tools_on_code_node(self):
        self.assertCaught(mutate(lambda w: w["nodes"]["setup"].update(tools=[CLOSE])), "tools on a code node")

    def test_route_to_missing_node(self):
        self.assertCaught(mutate(lambda w: w["nodes"]["debt"]["transitions"].append(route("ghost", "x", ["y"]))),
                          "missing node 'ghost'")

    def test_passthrough_without_always(self):
        self.assertCaught(mutate(lambda w: w["nodes"]["setup"].update(transitions=[route("opening", "x", ["y"])])),
                          "must end with an always")

    def test_close_call_without_end_route(self):
        self.assertCaught(mutate(lambda w: w["nodes"]["debt"].update(transitions=[])), "no route on its result")

    def test_braces_in_code(self):
        def f(w):
            w["nodes"]["setup"]["pre_actions"][0]["function"]["parameters"]["properties"]["code"]["default"] = "d = {'a': {'b': 1}}"
        self.assertCaught(mutate(f), "code contains")

    def test_boolean_one_spelling(self):
        def f(w):
            w["nodes"]["opening"]["transitions"][1] = route("debt", "verify_identity_response.data.all_verified", ["true"])
        self.assertCaught(mutate(f), "one spelling only")

    def test_node_cannot_reach_end(self):
        def f(w):
            w["nodes"]["loop"] = {"node_type": "conversation", "task_message": "", "transitions": [
                {"target_node": "loop", "condition": {"operator": "always"}}]}
            w["nodes"]["opening"]["transitions"].append(route("loop", "x", ["y"]))
        self.assertCaught(mutate(f), "no path from this node")

    def test_unknown_tool_field(self):
        def f(w):
            w["nodes"]["debt"]["tools"] = [api_tool("close_call", {"customer_id": {}, "outcome": {}, "mood": {}})]
        self.assertCaught(mutate(f), "close_call.mood is not a field")

    def test_value_not_allowed(self):
        def f(w):
            w["nodes"]["debt"]["tools"] = [api_tool("close_call", {"customer_id": {}, "outcome": {"enum": ["promise", "won"]}})]
        self.assertCaught(mutate(f), "value 'won' is not allowed")

    def test_missing_required_field(self):
        self.assertCaught(mutate(lambda w: w["nodes"]["debt"].update(tools=[api_tool("close_call", {"customer_id": {}})])),
                          "missing required field 'outcome'")

    def test_unwritten_placeholder(self):
        self.assertCaught(mutate(lambda w: w["nodes"]["debt"].update(task_message="Offer {{floor_txt}}.")),
                          "{{floor_txt}} is never written")

    def test_forbidden_word_before_verification(self):
        self.assertCaught(mutate(lambda w: w["nodes"]["opening"]["on_enter"].update(text="Hello, about a debt.")),
                          "says 'debt' before identity is verified")

    def test_required_sentence_missing(self):
        self.assertCaught(mutate(lambda w: w["nodes"]["debt"]["on_enter"].update(text="Hi.")), "required sentence missing")

    def test_restricted_word_is_a_warning(self):
        wf = mutate(lambda w: w["nodes"]["opening"]["on_enter"].update(text="This call is recorded."))
        warns = [m for level, m in V.validate(wf, API, RULES) if level == V.WARN]
        self.assertTrue(any("restricted word 'recorded'" in m for m in warns), warns)


if __name__ == "__main__":
    unittest.main()
