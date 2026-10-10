"""Node and tool building blocks: tool shapes follow the tool API file, and a small workflow
assembled from them passes the validator."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import validate as V  # noqa: E402
from lib import nodes as N  # noqa: E402

SPEC = {"servers": [{"url": "https://bank.example/v9/"}], "paths": {
    "/check_member": {"post": {"requestBody": {"content": {"application/json": {"schema": {
        "properties": {"member_ref": {"type": "string"}, "kind": {"type": "string", "enum": ["postcode", "birth_year"]},
                       "value": {"type": "string"}},
        "required": ["member_ref", "kind", "value"]}}}}}},
    "/end_contact": {"post": {"requestBody": {"content": {"application/json": {"schema": {
        "properties": {"member_ref": {"type": "string"}, "result": {"type": "string", "enum": ["done", "failed"]}},
        "required": ["member_ref", "result"]}}}}}},
}}


class TestNodes(unittest.TestCase):
    def setUp(self):
        self.api = N.api_spec_tools(SPEC)

    def test_tool_url_and_fields_come_from_the_api_file(self):
        t = N.api_tool(self.api, "check_member", "Checks one answer.", baked={"member_ref": "{{member_ref}}"})
        params = t["function"]["parameters"]["properties"]
        self.assertEqual(params["url"]["default"], "https://bank.example/v9/check_member")
        body = params["body"]
        self.assertEqual(sorted(body["properties"]), ["kind", "member_ref", "value"])
        self.assertEqual(body["required"], ["member_ref", "kind", "value"])
        self.assertEqual(body["properties"]["kind"]["enum"], ["postcode", "birth_year"])
        self.assertEqual(body["properties"]["member_ref"]["default"], "{{member_ref}}")

    def test_model_filled_placeholders_cannot_collide_with_variables(self):
        t = N.api_tool(self.api, "check_member", "x")
        body = t["function"]["parameters"]["properties"]["body"]["properties"]
        self.assertEqual(body["value"]["default"], "{{check_member_value}}")

    def test_unless_route_shape(self):
        r = N.unless("floor", "d", {"variable": "too_much", "operator": "equals", "operand": "yes"}, "special", ["a", "b"])
        groups = r["condition"]["conditions"]
        self.assertEqual(groups[0]["conditions"][1]["operator"], "is_not_set")
        self.assertEqual([c["operand"] for c in groups[1]["conditions"][1:]], ["a", "b"])

    def test_code_node_rejects_double_braces(self):
        with self.assertRaises(AssertionError):
            N.code_node("bad", "x = {'a': {'b': 1}}", [N.always("next")])

    def test_assembled_workflow_passes_the_validator(self):
        close = N.api_tool(self.api, "end_contact", "Ends the contact. CALL it last.", baked={"member_ref": "{{member_ref}}"})
        check = N.api_tool(self.api, "check_member", "Checks one answer.", baked={"member_ref": "{{member_ref}}"})
        wf = {
            "initial_node": "setup",
            "system_prompt": "Be brief.",
            "nodes": {
                "setup": N.code_node("setup", "vars['greeting'] = 'Hello'", [N.always("talk")]),
                "talk": N.conversation("talk", "Greet with {{greeting}}.", [check, close],
                                       [N.tool_ok("end", "end_contact"), N.failed_more_than("talk_down", "check_member", 1)],
                                       N.says("Hello.")),
                "talk_down": N.conversation("talk_down", "Apologise and end.", [close], [N.tool_ok("end", "end_contact")],
                                            {"type": "llm"}),
                "end": N.end_node(),
            },
            "test_variables": {"member_ref": "m1"},
        }
        problems = [p for p in V.validate(wf, SPEC, {}) if p[0] == V.ERROR]
        self.assertEqual(problems, [], json.dumps(problems))


if __name__ == "__main__":
    unittest.main()
