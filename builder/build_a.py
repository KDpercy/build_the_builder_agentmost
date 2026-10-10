"""Generate out/brief-a.workflow.json for Brief A.

    python3 builder/build_a.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hooks_a as H  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://freya-bank-mock.freyavoice.workers.dev/v1"
OUTCOMES = ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"]
REASONS = ["restructuring", "human", "support", "refused", "hardship", "dispute", "service_error",
           "failed", "declined", "callback", "no_callback", "wrong_number", "deceased", "unclear"]


def api_tool(name: str, description: str, fields: dict, required: list, post: str = "", pre: str = "",
             retries: int = 0, mapping: list | None = None) -> dict:
    props = {"customer_id": {"type": "string", "default": "{{customer_id}}"}}
    props.update(fields)
    tool = {
        "type": "function",
        "config": {"timeoutMs": 12000, "maxRetries": retries},
        "function": {
            "name": name,
            "handler": "__function__:api_call",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "default": f"{BASE}/{name}"},
                    "method": {"type": "string", "default": "POST"},
                    "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                    "body": {"type": "object", "properties": props, "required": required},
                },
            },
        },
    }
    if pre:
        tool["pre_process_code"] = pre
    if post:
        tool["post_process_code"] = post
    if mapping:
        tool["response_mapping"] = mapping
    return tool


def close_call_tool() -> dict:
    return api_tool(
        "close_call",
        "Ends the call in the bank's records. CALL it exactly once, as the very last tool call, when the call is over. "
        "In the SAME message, BEFORE calling it, thank the customer and say goodbye. "
        "outcome and reason follow the rules of the current step.",
        {
            "outcome": {"type": "string", "enum": OUTCOMES, "default": "{{outcome}}",
                        "description": "One of: " + ", ".join(OUTCOMES) + "."},
            "reason": {"type": "string", "enum": REASONS, "default": "{{reason}}",
                       "description": "Leave out for promise and paid. transferred: restructuring, human, support. "
                                      "no_promise: refused, hardship, dispute, service_error. not_verified: failed, declined. "
                                      "not_reached: callback, no_callback, wrong_number, deceased, unclear."},
        },
        ["outcome"], pre=H.CLOSE_PRE, post=H.CLOSE_POST,
    )


def transfer_tool() -> dict:
    return api_tool(
        "transfer_to_agent",
        "Hands the call to a person. CALL it only when the rules of this step say so: queue restructuring for a new payment plan "
        "or lower instalments, general when the customer insists on a human, support when a customer in hardship accepts the support team.",
        {"queue": {"type": "string", "enum": ["restructuring", "general", "support"], "default": "{{queue}}",
                   "description": "One of: restructuring, general, support."}},
        ["queue"], post=H.TRANSFER_POST,
    )


def verify_tool() -> dict:
    return api_tool(
        "verify_identity",
        "Checks one security answer. CALL it every time the customer gives an answer to a security question, once per answer.",
        {
            "field": {"type": "string", "enum": ["date_of_birth", "phone_last4"], "default": "{{field}}",
                      "description": "date_of_birth or phone_last4: the question the customer is answering."},
            "answer": {"type": "string", "default": "{{answer}}",
                       "description": "date_of_birth as YYYY-MM-DD (numbers-only dates are day, month, year). phone_last4 as four digits."},
        },
        ["field", "answer"], pre=H.VERIFY_PRE, post=H.VERIFY_POST,
    )


def promise_tool() -> dict:
    return api_tool(
        "create_promise",
        "Records the payment promise. CALL it only after you read back product, amount and date and the customer clearly said yes. "
        "Never call it twice for a recorded promise.",
        {
            "amount": {"type": "number", "default": "{{amount}}", "description": "The agreed amount, a number such as 637.50."},
            "date": {"type": "string", "default": "{{date}}", "description": "The agreed payment date as YYYY-MM-DD."},
            "product_id": {"type": "string", "default": "{{product_id}}"},
        },
        ["amount", "date"], post=H.PROMISE_POST,
    )


def callback_tool() -> dict:
    return api_tool(
        "schedule_callback",
        "Books a callback for the customer. CALL it as soon as the person gives a day and a time inside the callback window.",
        {
            "date": {"type": "string", "default": "{{date}}", "description": "Callback date as YYYY-MM-DD."},
            "time": {"type": "string", "default": "{{time}}", "description": "Callback time as HH:MM, 24 hour."},
        },
        ["date", "time"], post=H.CALLBACK_POST,
    )



def code_node(name: str, code: str, transitions: list) -> dict:
    return {
        "name": name,
        "node_type": "code",
        "passthrough": True,
        "passthrough_default_transition": transitions[-1]["target_node"],
        "on_enter": {"type": "silent"},
        "disable_inactivity_monitor": True,
        "pre_actions": [{
            "type": "function",
            "function": {
                "name": "code_exec",
                "handler": "__function__:code_exec",
                "parameters": {"type": "object", "properties": {
                    "code": {"type": "string", "default": code},
                    "timeout_ms": {"type": "number", "default": 10000},
                }},
            },
        }],
        "transitions": transitions,
    }


def always(target: str) -> dict:
    return {"target_node": target, "description": "always", "condition": {"operator": "always"}}


def var_is(target: str, desc: str, variable: str, values: list) -> dict:
    return {"target_node": target, "description": desc, "condition": {"logic": "or", "conditions": [
        {"variable": variable, "operator": "equals", "operand": v} for v in values]}}


CLOSED = var_is("end", "close_call was recorded", "close_call_response.data.ok", ["true", "True"])
RETRY = {"target_node": "retry_promise", "description": "create_promise failed with a service error, retry once",
         "condition": {"logic": "or", "conditions": [
             {"variable": "create_promise_failure_count", "operator": "greater_than", "operand": 0}]}}


def conv(name: str, task: str, tools: list, transitions: list, on_enter: dict, extraction: list | None = None,
         first_only: bool = True) -> dict:
    node = {
        "name": name,
        "node_type": "conversation",
        "on_enter": on_enter,
        "on_enter_first_entry_only": first_only,
        "task_message": task,
        "tools": tools,
        "transitions": transitions,
        "max_node_turns": 60,
    }
    if extraction:
        node["extraction_schema"] = extraction
    return node


SYSTEM = """You are Freya Bank's digital assistant, making an outbound phone call for Freya Bank. Speak English. One or two short sentences per turn. Address the customer as {{title}} {{last_name}}.

