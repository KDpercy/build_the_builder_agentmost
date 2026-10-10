# PLAN (rewritten for kit version 3)

## 1. Strategy

The kit ships a working builder: Claude, run through the Claude Agent SDK
with one short skill, reads the brief, writes the workflow, tests it and fixes
it. Freya says it reached 10 of 10 on Brief A in one run. We start from that
builder and make it better in three ways, in this order:

1. Reliable: the same agent passes three runs out of three, with customers
   who talk in pieces, correct themselves, ramble, ask back and use words for
   numbers, and with up to three products.
2. Brief-agnostic: it reads a brief it has never seen, including one that is
   raw material with a memo that overrides an earlier document.
3. Compliant and safe: one command, under 30 minutes, a clean trace, and it
   never ends without a valid agent.

We do that by growing the skill into a few skills plus a small tested helper
library and a validator. We do not build a rigid brief-to-workflow compiler:
a fixed schema breaks on the first rule kind it did not foresee.

Lessons from the paper Freya took the format from (arXiv 2609.04611), where
the best coding agent passed 23.9% and experts 82.2%:
- Agents search the records by keyword instead of reading them. Read every
  line of every brief file.
- They ship the first design that runs. Compare designs on score.
- Deterministic guards around the model beat raw model output.
- They validate with tests that cannot fail. A test must be able to fail.
- They never ask the client. We have none, so every gap is logged, not guessed.

## 2. How we are scored

- Final: 2 briefs x 30 customers, each run 3 times; a customer counts only if
  all 3 runs pass. No partial credit.
- A run passes when the bank's records are exactly right, the conversation
  stayed inside the brief (a judge model reads the transcript) and the agent
  told the truth about what was recorded.
- The bank does not enforce the brief. A promise on a holiday is recorded.
- Ties: total promised amount on passed customers, then shorter build time,
  then earlier submission.
- Top ten: Freya reruns the builder from our commit and compares. A reviewer
  agent reads every trace against the code.
- Mechanics of the checks: dev/KIT_NOTES.md section 2.

## 3. Target workflow shape

Freya's docs describe a builder whose 6-node workflow passed its practice
cases, and the patterns it used. That is our starting shape. The brief decides
the real nodes; compare this against a simpler variant on score.

1. `setup`: code node, first. Computes date facts from `now` and the brief's
   calendar: today, business days ahead, each band's deadline, the dates the
   persuasion rules need, the callback window. Writes them as text variables.
2. `greeting`: fixed opening line taken from the brief. Finds out who is on
   the line. Forks on an extracted enum, not on competing intents.
3. `someone_else`: only the tools the brief allows there.
4. `identity`: the verification tool with a post-hook that turns the bank's
   reply into a plain `what_to_do_next` line. Routes on the bank's reply:
   verified, or no wrong answers left.
5. `load_account`: api_request node, so the account call cannot be skipped or
   made early. Then a code node that computes, per product: band, deadline,
   floor, attempts allowed, the spoken product name. Text facts for prompts.
6. `collect`: the negotiation. The model talks; dates and amounts come from
   the computed facts. The promise tool has hooks that say what to do next.
7. Closing: one close per call, last, with outcome and reason. Then an
   `end_call` node.

Rules for every generated workflow:
- A tool exists only in the nodes where the brief allows it.
- Routes use bank replies and variables written by our code. Model judgement
  only where nothing else can decide.
- Arithmetic, dates and counting happen in code. The model gets finished facts.
- Hard rules and required sentences are copied word for word from the brief.
- Nothing about the account in any prompt the model sees before verification.
- Every tool result tells the model what to do next. No silent turns.
- Every path sets an outcome and reaches an `end_call` node.

## 4. Builder architecture

    builder/build.py <tool_api_file> <brief_file>...
      1. start trace, start 25-minute budget
      2. run the agent (Claude Agent SDK) with our skills:
           read-brief      every file, every line -> out/<slot>/rules.json
           design-agent    rules + tool API -> out/<slot>/workflow.json,
                           assembled from builder/lib/ building blocks
           check-agent     validator, local code tests, dry run, then
                           platform tests only if they exist for this brief
      3. save with freya.save_workflow(slot, ...), export to submission/
      4. finish trace: end time, ids, node and tool counts, tests, scrub keys
      fallback: if anything fails or time runs out, keep the last workflow
      that passed the validator. Never exit without a saved agent.

