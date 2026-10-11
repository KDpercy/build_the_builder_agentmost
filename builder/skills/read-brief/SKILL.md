---
name: read-brief
description: Read every brief file and the tool API file line by line and write the rule ledger (work/rules.json) and the parameters (work/spec.json) that the design step needs. Use first, before designing any workflow.
---

# Read the brief

Most failed calls come from one rule that was skipped. Read every line of every file in
`input/`. Do not search by keyword instead of reading. Use only what the inputs say: never
copy a rule, value or sentence from anything else, and never guess a missing value.

## 1. Read
- Read each brief file from the first line to the last. If a file is long, read it in parts
  until you have seen every line.
- Read the tool API file: every tool, every request field, every allowed value, every response
  field. The tool names are fixed; fields and allowed values may differ from what you expect.

## 2. Resolve the documents (raw material)
The brief may be several documents: a mail, a policy extract, a memo, a code list.
- List each document with its date or order.
- A later memo or mail that changes a rule wins over the earlier document, unless it says it
  applies only to some cases. A code list defines allowed values and their meaning.
- Write every conflict and its winner, with both quotes, into `conflicts` in rules.json.

## 3. Write work/rules.json, the rule ledger
A list. One entry per atomic rule (one condition, one action):
    {"id": "R12", "quote": "<exact words from the brief>", "file": "<file name>",
     "kind": "<opening | who_is_on_line | third_party | identity | debt_statement | dates |
              amounts | persuasion | read_back | recording | special_case | closing |
              required_sentence | forbidden | other>",
     "rule": "<the rule in one plain sentence>",
     "implemented_by": ""}            filled in by the design step
- The quote must appear word for word in the file. The check step verifies this.
- Split compound rules. "Say X, ask nothing else, and close as Y" is three rules.
- Precedence ("this comes before rule N", "takes priority") is its own rule.
- Numbers, dates, limits, counts and exact sentences go in the rule, unchanged.

## 4. Write work/spec.json, the parameters
The exact keys are in builder/reference/SPEC.md (read it in full). Fill every field the inputs give; leave a field out when the inputs say nothing about it,
and add a `gaps` list naming each missing item. Never invent a value.
    call_variables        names and meaning of the variables every call starts with
    opening               the first sentence's required content; who to ask for and how
    forbidden_before_verification   words that must not be said before identity passes
    confirmation_words    what counts as confirming identity, and what does not
    identity              questions in order, the tool field values for each, answer
                          format per question (date / digits:N / year / text), numeric date
                          order, wrong-answer limit and what does not count as wrong
    calendar              business days, weekend days, holidays, how "Nth business day after
                          today" is counted, "this"/"next" weekday meaning
    bands                 per band: days-late range, deadline rule, persuasion attempts
    products              per product type: spoken name, floor field, any other rule
    persuasion            what each attempt proposes (amount and date)
    callback              window (days and hours, inclusive or not), retries allowed
    special_cases         each: trigger words, action, tool call, outcome/reason, precedence
    outcomes              the outcome table: outcome, reason, when
    notes                 when notes are written, reasons, when never to write them
    required_sentences    exact sentences, with when they must be said
    restricted_words      words the brief forbids in one situation and requires in another
                          (for example a word allowed only after a tool succeeded)
    tool_failures         what to do when each tool fails, and how many retries
    multi_product         ordering, one read-back or many, per-product counting
    tools                 per tool: the API fields to fill from call variables, and which the
                          agent fills

## 4b. Words with a condition
Look for every rule that allows a word or a claim only after something happens (for example
a claim allowed only after a tool succeeded). Put each such word in `restricted_words`. If a
required sentence (the opening, a fixed line) needs the same idea, write it in other words in
the spec, and note the paraphrase in rules.json. Keep the paraphrase plain and as close to the
original as possible, so a reader still recognises the required statement: prefer a related
form of the same word (a noun instead of a verb) over an unusual synonym. Never put such a word in a line spoken
before the condition can be true.

## 5. Check before moving on
- Every line of every brief file is covered by at least one rule or is plainly descriptive.
- Every rule with a number, date or sentence has it in spec.json too.
- `gaps` lists anything the design step must handle without a value. Prefer the safe
  behaviour: do less, record nothing uncertain, close honestly.
