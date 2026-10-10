# HANDOFF

Rewrite this file at the end of every session. Keep it under 40 lines.

## Where we are
- Phase: 2 started. Example builder on Brief B (it saw builder/ + PATTERNS.md): agent
  ffcb39ae-6222-4dfd-8d40-eaa0aab74316, wf d4076f50; runs B: 3/3, then reps3 2/3, 2/3, 3/3.
  22 min, 35 turns, $3.26, trace traces/20261010-193830.jsonl (no keys). build_b.py
  imports build_a/hooks_a: a change to A changes B.
- (Phase 1 history) fix 1 saved v5: PUB-06 3/3, full reps3 9/10 but PUB-05 0/3 (floor offered
  to hardship). Fix 1b (hardship guard) saved, commit bbc7086: PUB-05 3/3, PUB-06 3/3.
  Full reps3 after 1b: 9/10 (runs 10,10,9), only PUB-10 2/3 on the opening 'recorded'.
  Pre-fix workflow copy: scratchpad brief-a.before-fix1.json (regenerate via git if lost).
- Commit: bcbb66f (kit + dev notes). No GitHub remote yet (brew can't build gh on
  macOS 13; use the gh .pkg from github.com/cli/cli/releases).
- Hand agent: slot brief-a, agent 41e5caa1-7cb6-4984-b177-b9ccc19bff1b, source
  builder/build_a.py + hooks_a.py -> out/brief-a.workflow.json (Brief A values inside).
- Scores (A): base 0/10 | example builder 9,9,9,10 (15 min, $2.09) | reps3 8/10
  (PUB-06, PUB-10) | pieces 4/10, but PUB-01,07,08,09,10 hit `snekbox` outage; rerun
  `--style pieces --only PUB-01,PUB-07,PUB-08,PUB-09,PUB-10` -> results/brief-a-pieces-rerun.json

## Next step (one, concrete)
- Fixes 2+3 saved (v7, b563f22): full reps3 9/10 (10,10,9), PUB-10 now 3/3; PUB-09 1 fail:
  floor offered to a restructuring request. Fix 1c (special_case guard) saved, 150b060: PUB-05,06,08,09 all 3/3 (floor line only
  in PUB-06). Full reps3 after 1c: 10/10. Styles (1 run each): pieces 10, corrects 10, asks_back 10,
  in_words 10, talkative 7 (PUB-01,03,05; real, no outage). Fixes A-C saved (6fce695): PUB-01,03,05 3/3 talkative AND
  3/3 plain. Full after A-C: plain reps3 9/10 (PUB-05 1 fail), talkative 7/10.
  D+E saved (72fda28): PUB-05 plain 3/3, PUB-06+09 talkative 3/3. Phase 1 DONE:
  final full reps3 10/10 (results/phase1-final.json, all 30 calls, turns < 5 s). Next: Phase 2, example builder baseline on Brief B
  (Kerem approved the cost, 10 Oct ~19:35).

## Failing customers and what we think causes them
| Case | Family | Symptom | Suspected cause |
| --- | --- | --- | --- |
| PUB-09 talk | Restructuring | agent silent 60 s after user sent '"' -> hangup | empty model reply on junk input; simulator junk |
| PUB-08 talk | Paid | customer hung up right after a correct re-ask | simulator side, not ours |

| outage | any | verify loops forever, no close_call | fix 3 caps it; failure paths can't be reproduced on demand |

## Patterns learned (copy to builder/PATTERNS.md when a fix proves it)
- State the brief counts ("once", attempts) must live in variables, not prompts.
- Keep words that a later check forbids out of mandatory lines.
- Every retry loop needs a cap and an exit that still calls close_call.

## Decisions made (do not reopen without a reason)
- Move dev/ out of the kit folder during any builder run.
- build_a.py/hooks_a.py are the Phase 1 hand agent only, never the shipped builder.
- Opening paraphrased to 'a recording of this call is kept' (Kerem chose, 10 Oct).
- Final briefs stay collections (README l.71-72: same kind of call, same 7 tools).
  Variant briefs wait for Phase 4; keep going phase by phase.

## Budgets
- Freya: 99.60 after first run; one 10-customer run ~0.16 credits (~600 runs left)
- Builder model: example builder A $2.09 / 15 min; B $3.26 / 22 min
- 10 Oct ~17:30: bank mock returned Cloudflare 403/1010 to Python; Freya fixed it.
- Claude plan: no limit hit yet
