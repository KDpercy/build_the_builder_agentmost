"""Check a Freya workflow file without a model and without the platform.

    python3 builder/validate.py <workflow.json> <tool_api.json> [<rules.json>]

Prints one line per problem and exits 1 if any ERROR was found.
`rules.json` is optional. Its brief-specific values come from the brief at run time:
    {"forbidden_before_verification": ["debt", ...],   words never spoken before the gate
     "restricted_words": ["<word>", ...],               words no fixed spoken line may contain
     "required_sentences": ["<sentence>", ...],
     "call_variables": ["<name>", ...]}                 variables every call starts with
Nothing in this file is specific to one brief.
"""
import json
import re
import sys
from collections import deque

ERROR, WARN = "ERROR", "WARN"
# Our generated agents must never claim an action succeeded before a tool confirmed it, and a
# literal judge reads these words that way. A fixed line spoken before any tool runs must avoid them.
CLAIM_WORDS = ("recorded", "booked", "saved", "transferred", "scheduled")
ENGINE_SUFFIXES = ("_response", "_args", "_status_code", "_success_count", "_failure_count")
CALL_VARIABLES: set = set()          # the brief's call variables come from rules["call_variables"]
PLACEHOLDER = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")
VAR_WRITE = re.compile(r"vars\[\s*['\"](\w+)['\"]\s*\]\s*=")
DYNAMIC_WRITE = re.compile(r"vars\[([^\]]*\+[^\]]*)\]\s*=")


def load_api(spec: dict) -> dict:
    """Map tool name -> {"props": {field: enum or None}, "required": [...], "params": {...}} from an
    OpenAPI file, named exactly as the workflow building blocks name them."""
    from lib.nodes import api_spec_tools
    return {name: {"props": {k: v.get("enum") for k, v in t["props"].items()}, "required": t["required"],
                   "params": t["params"]}
            for name, t in api_spec_tools(spec).items()}


def all_tools(node: dict) -> list:
    return list(node.get("tools", [])) + list(node.get("pre_actions", []))


def code_snippets(node: dict) -> list:
    out = []
    for t in all_tools(node):
        for key in ("pre_process_code", "post_process_code"):
            if t.get(key):
                out.append(t[key])
        fn = t.get("function", {})
        if fn.get("handler", "").endswith("code_exec"):
            out.append(fn.get("parameters", {}).get("properties", {}).get("code", {}).get("default", ""))
    return out


def spoken_lines(node: dict) -> list:
    """Fixed text the agent says word for word."""
    on = node.get("on_enter") or {}
    return [on["text"]] if on.get("type") == "tts" and on.get("text") else []


def conditions(cond: dict) -> list:
    """Flatten a condition tree into its leaf conditions."""
    if not isinstance(cond, dict):
        return []
    if "conditions" in cond:
        return [leaf for c in cond["conditions"] for leaf in conditions(c)]
    return [cond]


def check_nulls(wf, path="workflow") -> list:
    if wf is None:
        return [(ERROR, f"{path} is null; omit the field or use \"\"")]
    if isinstance(wf, dict):
        return [p for k, v in wf.items() for p in check_nulls(v, f"{path}.{k}")]
    if isinstance(wf, list):
        return [p for i, v in enumerate(wf) for p in check_nulls(v, f"{path}[{i}]")]
    return []


def check_structure(wf: dict) -> list:
    out, nodes = [], wf.get("nodes", {})
    if wf.get("initial_node") not in nodes:
        out.append((ERROR, f"initial_node {wf.get('initial_node')!r} is not a node"))
    for name, n in nodes.items():
        kind = n.get("node_type")
        if n.get("tools") and kind != "conversation":
            out.append((ERROR, f"{name}: tools on a {kind} node are dropped by the platform"))
        if n.get("pre_actions") and kind not in ("api_request", "code"):
            out.append((ERROR, f"{name}: pre_actions on a {kind} node are dropped by the platform"))
        trans = n.get("transitions", [])
        for t in trans:
            if t.get("target_node") not in nodes:
                out.append((ERROR, f"{name}: route to missing node {t.get('target_node')!r}"))
        if n.get("passthrough"):
            if not n.get("passthrough_default_transition"):
                out.append((ERROR, f"{name}: passthrough node without passthrough_default_transition"))
            if not trans or trans[-1].get("condition", {}).get("operator") != "always":
                out.append((ERROR, f"{name}: passthrough node must end with an always transition"))
        if kind == "conversation" and any(t["function"]["name"] == "close_call" for t in n.get("tools", [])):
            closes = any("close_call" in str(c.get("variable", "")) for t in trans for c in conditions(t.get("condition")))
            if not closes:
                out.append((ERROR, f"{name}: has close_call but no route on its result to an end node"))
    return out


