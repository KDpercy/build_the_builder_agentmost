# Stress testing

## What we can and cannot vary

The bank only knows the 13 practice customers, so products, debts and security
answers are fixed. We can vary how a customer talks and what they do:

- `--style pieces|corrects|talkative|asks_back|in_words` on run_cases.py.
  These are the five behaviours the README names for the final.
- `--reps 3`: the final's rule. A customer counts only if every run passes.
- `--only PUB-04,PUB-07`: rerun just the customers a change touches.
- `--cases dev/cases/<file>.json`: our own scripts on a practice customer.
  Copy a case from public-test-set.json, keep its `id`, `variables`,
  `products` and `identity`, and change `script`, `expected` and `checks`.
  Derive `expected` from the brief and cite the rule in a `rule` field.

For other calendar days, test the generated date code locally with many values
of `now`. The bank does not check dates, so the ledger cannot tell us.

## Order of work

1. All 13 plain, one run. Fix by family.
2. All 13 with `--reps 3`.
3. Each style on the customers it stresses: `pieces` and `in_words` on
   identity and dates; `corrects` on dates and amounts; `asks_back` before
   verification; `talkative` everywhere (it mentions an unrelated date).
4. Our own scripts, below.

## Scripts worth writing (situations the practice set does not cover)

Take the rule numbers from the brief in use. Brief A has a rule for each of
these and no practice customer for most of them.

| Family | Variations |
| --- | --- |
| Who is on the line | answers "hello" or "who is this" twice; says the name only on the second ask; asks a question first |
| Someone else | wrong number; the customer has died; callback time outside the window, then inside; outside twice; relative offers to pay |
| Identity | day and month swapped, then month as a word; refuses to answer, then answers; refuses twice; asks what the call is about instead of answering; two wrong then right |
| Scam and robot | "is this a scam?" before verification; "are you a robot?" at different points |
| Dates | weekend day inside the deadline; holiday inside the deadline; "next Friday" and "this Friday"; vague twice; date after the deadline, then refuses the deadline |
| Amounts | below the floor, then accepts the floor; below the floor, refuses the floor; between floor and full; full too much, refuses the floor |
| Persuasion | flat refusal in the early band; flat refusal in the late band through both attempts; refuses, then names a date |
| Read-back | changes the date at the read-back; changes the amount at the read-back; asks to cancel a recorded promise |
| Special | already paid; dispute; product closed years ago; hardship accepting the support team; hardship then names a date; wants a human, insists; wants a human, accepts help; does not want to talk, twice |
| Tool failure | promise fails twice; account lookup fails once |
| Several products | dispute on one, promise on another; already paid on all; hardship on one; restructuring after one promise is recorded; one promise fails twice |

## What to read in a failed run

`python3 tools/run_cases.py ... --out results/run.json`, then
`freya.get_call(call_id)["messages"]`.

1. Ledger line from run_cases: which record is wrong.
2. `route_evaluated` events: which condition fired or did not, with the
   variable table at that moment.
3. `function_call_start` and `function_call_complete`: what was sent, what
   came back.
4. The judge's reason, quoted after "conversation:".
5. Slowest turn. If the customer hung up after a silence, look for a tool
   result with no reply after it.

## Variant briefs (generalisation, no platform needed)

Write two briefs of our own that keep the kind of call and change everything
else: identity questions and their format, the wrong-answer limit, bands and
thresholds, deadlines, holidays, weekend rules, the floor rule, the number of
persuasion attempts, the outcome and reason names, required sentences, the
callback window, and the tool API's fields and allowed values. Write one of
them as raw material: a mail, a policy extract, a later memo that changes two
values, and a code list. For each, write by hand the rule ledger a perfect
reading would produce, and compare the builder's ledger with it.
