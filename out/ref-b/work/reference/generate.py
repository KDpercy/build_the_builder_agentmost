"""Reference generator: spec.json + tool API file -> Freya workflow.

    python3 builder/reference/generate.py <spec.json> <tool_api.json> <out_workflow.json>

Flow (one to three products): setup -> opening -> (third_party | identity) -> load_account ->
compute_debt -> debt (today question) -> product_k ... -> readback -> end, plus one node per
special case that has a fixed line (a one-time offer), and failure exits.
Every brief-specific word comes from the spec. A builder run copies this file into its work
folder and edits it only where the brief has a rule the spec cannot express.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
# Works from builder/reference and from a copy in a run's work/ folder (lib stays in builder/).
for p in (HERE.parent.parent / "builder", HERE.parent):
    sys.path.insert(0, str(p))
from lib import nodes as N  # noqa: E402
from reference import code as C  # noqa: E402
from reference import hooks as H  # noqa: E402
from reference import prompts as P  # noqa: E402


def tools_for(spec: dict, api: dict) -> dict:
    """Every tool the workflow may use, built from the tool API file."""
    tn, tf = spec["tool_names"], spec.get("tool_fields", {})
    cust = {tf["customer"]: "{{" + spec["customer_variable"] + "}}"}       # required spec keys: fail loudly if missing
    notes_used = bool((spec.get("notes") or {}).get("used"))
    t = {
        "verify": N.api_tool(api, tn["verify"], "Checks one security answer. CALL it every time the customer gives a complete answer "
                             "to a security question, once per answer.", baked=cust, pre=H.verify_pre(spec), post=H.verify_post(spec)),
        "transfer": N.api_tool(api, tn["transfer"], P.transfer_description(spec), baked=cust,
                               post=H.simple_post("The transfer is done. Tell the customer you are connecting them now, thank them, say goodbye "
                                                  "and call the closing tool.",
                                                  "The transfer did NOT work. Never say they are being transferred. Call it once more with the "
                                                  "same queue; if it fails again, tell the customer and continue.")),
        "close": N.api_tool(api, tn["close"], "Ends the call in the bank's records. CALL it exactly once, as the very last tool call, always with the outcome (and the reason when there is one). "
                            "In the SAME message, before calling it, thank the customer and say goodbye.", baked=cust,
                            pre=H.close_pre(spec),
                            post=H.simple_post("", "The closing call failed. If the error says the call is already closed, say nothing and do nothing more. "
                                                   "Otherwise call it once more with the outcome and the reason filled in. Say nothing else.")),
        "promise": N.api_tool(api, tn["promise"], "Records the payment promise of ONE product. CALL it only after the single read-back of all "
                              "agreed products got a clear yes. Once per agreed product, one per message, in product order.",
                              baked=cust, pre=H.promise_pre(spec), post=H.promise_post(spec)),
        "callback": N.api_tool(api, tn["callback"], "Books a callback. CALL it as soon as the person gives a day and a time inside the "
                               "callback window.", baked=cust,
                               post=H.simple_post(P.callback_ok(spec), P.callback_fail(spec))),
    }
    if notes_used and tn.get("note"):
        t["note"] = N.api_tool(api, tn["note"], "Records why ONE product ended without a promise. CALL it only at the end of the call, "
                               "once for every product without a recorded promise. NEVER call it when the call is transferred.",
                               baked=cust, pre=H.note_pre(spec),
                               post=H.simple_post("The note is saved. Write the next note, if any, then close.",
                                                  "The note was NOT saved. Try once more, then continue."))
    return t


def build(spec: dict, api_spec: dict) -> dict:
    api = N.api_spec_tools(api_spec)
    tn = spec["tool_names"]
    T = tools_for(spec, api)
    closed = N.tool_ok("end", tn["close"])
    give_up = N.failed_more_than("end", tn["close"], 1)
    specials = sorted(spec.get("special_cases") or [], key=lambda s: s.get("precedence", 99))
    names = [s["name"] for s in specials]
    extraction = ([N.enum_extraction("special_case", names, P.special_extraction(specials))] if names else []) + [P.too_much_extraction()]
    offer_nodes = [s for s in specials if s.get("line")]
    to_offer = [N.var_is("sc_" + s["name"], "the customer said: " + s.get("trigger", s["name"]), "special_case", [s["name"]])
                for s in offer_nodes]
    end_tools = [T["promise"]] + ([T["note"]] if "note" in T else []) + [T["transfer"], T["close"]]
    nodes = {
        "setup": N.code_node("setup", C.setup_source(spec), [N.always("opening")]),
        "opening": N.conversation("opening", P.opening_task(spec), [T["transfer"], T["close"]],
                                  [closed, give_up, N.var_is("identity", "the customer confirmed who they are", "speaker", ["customer"]),
                                   N.var_is("third_party", "someone else answered", "speaker", ["someone_else"])],
                                  N.says(P.opening_line(spec)), extraction=[P.speaker_extraction(spec)]),
        "third_party": N.conversation("third_party", P.third_party_task(spec), [T["callback"], T["transfer"], T["close"]],
                                      [closed, give_up, N.failed_more_than("callback_failed", tn["callback"], 1)], {"type": "llm"}),
        "callback_failed": N.conversation("callback_failed", P.callback_failed_task(spec), [T["close"]], [closed, give_up], {"type": "llm"}),
        "identity": N.conversation("identity", P.identity_task(spec), [T["verify"], T["transfer"], T["close"]],
                                   [closed, give_up, N.failed_more_than("service_down", tn["verify"], 1),
                                    N.var_is("load_account", "all security answers verified",
                                             tn["verify"] + "_response.data." + spec["identity"].get("response", {}).get("all_verified", "all_verified"),
                                             ["true", "True"])],
                                   N.says(spec["identity"]["first_line"])),
        "service_down": N.conversation("service_down", P.service_down_task(spec), [T["close"]], [closed, give_up], {"type": "llm"}),
        "load_account": {
            "name": "load_account", "node_type": "api_request", "passthrough": True,
            "passthrough_default_transition": "compute_debt", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
            "pre_actions": [N.api_tool(api, tn["account"], "Get the late products.", baked={spec["tool_fields"]["customer"]: "{{" + spec["customer_variable"] + "}}"},
                                       post=C.GET_ACCOUNT_POST, retries=2)],
            "response_mapping": C.products_mapping(spec), "transitions": [N.always("compute_debt")],
        },
        "compute_debt": N.code_node("compute_debt", C.debt_source(spec),
                                    [N.var_is("debt", "account facts ready", "debt_state", ["ok"]), N.always("account_error")]),
        "account_error": N.conversation("account_error", P.account_error_task(spec), [T["close"]], [closed, give_up], {"type": "llm"}),
        "debt": N.conversation("debt", P.debt_task(spec), [T["transfer"], T["close"]],
                               [closed, give_up] + to_offer + [
                                   P.tool_move("readback", "CALL it when the customer can pay everything today, or agreed one allowed date for everything."),
                                   P.tool_move("product_1", "CALL it for any other answer, to go through the products one by one.")],
                               N.says("{{debt_line}}"), extraction=extraction),
        "readback": N.conversation("readback", P.readback_task(spec), end_tools, [closed, give_up], {"type": "llm"}, max_turns=40),
        "end": N.end_node(),
    }
    for k in range(1, C.MAX_PRODUCTS + 1):
        done = f"product_{k}_done"
        nodes[f"product_{k}"] = N.conversation(
            f"product_{k}", P.product_task(spec, k), [T["transfer"]],      # no close tool: closing happens after read-back
            [closed, give_up] + to_offer + [P.tool_move(done, f"CALL it when product {k} is settled: agreed amount and date, refused after its "
                                                              "attempts, or settled by a special case.")],
            {"type": "llm"}, extraction=extraction, max_turns=40)
        nxt = [{"target_node": f"product_{k + 1}", "description": "another product follows",
                "condition": {"logic": "or", "conditions": [{"variable": "n_products", "operator": "greater_than", "operand": k}]}}] \
            if k < C.MAX_PRODUCTS else []
        nodes[done] = N.code_node(done, f"vars['handled_products'] = '{k}'\n", nxt + [N.always("readback")])
    # Deterministic retry of a failed promise (the model must not decide or talk before it).
    tf = spec.get("tool_fields", {})
    pr = tn["promise"]
    # The engine stores call arguments under the placeholder name: <tool>_args.<tool>_<field>.
    args = {tf.get(k, k): "{{" + pr + "_args." + pr + "_" + tf.get(k, k) + "}}" for k in ("product", "amount", "date")}
    args[tf["customer"]] = "{{" + spec["customer_variable"] + "}}"
    retry = N.api_tool(api, pr, "Retry the last failed promise once.", baked=args, pre=H.promise_pre(spec))
    nodes["retry_promise"] = {
        "name": "retry_promise", "node_type": "api_request", "passthrough": True,
        "passthrough_default_transition": "promise_retry_failed", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
        "pre_actions": [retry], "response_mapping": [{"path": "data.ok", "variable": "retry_ok"}],
        "transitions": [N.var_is("promise_retry_ok", "the retry recorded the promise", "retry_ok", ["true", "True"]),
                        N.always("promise_retry_failed")],
    }
    nodes["promise_retry_ok"] = N.conversation("promise_retry_ok", P.retry_ok_task(spec), end_tools, [closed, give_up], {"type": "llm"})
    nodes["promise_retry_failed"] = N.conversation("promise_retry_failed", P.retry_failed_task(spec), end_tools, [closed, give_up],
                                                   {"type": "llm"})
    to_retry = N.failed_more_than("retry_promise", pr, 0)
    nodes["readback"]["transitions"].insert(2, to_retry)
    for s in offer_nodes:
        nodes["sc_" + s["name"]] = N.conversation("sc_" + s["name"], P.offer_task(spec, s), end_tools, [closed, give_up, to_retry],
                                                  N.says(s["line"]), max_turns=40)
    return {"initial_node": "setup", "system_prompt": P.system_prompt(spec), "nodes": nodes, "global_nodes": {},
            "test_variables": {spec["customer_variable"]: "c_test", spec.get("now_variable") or "now": "2030-01-07T11:00"}}


def main(argv: list) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    spec, api = json.loads(pathlib.Path(argv[1]).read_text()), json.loads(pathlib.Path(argv[2]).read_text())
    pathlib.Path(argv[3]).write_text(json.dumps(build(spec, api), indent=1))
    print(argv[3])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
