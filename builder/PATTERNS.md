# Patterns (generic, no brief values)

Each pattern: the problem, the fix, the evidence. Phase 3 turns these into skills/lib.

## 1. Counted rules live in routes, not prompts  (status: testing)
Problem: a rule like "offer X once" or "attempt 1 uses X if the customer said Y" was a
prompt line; the model forgot the state and re-offered X or proposed the wrong amount.
Fix: extract the trigger as an enum (`full_too_much: yes`), route to a new node whose
fixed `tts` entry line makes the offer exactly once, and whose prompt only lists what
is still allowed. The attempt plan (amount + date per attempt) is computed in code.
Evidence: Brief A PUB-06 failed 3 of 5 runs before.
