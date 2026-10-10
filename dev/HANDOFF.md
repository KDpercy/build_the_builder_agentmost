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
  ref-a (agent cbc21b5c): 9/10 twice; PUB-10 retry fixed (args naming, close count): 3/3.
  ref-b (agent 7ca97613): 0/3 -> 2/3 after giving read-back the facts. Latest retest
  (22:13, after removing the floor from attempt lines) found two real reference bugs:
  1. PUB-06 0/3: "full amount is too much" is extracted as a special case (hardship once,
     restructuring twice) because the reference has no separate too-much value. Fix: add a
     `full_too_much` extraction and exclude it in the special_case description (pattern 2).
  2. PUB-12 2 of 3 runs: product_3 called close_call itself, skipping read-back and notes.
     Fix: remove the close tool from product steps; special cases there move on to
     product_k_done and readback closes with their codes (needs a refused-close spec key).
- Invented-bank test proves the reference has no brief values.

## Next step (one, concrete)
- Fix reference bugs 1 and 2 above, retest PUB-06/PUB-12 x3, then full A and B.
- Then the first end-to-end run of our builder (costs ~$3; key only in a subshell):
  (source env.sh && source env.builder.sh && BUILD_SLOT=ref-a python3 builder/build.py tools/openapi.json briefs/brief-a.md)
  then read traces/ref-a-*.jsonl and out/ref-a/stage/work/ (spec.json vs dev/specs/brief-a.spec.json).

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
- 10 Oct 22:02: Freya API 503 'API key validation temporarily unavailable' for ~1 min.