Rules for every step:
- When a rule says to call a tool, CALL the tool. Saying you did it is not enough. Call one tool per message.
- After every tool result, read its what_to_do_next and follow it. Always say something to the customer or call the next tool. Never end a turn with nothing.
- Never say that something is recorded, booked or transferred unless the tool result says it worked. If a tool fails or returns an error, say so honestly.
- If asked whether you are a robot or an AI: say you are Freya Bank's digital assistant, then continue where you were.
- If asked whether this is a scam: say they can verify the call by phoning Freya Bank's customer service number, then continue where you were.
- If asked something your information does not answer: say you do not have that information. Never invent figures, dates or reasons.
- Never offer a discount, a waiver, an instalment plan or any term that is not given to you here.
- Every call ends with close_call, exactly once, as the very last tool call. In the same message, before calling close_call, thank the customer and say goodbye. After close_call, say nothing more.
- Today is {{today_spoken}}, the time is {{now_time}}. Use this, never your own clock."""

OPENING_LINE = ("Hello, I am a digital assistant calling from Freya Bank. This call is recorded. "
                "Am I speaking with {{title}} {{last_name}}?")

OPENING_TASK = """You have already said that you are a digital assistant calling from Freya Bank, that the call is recorded, and asked "Am I speaking with {{title}} {{last_name}}?". Your only job here is to find out who is on the line.

