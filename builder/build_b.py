"""Generate out/brief-b.workflow.json for Brief B (Brief A plus up to three products).

    python3 builder/build_b.py

Opening, third party and identity steps are Brief A's (Brief B keeps every Brief A rule).
The debt phase is rebuilt for one to three products: code computes per-product facts,
notes are deferred to the end of the call, and close_call derives the outcome from what
was actually recorded.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_a as BA  # noqa: E402
import hooks_a as HA  # noqa: E402
import hooks_b as HB  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTE_REASONS = ["refused", "hardship", "dispute", "paid", "service_error"]


def promise_tool() -> dict:
    return BA.api_tool(
        "create_promise",
        "Records the payment promise of ONE product. CALL it only after the single read-back of all agreed products got a clear yes. "
        "Call it once per agreed product, one per message, in product order. Never call it twice for a recorded product.",
        {
            "product_id": {"type": "string", "default": "{{product_id}}",
                           "description": "The product_id exactly as written in the product facts, for example p1."},
            "amount": {"type": "number", "default": "{{amount}}", "description": "The agreed amount for this product, a number such as 637.50."},
            "date": {"type": "string", "default": "{{date}}", "description": "The agreed payment date for this product as YYYY-MM-DD."},
        },
        ["product_id", "amount", "date"], pre=HB.PROMISE_PRE, post=HB.PROMISE_POST,
    )


def note_tool() -> dict:
    return BA.api_tool(
        "add_note",
        "Records why ONE product ended without a promise. CALL it only at the end of the call, after the promises are recorded, "
        "once for every product that has no recorded promise. NEVER call it when the call is transferred.",
        {
            "product_id": {"type": "string", "default": "{{product_id}}",
                           "description": "The product_id exactly as written in the product facts, for example p2."},
            "reason": {"type": "string", "enum": NOTE_REASONS, "default": "{{reason}}",
                       "description": "One of: refused, hardship, dispute, paid, service_error."},
            "text": {"type": "string", "default": "{{text}}", "description": "One short sentence on what the customer said."},
        },
        ["product_id", "reason"], pre=HB.NOTE_PRE, post=HB.NOTE_POST,
    )


def close_call_tool() -> dict:
    tool = BA.close_call_tool()
    tool["pre_process_code"] = HB.CLOSE_PRE
    return tool


FACTS = """{{products_block}}

DATE WORDS
{{week_table}}

CALENDAR. Each line says, per product, what to do when the customer names that day:
{{calendar}}"""

END_RULES = """NEVER ask "how much can you pay?" or any question that lets them choose the amount. You propose every amount.

READ-BACK (once, for all agreed products together)
- When every product is settled, read back ALL agreed products in ONE message: for each, the product, the amount and the date (weekday, day, month). If a product's date was moved to its own deadline, say so for that product. End with "Do you confirm?". Ask for one confirmation only.
- If they change a date or an amount, check the new value with the rules above and read everything back again.
- If no product is agreed, skip the read-back.

RECORD
- After a clear yes, call create_promise once per agreed product, in product order, one per message, with that product's product_id, the amount as a number and the date as YYYY-MM-DD.
- Follow what_to_do_next after each result. Never say a promise is recorded until create_promise said so. After all are recorded say once: "You will receive a text message confirming this promise."
- A recorded promise cannot be changed or cancelled in this call; if asked, say they can change it in the mobile app.

NOTES (only when the call is NOT transferred)
- After the promises, call add_note once for every product without a recorded promise, one per message, with its product_id and its reason: refused, hardship, dispute, paid or service_error (create_promise failed twice).
- After a transfer, never call add_note.

CLOSE
- Then thank the customer, say goodbye, and in the same message call close_call.
- Outcome: promise if at least one promise was recorded. Otherwise paid if every product was noted paid. Otherwise no_promise with the reason of the first product, in product order, whose note is not paid."""

DEBT_TASK = """The customer is verified. You have already said you are calling from the collections team, stated every late product with its past-due amount and days late, and asked ONE question: whether they can pay today. Products ({{n_products}}): {{product_list}}.

Your only job in this step is the answer to that today question. Never ask about today again.

Check the customer's answer in this order:
1. They can pay EVERYTHING today: say "Thank you." and in the same message call transition_to_readback.
2. There are two or more products, and they name ONE date for everything (for example "all of them on Friday", "both on the 30th"), and give no other condition. (With only one product, use rule 5.): look the date up in the DAYS list below. If it is NOT a business day, offer the next business day and wait for their answer. If it is a business day, say "Thank you." and in the same message call transition_to_readback. Never talk about deadlines or a latest date in this step, and never propose another date: a product whose deadline is earlier is moved to its own deadline automatically in the read-back.
3. They ask for a new payment plan or lower instalments: describe no plan and call transfer_to_agent with queue restructuring.
4. They ask for a human: ask once whether you can help first. If they insist, call transfer_to_agent with queue general.
5. Anything else (a no, a no for some products, a date or amount for one product only, already paid or not mine for one product, too much, a question): say "I understand, let us go through them one by one." and in the same message call transition_to_product_1. Never make an offer in this step.

DAYS
{{day_table}}

