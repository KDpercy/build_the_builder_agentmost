"""Ask the live mock every stored answer of test-customers.json and compare status and body."""
import json, sys, urllib.request, urllib.error
BASE = sys.argv[1].rstrip("/") + "/voice/v1/"
data = json.load(open(sys.argv[2]))["customers"]
CUST = {"cards.list": {"aiFlow": "CardOps"}, "contact.email.get": {"intAddressInfoType": "E"}}
ok = bad = 0
def call(service, body):
    req = urllib.request.Request(BASE + service, json.dumps({"data": body, "call": {"lang": "tr"}}).encode(), {"content-type": "application/json", "User-Agent": "mock-sweep/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r: st, raw = r.status, r.read()
    except urllib.error.HTTPError as e: st, raw = e.code, e.read()
    try: return st, json.loads(raw)
    except ValueError: return st, "NOT JSON: " + raw[:200].decode(errors="replace")
for c in data:
    no, svcs = c["customerNo"], c["services"]
    cards = (svcs["cards.list"]["response"].get("data") or {}).get("cards", [])
    for service, node in svcs.items():
        cases = []
        if "http" in node:
            body = {"customerNo": no, **CUST.get(service, {})}
            if service == "statement.pdf.send":
                body.update(cardNumber=cards[0]["cardNumber"] if cards else "x", currencyType="TL", statementDate="01.01.2026", emailAddress="a@b")
            cases.append((body, node))
        else:
            for card, v in node.items():
                if "http" in v: cases.append(({"cardNumber": card}, v))
                else:
                    for w, x in v.items(): cases.append(({"cardNumber": card, "newStatementWeek": int(w), "statementDay": 5}, x))
        for body, want in cases:
            st, got = call(service, body)
            if st == want["http"] and got == want["response"]: ok += 1
            else:
                bad += 1; print("DIFF", no, service, body, st, want["http"], str(got)[:120])
print(ok, "match,", bad, "differ")
