# HANDOFF

Rewrite this file at the end of every session. Keep it under 40 lines.

## Where we are (Sat 10 Oct, ~21:35)
- Phase 1 DONE: Brief A hand agent 41e5caa1 10/10 --reps 3. Phase 2 DONE: Brief B hand agent
  ffcb39ae 3/3 --reps 3, 3 styles 3/3, 6 custom B cases pass. Hand agents now in dev/hand/.
- Phase 3 well under way (all committed, 60+ unit tests green, `python3 -m unittest discover -s builder/tests`):
  builder/validate.py, lib/ (calendar, date facts, nodes, identity hooks), reference/ (generate,
  code, hooks, prompts, SPEC.md), skills/ (read-brief, design-agent, check-agent), build.py,
  PATTERNS.md (generic; evidence in dev/PATTERNS-evidence.md), DESIGN.md.
- Reference agents built only from dev/specs/brief-{a,b}.spec.json (answer-key specs):
  ref-a (agent cbc21b5c): 9/10 twice; PUB-10 retry fixed in 3 steps (args naming, close count).
  ref-b (agent 7ca97613): 0/3 on first try (read-back lacked dates/deadlines; early-band extra
  offer) -> fixed in b62389b, saved, retest next.
- Invented-bank test proves the reference has no brief values.

## Next step (one, concrete)
- Retest ref-a PUB-10 x3 and ref-b on B + custom sets; then first end-to-end build.py run on
  Brief A with BUILD_SLOT=rehearsal-a (costs ~$3; Kerem allowed builder runs, key in subshell).

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