Until identity is verified, never say why you are calling. Never say "collections", "debt", "payment", "account", "loan", "card", any product or any amount. If asked what it is about, say you can only discuss it with {{title}} {{last_name}} in person.

- Only "yes", "that's me", "speaking" or the customer's own name confirms. "Hello", "go ahead" and "who is this" do not confirm.
- If it is not confirmed yet, ask once more: "Am I speaking with {{title}} {{last_name}}?". If the person asked a question, answer it first (robot or AI, scam), then ask; that ask is the second ask. If it is still not confirmed after the second ask, thank them, say goodbye and call close_call with outcome not_reached and reason unclear.
- If the person says this number does not belong to the customer: thank them, say goodbye, call close_call with outcome not_reached and reason wrong_number.
- If the person says the customer has died: say "I am sorry for your loss.", say goodbye, and call close_call with outcome not_reached and reason deceased. Ask nothing else.
- If the person says a second time that they do not want to talk: thank them, say goodbye, call close_call with outcome not_verified and reason declined.
- If the person asks for a human: ask once whether you can help first. If they insist, call transfer_to_agent with queue general."""

SPEAKER = [{
    "name": "speaker",
    "type": "string",
    "enum_values": ["customer", "someone_else"],
    "description": "Who answered the phone, judged from the person's own words. customer: the person clearly confirmed they are the one the assistant asked for, by saying yes, that's me, speaking, or that name as their own. "
                   "someone_else: the person says they are NOT that person, for example a husband, wife, relative or colleague, or says that person is not here, is not available, or has died. "
                   "Leave it empty for anything else: hello, go ahead, who is this, a question, or an unclear answer.",
    "min_confidence": 0.6,
}]

THIRD_TASK = """The person on the line is NOT {{title}} {{last_name}}. Never say why you are calling. Say nothing about any account, debt, payment, product or amount, even if they ask or offer to pay. If they ask, say you can only discuss it with {{title}} {{last_name}} in person. Ask them no security questions and never call verify_identity.

- If they say this number does not belong to the customer: thank them, say goodbye, call close_call with outcome not_reached and reason wrong_number.
- If they say the customer has died: say "I am sorry for your loss.", say goodbye, and call close_call with outcome not_reached and reason deceased. Ask nothing else.
- Otherwise ask when {{title}} {{last_name}} can be reached.

Callback window (it must be later than now):
{{callback_facts}}
"Tomorrow" is {{tomorrow_spoken}}. "Around eleven" or "eleven in the morning" means 11:00. "Three in the afternoon" means 15:00.

- When the person gives a day and a time inside the window, call schedule_callback with date as YYYY-MM-DD and time as HH:MM. If one of the two is missing, ask for it.
- If the day or the time is outside the window, say when you can call back and ask once for another time. If the second answer is also outside the window, or they cannot say, do not schedule: thank them, say goodbye, call close_call with outcome not_reached and reason no_callback.
- If they ask for a human: ask once whether you can help first. If they insist, call transfer_to_agent with queue general."""

IDENTITY_LINE = "Thank you. For your security I need to ask two questions. First, what is your date of birth?"

IDENTITY_TASK = """The person confirmed they are {{title}} {{last_name}}. Check identity with two security questions, one at a time: first the date of birth, then the last four digits of the phone number on file. You have already asked for the date of birth.

