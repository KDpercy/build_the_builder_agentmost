# Patterns (generic, no brief values)

Each pattern: the problem, the fix, the evidence. Phase 3 turns these into skills/lib.

## 1. Counted rules live in routes, not prompts  (status: passed 3/3 once)
Problem: a rule like "offer X once" or "attempt 1 uses X if the customer said Y" was a
prompt line; the model forgot the state and re-offered X or proposed the wrong amount.
Fix: extract the trigger as an enum (`full_too_much: yes`), route to a new node whose
fixed `tts` entry line makes the offer exactly once, and whose prompt only lists what
is still allowed. The attempt plan (amount + date per attempt) is computed in code.
Evidence: Brief A PUB-06 failed 3 of 5 runs before; 3/3 after, fixed line said every
time. Not yet seen: the attempt-1 path (customer gave a non-answer after the offer).

## 2. A new route must yield to every rule that outranks it  (status: testing)
Problem: the "full amount too much" route also fired on "I lost my job and cannot pay
anything", so the agent offered the floor to a hardship customer (no persuasion allowed).
Fix: extract each higher-priority trigger too (hardship) and AND it out of the route.
When unsure whether an unextracted value is unset or "", test both (is_not_set OR
not_equals). Evidence: Brief A PUB-05 3/3 before fix 1, 0/3 after it.
Builder rule: when adding a route, list the brief's precedence rules ("comes before")
and guard the route against each.
