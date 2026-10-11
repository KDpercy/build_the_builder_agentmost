# Final-day runbook (Sun 11 Oct)

All commands from the kit folder:

    cd /Users/macbookpro/Desktop/AgentMost/build-the-builder

## Rehearsal (before the freeze)
Exactly the 19:00 commands on practice material, no BUILD_PRACTICE (worst case: no practice
customers). They start no simulations, so they may run while a measurement is going. One at a time:

    (source env.sh && source env.builder.sh && python3 builder/build.py briefs/rehearsal1/openapi.json briefs/rehearsal1/brief-a.md)
    (source env.sh && source env.builder.sh && python3 builder/build.py briefs/rehearsal2/openapi.json briefs/rehearsal2/brief-a.md briefs/rehearsal2/brief-b.md)
    (source env.sh && source env.builder.sh && python3 builder/build.py briefs/rehearsal3/tools-api.json briefs/rehearsal3/01-mail.md briefs/rehearsal3/02-policy.md briefs/rehearsal3/03-memo.md briefs/rehearsal3/04-codes.md)

After each: dev/check_build.sh <slot>. Then score rehearsal1 on the practice customers (A, --reps 3)
with builder/run_tests.py. Afterwards move submission/rehearsal* to out/ so submission/ holds only
the final exports.

## 16:00 freeze (Madrid; = 17:00 Istanbul). Code changes stop at 15:30
1. All unit tests green:
       python3 -m unittest discover -s builder/tests
2. Commit, push, note the hash in dev/HANDOFF.md:
       git add -A && git commit -m "chore: freeze" && git push && git log --oneline | head -1
3. Anthropic credit covers at least 4 builder runs (~$1 each, plus margin).
4. No simulation stuck in "running" on the Simulation page of the web app.

## 19:00 final briefs arrive
1. Save every file exactly as sent, one folder per brief:
       briefs/final1/   (brief file(s) + its tool API file)
       briefs/final2/
   Do not edit them. Commit them as received.
2. Practice customers? Look at what came with the brief:
   - nothing about practice customers -> leave BUILD_PRACTICE unset (the build only validates,
     smoke-tests and dry-runs; ~3 min, ~$0.75)
   - a cases/test-set JSON file (same shape as public-test-set.json) -> save it in the brief's
     folder and add BUILD_PRACTICE=briefs/final1/<cases file>.json before python3 in the command
   - a new public-test-set.json with a new brief letter -> replace ours, commit, and add
     BUILD_PRACTICE=<letter>
   With practice customers a build runs simulations (one at a time, ~10-20 min): build the two
   briefs one after the other, never at the same time.
3. Build each brief, one at a time (≈5-15 min each). A brief made of several files: pass all of
   them, in a sensible order (earlier documents first, memos last):
       (source env.sh && source env.builder.sh && python3 builder/build.py briefs/final1/<tool api>.json briefs/final1/<file1> [<file2> ...])
       (source env.sh && source env.builder.sh && python3 builder/build.py briefs/final2/<tool api>.json briefs/final2/<file1> [<file2> ...])
   No BUILD_SLOT on final runs: the slot is the folder name plus the brief file names
   (e.g. final1-brief), and the export goes to submission/<slot>.workflow.json.
4. Check each run (one command does all of this: `dev/check_build.sh <slot>`, exit 0 = fine):
   - it printed "saved <slot>: workflow ..., agent ..."
   - submission/<slot>.workflow.json exists
   - the trace has no keys:
         grep -c "fak_\|sk-ant" traces/<slot>-*.jsonl      # must print 0
   - read out/<slot>/work/spec.json "gaps" and rules.json: anything surprising?
5. Commit and push: briefs/, out/, traces/, submission/
       git add -A && git commit -m "final: builds of final briefs" && git push
6. Submit following Freya's emailed steps. Command for the form:
       python3 builder/build.py <tool_api_file> <brief_file> [<brief_file> ...]

## If something breaks
- Builder crashes or saves nothing: read the end of traces/<slot>-*.jsonl. Fix the bug in
  builder code only (no value, rule or sentence from a final brief), commit, then rebuild
  BOTH briefs from the new commit so commit, workflows and traces match.
- Freya API 502/503/504: wait a minute and rerun the same command (the slot is reused).
- A simulation stuck in "running": stop it on the Simulation page.
- Never edit an agent in the Freya editor. Never edit a workflow file by hand.