def check_code(wf: dict) -> list:
    out = []
    for name, n in wf.get("nodes", {}).items():
        for code in code_snippets(n):
            if "{{" in code or "}}" in code:
                out.append((ERROR, f"{name}: code contains '{{{{' or '}}}}', which the platform templates"))
    return out


def check_booleans(wf: dict) -> list:
    out = []
    for name, n in wf.get("nodes", {}).items():
        for t in n.get("transitions", []):
            leaves = conditions(t.get("condition"))
            for c in leaves:
                if c.get("operator") == "equals" and str(c.get("operand")).lower() == "true":
                    spellings = {str(x.get("operand")) for x in leaves
                                 if x.get("variable") == c.get("variable") and x.get("operator") == "equals"}
                    if not {"true", "True"} <= spellings:
                        out.append((ERROR, f"{name}: {c.get('variable')} is tested as a boolean in one spelling only"))
    return out


def graph(wf: dict) -> dict:
    return {k: {t.get("target_node") for t in n.get("transitions", [])} for k, n in wf.get("nodes", {}).items()}


def check_paths(wf: dict) -> list:
    out, nodes, g = [], wf.get("nodes", {}), graph(wf)
    seen, todo = set(), deque([wf.get("initial_node")])
    while todo:
        k = todo.popleft()
        if k in seen or k not in g:
            continue
        seen.add(k)
        todo.extend(g[k])
    for k in nodes:
        if k not in seen:
            out.append((WARN, f"{k}: not reachable from the initial node"))
    ends = {k for k, n in nodes.items() if n.get("node_type") == "end_call"}
    if not ends:
        return out + [(ERROR, "no end_call node")]
    reach_end = set(ends)
    changed = True
    while changed:
        changed = False
        for k, tg in g.items():
            if k not in reach_end and tg & reach_end:
                reach_end.add(k)
                changed = True
    for k in seen - reach_end:
        out.append((ERROR, f"{k}: no path from this node to an end_call node"))
    return out


def check_tools(wf: dict, api: dict) -> list:
    out = []
    for name, n in wf.get("nodes", {}).items():
        for t in all_tools(n):
            fn = t.get("function", {})
            if not fn.get("handler", "").endswith("api_call"):
                continue
            tool = fn.get("name")
            if tool not in api:
                out.append((ERROR, f"{name}: tool {tool!r} is not in the tool API file"))
                continue
            body = fn.get("parameters", {}).get("properties", {}).get("body", {}).get("properties", {})
            for field, spec in body.items():
                if field not in api[tool]["props"]:
                    out.append((ERROR, f"{name}: {tool}.{field} is not a field of the tool API"))
                    continue
                allowed = api[tool]["props"][field]
                for v in spec.get("enum", []) or []:
                    if allowed and v not in allowed:
                        out.append((ERROR, f"{name}: {tool}.{field} value {v!r} is not allowed by the tool API"))
            for field in api[tool]["required"]:
                if field not in body:
                    out.append((ERROR, f"{name}: {tool} is missing required field {field!r}"))
            url = str(fn.get("parameters", {}).get("properties", {}).get("url", {}).get("default", ""))
            for p, info in api[tool].get("params", {}).items():
                if info["required"] and (p + "=" not in url if info["in"] == "query" else "{" + p + "}" in url):
                    out.append((ERROR, f"{name}: {tool} url does not fill the {info['in']} parameter {p!r}"))
    return out


def dynamic_patterns(code: str) -> list:
    """vars['p' + k + '_block'] = ... -> regex ^p\\w+_block$ (computed variable names)."""
    out = []
    for expr in DYNAMIC_WRITE.findall(code):
        parts = [x.strip() for x in expr.split("+")]
        rx = "".join(re.escape(x[1:-1]) if x[:1] in "'\"" and x[-1:] == x[:1] else r"\w+" for x in parts)
        out.append(re.compile("^" + rx + "$"))
    return out


def written_variables(wf: dict) -> tuple:
    names = set(CALL_VARIABLES) | set(wf.get("test_variables", {}))
    patterns = []
    for n in wf.get("nodes", {}).values():
        for code in code_snippets(n):
            names |= set(VAR_WRITE.findall(code))
            patterns += dynamic_patterns(code)
        for m in n.get("response_mapping", []):
            names.add(m.get("variable"))
        for t in n.get("tools", []):
            for m in t.get("response_mapping", []) or []:
                names.add(m.get("variable"))
        for e in n.get("extraction_schema", []) or []:
            names.add(e.get("name"))
    return names, patterns