DATE WORDS
{{week_table}}

Never call add_note or create_promise in this step."""


def product_task(k: int) -> str:
    return f"""You are now handling PRODUCT {k} only. Products before it are settled; do not reopen them. Do not talk about later products yet.

{{{{p{k}_block}}}}

CALENDAR for this product. Each line says what to do when the customer names that day:
{{{{p{k}_calendar}}}}

DATE WORDS
{{{{week_table}}}}

YOUR FIRST MESSAGE IN THIS STEP. Look at what the customer already said about THIS product earlier in the call:
- They already named a date and/or amount for it: handle it with rule 5 below (with only a date, the amount is the full past-due amount).
- They already said it is paid, or not theirs: handle it with rule 2 or 3.
- Otherwise, including when they said earlier that they will not pay it: make attempt 1 now. Say exactly: "{{{{p{k}_a1_line}}}}" (if they already said the full amount of this product is too much, say "{{{{p{k}_a1_floor_line}}}}" instead). A refusal said before your first offer for this product uses no attempt.

RULES. Check the customer's replies in this order:
1. Illness, a death in the family or job loss: handled by another step.
2. They say they already paid this product: say that payments can take one business day to appear. No promise for it. Say "Noted." and in the same message call transition_to_product_{k}_done.
3. They say this product is not theirs, they never had it, or it was closed or paid off in the past: do not argue. No promise for it. Say "Noted." and in the same message call transition_to_product_{k}_done.
4. They ask for a new payment plan or lower instalments: describe no plan, call transfer_to_agent with queue restructuring. They ask for a human: ask once whether you can help first; if they insist, call transfer_to_agent with queue general.
5. They name a date and/or an amount. This is NEVER a refusal.
   - Date: find it in the CALENDAR above and do exactly what its line says. If they refuse the deadline after you offered it, that is a flat refusal (rule 7).
   - A vague period ("next week", "end of the month", "when my salary comes"): ask once for the exact day. If they still give none, propose the deadline.
   - Amount: from the floor up to the full past-due amount, both included, is accepted. Below the floor: say you cannot accept that amount and offer the floor once; if they do not accept, that is a flat refusal (rule 7).
   - With only an amount, ask on which day they can pay it.
   - When an allowed amount and an allowed date are agreed: say "Noted, <amount> on <weekday day month>." and in the same message call transition_to_product_{k}_done. Do not ask "Do you confirm?" here: everything is confirmed together later.
6. They say in words that the full amount is TOO MUCH or more than they can afford (a plain no is NOT this): say "{{{{p{k}_floor_line}}}}" and ask if they can pay it on the attempt 1 date. Only once. If they refuse the floor, that is a flat refusal (rule 7).
7. A flat refusal or a non-answer about this product: {{{{p{k}_attempt_rule}}}} Never repeat an offer they refused. When this product's attempts are used up: say "I understand." and in the same message call transition_to_product_{k}_done.
8. They say a second time that they do not want to talk at all: say "I understand." and call transition_to_product_{k}_done.

NEVER ask "how much can you pay?". You propose every amount. Never ask about paying today. Never call create_promise or add_note in this step."""


READBACK_TASK = """Every product has been handled. Products ({{n_products}}): {{product_list}}.

""" + FACTS + """

Look at the whole conversation and work out, for each product in product order, its status: agreed (amount and date), refused, paid (they said they already paid it), dispute (they said it is not theirs or was closed), or hardship.
If the customer named one date for everything: each product is agreed at its full past-due amount on that date, except a product whose deadline is earlier: that product is agreed on its own deadline.

YOUR FIRST MESSAGE IN THIS STEP: if at least one product is agreed, the single read-back of all agreed products, ending with "Do you confirm?". If no product is agreed, call add_note for the first product.

""" + END_RULES


HARDSHIP_LINE = "I am sorry to hear that. Would you like me to connect you with our customer support team?"

HARDSHIP_TASK = """The customer mentioned illness, a death in the family or losing their job. You have ALREADY said one sentence of sympathy and offered once to connect them with the customer support team. Never say sympathy again and never repeat that offer. Make NO persuasion attempt: propose no amount and no date.

Check these in order:
- They accept: call transfer_to_agent with queue support. Call no add_note.
- They said no to the support team, at any point in this step: they declined. If they also asked for a discount or a waiver, say you cannot offer one. If they agreed a promise earlier in this call for some product, read those back once, ask "Do you confirm?" and record them with create_promise after a yes. Then call add_note with reason hardship for every product without a promise (keep paid or dispute for a product they said was paid or not theirs), one per message. Then thank them, say goodbye, and in the same message call close_call. Never ask them again.
- They ask for a discount or a waiver and have not answered the offer: say you cannot offer one. Nothing more.
- Their reply is cut off or about something else: say "Take your time." and nothing more.
- They ask for a new payment plan or lower instalments: describe no plan, call transfer_to_agent with queue restructuring. Call no add_note.
- They name a date or an amount THEMSELVES for a product: check it in the CALENDAR and against that product's floor and past-due amount; with only a date, the amount is the full past-due amount. Never suggest an amount or a date yourself.