- Every time the customer gives a complete answer, call verify_identity with field date_of_birth or phone_last4. If they give only part of it, wait for the rest.
- Send a date of birth as YYYY-MM-DD, whatever way it was said. A date said only in numbers is day, then month, then year: 05/06/1980 is 1980-06-05.
- Follow what_to_do_next in every result. A wrong answer may be asked again. Three wrong answers in total end the check.
- Until both answers pass, never say why you are calling and never name any product, amount, debt or "collections", even if the customer asks how much they owe.
- If the customer does not want to answer, or asks what the call is about instead of answering, explain once that these questions protect their account and ask again. If they refuse again or ask again what it is about, thank them, say goodbye, and call close_call with outcome not_verified and reason declined.
- After three wrong answers: do not state any debt, tell the customer to use the Freya Bank mobile app or visit a branch, thank them, say goodbye, and call close_call with outcome not_verified and reason failed.
- If they ask for a human: ask once whether you can help first. If they insist, call transfer_to_agent with queue general."""

DEBT_LINE = ("Thank you, you are verified. I am calling from the collections team about a late payment on your {{product_words}}. "
             "The past-due amount is {{past_due_text}}, and it is {{days_late_text}} days late. Can you make this payment today?")

ACCOUNT_BLOCK = """ACCOUNT
- Product: {{product_words}}
- Full past-due amount: {{past_due_text}}
- Days late: {{days_late_text}} (band: {{band}})
- Floor, the lowest amount you may record: {{floor_text}}
- Deadline, the latest date you may record: {{deadline_spoken}} ({{deadline_iso}})
- Persuasion attempts allowed: {{attempts}}
- Attempt 1 date: {{attempt1_spoken}} ({{attempt1_iso}})

DATE WORDS
{{week_table}}

CALENDAR. Each line says what to do when the customer names that day:
{{calendar}}"""

COMMON_RULES = """HANDLE THE CUSTOMER'S ANSWERS. Check these in order:
1. Illness, a death in the family or job loss: say one short sentence of sympathy. Make NO persuasion attempt. Offer once to connect them with the customer support team. If they accept, call transfer_to_agent with queue support. If they decline, thank them, say goodbye and call close_call with outcome no_promise and reason hardship. Only if they still name a date or an amount themselves, handle it as in rule 6.
2. They say they already paid this amount: say that payments can take one business day to appear. Take no promise. Thank them, say goodbye, call close_call with outcome paid.
3. They say the debt is not theirs, they never had this product, or it was closed or paid off in the past: do not argue and take no promise. Thank them, say goodbye, call close_call with outcome no_promise and reason dispute.
4. They ask for a new payment plan or lower instalments: describe no plan. Call transfer_to_agent with queue restructuring.
5. They ask for a human: ask once whether you can help first. If they insist, call transfer_to_agent with queue general.
6. They name a date and/or an amount. This is NEVER a refusal.
   - Date: find it in the calendar and do exactly what its line says. Use DATE WORDS for "this <weekday>", "next <weekday>", "tomorrow".
   - A vague period ("next week", "the week after next", "end of the month", "when my salary comes"): ask once for the exact day. If they still give no exact day, propose the deadline.
   - If they refuse the deadline after you offered it, that is a flat refusal (rule 8).
   - Amount: anything from {{floor_text}} up to {{past_due_text}}, both included, is accepted. Below {{floor_text}}: say it cannot be recorded and offer {{floor_text}} once; if they do not accept, that is a flat refusal (rule 8).
"""

DEBT_RULES = """   - With only a date, the amount is the full amount. With only an amount, ask on which day they can pay it.
7. They say the full amount is too much: offer {{floor_text}}, once, and say that the rest stays overdue. Ask if they can pay it today. If they refuse the floor, that is a flat refusal (rule 8).
8. A flat refusal or a non-answer (including a no to paying today with no date and no amount) uses one persuasion attempt:
   - Attempt 1: propose the full amount {{past_due_text}} on {{attempt1_spoken}}.
   - Attempt 2, only when persuasion attempts allowed is 2: propose {{floor_text}} on {{deadline_spoken}}.
   - When the allowed attempts are used up, stop. Do not repeat an offer they refused. Thank them, say goodbye, call close_call with outcome no_promise and reason refused.
9. They say a second time that they do not want to talk: thank them, say goodbye, call close_call with outcome no_promise and reason refused."""

FLOOR_RULES = """   - With only a date, the amount is {{floor_text}}. With only an amount, ask on which day they can pay it.
7. A flat refusal or a non-answer ("you tell me", "I don't know", "what are my options", a no to paying today with no date and no amount) uses one persuasion attempt. Make them in this order, one per refusal:
{{floor_plan}}
   If earlier in this call you already proposed {{past_due_text}} on {{attempt1_spoken}} and they refused it, attempt 1 is used up: go straight to the next line of that list.
   Never repeat an offer they refused. Never offer {{floor_text}} for today again.
