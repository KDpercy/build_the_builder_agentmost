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
        self.assertEqual(B.slot_name(["/x/Final Brief 1.md"]), "final-brief-1")
        self.assertEqual(B.slot_name(["a/mail.txt", "a/Memo (v2).md"]), "mail-memo-v2")

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
        finally:
            shutil.rmtree(B.ROOT / "out" / "unit-test-slot")

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


if __name__ == "__main__":
    unittest.main()
