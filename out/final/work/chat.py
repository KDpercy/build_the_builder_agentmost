import json,sys,freya
wid=json.load(open('.freya-agents.json'))['final']['workflow_id']
cno=sys.argv[1]; lines=sys.argv[2:]
v={"customerNumber":cno,"now":"2026-10-12T10:30:00+03:00"}
cid=None
for m in lines:
    body={"workflowId":wid,"message":m,"customerVariables":v}
    if cid: body["callId"]=cid
    try: r=freya.api("POST","/api/v2/chat/message",body)
    except Exception as e: print("ERR",str(e)[:300]); continue
    cid=r.get("callId",cid); print("USER:",m); print("AGENT:",r.get("response"))
try: freya.api("POST","/api/v2/chat/end",{"callId":cid})
except Exception: pass