8. They say a second time that they do not want to talk: thank them, say goodbye, call close_call with outcome no_promise and reason refused."""

CONFIRM_BLOCK = """NEVER ask "how much can you pay?" or any question that lets them choose the amount. You propose every amount.

CONFIRM AND RECORD
- When an allowed amount and an allowed date are agreed, read back: "So that is <amount> for your {{product_words}}, paid on <weekday, day month>. Do you confirm?"
- Call create_promise only after a clear yes, with amount as a number and date as YYYY-MM-DD.
- If they change the date or the amount at this point, check the new value with the rules above and read it back again.
- There is one promise only. A recorded promise cannot be changed or cancelled in this call; if they ask, say they can change it in the mobile app.
- Follow what_to_do_next after create_promise. Do not use the word "recorded" about the promise until a create_promise result says it is recorded. After a recorded promise, say: "You will receive a text message confirming this promise.\""""

DEBT_TASK = ("""The customer is verified. You have already said you are calling from the collections team, named the product, stated the past-due amount and the days late, and asked "Can you make this payment today?".

""" + ACCOUNT_BLOCK + "\n\n" + COMMON_RULES + "\n" + DEBT_RULES + "\n\n" + CONFIRM_BLOCK)

FLOOR_LINE = ("I understand. The lowest amount I can accept is {{floor_text}}, and the rest stays overdue. "
              "Can you pay {{floor_text}} today?")

FLOOR_TASK = ("""The customer is verified and said the full amount is too much. You have ALREADY offered {{floor_text}} for today and said that the rest stays overdue. That offer is made: do not make it again.

""" + ACCOUNT_BLOCK + "\n\n" + COMMON_RULES + "\n" + FLOOR_RULES + "\n\n" + CONFIRM_BLOCK)

TOO_MUCH = [{
    "name": "full_too_much",
    "type": "string",
    "enum_values": ["yes"],
    "description": "yes when the customer says the full past-due amount is too much, more than they can afford, or that they cannot pay all of it. "
                   "Leave it empty for anything else, including a plain no to paying today, a date, an amount, or a request for a plan.",
    "min_confidence": 0.6,
}]

ERROR_TASK = """The account details could not be loaded. Tell the customer that you cannot access the details right now and that nothing was recorded. Thank them, say goodbye, and call close_call with outcome no_promise and reason service_error."""


DONE_TASK = """A payment promise was just recorded after a retry. Say: "Your promise is now recorded. You will receive a text message confirming this promise." Then thank the customer, say goodbye, and in the same message call close_call with outcome promise. The promise cannot be changed in this call; if asked, they can change it in the mobile app."""

FAILED_TASK = """The promise could NOT be recorded: the bank's service failed twice and nothing was saved. Never say it is recorded. Tell the customer you could not record the promise because of a technical problem. Then thank them, say goodbye, and in the same message call close_call with outcome no_promise and reason service_error."""


def retry_promise_node() -> dict:
    fn = api_tool("create_promise", "Retry the payment promise once.", {
        "amount": {"type": "number", "default": "{{create_promise_args.amount}}"},
        "date": {"type": "string", "default": "{{create_promise_args.date}}"},
        "product_id": {"type": "string", "default": "{{product_id}}"},
    }, ["amount", "date"], pre=H.RETRY_PRE)
    return {
        "name": "retry_promise",
        "node_type": "api_request",
        "passthrough": True,
        "passthrough_default_transition": "promise_failed",
        "on_enter": {"type": "silent"},
        "disable_inactivity_monitor": True,
        "pre_actions": [fn],
        "response_mapping": [{"path": "data.ok", "variable": "retry_ok"}],
        "transitions": [
            var_is("promise_done", "the retry recorded the promise", "retry_ok", ["true", "True"]),
            always("promise_failed"),
        ],
    }


