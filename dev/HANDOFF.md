# HANDOFF

Rewrite this file at the end of every session. Keep it under 40 lines.

## Where we are
- Phase: 1, fix 1 saved v5: PUB-06 3/3, full reps3 9/10 but PUB-05 0/3 (floor offered
  to hardship). Fix 1b (hardship guard on floor route) written, dry-run valid, not saved.
  Pre-fix workflow copy: scratchpad brief-a.before-fix1.json (regenerate via git if lost).
- Commit: bcbb66f (kit + dev notes). No GitHub remote yet (brew can't build gh on
  macOS 13; use the gh .pkg from github.com/cli/cli/releases).
- Hand agent: slot brief-a, agent 41e5caa1-7cb6-4984-b177-b9ccc19bff1b, source
  builder/build_a.py + hooks_a.py -> out/brief-a.workflow.json (Brief A values inside).
- Scores (A): base 0/10 | example builder 9,9,9,10 (15 min, $2.09) | reps3 8/10
  (PUB-06, PUB-10) | pieces 4/10, but PUB-01,07,08,09,10 hit `snekbox` outage; rerun
  `--style pieces --only PUB-01,PUB-07,PUB-08,PUB-09,PUB-10` -> results/brief-a-pieces-rerun.json

## Next step (one, concrete)
- Kerem: save fix 1b, run `--only PUB-05,PUB-06 --reps 3`, then full `--reps 3`,
  then `--style pieces`. Then fix 2/3 on Kerem's go.

## Failing customers and what we think causes them
| Case | Family | Symptom | Suspected cause |
| --- | --- | --- | --- |
| PUB-06 | Amounts | floor offered twice (3 of 5 runs) | "full too much" not tracked; attempt 1 proposes full amount or re-offers floor today |
| PUB-10 | Tool failure | judge: "recorded" said before success | the word is in the required opening line |
| outage | any | verify loops forever, no close_call | VERIFY_POST says "call again" with no cap; no safety close |

## Patterns learned (copy to builder/PATTERNS.md when a fix proves it)
- State the brief counts ("once", attempts) must live in variables, not prompts.
- Keep words that a later check forbids out of mandatory lines.
- Every retry loop needs a cap and an exit that still calls close_call.

## Decisions made (do not reopen without a reason)
- Move dev/ out of the kit folder during any builder run.
- build_a.py/hooks_a.py are the Phase 1 hand agent only, never the shipped builder.
- Final briefs stay collections (README l.71-72: same kind of call, same 7 tools).
  Variant briefs wait for Phase 4; keep going phase by phase.

## Budgets
- Freya: 99.60 after first run; one 10-customer run ~0.16 credits (~600 runs left)
- Builder model: one example-builder run $2.09 / 15 min
- Claude plan: no limit hit yet
