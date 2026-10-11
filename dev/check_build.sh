#!/bin/bash
# After a final build: dev/check_build.sh <slot>. Checks the RUNBOOK step 4 items in one go.
slot="$1"; [ -z "$slot" ] && { echo "usage: dev/check_build.sh <slot>"; exit 2; }
cd "$(dirname "$0")/.." || exit 2
trace=$(ls -t traces/"$slot"-*.jsonl 2>/dev/null | head -1)
[ -z "$trace" ] && { echo "FAIL no trace for $slot"; exit 1; }
echo "trace: $trace"
python3 - "$trace" "$slot" <<'PY'
import json, os, sys
trace, slot = sys.argv[1], sys.argv[2]
ev = [json.loads(l) for l in open(trace)]
end = [e for e in ev if e["event"] == "end"]
done = [e for e in ev if e["event"] == "model_done"]
bad = 0
if not end or not end[-1].get("ok"):
    print("FAIL run did not end ok:", end[-1] if end else "no end event"); bad = 1
else:
    e = end[-1]
    print(f"ok    agent {e['agent_id']}  {e['nodes']} nodes, {e['tools']} tools, {e['seconds']} s")
    print(("ok    " if os.path.exists(e["export"]) else "FAIL  missing ") + e["export"])
    bad |= not os.path.exists(e["export"])
if done:
    d = done[-1]; print(f"model {d.get('turns')} turns, {d.get('seconds')} s, ${d.get('cost_usd')}")
for k in ("budget_exceeded", "model_error", "fallback_generate"):
    for e in ev:
        if e["event"] == k: print("NOTE ", k, str(e)[:200])
tests = [e for e in ev if e["event"] == "test"]
print(f"checks run by the model: {len(tests)}")
spec = f"out/{slot}/work/spec.json"
if os.path.exists(spec):
    gaps = json.load(open(spec)).get("gaps") or []
    print(f"spec gaps: {len(gaps)}"); [print("  -", str(g)[:160]) for g in gaps]
else:
    print("FAIL no", spec); bad = 1
sys.exit(bad)
PY
rc=$?
keys=$(grep -c -E "fak_[A-Za-z0-9]{8,}|sk-ant-[A-Za-z0-9_-]{8,}" "$trace")
[ "$keys" = "0" ] && echo "ok    no keys in trace" || { echo "FAIL $keys key-like strings in trace"; rc=1; }
exit $rc