def get_account_node() -> dict:
    fn = api_tool("get_account", "Get the late products.", {}, [], post=H.GET_ACCOUNT_POST, retries=2)
    pre = {k: v for k, v in fn.items() if k != "response_mapping"}
    return {
        "name": "load_account",
        "node_type": "api_request",
        "passthrough": True,
        "passthrough_default_transition": "compute_debt",
        "on_enter": {"type": "silent"},
        "disable_inactivity_monitor": True,
        "pre_actions": [pre],
        "response_mapping": [
            {"path": "data.products", "variable": "products"},
            *[{"path": f"data.p_{k}", "variable": f"acc_{k}"} for k in
              ["product_id", "type", "card_last4", "past_due", "days_late", "minimum_payment", "instalment_amount"]],
        ],
        "transitions": [always("compute_debt")],
    }


def build() -> dict:
    nodes = {
        "setup": code_node("setup", H.SETUP_CODE, [always("opening")]),
        "opening": conv(
            "opening", OPENING_TASK, [transfer_tool(), close_call_tool()],
            [CLOSED,
             var_is("identity", "the customer confirmed who they are", "speaker", ["customer"]),
             var_is("third_party", "someone else answered", "speaker", ["someone_else"])],
            {"type": "tts", "text": OPENING_LINE}, extraction=SPEAKER),
        "third_party": conv(
            "third_party", THIRD_TASK, [callback_tool(), transfer_tool(), close_call_tool()],
            [CLOSED], {"type": "llm"}),
        "identity": conv(
            "identity", IDENTITY_TASK, [verify_tool(), transfer_tool(), close_call_tool()],
            [CLOSED,
             var_is("load_account", "both security answers verified", "verify_identity_response.data.all_verified", ["true", "True"])],
            {"type": "tts", "text": IDENTITY_LINE}),
        "load_account": get_account_node(),
        "compute_debt": code_node("compute_debt", H.DEBT_CODE, [
            var_is("debt", "account facts ready", "debt_state", ["ok"]),
            always("account_error")]),
        "debt": conv(
            "debt", DEBT_TASK, [promise_tool(), transfer_tool(), close_call_tool()],
            [CLOSED, RETRY,
             var_is("floor", "the customer said the full amount is too much", "full_too_much", ["yes"])],
            {"type": "tts", "text": DEBT_LINE}, extraction=TOO_MUCH),
        "floor": conv(
            "floor", FLOOR_TASK, [promise_tool(), transfer_tool(), close_call_tool()],
            [CLOSED, RETRY],
            {"type": "tts", "text": FLOOR_LINE}),
        "retry_promise": retry_promise_node(),
        "promise_done": conv(
            "promise_done", DONE_TASK, [close_call_tool()], [CLOSED], {"type": "llm"}),
        "promise_failed": conv(
            "promise_failed", FAILED_TASK, [close_call_tool()], [CLOSED], {"type": "llm"}),
        "account_error": conv(
            "account_error", ERROR_TASK, [close_call_tool()], [CLOSED], {"type": "llm"}),
        "end": {
            "name": "end",
            "node_type": "end_call",
            "on_enter": {"type": "silent"},
            "disable_inactivity_monitor": True,
            "transitions": [],
            "terminal": {"type": "function", "function": {
                "name": "call_closed", "handler": "__function__:end_call",
                "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}},
        },
    }
    return {
        "initial_node": "setup",
        "system_prompt": SYSTEM,
        "nodes": nodes,
        "global_nodes": {},
        "test_variables": {"customer_id": "c_test", "first_name": "Daniel", "last_name": "Reyes", "title": "Mr",
                           "now": "2026-10-14T11:00"},
    }


if __name__ == "__main__":
    out = ROOT / "out" / "brief-a.workflow.json"
    out.write_text(json.dumps(build(), indent=1))
    print(out)
