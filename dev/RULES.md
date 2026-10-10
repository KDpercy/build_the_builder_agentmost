# Rules for development sessions

Read this at the start of every Claude Code session, then dev/HANDOFF.md.
This file is for building the builder. A builder run must never read dev/.

There is deliberately no CLAUDE.md in the kit's top folder: the example
builder loads project settings from there, so anything in a top-level
CLAUDE.md would become part of every builder run.

## What we are building
A builder: one command that reads a bank's brief files plus a tool API file
and creates a phone agent (a workflow) on Freya, with no manual step. Only the
phone agents are scored. Calls are in English, in text.

Our command: `python3 builder/build.py <tool_api_file> <brief_file> [<brief_file> ...]`
(the argument order is ours to choose; it goes in the submission form).

## Deadlines (Madrid time)
- Sunday 17:00  our own freeze of the builder
- Sunday 19:00  final briefs arrive (17:00 UTC), each with its own tool API file
- Sunday 21:00  our target to submit
- Sunday 22:00  submissions close (20:00 UTC)

## Competition rules that must never be broken
1. No manual edits to a phone agent after the builder runs.
2. Nothing brief-specific in the builder: no rule, value, date, name or
   sentence from ANY brief in builder code, skills or prompts. Whatever the
   builder can take from the brief, it takes from the brief at run time.
3. After the final briefs open: bug fixes only.
4. A builder run takes 30 minutes at most per brief, tests included.
5. Use `freya.save_workflow(slot, ...)`. Never create a workflow per run.
6. Never change the phone agent's model (`AGENT_LLM` in freya.py).
7. The phone agent calls only the bank's tool API. Code steps and hooks
   inside the workflow are allowed and expected.
8. No probing or load-testing. One simulation at a time.
9. Every builder run leaves a trace: start and end time, each model call
   (model and a one-line purpose), what it created on Freya, every test it
   ran. No keys in a trace.
10. Do not go looking for held-out data, grader internals or anything about
    the final briefs. We win by reading the brief well.

## How to work with me (Kerem)
- I am not an experienced engineer. Detect my OS and shell, then give exact
  commands. Short explanations. Show changed code only.
- I run long commands (tests, builder runs) in my own terminal and paste back
  only the failing lines.
- Ask before deleting anything in the Freya workspace, before a test run
  longer than ten minutes, and before a builder run (it costs money).
- If the kit contradicts these files, the kit wins. Tell me.

## Token and money rules
- dev/KIT_NOTES.md is the digest of the kit. Read it instead of the docs.
  Open a doc only for the exact JSON shape of the thing being written.
- One task per session. Rewrite dev/HANDOFF.md before ending a session.
- Sub-agents only for isolated tasks that need no Freya platform time.
- Three budgets, tracked in HANDOFF.md: my Claude plan (these sessions), the
  builder model's API credit (builder runs), Freya credits (test runs).
- Test ladder, cheapest first: local unit test of generated code, our
  validator, `freya.validate_workflow` dry run, one chat turn,
  `run_cases.py --only <ids>`, a full run, `--reps 3`, styles.

## Secrets
- env.sh holds FREYA_API_KEY, FREYA_API_URL and FREYA_BANK_TEAM_KEY. It is
  gitignored. Never print it, never `cat` it, never commit it.
- The builder's model key lives in env.builder.sh as ANTHROPIC_API_KEY, and is
  sourced only in the terminal tab that runs the builder. Never source it in
  the terminal where Claude Code runs, or these sessions bill the API key.
- Scrub every trace for `fak_`, the team key and `sk-ant` before committing.
- .freya-agents.json stays out of git: it points at workflows in my workspace
  and would break Freya's rerun in theirs.

## Layout
- briefs/ docs/ examples/ tools/ freya.py   the kit, left as it is
- .claude/skills/                           the builder's skills
- builder/                                  our builder: build.py, lib/, tests/
- out/<slot>/                               everything a run generates
- traces/                                   one trace per builder run
- submission/                               exported workflows for the final
- dev/                                      these notes; never read by a run

## Status (update after every phase)
- Phase: 0 done except GitHub push (no `gh`); Phase 1 analysis done, no fix applied yet
- Last scores (Brief A): base agent 0/10; example-builder agent 41e5caa1 10/10 once,
  8/10 with --reps 3, pieces 4/10 (5 of 6 fails = Freya code-sandbox outage)
- Next step: Kerem approves fixes 1-3 in dev/HANDOFF.md; rerun of spoiled pieces customers pending
- Known problems: GitHub repo not created (install gh from the .pkg); builder/build_a.py and
  hooks_a.py hold Brief A values (Phase 1 only, never ship); dev/ must be moved aside
  during builder runs; results/ must exist before run_cases.py
