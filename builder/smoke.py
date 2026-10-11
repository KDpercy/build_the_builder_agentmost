"""Run the generated code steps locally on a fake call, before anything reaches the platform.

    python3 builder/smoke.py <workflow.json> <tool_api.json> <spec.json>

Builds a fake account from the account tool's response schema in the tool API file, stores it
the way the platform does (flattened: <node>_response.data.<list>.<i>.<field>), runs every code
node in order on several dates, and fails if the account facts come out in an error state.
"""
import json
import sys


def fake_value(name: str, schema: dict, i: int):
    if schema.get("enum"):
        return schema["enum"][i % len(schema["enum"])]
    t = schema.get("type")
    if t == "integer":
        return [3, 12, 25, 40, 60][i % 5]
    if t == "number":
        return [120.0, 840.5, 2100.0][i % 3]
    return f"x{i}{name[:2]}"


def fake_account(api: dict, spec: dict, n: int) -> dict:
    """Flattened variables for an account reply with n products, from the response schema."""
    name = spec["tool_names"]["account"]
    resp = api["paths"]["/" + name]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["properties"]
    path = str((spec.get("products") or {}).get("response_path") or "data.products").split(".")[-1]
    items = resp[path]["items"]["properties"]
    out = {}
    for i in range(n):
        for f, sch in items.items():
            out[f"load_account_response.data.{path}.{i}.{f}"] = fake_value(f, sch, i)
    return out


def run(workflow: dict, api: dict, spec: dict) -> list:
    problems = []
    codes = [n for n in workflow["nodes"].values() if n.get("node_type") == "code"]
    now_var = spec.get("now_variable") or "now"
    for now in ("2030-01-07T09:00", "2030-01-11T15:30", "2030-02-28T18:59"):
        for n_products in (1, 2, 3):
            v = {now_var: now, **fake_account(api, spec, n_products)}
            for node in codes:
                code = node["pre_actions"][0]["function"]["parameters"]["properties"]["code"]["default"]
                try:
                    exec(code, {"vars": v})
                except Exception as e:     # a code step must never raise
                    problems.append(f"{node['name']} raised {e!r} (now={now}, products={n_products})")
            for key in ("date_state", "debt_state"):
                if key in v and str(v[key]) != "ok":
                    problems.append(f"{key} = {v[key]!r} {v.get('debt_error', '')} (now={now}, products={n_products})")
            if v.get("debt_state") == "ok" and v.get("n_products") != str(n_products):
                problems.append(f"read {v.get('n_products')} products, expected {n_products}")
    return problems


def main(argv: list) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    wf, api, spec = (json.load(open(p)) for p in argv[1:4])
    problems = run(wf, api, spec)
    for p in problems[:20]:
        print("ERROR", p)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
