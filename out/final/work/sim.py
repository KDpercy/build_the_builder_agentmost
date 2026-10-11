import json, re, freya, sys
txt = open('input/case/example-scenarios.md').read()
parts = re.split(r'\n## Example \d+: ', txt)[1:]
personas, vars_ = [], []
for p in parts:
    title = p.split('\n')[0]
    cust = re.search(r'Customer number:\*\* `(\d+)`', p).group(1)
    now = re.search(r'now:\*\* `([^`]+)`', p).group(1)
    sit = re.search(r'\*\*Situation:\*\* (.*?)\n', p).group(1)
    exp = p.split('**Expected behaviour:**')[1].split('---')[0].strip()
    personas.append({"name": "final-" + title[:40], "prompt": "Sen Freya Bank müşterisisin ve bankanın sesli asistanını aradın. Yalnızca Türkçe, kısa konuş. Durum: " + sit + " Asistan sorduğunda buna göre cevap ver; amacına ulaşınca veya yönlendirilince görüşmeyi bitir.",
                     "successCriteria": exp, "tags": ["final-practice"]})
    vars_.append({"customerNumber": cust, "now": now})
made = freya.create_personas(personas)["personas"]
vmap = {m["id"]: v for m, v in zip(made, vars_)}
sim, it, st = freya.run_simulation(sys.argv[1], "final-examples", vmap, max_seconds=300)
print(sim, it, st)
res = freya.get_iteration(sim, it)
json.dump(res, open('work/sim_result.json', 'w'), ensure_ascii=False, indent=1)
for r in res.get("runs", []):
    print(json.dumps({k: r.get(k) for k in ("personaName", "personaId", "callId", "successCriteriaResult", "status")}, ensure_ascii=False)[:1500])
