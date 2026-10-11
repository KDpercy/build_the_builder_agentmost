"""Workflow building blocks. Tool shapes come from the bank's tool API file at run time.

Nothing here is specific to one brief: no URL, field name, allowed value or sentence.
"""


import re
from collections import Counter


def _clean(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_")


def tool_names(spec: dict) -> dict:
    """(path, method) -> tool name: the operationId, else the last path segment, else (when two
    services share that segment, e.g. /cards/get and /statement/week/get) the whole path."""
    ops = [(path, method, op) for path, m in spec.get("paths", {}).items() for method, op in m.items()
           if isinstance(op, dict)]
    last = Counter(_clean(path.strip("/").split("/")[-1]) for path, _, _ in ops)
    out = {}
    for path, method, op in ops:
        seg = _clean(path.strip("/").split("/")[-1])
        name = _clean(op.get("operationId", "")) or (seg if last[seg] == 1 else _clean(path.strip("/").replace("/", "_")))
        out[(path, method)] = name
    return out


def api_spec_tools(spec: dict) -> dict:
    """Tool name -> {"url", "method", "props": body fields, "required", "params": query/path
    parameters, "summary"} from an OpenAPI file."""
    base = (spec.get("servers") or [{}])[0].get("url", "").rstrip("/")
    names = tool_names(spec)
    tools = {}
    for (path, method), name in names.items():
        op = spec["paths"][path][method]
        schema = (op.get("requestBody", {}).get("content", {})
                  .get("application/json", {}).get("schema", {}))
        params = {p["name"]: {"in": p.get("in", "query"), "required": bool(p.get("required")),
                              "schema": p.get("schema", {}), "description": p.get("description", "")}
                  for p in op.get("parameters", []) if isinstance(p, dict) and p.get("in") in ("query", "path")}
        tools[name] = {
            "url": base + path, "method": method.upper(),
            "props": schema.get("properties", {}), "required": schema.get("required", []),
            "params": params, "summary": op.get("summary", "") or op.get("description", ""),
        }
    return tools


def tool_url(t: dict, name: str, baked: dict) -> str:
    """The URL with path parameters filled and query parameters appended, each from a call
    variable (baked) or a model-filled placeholder."""
    url, query = t["url"], []
    for p, info in t.get("params", {}).items():
        value = baked.get(p, "{{" + name + "_" + p + "}}")
        if info["in"] == "path":
            url = url.replace("{" + p + "}", value)
        else:
            query.append(f"{p}={value}")
    return url + ("?" + "&".join(query) if query else "")


def api_tool(api: dict, name: str, description: str, fields: dict | None = None, baked: dict | None = None,
             pre: str = "", post: str = "", retries: int = 0, timeout_ms: int = 20000) -> dict:
    """An api_call tool for `name`, every body field taken from the tool API.

    fields: per-field overrides {field: {"description", "default", "enum"}} for model-filled fields.
    baked:  {field: "{{variable}}"} values filled from call variables (hidden from the model).
    Fields not mentioned get a model-filled placeholder named "<tool>_<field>", which no other
    variable uses (a placeholder that matches a variable name would be baked by the engine).
    """
    t = api[name]
    fields, baked = fields or {}, baked or {}
    props = {}
    for field, schema in t["props"].items():
        p = {"type": schema.get("type", "string")}
        if field in baked:
            p["default"] = baked[field]
        else:
            p["default"] = "{{" + name + "_" + field + "}}"
            if schema.get("enum"):
                p["enum"] = list(schema["enum"])
            if schema.get("description"):
                p["description"] = schema["description"]
            p.update(fields.get(field, {}))
        props[field] = p
    tool = {
        "type": "function",
        "config": {"timeoutMs": timeout_ms, "maxRetries": retries},
        "function": {
            "name": name, "handler": "__function__:api_call", "description": description,
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "default": tool_url(t, name, baked)},
                "method": {"type": "string", "default": t["method"]},
                "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                "body": {"type": "object", "properties": props, "required": list(t["required"])},
            }},
        },
    }
    if pre:
        tool["pre_process_code"] = pre
    if post:
        tool["post_process_code"] = post
    return tool


def always(target: str) -> dict:
    return {"target_node": target, "description": "always", "condition": {"operator": "always"}}


def var_is(target: str, description: str, variable: str, values: list) -> dict:
    return {"target_node": target, "description": description, "condition": {"logic": "or", "conditions": [
        {"variable": variable, "operator": "equals", "operand": v} for v in values]}}


def tool_ok(target: str, tool: str) -> dict:
    """Route when a tool result says ok, in both boolean spellings."""
    return var_is(target, f"{tool} succeeded", f"{tool}_response.data.ok", ["true", "True"])


def failed_more_than(target: str, tool: str, times: int) -> dict:
    return {"target_node": target, "description": f"{tool} failed more than {times} time(s)",
            "condition": {"logic": "or", "conditions": [
                {"variable": f"{tool}_failure_count", "operator": "greater_than", "operand": times}]}}


def unless(target: str, description: str, trigger: dict, blocker: str, blocked_values: list) -> dict:
    """Route on `trigger` only when `blocker` holds none of `blocked_values`.

    Works whether an unextracted variable is unset or an empty string.
    """
    return {"target_node": target, "description": description, "condition": {"logic": "or", "conditions": [
        {"logic": "and", "conditions": [trigger, {"variable": blocker, "operator": "is_not_set"}]},
        {"logic": "and", "conditions": [trigger] + [
            {"variable": blocker, "operator": "not_equals", "operand": v} for v in blocked_values]},
    ]}}


def code_node(name: str, code: str, transitions: list) -> dict:
    assert "{{" not in code and "}}" not in code, name
    return {
        "name": name, "node_type": "code", "passthrough": True,
        "passthrough_default_transition": transitions[-1]["target_node"],
        "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
        "pre_actions": [{"type": "function", "function": {
            "name": "code_exec", "handler": "__function__:code_exec",
            "parameters": {"type": "object", "properties": {
                "code": {"type": "string", "default": code},
                "timeout_ms": {"type": "number", "default": 10000}}}}}],
        "transitions": transitions,
    }


def conversation(name: str, task: str, tools: list, transitions: list, on_enter: dict,
                 extraction: list | None = None, max_turns: int = 60) -> dict:
    node = {
        "name": name, "node_type": "conversation", "on_enter": on_enter,
        "on_enter_first_entry_only": True, "task_message": task, "tools": tools,
        "transitions": transitions, "max_node_turns": max_turns,
    }
    if extraction:
        node["extraction_schema"] = extraction
    return node


def says(text: str) -> dict:
    """on_enter that speaks a fixed line word for word."""
    return {"type": "tts", "text": text}


def end_node(name: str = "end") -> dict:
    return {
        "name": name, "node_type": "end_call", "on_enter": {"type": "silent"},
        "disable_inactivity_monitor": True, "transitions": [],
        "terminal": {"type": "function", "function": {
            "name": "call_closed", "handler": "__function__:end_call",
            "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}},
    }


def enum_extraction(name: str, values: list, description: str, min_confidence: float = 0.6) -> dict:
    return {"name": name, "type": "string", "enum_values": list(values), "description": description,
            "min_confidence": min_confidence}
