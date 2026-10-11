# Variant V2: Kestrel Mutual (dev only)

A clean single-document brief (like brief A) for an invented business lender, with its own
tool API and a hand-written answer key. It tests whether the builder reads values from the brief
instead of assuming brief A / B / V1 shapes, and it deliberately includes rules the reference
generator cannot express yet.

Files: `brief.md`, `tools-api.json` (same 7 tools, renamed fields and enums),
`answer-key.spec.json` (SPEC.md keys, plus a `not_expressible` list with quotes and suggested spec).

What changes versus A and V1:
- call variables `ref_no`, `forename`, `family_name`, `courtesy_title`, `local_time`; tool customer field `party_ref`
- three identity questions (company_number text, founded_year year, account_last3 digits:3), limit 2, hint `two_digit_year`
- Friday-Saturday weekend, three holidays in Nov-Dec 2026
- three bands; the worst band has three persuasion attempts
- two facility types (revolving_line, equipment_lease), no floor field in the API
- same-day callback, 12:00-15:00, ask again once
- notes used, own note codes; own disposition/cause table

Deliberately new rule kinds (see `not_expressible` in the answer key):
1. deadline in calendar days, moved back to the previous working day
2. floor = 25% of the overdue amount, rounded up to a whole unit
3. split-payment request -> payment link by text, `pay_link` / `split_requested`, closed after all facilities and overriding `agreed`
4. explicit closing precedence (`handed_off` > `pay_link` > `agreed`)
5. skip a persuasion attempt that repeats an already refused offer
6. named non-working day -> next working day, capped at the deadline
7. no callback slot left today -> close without asking
