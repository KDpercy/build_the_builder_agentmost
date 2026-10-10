"""Check a Freya workflow file without a model and without the platform.

    python3 builder/validate.py <workflow.json> <tool_api.json> [<rules.json>]

Prints one line per problem and exits 1 if any ERROR was found.
`rules.json` is optional. Its brief-specific values come from the brief at run time:
    {"forbidden_before_verification": ["debt", ...],   words never spoken before the gate
     "restricted_words": ["recorded", ...],             words no fixed spoken line may contain
     "required_sentences": ["You will receive ...", ...]}
Nothing in this file is specific to one brief.
"""
import json
import re
import sys
from collections import deque

ERROR, WARN = "ERROR", "WARN"
ENGINE_SUFFIXES = ("_response", "_args", "_status_code", "_success_count", "_failure_count")
CALL_VARIABLES = {"customer_id", "first_name", "last_name", "title", "now"}
PLACEHOLDER = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")
VAR_WRITE = re.compile(r"vars\[\s*['\"](\w+)['\"]\s*\]\s*=")
DYNAMIC_WRITE = re.compile(r"vars\[([^\]]*\+[^\]]*)\]\s*=")


def load_api(spec: dict) -> dict:
    """Map tool name -> {"props": {field: enum or None}, "required": [...]} from an OpenAPI file."""
    tools = {}
    for path, ops in spec.get("paths", {}).items():
        for op in ops.values():
            schema = (op.get("requestBody", {}).get("content", {})
                      .get("application/json", {}).get("schema", {}))
            props = {k: v.get("enum") for k, v in schema.get("properties", {}).items()}
            tools[path.strip("/").split("/")[-1]] = {"props": props, "required": schema.get("required", [])}
    return tools


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


def check_placeholders(wf: dict) -> list:
    out = []
    known, patterns = written_variables(wf)
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
    for word in rules.get("restricted_words", []):
        for k, n in nodes.items():
            for line in spoken_lines(n):
                if re.search(r"\b" + re.escape(word.lower()) + r"\b", line.lower()):
                    out.append((WARN, f"{k}: fixed line contains restricted word {word!r}; check it is spoken only when allowed"))
    everything = json.dumps(wf)
    for sentence in rules.get("required_sentences", []):
        if sentence not in everything:
            out.append((ERROR, f"required sentence missing: {sentence!r}"))
    return out


def validate(wf: dict, api_spec: dict, rules: dict | None = None) -> list:
    api = load_api(api_spec)
    problems = check_nulls(wf)
    for check in (check_structure, check_code, check_booleans, check_paths, check_placeholders):
        problems += check(wf)
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
