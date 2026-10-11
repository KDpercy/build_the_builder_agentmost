import sys, json, freya, time
wf = sys.argv[1]; cust = sys.argv[2]; lines = sys.argv[3:]
vars_ = {"customerNumber": cust, "now": "2026-10-12T10:30:00+03:00"}
cid = None
for m in ["Alo"] + lines:
    body = {"workflowId": wf, "message": m, "customerVariables": vars_}
    if cid: body["callId"] = cid
    for a in range(2):
        try:
            r = freya.api("POST", "/api/v2/chat/message", body); break
        except RuntimeError as e:
            print("ERR", str(e)[:200]); time.sleep(3); r = {}
    cid = r.get("callId", cid)
    print("USER:", m); print("BOT :", r.get("response")); print(flush=True)
try: freya.api("POST", "/api/v2/chat/end", {"callId": cid})
except Exception as e: pass
