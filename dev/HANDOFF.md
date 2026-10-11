# HANDOFF

Rewrite this file at the end of every session. Keep it under 40 lines.

## MORNING REPORT (Sun 11 Oct, written ~00:55)
- Our builder works end to end. Run 1 (Brief A): 7.5 min, $0.79, its own test 10/10.
  Run 2 (raw-material variant V1, no practice customers): 2.7 min, $0.81, spec matches the
  answer key, both memo overrides applied. Total builder spend tonight $1.60.
- Reference agents (generic code from a spec): A 9/10 (the 1 fail was a judge glitch),
  B 3/3, PUB-06/PUB-10 3/3 each. 69 unit tests green. No practice-brief names in builder code.
- (RESOLVED 09:55: Kerem stopped it on the Simulation page of the web app. A stuck
  simulation can be stopped there.) WAS BLOCKER: Freya simulation ba5fc132 stuck in 'running' since 00:06; every new simulation is
  refused. Ask Freya (dev@freyavoice.ai) to clear it. The waiting client was stopped at 00:55
  (no polling overnight). When clear, run Brief A on the run-1 agent:
  source env.sh && python3 tools/run_cases.py 1e3ff1a8-4477-4b94-a6e5-54054a299c0a --brief A --reps 3 --out results/rehearsal-a-reps3.json
- First thing today: if unblocked, `--reps 3` on rehearsal-a; then a builder run on Brief B
  (BUILD_PRACTICE=B); then Phase 5 rehearsal (section 7 of PLAN). GitHub remote still missing.

## Sunday log
- 09:55 rehearsal-a (builder run 1, Brief A) --reps 3: 9/10. Only PUB-10 1/3: its opening said
  "this call is recorded" (fixed in the validator after run 1). Ledger right in all 30 calls.
- 10:11 BUILDER RUN 3: Brief B ONLY (my mistake: Brief B says "every rule of Brief A applies").
  3.7 min, $0.52, 1/3. The builder did not guess Brief A's values: listed them as gaps and
  refused to tune to test answers. Correct command for B passes both files:
  python3 builder/build.py tools/openapi.json briefs/brief-a.md briefs/brief-b.md
- 11:12 BUILDER RUN 5 (Brief A, all fixes): 17 min, $1.04. Self-test 9/10 twice; fixed a missing
  sympathy line itself; PUB-04 once recorded 20 Oct instead of the deadline -> after-deadline
  offers now name the exact date and a yes agrees it (generic fix in date_facts/code).
- 11:13 BUILDER RUN 6 on variant V2 (rules the generator could not express): 3.8 min, $1.01.
  58 rules; edited its own generator copy for the split-payment link case and the special
  closing order; validator, smoke and dry run clean; opening paraphrased plainly.
- Parallel work: calendar-day deadlines, % floors, mark_agreed tool (agreements in variables,
  read-back from them), notes-before-close guidance, run_tests.py (outage-tolerant), RUNBOOK.md.
- 11:10 GitHub repo created and pushed: github.com/KDpercy/build_the_builder_agentmost (private).
- 10:16 BUILDER RUN 4: Brief A + B files, BUILD_PRACTICE=B, slot ref-b: 11 min, $0.92, valid,
  51 rules, but its test hit a Freya 504 -> simulation f9473ed6 stuck again (needs a stop in
  the web app). Untested. Its opening paraphrase "this call is being taped" is weak -> read-brief
  now asks for a plain paraphrase close to the original.

## Overnight log
- 23:50 reference retests: PUB-06 3/3; ref-a full 9/10 (PUB-01 judge 'no verdict', ledger ok);
  ref-b full 3/3; PUB-12 2/3 -> read-back now finds agreements by their "Noted" line.
- 23:50 BUILDER RUN 1 (build.py, Brief A, slot rehearsal-a): 7.5 min, 25 turns, $0.79, its own
  test 10/10, agent 1e3ff1a8, trace traces/rehearsal-a-20261010-235028.jsonl (no keys).
  Found: (a) it read Claude's project memory because the stage was inside the repo -> stage now
  in a temp dir outside the repo (56ee245); (b) it started its test with nohup & -> forbidden;
  (c) its opening said "this call is recorded" -> validator now errors on success-claim words
  spoken before verification (231136c).
- 00:06 Freya simulation ba5fc132 stuck in 'running' -> every new simulation refused ("another
  simulation is running"). No documented way to stop it. Platform tests paused; a client keeps
  retrying every 30 s (rehearsal-a Brief A run). ASK FREYA in the morning if still stuck.
- Phase 4 started: variant V1 (dev/variants/v1: mail + policy + memo overriding 2 points + code
  list, own tool API with renamed fields/codes/call variables) and its answer-key spec. Writing
  it found builder assumptions -> fixed: `now` and `customer_id` names, form of address,
  practice-brief names as code defaults (7eaf509).
- 00:44 BUILDER RUN 2 on V1 (no practice customers, BUILD_PRACTICE unset): 2.7 min, 29 turns,
  $0.81. Spec matches the answer key on every key value; both memo overrides applied and
  logged as conflicts; 53 ledger rules; 4 sensible gaps. build.py's final gate wrongly
  rejected it (my bug: ignored the brief's call variables) -> fixed, finished by hand (logged
  in the trace as manual_finish), saved to slot ref-b.

## Agents on Freya (slot: agent id)
- brief-a: 41e5caa1 (hand A, dev/hand/build_a.py)    brief-b: ffcb39ae (hand B, dev/hand/build_b.py)
- ref-a: cbc21b5c (reference from dev/specs/brief-a.spec.json)
- ref-b: 7ca97613 (now holds builder run 2's V1 agent; regenerate ref-b from its spec if needed)
- rehearsal-a: 1e3ff1a8 (builder run 1)        base: cb38a9f1 (kit example)

## Failing customers and what we think causes them
| Case | Family | Symptom | Suspected cause |
| --- | --- | --- | --- |
| A PUB-08 talk | Paid | customer hung up right after a correct re-ask | simulator side |
| A PUB-09 talk | Restr. | silent after user sent '"' | fixed by rule E (always reply) |

## Patterns learned (builder/PATTERNS.md has 6, with evidence)
- Counted rules -> routes + fixed lines; new routes yield to outranking rules; no
  restricted words in spoken lines; cap retries; fragments are not answers.

## Decisions made (do not reopen without a reason)
- Move dev/ out of the kit folder during any builder run.
- build_a/b and hooks_a/b are hand agents only, never the shipped builder (Brief values).
- Final briefs stay collections (README l.71-72). Variant briefs wait for Phase 4.
- Opening says "a recording of this call is kept" (Kerem, 10 Oct).
- Claude runs tests and builder runs itself (key only in a subshell); one sim at a time.

## Budgets
- Freya: ~0.16 credits per 10-customer run; ~95 left.
- Builder model: example builder A $2.09 / 15 min; B $3.26 / 22 min. Kerem added ~$10.
  Our builder: run 1 (A) $0.79; run 2 (V1) $0.81; run 3 (B only) $0.52; run 4 (A+B) $0.92;
  run 5 (A) $1.04; run 6 (V2) $1.01. Total ~$5.09 of ~$10.
- 10 Oct ~17:30: bank mock gave Cloudflare 403/1010 to Python; Freya fixed it.
- 10 Oct 22:02: Freya API 503 'API key validation temporarily unavailable' for ~1 min.
