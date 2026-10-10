# HANDOFF

Rewrite this file at the end of every session. Keep it under 40 lines.

## MORNING REPORT (Sun 11 Oct, written ~00:55)
- Our builder works end to end. Run 1 (Brief A): 7.5 min, $0.79, its own test 10/10.
  Run 2 (raw-material variant V1, no practice customers): 2.7 min, $0.81, spec matches the
  answer key, both memo overrides applied. Total builder spend tonight $1.60.
- Reference agents (generic code from a spec): A 9/10 (the 1 fail was a judge glitch),
  B 3/3, PUB-06/PUB-10 3/3 each. 69 unit tests green. No practice-brief names in builder code.
- BLOCKER: Freya simulation ba5fc132 stuck in 'running' since 00:06; every new simulation is
  refused. Ask Freya (dev@freyavoice.ai) to clear it. A client is still waiting and will run
  Brief A on the run-1 agent (rehearsal-a, 1e3ff1a8) by itself once it clears
  -> results/rehearsal-a-run2.json.
- First thing today: if unblocked, `--reps 3` on rehearsal-a; then a builder run on Brief B
  (BUILD_PRACTICE=B); then Phase 5 rehearsal (section 7 of PLAN). GitHub remote still missing.

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
  Our builder: run 1 (A) $0.79 / 7.5 min; run 2 (V1) $0.81 / 2.7 min.
- 10 Oct ~17:30: bank mock gave Cloudflare 403/1010 to Python; Freya fixed it.
- 10 Oct 22:02: Freya API 503 'API key validation temporarily unavailable' for ~1 min.
