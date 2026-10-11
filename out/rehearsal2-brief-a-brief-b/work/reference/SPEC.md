# work/spec.json: every key the reference generator reads

Fill each value from the brief and the tool API file. The example values below are invented
(a fictional bank) and only show the shape. Never copy an example value into a real spec.
Text values are spoken or shown to the phone agent: copy required sentences word for word.

| Key | Type | Meaning |
| --- | --- | --- |
| `agent_identity` | text | how the agent describes itself ("the Northwind Credit assistant") |
| `customer_variable` | text | REQUIRED. Call variable passed to every tool as the customer |
| `now_variable` | text | call variable holding the current date and time (default `now`) |
| `address_as` | text | REQUIRED. How to name the customer, with the brief's call variables, e.g. `{{honorific}} {{family_name}}` |
| `opening.first_sentence` | text | the required first sentence |
| `opening.ask` | text | the who-is-this question, with call variables |
| `forbidden_before_verification` | list | words never said before identity passes |
| `confirmation_words.confirms` / `does_not_confirm` | lists | what counts as confirming identity |
| `confirmation_words.asks` | int | how many times to ask before closing as unclear |
| `confirmation_words.close_if_unclear` | [outcome, reason] | close codes when still unclear |
| `identity.questions` | list of {value, ask, kind} | in order; `value` = the tool's allowed value; `kind` = `date`, `digits:N`, `year` or `text` |
| `identity.question_field` / `answer_field` | text | request body field names of the check tool |
| `identity.numeric_date_order` | `dmy`/`mdy`/`ymd` | how to read a date said only in numbers |
| `identity.wrong_answer_limit` | int | wrong answers that end the check |
| `identity.first_line` | text | spoken right after confirmation; asks the first question |
| `identity.response` | {ok, verified, all_verified, left, hint} | response field names of the check tool |
| `identity.hints` | {hint value: instruction} | what to do for each hint the tool can return |
| `identity.on_failed` | {say, close: [o, r]} | after the wrong-answer limit |
| `identity.on_declined` | {explain_once, counts_as_declining, close: [o, r]} | refusal to answer |
| `calendar` | {holidays: [YYYY-MM-DD], weekend: [0-6, Mon=0], count_today: bool} | business days |
| `bands` | list of {name, min_days, max_days, deadline, attempts} | `deadline` is a date expression |
| `persuasion.attempts` | list of {amount, date} | one per attempt; amount `full`, `floor` or `full_or_floor_if_too_much`; date is a date expression |
| `persuasion.floor_offer` | {once: bool, say_with_offer: text} | the lower-amount offer |
| `persuasion.close_refused` | [outcome, reason] | close codes when every product is refused after its attempts |
| `products.type_field` | text | the account field holding the product type |
| `products.fields` | {id, due_amount, late_days} | the account's field names for the id, the overdue amount and the days late |
| `products.types` | {type: {spoken, floor_field}} or {type: {spoken, floor_percent, floor_round}} | `spoken` may use `{field}` from the account, e.g. `card {last}`. Floor from an account field, or a percentage of the overdue amount; `floor_round` = `up_whole`, `down_whole` or `cents` |
| `products.response_path` | text | the field of the account reply that holds the product list, e.g. `products` (`data.products` also works) |
| `debt_statement` | text | how the debt is introduced after verification |
| `first_ask` / `first_ask_all` | text | the first question for one product / several products |
| `callback` | {days, from, to, later_than_now, ask_again_once, close_booked, close_none} | days are date expressions |
| `third_party` | {wrong_number: [o, r], deceased: {say, close}} | someone else answers |
| `special_cases` | list of {name, trigger, precedence, action, transfer?, close?, line?, accept?, decline?} | `line` = a fixed sentence said once (a one-time offer); then `accept`/`decline` |
| `outcome_logic` | {on_transfer, reason_by_queue, on_promise, all_notes_paid, paid_note, no_deal, verify_failed, promise_failed} | closing codes the hook enforces; `no_deal` = the outcome when no promise was recorded |
| `notes` | {used: bool, reasons: [...], service_error_reason} | whether and how notes are written |
| `sentences.after_promise` | text | required sentence after a recorded promise |
| `read_back.ask` | text | the confirmation question |
| `robot_question` / `scam_question` | text | what to do when asked |
| `never_offer` | list | things the agent must never offer |
| `tool_names` | {verify, account, promise, callback, transfer, note, close} | tool names from the API file |
| `tool_fields` | {customer, product, amount, date, queue, note_reason, outcome, reason} | REQUIRED. Request field names |

Date expressions: `today`, `next_business_day`, `deadline`, `business_days_after_today:N`,
`calendar_days_after_today:N` (add `:back` or `:forward` to move off a non-working day),
`last_business_day_this_week`, `last_business_day_this_week_or_next_if_today`.
If the brief needs one that is not here, add it to `lib/date_facts.py` in your work copy.

A complete invented example is `SPEC` in `builder/tests/test_generate.py`.
