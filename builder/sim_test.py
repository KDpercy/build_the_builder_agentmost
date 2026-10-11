"""Run scenarios as one Freya chat simulation (simulated customers + the platform's judge) against
a saved agent. For cases whose expected behaviour is written down but that have no practice
customers on Freya. Unlike the chat route, a simulation shows how calls end.

    python3 builder/sim_test.py <agent_id> work/scenarios.json

work/scenarios.json:
    [{"name": "...", "variables": {...call variables...},
      "customer": "who the simulated customer is and what they do, in the call's language",
      "criteria": ["one expected behaviour per line, from the case", "..."]}, ...]

Prints PASS/FAIL per scenario with the judge's reason and the call id (read it with
freya.get_call(call_id) before changing anything). One simulation at a time.
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

CUSTOMER_RULES = ("Write only the words you say on the phone: no brackets, no stage directions. One or two short "
                  "sentences per turn, in the language of the call. When the assistant says goodbye or routes you "
                  "elsewhere, say a short goodbye and nothing more. Never invent facts that are not written below.")


def main(argv: list) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    os.chdir(ROOT)
    import freya
    scenarios = json.load(open(argv[2]))
    personas = [{"name": f"scenario {i + 1}: {s['name']}"[:120], "prompt": CUSTOMER_RULES + "\n\n" + s["customer"],
                 "successCriteria": "All of these are true:\n- " + "\n- ".join(s["criteria"]), "tags": ["builder-scenarios"]}
                for i, s in enumerate(scenarios)]
    made = freya.create_personas(personas)["personas"]
    variables = {p["id"]: s.get("variables", {}) for p, s in zip(made, scenarios)}
    names = {p["id"]: s["name"] for p, s in zip(made, scenarios)}
    sim_id, it_id, status = freya.run_simulation(argv[1], f"scenarios {time.strftime('%H:%M:%S')}", variables)
    runs = freya.get_iteration(sim_id, it_id)["runs"]
    passed = 0
    for r in runs:
        ok = r.get("outcome") == "pass"
        passed += ok
        print(("PASS" if ok else "FAIL"), names.get(r.get("personaId"), r.get("personaId")), "| call", r.get("callId"))
        if not ok:
            print("      ", " ".join(str(r.get("reason") or "no verdict").split())[:700])
    print(f"\n{passed} / {len(runs)} passed. Simulation {sim_id}, status {status}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
