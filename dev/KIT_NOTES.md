# Kit notes (kit version 3)

A digest of the kit for development sessions, written from a full read of
README.md, both briefs, tools/openapi.json, the three docs, freya.py,
tools/run_cases.py, tools/score.py, examples/ and the example skill. It exists
so a session does not have to re-read 90 KB of docs. When a detail matters,
open the doc named in brackets. The kit wins over this file.

Builder runs must never read anything in dev/.

## 1. Commands

    source env.sh
    python3 -c "import freya,json; print(freya.save_workflow('base', json.load(open('examples/base-agent.json'))))"
    python3 tools/run_cases.py <agent_id> --brief A
        --reps 3                 a customer counts only if every run passes
        --style pieces|corrects|talkative|asks_back|in_words
        --only PUB-04,PUB-07     run a few customers
        --out results/run.json   keeps the call id of every customer
        --cases file.json        another case file (see section 2)
    python3 examples/agent_builder.py briefs/brief-a.md [briefs/brief-b.md]

freya.py: `validate_workflow(name, wf)` is a dry run, `save_workflow(slot, wf)`
creates once then updates and publishes, `export_workflow(id, path)` writes the
file we submit, `get_call(call_id)` returns the transcript with tool calls and
routing events. `POST /api/v2/chat/message` runs one turn in seconds. [api.md]

## 2. How a customer is scored

- run_cases.py asks the bank for a session per case id
  (`/v1/practice/sessions`, header `x-team-key`). The bank returns the call
  variables, including a fresh `customer_id`. Only the 13 practice ids exist,
  so we cannot invent bank customers. We can change what a customer says:
  `--style`, or a case file that reuses a practice id with another script.
- The customer is a persona played by a model. Its prompt is the case script.
  It says "Yes, I confirm." to a correct read-back and "Thank you, goodbye."
  after the agent's goodbye. It hangs up if the agent stays silent too long.
- Ledger checks (score.py), all exact: outcome and reason; every promise
  (product_id, amount to 2 decimals, date); every note (product_id, reason);
  every callback (date, time); every transfer queue; the last bank call is
  `close_call`; no `get_account` or `create_promise` before verification; no
  `verify_identity` or `get_account` when the expected outcome is "not reached".
- Conversation checks: a judge model reads the transcript against the case's
  `checks` list. One failed check fails the customer.
- One simulation at a time per workspace. Ten customers take 3 to 11 minutes.
  A slow model can fail a run that is not our fault; run_cases prints a
  warning when the median slowest turn is above 10 seconds.

## 3. Workflow engine facts [workflow-format.md]

- Three separate model calls per user turn: extraction, routing, dialogue.
  Routing never sees `task_message`. Dialogue only sees the current node's
  tools. Variable conditions are evaluated in code, with no model call.
- Top level: `initial_node`, `system_prompt`, `nodes`, `global_nodes`,
  `test_variables`, `tools` (lifecycle tools). Leave `agent_config` out.
- No `null` anywhere. Omit the field or use "".
- Node types we need: `conversation` (prompt, tools, extraction, routes),
  `api_request` (engine runs a call on entry), `code` (engine runs Python on
  entry), `end_call` (hangs up).
- `tools` survive only on conversation nodes, `pre_actions` only on
  api_request and code nodes. The platform strips the wrong one silently.
- Passthrough nodes need `passthrough_default_transition` and a last `always`
  transition, or they deadlock.
- `on_enter`: `tts` (fixed line, `{{var}}` works), `llm`, `silent`.
- Variables are global for the call. An unset `{{var}}` in a prompt stays as
  literal text. `{{var}}` works in prompts, entry lines, URLs, bodies.
- Conditions: `equals`, `not_equals`, `greater_than`, `less_than`, `contains`,
  `is_set`, `is_not_set`, `always`, `matches_intent`. Variable checks go in a
  top-level `"logic": "or"` group; AND is a nested group.
- `equals` compares text. Booleans arrive as "true" or "True": test both, or
  route on a string that our own code writes. Use `greater_than` and
  `less_than` for counters.
- Routing order: loop_condition, then the node's transitions in list order
  (deterministic ones first), then global nodes. Routing runs again after a
  tool result, so a route on a tool result fires in the same turn.
- Prefer a self-transition with `always` at the end of the list over
  `loop_condition`. To fork on what the customer said, extract an enum and
  route with `equals`; it beats several `matches_intent` routes.
- Extraction: set `min_confidence` on every variable (default 0.95 silently
  drops values). Type dates as `date`. The built-in date rules resolve vague
  dates to a concrete day and use the real clock, not our `now`.
- `max_node_turns` defaults to 10 user turns. Raise it on long nodes and give
  it a `max_turn_transition`.
- `end_call` node: the farewell comes from `terminal`, not from `on_enter`.
  The call's ended reason is the terminal's function name.
- `context_variables` was dropped on save in a test on 10 October. Do not use.

## 4. Tools, hooks and code [tools-and-code.md]

- Tool shape: `function.name`, `handler` (`__function__:api_call`,
  `code_exec`, `end_call`), `description`, `parameters`, `config`.
- A parameter with a `default` that resolves is baked and hidden from the
  model. A `default` of `{{x}}` where no variable `x` exists is filled by the
  model. Never use `const`. Baking happens when the node is entered.
