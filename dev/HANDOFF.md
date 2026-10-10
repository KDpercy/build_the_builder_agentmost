# HANDOFF

Rewrite this file at the end of every session. Keep it under 40 lines.

## Where we are (Sat 10 Oct, ~21:00)
- Phase 1 DONE: Brief A hand agent 41e5caa1 10/10 --reps 3 (results/phase1-final.json).
- Phase 2 nearly done: Brief B hand agent ffcb39ae (example builder + our A code) 3/3 --reps 3,
  pieces/corrects/talkative 3/3, PUB-07 vague-date bug fixed (3/3), our 6 custom B cases
  (dev/cases/b-set1/2.json: paid+dispute, restructuring, paid+refusal, all paid, hardship,
  human) all pass. Brief A customers on B agent fail only on notes (Brief A never notes).
- Phase 3 started early (all committed, 54+ unit tests green):
  builder/validate.py (+ledger check), lib/calendar_code.py, lib/date_facts.py (matches hand
  agent on 360 date cases), lib/nodes.py, lib/hooks.py (identity answers), reference/
  (generate.py, code.py, hooks.py, prompts.py: spec + tool API -> workflow, no brief values),
  skills/read-brief, design-agent, check-agent, build.py (staging, trace, budget, fallback),
  DESIGN.md. dev/specs/brief-a.spec.json = hand-written answer key spec.
- Reference agent from the Brief A spec: slot ref-a, agent cbc21b5c; first Brief A run going.

## Next step (one, concrete)
- Read results/ref-a-run1.json; fix the reference until it matches the hand agent; then write
  the Brief B spec and test the reference on B; then a full build.py run on Brief A.
- Before freeze: move build_a/b + hooks_a/b to dev/hand/ (they hold brief values) and strip
  brief examples from PATTERNS.md (it is staged into builder runs).

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
- 10 Oct ~17:30: bank mock gave Cloudflare 403/1010 to Python; Freya fixed it.
