# Builder

One command turns a bank's brief files and its tool API file into a Freya phone agent:

    python3 builder/build.py <tool_api_file> <brief_file> [<brief_file> ...]

Needs `FREYA_API_KEY`, `FREYA_BANK_TEAM_KEY` (see `env.example`) and `ANTHROPIC_API_KEY`
(or a Claude login), and `pip install claude-agent-sdk`. A brief made of several documents
(a mail, a policy, a memo, a code list) is passed as several files. Optional environment:
`BUILDER_MODEL` (default `claude-opus-5-5`), `BUILD_PRACTICE=<letter>` when the bank has practice
customers for the brief (otherwise no platform tests are run), `BUILD_BUDGET_S` (default 1500).

## What one run does
1. **Stage.** Copies the inputs, the kit files and the builder's library into a temporary folder
   outside this repository, so the run sees nothing else (no notes, no other brief's outputs).
2. **Read** (skill `read-brief`). Claude reads every line of every brief file and the tool API
   file, resolves conflicts between documents (a later memo wins over an earlier policy), and
   writes `work/rules.json` (every atomic rule with its exact quote and where the workflow
   implements it) and `work/spec.json` (the parameters, see `reference/SPEC.md`).
3. **Design** (skill `design-agent`). Generates the workflow with `reference/generate.py` from the
   spec. Where the brief has a rule the spec cannot express, Claude edits its own copy of the
   generator, never the workflow JSON.
4. **Check** (skill `check-agent`), cheapest first: `validate.py` (structure, tool fields and
   values against the tool API, placeholders, words forbidden before identity is verified,
   required sentences, the rule ledger quoted word for word), `smoke.py` (runs every code step on
   a fake account built from the tool API's response schema), the platform's dry run, then
   practice tests through `run_tests.py` only if practice customers exist.
5. **Save and export.** `freya.save_workflow(slot, ...)` (one workflow per brief, updated on reruns),
   export to `submission/<slot>.workflow.json`. If the final workflow fails the checks, the last
   one that passed is used; if none did, the workflow is generated from the spec. 25-minute budget.

Every brief value comes from the brief at run time. No rule, value, date, name or sentence from
any brief is in this folder; `tests/test_generate.py` builds an agent for an invented bank and
asserts that no practice-brief name appears in it.

## The trace
`traces/<slot>-<time>.jsonl`, one JSON object per line: `start` (time, commit, model, input
hashes), `prompt`, one `model_call` per model message (model and a one-line purpose), `test`
(every validator, smoke or practice-test command), `freya_save` / `freya_saved` (what was created
on Freya), `model_done` (turns, seconds, cost), `validate`, `end` (time, ok, workflow and agent
ids, node and tool counts, export path). Keys are scrubbed (`fak_…`, `sk-ant-…` and the values of
the key variables).

## Layout
| Path | What |
| --- | --- |
| `build.py` | the command: staging, Agent SDK run, trace, budget, fallback, save, export |
| `skills/` | `read-brief`, `design-agent`, `check-agent` (loaded into the run) |
| `reference/` | generic generator: `generate.py`, `prompts.py`, `code.py`, `hooks.py`, `SPEC.md` |
| `lib/` | calendar and date facts, workflow building blocks, identity answer cleaning |
| `validate.py`, `smoke.py` | checks without a model or platform |
| `run_tests.py` | practice tests that survive platform outages (retries, waits, stuck-cancel) |
| `PATTERNS.md` | the design rules learned from failed tests, without brief values |
| `tests/` | 74 unit tests: `python3 -m unittest discover -s builder/tests` |
