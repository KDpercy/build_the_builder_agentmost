# HANDOFF

Rewrite this file at the end of every session. Keep it under 40 lines.

## NOW (Sun 11 Oct ~12:10) - read this first after a compaction
- FROZEN 11 Oct ~15:20 Madrid at the commit "chore: freeze" (git log). After this: bug fixes only.
- Final briefs at 19:00 Madrid (17:00 UTC per RULES); our freeze 16:00 Madrid (= 17:00 Istanbul), code changes stop 15:30. Runbook: dev/RUNBOOK.md. Repo pushed to
  github.com/KDpercy/build_the_builder_agentmost (git push works from Claude's shell).
- Builder works end to end (builder/README.md). Last runs: A (run 5) 9/10 self-test, $1.04;
  V2 variant (unforeseen rules) handled by editing its generator copy, $1.01. Spend ~$5.09/10.
- Freya API DOWN since ~11:36 (504 on everything). An old wrapper (pid 7259, started 11:36,
  measuring reference A --reps 3) is still waiting: do NOT kill it (tip 3).
- Step 1 still to do when Freya is back: measure ref-a (agent cbc21b5c) --reps 3 and ref-b
  (7ca97613) --reps 3 + dev/cases/b-set1/2.json, via `python3 builder/run_tests.py ...`.
  Both were regenerated from dev/specs with all fixes (versions 10 and 13).
- Rehearsal builds done 12:15-12:27 (see log). Freeze 16:00 Madrid.
- Platform tips adopted (dev/KIT_NOTES.md): retry 5xx, never kill run_cases, cancel stuck
  simulations via POST /api/v2/simulations/{id}/cancel, outage != agent bug.
- Anthropic key: $9.53 at 12:07 (topped up; ~$1 per build = room for rehearsal + finals + reruns).
- Kerem to do: ask Freya about practice customers for the
  final briefs and who supplies model credentials on their rerun.

## Sunday log
- 14:55-15:12 CASES-FILE BUILD (rehearsal1, BUILD_PRACTICE=dev/cases/a-set1.json): 17 min, $0.85.
  Freya back. Practice 3/5 -> builder fixed its generator copy (who-is-on-the-line asked 3-4x,
  "another time" asked twice) -> 5/5. Fix ported to builder/reference with spec-counted limits
  (543b78f). Key now ~$6.05.
- 15:19-15:26 frozen-commit check: plain build of A at 9b33faa (BUILD_SLOT=frozen-check, 2.4 min,
  $0.68) scored on dev/cases/a-set1.json: 5/5 (PUB-01, PUB-02 included). Key now ~$5.40.
- 15:20 FREEZE (see top). submission/ emptied (rehearsal exports in out/rehearsal-exports/).
- 12:50-14:40 Freya mostly down (504/500/503, calls hanging). Measurements: ref-A rep1 8/9 judge-pass
  (10th never ran), rep2 hung -> no score; rehearsal1 scoring: no simulation could be created; ref-B
  reps3 failed on 503; B set1 0/3 = outage (0 s turns, no verdict); B set2 2/3: PUB-12, PUB-13 pass,
  PUB-11 = platform retried the call (ledger has a complete first attempt, transcript only the
  retry, 58 s turn, customer hung up). No agent bug found in any run today.
  Fixes from it: run_tests watchdog cancels hung simulations mid-run (4f8674a); Freya POSTs that
  create something are never retried (a9e6f1e). No duplicate simulations were created.
- Cases-file build (BUILD_PRACTICE=<file>.json) never ran on the platform (Freya down); unit-tested.
- 12:15-12:27 rehearsal (no BUILD_PRACTICE, final-day commands, dev/check_build.sh): r1 A 3 min $0.74,
  r2 A+B 2.5 min $0.69, r3 V1 4 docs $0.52 -> found hardship `line` without the required sympathy
  sentence (fixed lines are spoken verbatim); fixed in read-brief + SPEC.md (ea5d33e), r3 rerun $0.70: ok.
  Also fixed: slot now includes the brief folder (final1/brief.md vs final2/brief.md), BUILD_PRACTICE
  takes a cases file. Rehearsal spend $2.65 -> key ~$6.90.
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