- Trap: a model-filled field whose placeholder name equals an existing
  variable gets baked. Give every placeholder a name nothing else writes.
- Body fields are leaves under `body.properties`, each with its own
  `default`, `description`, `enum`. Required ones go in `body.required`.
- The tool description decides whether the model calls it. Write the trigger:
  "CALL it every time ...". One tool per message, and speak after every result.
- A result is an envelope: `status`, `data` (the API's JSON), `message`,
  `status_code`, `header`. Mapping paths start with `data.`.
- The engine also writes `<tool>_response.data.<field>`, `<tool>_args.<field>`,
  `<tool>_status_code`, `<tool>_success_count`, `<tool>_failure_count`.
- `response_mapping` sits on the tool for `tools`, on the node for
  `pre_actions`.
- `pre_process_code` gets `vars` and `config` (the request). It can rewrite
  the body. `post_process_code` gets `result` (the envelope) and can add keys
  under `result["data"]` that the model then reads. Hooks only on api_call.
- Proven fix for "agent says nothing after a tool call" and "agent ignores a
  negative result": a post-hook that adds a plain `what_to_do_next` sentence
  to the result, and a prompt line telling the model to obey it.
- Code nodes: read and write through `vars`. `json`, `re`, `datetime` import.
  Never let a snippet raise; write a fallback for every variable. No `{{` or
  `}}` in code, including the end of nested dict literals. Write strings for
  routing flags.
- Verified pattern: a passthrough code node as `initial_node` computes a block
  of date facts from the call variable `now`, and later prompts show it with
  `{{date_facts}}`. The chat route may skip an initial code node.
- Verified pattern: a closing tool sets a variable, a route on that variable
  leads to an `end_call` node with `message_mode: "none"`; the agent says its
  goodbye in the conversation node before.
- Lifecycle tools: a workflow-level tool with `config.alwaysRunsAt:
  ["end_of_call"]` runs after the call ends. Unresolved parameters are filled
  by one model call; if all resolve, it runs directly.
- `maxRetries` retries a failed response. A retried write can record twice.
  `connect_retries` (a baked parameter) only retries a failed connection.

## 5. The example agent and the example builder

- examples/base-agent.json: two conversation nodes (identity, collection),
  four tools. It ends the call when the agent says "Have a good day" (an
  `end_call` tool with a `trigger_pattern`) and records the outcome with a
  workflow-level `close_call` lifecycle tool at end of call, whose outcome and
  reason are filled by a model from the conversation. It passed 2 of 13.
- examples/agent_builder.py: runs Claude through the Claude Agent SDK
  (`pip install claude-agent-sdk`) with one skill,
  `.claude/skills/build-phone-agent/SKILL.md`. Model from `BUILDER_MODEL`,
  default `claude-opus-5-5`. `setting_sources=["project"]`, cwd is the kit
  folder, tools Read, Write, Edit, Glob, Grep, Bash, max 150 turns. It writes
  every message to `traces/<start time>.jsonl` and prints turns, seconds and
  cost at the end. It needs a Claude login or `ANTHROPIC_API_KEY`.
- The README says this builder built a Brief A agent that passed 10 of 10 in
  one run. One run is not three, and it was Brief A with plain customers.
- The skill reads `tools/openapi.json` by fixed path and tests with
  `--brief A`. A final brief brings its own tool API file, and there may be no
  practice customers for it.

## 6. What a brief contains (structure only)

Call variables; the opening sentence and words that are forbidden before
verification; how to confirm who is on the line; rules when someone else
answers (callback window, wrong number, special cases); the security
questions, their order and format, the wrong-answer limit and its exceptions;
how to state the debt; the calendar (business days, holidays), bands by days
late with a deadline and a number of persuasion attempts; amount rules and a
floor per product type; the sequence for getting a promise; read-back and
recording rules, including what to do when the tool fails; other things
customers say, each with its outcome; an outcome and reason table; required
sentences. Brief B adds per-product rules, notes and a closing rule.

Brief A says of itself: "Most failed cases come from one rule that was
skipped." Every rule has to land somewhere in the workflow.

## 7. What can change in the final (from the kit itself)

- README: other numbers and limits, other identity questions, another outcome
  table, another calendar. One brief is raw material (a mail, a policy
  extract, a memo that changes it, a code list). Each brief has its own tool
  API file: same seven tool names, other fields and allowed values. Up to
  three products. Several calendar days. Three runs per customer.
- run_cases.py knows how to voice these identity answers: date_of_birth,
  phone_last4, postcode, birth_year, company_number, founded_year.
- score.py treats `not_reached`, `no_contact` and `unreached` alike.
- Use these only to write our own variant briefs for testing. None of it may
  be written into the builder.

## 8. Not known yet

1. Will the bank have practice customers for the final briefs, so a builder
   can test its agent during the final three hours? (Ask Freya.)
2. Cost of one practice run in Freya credits, and of one builder run in
   builder-model spend. Measure both on the first run.
3. When `close_call` is a lifecycle tool and only some of its parameters are
   resolved from variables, does the model fill the rest or is the field
   dropped? Test once.
4. Whether a post-hook's change to `result` also changes the flattened
   `<tool>_response.*` variables. The docs say not confirmed.
