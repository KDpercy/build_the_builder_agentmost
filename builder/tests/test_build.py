"""build.py without the model: slot names, staging isolation, trace scrubbing, fallback choice."""
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import build as B  # noqa: E402

GOOD = {"initial_node": "a", "system_prompt": "", "nodes": {
    "a": {"node_type": "conversation", "task_message": "", "transitions": [{"target_node": "end", "condition": {"operator": "always"}}]},
    "end": {"node_type": "end_call", "transitions": []}}}


class TestBuild(unittest.TestCase):
    def test_slot_name(self):
        self.assertEqual(B.slot_name(["/x/briefs/Final Brief 1.md"]), "final-brief-1")
        self.assertEqual(B.slot_name(["/x/briefs/a/mail.txt", "/x/briefs/a/Memo (v2).md"]), "a-mail-memo-v2")

    def test_same_file_names_in_two_folders_get_two_slots(self):
        one = B.slot_name(["/x/briefs/final1/brief.md"])
        two = B.slot_name(["/x/briefs/final2/brief.md"])
        self.assertNotEqual(one, two)
        self.assertEqual(one, "final1-brief")

    def test_practice_option(self):
        with tempfile.TemporaryDirectory() as d:
            cases = pathlib.Path(d) / "final-cases.json"
            cases.write_text("[]")
            self.assertIsNone(B.practice_args(""))
            self.assertEqual(B.practice_args("C"), "--brief C")
            self.assertEqual(B.practice_args(str(cases)), "--cases input/practice-cases.json")
            with self.assertRaises(SystemExit):
                B.practice_args(str(pathlib.Path(d) / "missing.json"))
            os.environ["BUILD_PRACTICE"] = str(cases)
            try:
                text = B.prompt_for("s", "api.json", ["b.md"], 0)
                st = B.stage("s", cases, [str(cases)])
                self.assertTrue((st / "input" / "practice-cases.json").exists())
            finally:
                del os.environ["BUILD_PRACTICE"]
            self.assertIn("run_tests.py <agent_id> --cases input/practice-cases.json", text)
            self.assertIn("NO practice customers", B.prompt_for("s", "api.json", ["b.md"], 0))

    def test_case_folder_is_accepted_by_main(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ)
            os.environ.pop("BUILD_TOOL_BASE_URL", None)
            try:
                with self.assertRaises(SystemExit) as e:      # passes the argument check, then needs the base URL
                    B.main(["build.py", d])
                self.assertIn("BUILD_TOOL_BASE_URL", str(e.exception))
            finally:
                os.environ.clear(); os.environ.update(env)

    def test_every_script_the_skills_name_is_staged(self):
        import re
        named = set()
        for skill in (B.ROOT / "builder" / "skills").rglob("SKILL.md"):
            named |= set(re.findall(r"builder/[\w/]+\.py", skill.read_text()))
        staged = lambda p: any(p == f or p.startswith(f + "/") for f in B.BUILDER_FILES)
        self.assertEqual(sorted(p for p in named if not staged(p)), [])

    def test_trace_scrubs_keys(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["FREYA_BANK_TEAM_KEY"] = "team-secret-123456"
            t = B.Trace(pathlib.Path(d) / "t.jsonl")
            t.log("x", a="fak_abcDEF123 and sk-ant-api03-xyz and team-secret-123456")
            t.close()
            text = (pathlib.Path(d) / "t.jsonl").read_text()
            for secret in ("fak_abc", "sk-ant-api03", "team-secret-123456"):
                self.assertNotIn(secret, text)

    def test_stage_excludes_dev_and_results(self):
        brief = B.ROOT / "briefs" / "brief-a.md"
        api = B.ROOT / "tools" / "openapi.json"
        st = B.stage("unit-test-slot", api, [str(brief)])
        try:
            self.assertTrue((st / "input" / "brief-a.md").exists())
            self.assertTrue((st / "freya.py").exists())
            self.assertTrue((st / "builder" / "validate.py").exists())
            self.assertTrue((st / "results").is_dir())
            self.assertFalse(any((st / "results").iterdir()))       # empty: no earlier scores
            for hidden in ("dev", "out", "briefs", "submission", "traces"):
                self.assertFalse((st / hidden).exists(), hidden)
            self.assertTrue((st / ".freya-agents.json").is_symlink())
            self.assertFalse(str(st).startswith(str(B.ROOT)), "stage must be outside the repository")
        finally:
            shutil.rmtree(st.parent)

    def test_pick_workflow_falls_back_to_last_good(self):
        with tempfile.TemporaryDirectory() as d:
            st = pathlib.Path(d)
            (st / "work").mkdir()
            broken = dict(GOOD, initial_node="missing")
            (st / "work" / "workflow.json").write_text(json.dumps(broken))
            (st / "work" / "good.workflow.json").write_text(json.dumps(GOOD))
            t = B.Trace(st / "t.jsonl")
            self.assertEqual(B.pick_workflow(st, {"paths": {}}, t), GOOD)
            (st / "work" / "good.workflow.json").unlink()
            self.assertIsNone(B.pick_workflow(st, {"paths": {}}, t))
            t.close()


class TestFallback(unittest.TestCase):
    def test_generates_from_spec_when_no_workflow_is_valid(self):
        sys.path.insert(0, str(B.ROOT / "builder"))
        from tests.test_generate import API, SPEC
        with tempfile.TemporaryDirectory() as d:
            st = pathlib.Path(d)
            (st / "work").mkdir()
            (st / "input").mkdir()
            shutil.copytree(B.ROOT / "builder", st / "builder", ignore=shutil.ignore_patterns("__pycache__"))
            (st / "input" / "api.json").write_text(json.dumps(API))
            (st / "work" / "spec.json").write_text(json.dumps(SPEC))
            t = B.Trace(st / "t.jsonl")
            B.generate_from_spec(st, st / "input" / "api.json", t)
            (st / "work" / "validate-rules.json").write_text(json.dumps({"call_variables": ["client_ref", "honorific", "family_name", "stamp"]}))
            self.assertIsNotNone(B.pick_workflow(st, API, t))
            t.close()


class TestRunTests(unittest.TestCase):
    def test_watchdog_picks_only_running_simulations_that_stopped_moving(self):
        import run_tests as R
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        ago = lambda m: (now - datetime.timedelta(minutes=m)).isoformat()
        sims = [{"id": "fresh", "status": "running", "updatedAt": ago(3)},
                {"id": "hung", "status": "running", "updatedAt": ago(R.STUCK_S / 60 + 1)},
                {"id": "old-done", "status": "completed", "updatedAt": ago(90)}]
        self.assertEqual([s["id"] for s in R.stuck(sims)], ["hung"])

    def test_freya_retries_only_reads_and_cancels(self):
        import run_tests as R
        R.PAUSE_S = 0
        calls = []

        def api(method, path, *a, **k):
            calls.append(method)
            raise RuntimeError(f"{method} {path} -> 504: error code: 504")
        safe = R.freya_retry(api)
        for method, path, tries in (("GET", "/api/v2/simulations", 3), ("POST", "/api/v2/simulations/x/cancel", 3),
                                    ("POST", "/api/v2/simulations", 1)):
            calls.clear()
            with self.assertRaises(RuntimeError):
                safe(method, path)
            self.assertEqual(len(calls), tries, (method, path))

    def test_retry_on_platform_errors_only(self):
        import run_tests as R
        R.PAUSE_S = 0
        calls = []

        def flaky(n):
            calls.append(n)
            if len(calls) < 3:
                raise RuntimeError("GET /x -> 504: error code: 504")
            return "ok"
        self.assertEqual(R.with_retry(flaky)(1), "ok")
        self.assertEqual(len(calls), 3)

        def broken():
            raise RuntimeError("POST /y -> 400: bad request")
        with self.assertRaises(RuntimeError):
            R.with_retry(broken)()

    def test_age_of_a_timestamp(self):
        import run_tests as R
        self.assertGreater(R.age_s("2020-01-01T00:00:00.000Z"), 3600)


class TestFinalRules(unittest.TestCase):
    def test_call_variables_come_from_the_runs_rules_and_spec(self):
        with tempfile.TemporaryDirectory() as d:
            st = pathlib.Path(d)
            (st / "work").mkdir()
            (st / "work" / "validate-rules.json").write_text(json.dumps({"call_variables": ["a"], "required_sentences": ["x"]}))
            (st / "work" / "spec.json").write_text(json.dumps({"customer_variable": "b", "now_variable": "c",
                                                               "address_as": "{{d}} {{e}}", "opening": {"ask": "Is it {{f}}?"}}))
            r = B.final_rules(st)
            self.assertEqual(r["call_variables"], ["a", "b", "c", "d", "e", "f"])
            self.assertEqual(r["required_sentences"], ["x"])


if __name__ == "__main__":
    unittest.main()