`rules.json` is the rule ledger: every atomic rule of the brief with its exact
quote, and where the workflow implements it (node, prompt line, route, code).
For raw material it also lists each conflict and which document wins and why.
The validator fails the build if a rule has no implementation or a quote is
not found word for word in the brief files.

`builder/lib/` holds generic, unit-tested generators: the calendar and
deadline code for a code node (parameters come from rules.json), hook
templates, node skeletons, the closing pattern. No brief values in it.

`builder/validate.py` checks a workflow without a model: no nulls; tools only
on conversation nodes; passthrough nodes end with `always`; no `{{` or `}}` in
code; booleans tested in both spellings; every path reaches an end node; every
tool field and allowed value exists in the given tool API file; no forbidden
pre-verification word in any prompt or entry line before the gate; every
required sentence present; every rule in the ledger implemented.

Isolation: a builder run must not see dev/ or another brief's outputs. Check
how the Agent SDK loads project settings and skills, and keep the run's view
clean. Final runs use no cache.

## 5. Phases (Madrid time)

Phase 0, Sat 13:30-14:30, mostly my own terminal: setup and three baselines.
  a. env.sh, git, private GitHub repo.
  b. Save examples/base-agent.json and score it on Brief A. Note the Freya
     credit before and after: that is the price of a test run.
  c. Run the example builder on Brief A. Note its score, minutes and cost.
  d. Score that agent again with `--reps 3` and once with `--style pieces`.
  Result: real numbers for what the starting builder does and what it costs.

Phase 1, Sat 14:30-19:00: a reliable agent for Brief A, by hand, to learn.
  Work on the workflow file the example builder wrote. Fix one failing family
  at a time, cheapest test first. Every fix is written down in
  builder/PATTERNS.md as a generic pattern with no brief values. This agent
  is never submitted; it is how we learn what the builder must know.

Phase 2, Sat 19:00-24:00: Brief B and the styles. Three runs of three on all
  13 practice customers, then each style.

Phase 3, Sun 09:00-14:00: put the patterns into the builder: skills,
  builder/lib/, validate.py, build.py with trace, time budget and fallback.
  Rebuild Brief A and B from scratch with it and compare with the hand agent.

Phase 4, Sun 14:00-16:00: generalisation. Two variant briefs of our own (see
  dev/STRESS_CASES.md), one written as raw material. No bank customers exist
  for them, so judge the output with the validator, local code tests and by
  reading the rule ledger against the variant.

Phase 5, Sun 16:00-17:00: full rehearsal of section 7 on Brief A and B. Freeze.

If we are behind on Sunday at 12:00: stop adding nodes. A better skill on top
of the kit's builder, with the validator and the trace, is a valid entry.

## 6. Sub-agents (only for tasks that need no platform time)

A. Calendar and deadline generator in builder/lib/ with unit tests: weekends,
   holidays, month end, a holiday after a weekend, a deadline on a holiday,
   "this" and "next" weekday, every band edge, several values of `now`.
B. validate.py with one failing fixture per check.
C. Variant briefs with their tool API files and hand-written rule ledgers.

Each gets a five-line brief: goal, files it may touch, inputs, the test that
proves it is done, and "read dev/KIT_NOTES.md only".

## 7. Sunday runbook

1. 16:00 rehearsal on Brief A and B: build, export, trace, submission form.
2. 17:00 freeze. Commit. Note the commit hash. Check the builder model's
   credit covers at least four full builder runs.
3. 19:00 final briefs arrive. Save them under briefs/ exactly as sent.
4. In the builder terminal, for each brief: `source env.sh`, then
   `python3 builder/build.py <its tool API file> <its brief file(s)>`.
   Final runs use no cache.
5. Export with `freya.export_workflow(workflow_id, "<brief>.workflow.json")`
   into submission/. Change nothing in the Freya editor.
6. If a bug must be fixed: fix, commit, rerun BOTH briefs from the new commit
   so commit, workflows and traces match. Nothing from a final brief goes
   into builder code, skills or prompts.
7. Scrub traces for keys. Commit submission/ and traces/.
8. Follow the submission steps Freya emails before 19:00. Send by 21:00.

## 8. Questions

For Freya (reply to the kit email from dev@freyavoice.ai):
1. During the final three hours, will the bank have practice customers for
   the final briefs, so a builder can test the agent it built?
2. When you rerun a top-ten builder that uses the Claude Agent SDK, do you
   supply the model credentials, and which model do you expect?

To measure ourselves: see dev/KIT_NOTES.md section 8.
