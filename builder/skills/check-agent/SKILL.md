---
name: check-agent
description: Check the generated workflow, cheapest test first, and keep the last version that passed. Use after design-agent and after every change.
---

# Check the agent

Cheapest first. A check must be able to fail. Stop testing when the time limit is near.

1. Validator (no model, no platform):
       python3 builder/validate.py work/workflow.json input/<tool api file> work/validate-rules.json
   Write work/validate-rules.json from spec.json first:
       {"forbidden_before_verification": [...], "restricted_words": [...], "required_sentences": [...],
        "call_variables": [every variable the brief says a call starts with]}
   Also check the ledger: every rule in work/rules.json quotes the brief word for word and
   has `implemented_by` filled:
       python3 -c "import json,sys; sys.path.insert(0,'builder'); import validate as V; \
         print(V.check_ledger(json.load(open('work/rules.json')), {p.name: p.read_text() for p in __import__('pathlib').Path('input').glob('*') if p.suffix != '.json'}))"
   Fix every ERROR. When there are none, copy work/workflow.json to work/good.workflow.json.
2. Code steps: run each generated code source locally with `vars = {"now": ...}` for several
   dates (a weekday, a Friday, a day before a holiday, after the last call hour) and check the
   facts against the brief by hand.
3. Platform dry run:
       python3 -c "import freya,json; print(freya.validate_workflow('<slot>', json.load(open('work/workflow.json'))))"
4. Platform tests, only if the bank has practice customers for this brief:
       python3 -c "import freya,json; print(freya.save_workflow('<slot>', json.load(open('work/workflow.json'))))"
       python3 tools/run_cases.py <agent_id> --brief <letter> --out work/run.json
   Read each FAIL line; read the call with freya.get_call(call_id) before changing anything.
   Run in the foreground and wait: never nohup, & or a background job. One simulation at a time.
5. Fix and retest, at most three rounds, while time allows:
   - If the failure comes from your spec or your generator copy (a value read wrongly, a rule
     the workflow does not enforce), fix it there, regenerate, repeat steps 1 and 3, save, and
     rerun only the failing cases with `--only <ids>`.
   - If it comes from information the inputs do not contain, do not guess and never copy a
     value from the expected test answers: record it in `gaps` and stop.
   - Keep the version that passed more cases; never leave a worse workflow than before.

Always leave work/good.workflow.json as the last version that passed step 1.
