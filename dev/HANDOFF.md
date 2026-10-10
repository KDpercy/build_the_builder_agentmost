# HANDOFF

Rewrite this file at the end of every session. Keep it under 40 lines.

## Where we are
- Phase: 0, step a (nothing done yet)
- Builder commit: none (no git repo yet)
- Last scores (brief, passed/total, reps, style): none

## Done this session
- Read RULES, PLAN, KIT_NOTES. Checked Phase 0: env.sh, .git,
  .freya-agents.json, results/, traces/, out/ are all missing.
- Found: `gh` not installed, `claude-agent-sdk` not installed.

## Next step (one, concrete)
- Kerem: create env.sh from env.example, fill the three Freya values, then
  run the check command and paste its output.

## Failing customers and what we think causes them
| Case | Family | Symptom | Suspected cause |
| --- | --- | --- | --- |

## Patterns learned this session (also added to builder/PATTERNS.md)
-

## Decisions made (do not reopen without a reason)
- Move dev/ out of the kit folder while any builder run is going (rule: a
  builder run must never read dev/).

## Budgets
- Freya credits left: ?          cost of one ten-customer run: ?
- Builder model credit left: ?   cost of one builder run: ?
- Claude plan: no limit hit yet