def check_placeholders(wf: dict, call_variables: list | None = None) -> list:
    out = []
    known, patterns = written_variables(wf)
    known |= set(call_variables or [])
    texts = [("system_prompt", wf.get("system_prompt", ""))]
    for k, n in wf.get("nodes", {}).items():
        texts.append((k, n.get("task_message", "")))
        texts += [(k, s) for s in spoken_lines(n)]
    for where, text in texts:
        for var in PLACEHOLDER.findall(text or ""):
            if var in known or any(s in var for s in ENGINE_SUFFIXES) or any(p.match(var) for p in patterns):
                continue
            out.append((ERROR, f"{where}: {{{{{var}}}}} is never written; it would be spoken literally"))
    return out


def pre_verification_nodes(wf: dict) -> set:
    """Nodes reachable from the start without crossing a route on an identity-verification result."""
    nodes, seen, todo = wf.get("nodes", {}), set(), deque([wf.get("initial_node")])
    while todo:
        k = todo.popleft()
        if k in seen or k not in nodes:
            continue
        seen.add(k)
        for t in nodes[k].get("transitions", []):
            gate = any("verif" in str(c.get("variable", "")) for c in conditions(t.get("condition")))
            if not gate:
                todo.append(t.get("target_node"))
    return seen


def check_rules(wf: dict, rules: dict) -> list:
    out, nodes = [], wf.get("nodes", {})
    for word in rules.get("forbidden_before_verification", []):
        pattern = re.compile(r"\b" + re.escape(word.lower()) + r"\b")
        for k in pre_verification_nodes(wf):
            for line in spoken_lines(nodes[k]):
                if pattern.search(line.lower()):
                    out.append((ERROR, f"{k}: says {word!r} before identity is verified"))
    for k in pre_verification_nodes(wf):
        for line in spoken_lines(nodes[k]):
            for word in CLAIM_WORDS:
                if re.search(r"\b" + word + r"\b", line.lower()):
                    out.append((ERROR, f"{k}: fixed line says {word!r} before any tool confirmed anything; say it in other words"))
    for word in rules.get("restricted_words", []):
        for k, n in nodes.items():
            for line in spoken_lines(n):
                if re.search(r"\b" + re.escape(word.lower()) + r"\b", line.lower()):
                    out.append((WARN, f"{k}: fixed line contains restricted word {word!r}; check it is spoken only when allowed"))
    everything = json.dumps(wf, ensure_ascii=False)
    for sentence in rules.get("required_sentences", []):
        if sentence not in everything:
            out.append((ERROR, f"required sentence missing: {sentence!r}"))
    return out


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def check_ledger(ledger: list, brief_texts: dict) -> list:
    """Every rule quotes its brief word for word and says where the workflow implements it."""
    out, briefs = [], {name: squash(t) for name, t in brief_texts.items()}
    everything = " ".join(briefs.values())
    for r in ledger:
        rid, quote = r.get("id", "?"), squash(r.get("quote", ""))
        if not quote:
            out.append((ERROR, f"rule {rid}: no quote"))
        elif quote not in briefs.get(r.get("file", ""), everything):
            out.append((ERROR, f"rule {rid}: quote not found word for word in {r.get('file') or 'the brief'}"))
        if not str(r.get("implemented_by", "")).strip():
            out.append((ERROR, f"rule {rid}: not implemented anywhere"))
    return out


def validate(wf: dict, api_spec: dict, rules: dict | None = None) -> list:
    api = load_api(api_spec)
    problems = check_nulls(wf)
    for check in (check_structure, check_code, check_booleans, check_paths):
        problems += check(wf)
    problems += check_placeholders(wf, (rules or {}).get("call_variables"))
    problems += check_tools(wf, api)
    problems += check_rules(wf, rules or {})
    return problems


def main(argv: list) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    wf = json.load(open(argv[1]))
    api = json.load(open(argv[2]))
    rules = json.load(open(argv[3])) if len(argv) > 3 else {}
    problems = validate(wf, api, rules)
    for level, msg in problems:
        print(f"{level} {msg}")
    errors = sum(1 for level, _ in problems if level == ERROR)
    print(f"{errors} error(s), {len(problems) - errors} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
