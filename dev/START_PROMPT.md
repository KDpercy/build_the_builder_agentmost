# Start here

## Phase 0: do this yourself first (about 30 minutes, almost no Claude tokens)

Terminal tab 1, in the kit folder:

    cp env.example env.sh          # then put in your Freya API key and a team key of 16+ characters
    source env.sh
    git init
    git add -A && git commit -m "kit v3 and dev notes"

Check `git status` shows no env.sh before you commit. Then make a private
GitHub repository and push.

Baseline 1, the example agent. Note the Freya credit shown in the workspace
before and after: the difference is what one test run costs.

    python3 -c "import freya,json; print(freya.save_workflow('base', json.load(open('examples/base-agent.json'))))"
    python3 tools/run_cases.py <agent_id it printed> --brief A

Baseline 2, the example builder. It needs a Claude login or an API key. To
use your API key, create env.builder.sh with one line,
`export ANTHROPIC_API_KEY=...`, and source it in this tab only:

    pip install claude-agent-sdk
    source env.builder.sh
    python3 examples/agent_builder.py briefs/brief-a.md

It runs for up to about 30 minutes and prints its turns, seconds and cost at
the end. If the API credit runs out mid-run the build stops, so check the
balance first. Write down: customers passed, minutes, cost.

Baseline 3, how stable that agent is:

    python3 tools/run_cases.py <agent_id of the built agent> --brief A --reps 3
    python3 tools/run_cases.py <agent_id of the built agent> --brief A --style pieces

## Then start Claude Code in the kit folder, in a different terminal tab

Do not source env.builder.sh in that tab. Paste:

You are my engineering partner for the Freya x YC "Build the Builder"
hackathon. Read dev/RULES.md, dev/PLAN.md and dev/KIT_NOTES.md. They hold the
rules, the plan and a digest of the kit. Do not re-read the kit's docs unless
you need an exact JSON shape.

My Phase 0 numbers:
- base agent on Brief A: <passed>/10, Freya credit used: <amount>
- example builder on Brief A: <passed>/10 in <minutes> min, cost <amount>
- that agent with --reps 3: <passed>/10; with --style pieces: <passed>/10
- failing lines: <paste the FAIL lines and their reasons>

Tell me which OS and shell you detect. Then start Phase 1 from dev/PLAN.md:
read the workflow the example builder wrote (out/brief-a.workflow.json) and
briefs/brief-a.md in full, list which brief rules that workflow does not
implement, and propose the first three fixes with the cheapest test for each.
Stop and show me before changing anything. Update the Status in dev/RULES.md
and write dev/HANDOFF.md before the session ends.

## Every later session starts with

Read dev/RULES.md and dev/HANDOFF.md. Continue with the next step listed there.
