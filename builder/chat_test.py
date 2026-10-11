"""Talk to a saved workflow turn by turn through Freya's chat API, with call variables, and print
what the agent says and which tools it called. For cases without practice customers on Freya.

    python3 builder/chat_test.py <workflow_id> '<call variables as JSON>' "first customer line" "second line" ...
    python3 builder/chat_test.py <workflow_id> --script conversations.json

conversations.json: [{"name": "...", "variables": {...}, "say": ["...", "..."]}, ...]
The chat route may skip a first code step (docs/api.md); a 504 on a long turn is retried once.
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def turn(workflow_id: str, message: str, variables: dict, call_id: str | None) -> dict:
    import freya
    body = {"workflowId": workflow_id, "message": message, "customerVariables": variables}
    if call_id:
        body["callId"] = call_id
    for attempt in (1, 2):
        try:
            r = freya.api("POST", "/api/v2/chat/message", body)
            return r.get("result") or r
        except RuntimeError as e:
            if attempt == 2 or "-> 504" not in str(e):
                raise
            time.sleep(5)
    return {}


def tools_called(call_id: str) -> list:
    import freya
    try:
        call = freya.get_call(call_id)
    except Exception as e:  # the call log is a bonus; the conversation is the result
        return [f"(call log unavailable: {str(e)[:80]})"]
    text = json.dumps(call)
    out = []
    for marker in ('"toolName": "', '"tool_name": "', '"functionName": "'):
        i = text.find(marker)
        while i >= 0:
            j = text.find('"', i + len(marker))
            out.append(text[i + len(marker):j])
            i = text.find(marker, j)
    return out


def converse(workflow_id: str, variables: dict, lines: list, name: str = "") -> str:
    print(f"=== {name or 'conversation'} {json.dumps(variables, ensure_ascii=False)}")
    call_id = None
    for line in lines:
        try:
            r = turn(workflow_id, line, variables, call_id)
        except RuntimeError as e:
            print(f"  ERROR {str(e)[:200]}")
            break
        call_id = r.get("callId") or call_id
        print(f"  CUSTOMER: {line}\n  AGENT:    {r.get('response')}")
    if call_id:
        print("  TOOLS:   ", " > ".join(tools_called(call_id)) or "(none found)")
        try:
            import freya
            freya.api("POST", "/api/v2/chat/end", {"callId": call_id})
        except Exception:  # ending is best effort
            pass
    return call_id or ""


def main(argv: list) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    os.chdir(ROOT)
    if argv[2] == "--script":
        for conv in json.load(open(argv[3])):
            converse(argv[1], conv.get("variables", {}), conv.get("say", []), conv.get("name", ""))
        return 0
    converse(argv[1], json.loads(argv[2]), argv[3:])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
