---
name: design-agent
description: Turn work/spec.json and work/rules.json into a Freya workflow with the reference generator, editing a copy of it only where the brief needs something the spec cannot express. Use after read-brief.
---

# Design the agent

## 1. Generate from the reference
    cp -r builder/reference work/reference
    python3 work/reference/generate.py work/spec.json input/<tool api file> work/workflow.json
The reference already does, generically: date facts from `now`; identity with answer
cleaning; third party and callback window; one to three products with per-product band,
deadline, floor and attempts; one read-back and one recording per product; notes only if
the spec uses them; special cases from the spec; a closing hook that sets the outcome from
what was actually recorded; retry caps on every failing tool.

## 2. Edit only what the spec cannot express
Go through work/rules.json. For each rule write in `implemented_by` where it lives: a node
name, a prompt line, a route, a code step or a hook. If a rule has no home, edit
work/reference (never builder/reference) to add one, then regenerate.

Hard rules for every edit (they come from failures we have seen):
1. A count in the brief ("once", "at most twice", a number of attempts) lives in a route,
   a variable or a fixed spoken line, never only in a prompt.
2. A new route must yield to every rule the brief says comes first: extract each
   higher-priority trigger and exclude it from the route.
3. A word the brief forbids in one situation must not appear in any fixed spoken line
   that can be said in that situation, even if another rule requires the idea. Paraphrase.
4. Every tool that can fail has a capped retry and an exit that still closes the call.
5. A rambling, cut-off or nonsense reply is never an answer or a refusal; the agent replies
   with a neutral line and never repeats an offer because of it.
6. Arithmetic, dates and counting happen in code. The model gets finished facts.
7. Tools exist only in the nodes where the brief allows them. Nothing about the account
   is in any prompt or line the model sees before verification.
8. Required sentences are copied word for word from the brief.
9. Code in code steps and hooks never raises and never contains a double brace.

## 3. Regenerate and hand over
    python3 work/reference/generate.py work/spec.json input/<tool api file> work/workflow.json
Then use check-agent. If a check fails, fix the spec or the generator copy, never the
workflow JSON by hand.