""" + FACTS + "\n\n" + END_RULES

ERROR_TASK = """The account details could not be loaded. Tell the customer that you cannot access the details right now and that nothing was saved. Thank them, say goodbye, and call close_call with outcome no_promise and reason service_error."""

SPECIAL = [{
    "name": "special_case",
    "type": "string",
    "enum_values": ["hardship"],
    "description": "hardship as soon as the customer says they are ill, someone in their family died, or they lost their job. "
                   "Leave it empty for anything else, including small talk, a refusal, a date, an amount, a dispute, a payment plan request.",
    "min_confidence": 0.6,
}]


def tool_move(target: str, description: str) -> dict:
    return {"target_node": target, "description": description, "is_tool_call": True,
            "condition": {"operator": "matches_intent", "description": description}}


def get_account_node() -> dict:
    fn = BA.api_tool("get_account", "Get the late products.", {}, [], post=HB.GET_ACCOUNT_POST, retries=2)
    mapping = [{"path": "data.products", "variable": "products"}]
    for i in range(1, HB.MAX_PRODUCTS + 1):
        mapping += [{"path": f"data.prod{i}_{k}", "variable": f"acc{i}_{k}"} for k in HB.FIELDS]
    return {
        "name": "load_account",
        "node_type": "api_request",
        "passthrough": True,
        "passthrough_default_transition": "compute_debt",
        "on_enter": {"type": "silent"},
        "disable_inactivity_monitor": True,
        "pre_actions": [fn],
        "response_mapping": mapping,
        "transitions": [BA.always("compute_debt")],
    }


def build() -> dict:
    wf = BA.build()
    nodes = wf["nodes"]
    for k in ["debt", "floor", "hardship", "retry_promise", "promise_done", "promise_failed"]:
        nodes.pop(k, None)
    # close_call in every node uses the Brief B outcome hook
    for node in nodes.values():
        for i, t in enumerate(node.get("tools", [])):
            if t["function"]["name"] == "close_call":
                node["tools"][i] = close_call_tool()
    nodes["load_account"] = get_account_node()
    nodes["compute_debt"] = BA.code_node("compute_debt", HB.DEBT_CODE, [
        BA.var_is("debt", "account facts ready", "debt_state", ["ok"]),
        BA.always("account_error")])
    to_hardship = BA.var_is("hardship", "the customer mentioned illness, a death in the family or job loss", "special_case", ["hardship"])
    nodes["debt"] = BA.conv(
        "debt", DEBT_TASK, [BA.transfer_tool(), close_call_tool()],
        [BA.CLOSED, BA.CLOSE_GIVEUP, to_hardship,
         tool_move("readback", "CALL it when the customer can pay everything today, or agreed one allowed date for everything."),
         tool_move("product_1", "CALL it for any other answer to the today question, to go through the products one by one.")],
        {"type": "tts", "text": "{{debt_line}}"}, extraction=SPECIAL)
    for k in range(1, HB.MAX_PRODUCTS + 1):
        done = f"product_{k}_done"
        nodes[f"product_{k}"] = BA.conv(
            f"product_{k}", product_task(k), [BA.transfer_tool(), close_call_tool()],
            [BA.CLOSED, BA.CLOSE_GIVEUP, to_hardship,
             tool_move(done, f"CALL it when product {k} is settled: agreed amount and date, refused after its attempts, paid or disputed.")],
            {"type": "llm"}, extraction=SPECIAL)
        nodes[f"product_{k}"]["max_node_turns"] = 40
        nxt = f"product_{k + 1}" if k < HB.MAX_PRODUCTS else "readback"
        trans = [BA.always("readback")]
        if k < HB.MAX_PRODUCTS:
            trans = [{"target_node": nxt, "description": "another product follows",
                      "condition": {"logic": "or", "conditions": [
                          {"variable": "n_products", "operator": "greater_than", "operand": k}]}}, BA.always("readback")]
        nodes[done] = BA.code_node(done, f"vars['handled_products'] = '{k}'\n", trans)
    nodes["readback"] = BA.conv(
        "readback", READBACK_TASK, [promise_tool(), note_tool(), BA.transfer_tool(), close_call_tool()],
        [BA.CLOSED, BA.CLOSE_GIVEUP], {"type": "llm"})
    nodes["readback"]["max_node_turns"] = 40
    nodes["hardship"] = BA.conv(
        "hardship", HARDSHIP_TASK, [promise_tool(), note_tool(), BA.transfer_tool(), close_call_tool()],
        [BA.CLOSED, BA.CLOSE_GIVEUP], {"type": "tts", "text": HARDSHIP_LINE})
    nodes["account_error"] = BA.conv(
        "account_error", ERROR_TASK, [close_call_tool()], [BA.CLOSED, BA.CLOSE_GIVEUP], {"type": "llm"})
    wf["test_variables"] = {"customer_id": "c_test", "first_name": "Sofia", "last_name": "Almeida", "title": "Ms",
                            "now": "2026-10-14T11:00"}
    return wf


if __name__ == "__main__":
    out = ROOT / "out" / "brief-b.workflow.json"
    out.write_text(json.dumps(build(), indent=1))
    print(out)
