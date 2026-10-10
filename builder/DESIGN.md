# Builder design (Phase 3 plan, written Sat 10 Oct from Phase 1-2 evidence)

## What the evidence says
- The kit's example builder (Claude + one short skill) reached 8/10 on Brief A with --reps 3.
  Hand fixes took it to 10/10. Every fix was generic (PATTERNS.md 1-6).
- Given our Brief A generator as reference code, the same example builder produced a Brief B
  agent that passed 3/3 --reps 3 and every style in one 22-minute, $3.26 run.
  So: a model that adapts good reference code beats one that starts from a blank page.
- Prompt-only rules fail on repeat runs; routes, fixed lines and code hold.

## Shape
    python3 builder/build.py <tool_api_file> <brief_file> [<brief_file> ...]
1. build.py: start the trace and a 25-minute budget, copy the inputs into out/<slot>/,
   run Claude through the Agent SDK with our skills, then save, export, finish the trace.
2. The model writes, in order:
   a. out/<slot>/rules.json   every atomic rule with its exact quote; for raw material, each
      conflict and which document wins (later memo over earlier policy) and why.
   b. out/<slot>/spec.json    the parameters our reference code needs, read from the brief:
      holidays, weekend, deadline counting, bands, attempts, floors per product type, spoken
      product names, identity questions and order, wrong-answer limit, callback window,
      outcome/reason table, note reasons, required sentences, forbidden pre-verification words,
      restricted words, special cases and their precedence.
   c. out/<slot>/generate.py  a copy of the reference generator, edited only where the brief
      has a rule the reference does not cover. Run it -> out/<slot>/workflow.json.
3. Checks, cheapest first: builder/validate.py (with rules from spec.json), unit tests of
   the generated code, freya.validate_workflow dry run; platform tests only if the bank has
   practice customers for this brief.
4. Fallback: keep the last workflow that passed validate.py; never exit without a saved agent.

## Reference generator (to build from build_a.py / build_b.py, values removed)
- builder/lib/calendar_code.py  done: dates from spec values, tested.
- builder/lib/nodes.py          code_node, conv, routes (always, var_is, failed_twice,
                                CLOSED, CLOSE_GIVEUP), api_tool from the tool API file.
- builder/lib/hooks.py          verify pre/post (date and digit normalising per identity
                                field type), promise/callback/transfer/note/close hooks.
- builder/reference/generate.py one-to-three-product flow (Brief B shape works for one
                                product too), every brief value read from spec.json.

## Skills (.claude/skills/, short, no brief values)
- read-brief: every file, every line; rules.json + spec.json; conflict resolution.
- design-agent: edit the reference generator; PATTERNS.md as hard rules.
- check-agent: validator, unit tests, dry run, then platform tests if they exist.

## Open questions to settle early on Sunday
- Freya's reply on practice customers for final briefs (decides whether step 3 can test).
- Builder model and credentials for Freya's rerun (asked by mail).
- Isolation: the run must not read dev/ or another brief's out/; build.py should run the SDK
  with cwd set to a clean staging folder that holds only the kit files and builder/.
