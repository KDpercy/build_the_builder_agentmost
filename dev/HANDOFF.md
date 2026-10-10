# HANDOFF

Rewrite this file at the end of every session. Keep it under 40 lines.

## Where we are (Sat 10 Oct, ~20:40)
- Phase 1 DONE: Brief A hand agent 41e5caa1 (slot brief-a, builder/build_a.py + hooks_a.py)
  10/10 --reps 3 plain (results/phase1-final.json); styles 1 run: pieces/corrects/asks_back/
  in_words 10, talkative fixed by A-E. Score history: results/log.jsonl.
- Phase 2 in progress: Brief B hand agent ffcb39ae (slot brief-b, build_b.py + hooks_b.py,
  made by the example builder, $3.26 / 22 min; imports build_a, so A fixes reach B).
  B: 3/3 --reps 3; pieces, corrects, talkative 3/3 each. On Brief A customers 8/10 and 7/10:
  PUB-05/08 fail only on notes (Brief B notes, Brief A never notes: expected, not a bug);
  PUB-07 was a real bug (vague date -> attempt 1), fixed in bc055ae, retest running.
- Custom Brief B cases (same practice ids, new scripts): dev/cases/b-set1.json, b-set2.json
  (rules 8-10, closing order, all paid, hardship, human). Running.
- builder/validate.py + builder/tests (17 unittest fixtures, all pass). Both workflows clean.
- Commits: latest bc055ae. No GitHub remote yet (gh .pkg from github.com/cli/cli/releases).

## Next step (one, concrete)
- Read results/b-pub07.json, b-set1.json, b-set2.json; fix B failures; then B --reps 3 on
  styles; then start Phase 3 design (builder/build.py) if time allows.

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
