"""Workflow building blocks. Tool shapes come from the bank's tool API file at run time.

Nothing here is specific to one brief: no URL, field name, allowed value or sentence.
"""


def api_spec_tools(spec: dict) -> dict:
    """Tool name -> {"url", "props": {field: schema}, "required": [...]} from an OpenAPI file."""
    base = (spec.get("servers") or [{}])[0].get("url", "").rstrip("/")
    tools = {}
    for path, ops in spec.get("paths", {}).items():
        for method, op in ops.items():
            schema = (op.get("requestBody", {}).get("content", {})
                      .get("application/json", {}).get("schema", {}))
            tools[path.strip("/").split("/")[-1]] = {
                "url": base + path, "method": method.upper(),
                "props": schema.get("properties", {}), "required": schema.get("required", []),
                "summary": op.get("summary", "") or op.get("description", ""),
            }
    return tools


def api_tool(api: dict, name: str, description: str, fields: dict | None = None, baked: dict | None = None,
             pre: str = "", post: str = "", retries: int = 0, timeout_ms: int = 12000) -> dict:
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
                "url": {"type": "string", "default": t["url"]},
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
