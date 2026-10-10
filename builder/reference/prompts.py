"""Prompt and line text for the reference workflow. Generic instructions; every brief-specific
word, sentence, list or code is read from spec.json. No brief values in this file."""


def _q(items) -> str:
    return ", ".join(f'"{x}"' for x in items or [])


def _close(pair) -> str:
    pair = list(pair or ["", ""]) + ["", ""]
    return f"outcome {pair[0]}" + (f" and reason {pair[1]}" if pair[1] else "")


def _who(spec: dict) -> str:
    """How the customer is named, from the call variables the brief defines."""
    return spec["address_as"]                       # required: the brief's call variables decide it


def tool_move(target: str, description: str) -> dict:
    return {"target_node": target, "description": description, "is_tool_call": True,
            "condition": {"operator": "matches_intent", "description": description}}


def system_prompt(spec: dict) -> str:
    who = spec.get("agent_identity") or "the bank's digital assistant"
    never = ", ".join(spec.get("never_offer") or [])
    return f"""You are {who}, making an outbound phone call. Speak English. One or two short sentences per turn. Address the customer as {_who(spec)}.

Rules for every step:
- When a rule says to call a tool, CALL the tool. Saying you did it is not enough. Call one tool per message.
- After every tool result, read its what_to_do_next and follow it. Always say something or call the next tool. Never end a turn with nothing.
- Never say that something is recorded, booked or transferred unless the tool result says it worked. If a tool fails, say so honestly.
- If asked whether you are a robot or an AI: {spec.get("robot_question") or "say who you are and continue"}.
- If asked whether this is a scam: {spec.get("scam_question") or "say how they can verify the call, and continue"}.
- If asked something your information does not answer: say you do not have that information. Never invent figures, dates or reasons.
- Never offer {never or "any term that is not given to you here"}.
- Customers ramble, talk about other things, stop in the middle of a sentence, or send text that makes no sense. That is never an answer, never a refusal and never a reason to end the call. Always reply, even to a single character: say "Take your time." and nothing more. Never repeat an offer, an amount or a date because of such a reply. Only a security question may be asked again.
- Never use words of sympathy unless a rule tells you to.
- Every call ends with the closing tool, exactly once, as the very last tool call. In the same message, before it, thank the customer and say goodbye. After it, say nothing more.
- Today is {{{{today_spoken}}}}, the time is {{{{now_time}}}}. Use this, never your own clock."""


def opening_line(spec: dict) -> str:
    o = spec.get("opening") or {}
    return (o.get("first_sentence", "") + " " + o.get("ask", "")).strip()


def speaker_extraction(spec: dict) -> dict:
    c = spec.get("confirmation_words") or {}
    return {"name": "speaker", "type": "string", "enum_values": ["customer", "someone_else"], "min_confidence": 0.6,
            "description": "Who answered, judged from the person's own words. customer: the person clearly confirmed they are the one asked for "
                           f"({', '.join(c.get('confirms') or ['yes'])}). someone_else: the person says they are NOT that person, or that person "
                           "is not here, not available, or has died. Leave it empty for anything else "
                           f"({', '.join(c.get('does_not_confirm') or [])}, a question, or an unclear answer)."}


def _special_lines(spec: dict, close_word: str = "the closing tool", cont: str = "", in_product: bool = False) -> str:
    """One line per special case without a fixed line. `cont` says how to move on when the case
    settles one product but does not end the call."""
    out = []
    for s in sorted(spec.get("special_cases") or [], key=lambda s: s.get("precedence", 99)):
        if s.get("line"):
            continue
        act = s.get("action", "")
        tr = f" Call the transfer tool with queue {s['transfer']}." if s.get("transfer") else ""
        if in_product:
            cl = ""
            mv = f" {cont}" if cont and not s.get("transfer") else ""
        else:
            cl = f" Then thank them, say goodbye and call {close_word} with {_close(s['close'])}." if s.get("close") and not s.get("transfer") else ""
            mv = f" {cont}" if cont and not s.get("close") and not s.get("transfer") else ""
        out.append(f"- Case {s['name']} ({s.get('trigger', s['name'])}): {act}.{tr}{cl}{mv}")
    return "\n".join(out)


def opening_task(spec: dict) -> str:
    c = spec.get("confirmation_words") or {}
    tp = spec.get("third_party") or {}
    dec = tp.get("deceased") or {}
    human = [s for s in spec.get("special_cases") or [] if s.get("transfer") and "human" in s.get("name", "")]
    ident = spec.get("identity") or {}
    lines = [
        f'You have already said: "{opening_line(spec)}". Your only job here is to find out who is on the line.',
        "",
        f"Until identity is verified, never say why you are calling. Never say any of these words: {_q(spec.get('forbidden_before_verification'))}, "
        f"any product or any amount. If asked what it is about, say you can only discuss it with {_who(spec)} in person.",
        "",
        f"- Only these confirm: {', '.join(c.get('confirms') or [])}. These do not: {', '.join(c.get('does_not_confirm') or [])}.",
        f"- If it is not confirmed, ask again: \"{(spec.get('opening') or {}).get('ask', '')}\". If the person asked a question, answer it first; "
        f"the ask after that counts. Ask at most {c.get('asks', 2)} times in total. If it is still not confirmed, thank them, say goodbye and call "
        f"the closing tool with {_close(c.get('close_if_unclear'))}.",
    ]
    if tp.get("wrong_number"):
        lines.append(f"- If the person says this number does not belong to the customer: thank them, say goodbye, call the closing tool with {_close(tp['wrong_number'])}.")
    if dec:
        lines.append(f"- If the person says the customer has died: say \"{dec.get('say', '')}\", say goodbye, and call the closing tool with {_close(dec.get('close'))}. Ask nothing else.")
    if (ident.get("on_declined") or {}).get("close"):
        lines.append(f"- If the person says a second time that they do not want to talk: thank them, say goodbye, call the closing tool with {_close(ident['on_declined']['close'])}.")
    for h in human:
        lines.append(f"- If the person asks for a human: {h.get('action', '')}. If they insist, call the transfer tool with queue {h['transfer']}.")
    return "\n".join(lines)


def third_party_task(spec: dict) -> str:
    tp, cb = spec.get("third_party") or {}, spec.get("callback") or {}
    dec = tp.get("deceased") or {}
    return f"""The person on the line is NOT {_who(spec)}. Never say why you are calling. Say nothing about any account, debt, payment, product or amount, even if they ask or offer to pay. If they ask, say you can only discuss it with {_who(spec)} in person. Ask them no security questions.

- If they say this number does not belong to the customer: thank them, say goodbye, call the closing tool with {_close(tp.get('wrong_number'))}.
- If they say the customer has died: say "{dec.get('say', '')}", say goodbye, and call the closing tool with {_close(dec.get('close'))}. Ask nothing else.
- Otherwise ask when {_who(spec)} can be reached.

Callback window:
{{{{callback_facts}}}}

- When the person gives a day and a time inside the window, call the callback tool with the date as YYYY-MM-DD and the time as HH:MM. If one of the two is missing, ask for it.
- If the day or the time is outside the window, say when you can call back and ask {'once' if cb.get('ask_again_once') else 'again'} for another time. If the next answer is also outside the window, or they cannot say, book nothing: thank them, say goodbye, call the closing tool with {_close(cb.get('close_none'))}."""


def callback_ok(spec: dict) -> str:
    cb = spec.get("callback") or {}
    return f"The callback is BOOKED. Tell the person the customer will be called back then. Thank them, say goodbye and call the closing tool with {_close(cb.get('close_booked'))}."


def callback_fail(spec: dict) -> str:
    return "The callback was NOT booked: the service failed. Never say it is booked. Call it once more with the same date and time."


def callback_failed_task(spec: dict) -> str:
    cb = spec.get("callback") or {}
    return f"The callback could NOT be booked: the service failed twice. Never say it is booked. Tell the person you could not book it. Thank them, say goodbye, and in the same message call the closing tool with {_close(cb.get('close_none'))}."


def identity_task(spec: dict) -> str:
    ident = spec.get("identity") or {}
    qs = ident.get("questions") or []
    order = "; then ".join(f"{q.get('ask', '')} (send field value {q.get('value')})" for q in qs)
    dec = ident.get("on_declined") or {}
    fail = ident.get("on_failed") or {}
    human = [s for s in spec.get("special_cases") or [] if s.get("transfer") and "human" in s.get("name", "")]
    lines = [
        f"The person confirmed they are {_who(spec)}. Check identity with these security questions, one at a time, in this order: {order}. You have already asked the first one.",
        "",
        "- Every time the customer gives a complete answer, call the check tool once with that question's field value and the answer. If they give only part of it, wait for the rest.",
        f"- Follow what_to_do_next in every result. A wrong answer may be asked again. {ident.get('wrong_answer_limit', 3)} wrong answers in total end the check.",
        "- Off-topic talk, an unfinished sentence or text that makes no sense is NOT an answer, NOT a wrong answer and NOT a refusal. Do not call the check tool for it. Reply in a few words and ask the same question again.",
        f"- Until every answer passes, never say why you are calling. Never say any of these words: {_q(spec.get('forbidden_before_verification'))}, any product or any amount, even if asked.",
        f"- If the customer does not want to answer ({dec.get('counts_as_declining', 'or asks what the call is about instead')}), explain once that {dec.get('explain_once', 'the questions protect their account')} and ask again. "
        f"If they refuse again, thank them, say goodbye, and call the closing tool with {_close(dec.get('close'))}.",
        f"- Close as failed ONLY when what_to_do_next says the check has ENDED. Then: {fail.get('say', '')}; thank them, say goodbye, and call the closing tool with {_close(fail.get('close'))}.",
    ]
    for h in human:
        lines.append(f"- If they ask for a human: {h.get('action', '')}. If they insist, call the transfer tool with queue {h['transfer']}.")
    return "\n".join(lines)


def service_down_task(spec: dict) -> str:
    pf = (spec.get("outcome_logic") or {}).get("promise_failed")
    return f"The identity check is not working right now: it failed twice. Never say why you are calling and name no product, debt or amount. Tell the customer there is a technical problem and that the bank will call again another time. Thank them, say goodbye, and in the same message call the closing tool with {_close(pf)}."


def account_error_task(spec: dict) -> str:
    pf = (spec.get("outcome_logic") or {}).get("promise_failed")
    return f"The account details could not be loaded. Tell the customer you cannot access the details right now and that nothing was saved. Thank them, say goodbye, and call the closing tool with {_close(pf)}."


def transfer_description(spec: dict) -> str:
    qs = [f"{s['transfer']} when {s.get('trigger', s['name'])}" for s in spec.get("special_cases") or [] if s.get("transfer")]
    qs += [f"{s['accept']['transfer']} when a customer in {s['name']} accepts the offer" for s in spec.get("special_cases") or []
           if (s.get("accept") or {}).get("transfer")]
    return "Hands the call to a person. CALL it only when a rule says so: " + "; ".join(qs) + "."


def special_extraction(specials: list) -> str:
    parts = [f"{s['name']}: {s.get('trigger', '')}." for s in specials]
    return ("Set it as soon as the customer says one of these, in any words. Check in this order and take the first that fits. "
            + " ".join(parts) + " Leave it empty for anything else, including small talk, a refusal, a date or an amount. "
            "Saying the full amount is too much, that they cannot pay it now, or that they can only pay less is NOT any of these: leave it empty.")


def too_much_extraction() -> dict:
    return {"name": "full_too_much", "type": "string", "enum_values": ["yes"], "min_confidence": 0.6,
            "description": "yes when the customer says the full past-due amount is too much, more than they can afford, or that they "
                           "can only pay part of it. Leave it empty for anything else."}


NOT_SPECIAL = ("Saying the full amount is too much, that they cannot pay now, or that they can only pay less is NOT a special case: "
               "it is handled by the amount and persuasion rules.")


def debt_task(spec: dict) -> str:
    return f"""The customer is verified. You have already stated every late product with its past-due amount and days late, and asked ONE question: whether they can pay today. Products ({{{{n_products}}}}): {{{{product_list}}}}.

Your only job in this step is the answer to that question. Never ask about today again.

Check the customer's answer in this order:
1. They can pay EVERYTHING today: say "Thank you." and in the same message call transition_to_readback.
2. There are two or more products and they name ONE date for everything, with no other condition: if it is not a business day, offer the next business day and wait. If it is, say "Thank you." and in the same message call transition_to_readback. Never talk about deadlines here: a product with an earlier deadline is moved to its own deadline in the read-back.
{_special_lines(spec, cont='Then go through the products one by one (rule 3).')}
   {NOT_SPECIAL}
3. Anything else (a no, a date or amount for one product, a vague period, too much, a question): with two or more products say "I understand, let us go through them one by one."; with one product say only "I understand." Then, in the same message, call transition_to_product_1. Never make an offer in this step.

DATE WORDS
{{{{week_table}}}}

Never record a promise or write a note in this step."""


def product_task(spec: dict, k: int) -> str:
    p = spec.get("persuasion") or {}
    fo = p.get("floor_offer") or {}
    rest = f' and say: "{fo["say_with_offer"]}"' if fo.get("say_with_offer") else ""
    return f"""You are now handling PRODUCT {k} only. Products before it are settled; do not reopen them. Do not talk about later products yet.

{{{{p{k}_block}}}}

PERSUASION ATTEMPTS for this product, in order, one per flat refusal or non-answer:
{{{{p{k}_attempts}}}}

CALENDAR for this product. Each line says what to do when the customer names that day:
{{{{p{k}_calendar}}}}

DATE WORDS
{{{{week_table}}}}

YOUR FIRST MESSAGE IN THIS STEP. Look at what the customer already said about THIS product:
- They already named a date and/or amount for it: handle it with rule 2 below (with only a date, the amount is the full past-due amount).
- They already gave only a vague period ("next week", "end of the month", "when my salary comes"): ask once for the exact day, and nothing else. This uses no attempt.
- Otherwise, including when they said earlier that they will not pay: make attempt 1 now. A refusal said before your first offer for this product uses no attempt.

RULES. Check the customer's replies in this order:
1. Special cases:
{_special_lines(spec, cont=f'Say "Noted." and in the same message call transition_to_product_{k}_done.', in_product=True)}
   {NOT_SPECIAL}
2. They name a date and/or an amount. This is NEVER a refusal.
   - Date: find it in the CALENDAR and do exactly what its line says. If they refuse the deadline after you offered it, that is a flat refusal (rule 4).
   - A vague period: ask once for the exact day. If they still give none, propose the deadline.
   - Amount: from the floor up to the full past-due amount, both included, is accepted. Below the floor: say you cannot accept that amount and offer the floor once; if they do not accept, that is a flat refusal (rule 4).
   - With only an amount, ask on which day they can pay it.
   - When an allowed amount and an allowed date are agreed: say "Noted, <amount> on <weekday day month>." and in the same message call transition_to_product_{k}_done. Do not ask "Do you confirm?" here: everything is confirmed together later.
3. They say in words that the full amount is TOO MUCH (a plain no is NOT this): offer the floor{rest}, {'only once' if fo.get('once') else 'once'}, on the attempt 1 date. If they refuse the floor, that is a flat refusal (rule 4).
4. A flat refusal or a non-answer about this product: make the next persuasion attempt from the list. Never repeat an offer they refused. When the attempts are used up: say "I understand." and in the same message call transition_to_product_{k}_done.

NEVER ask "how much can you pay?". You propose every amount. Never ask about paying today. Never record a promise, write a note or close the call in this step: the call is closed after all products."""


def _closing_codes(spec: dict) -> str:
    rows = [f"  - {s['name']} ({s.get('trigger', '')}): {_close(s['close'])}" for s in spec.get("special_cases") or [] if s.get("close")]
    ref = (spec.get("persuasion") or {}).get("close_refused")
    if ref:
        rows.append(f"  - every product refused after its attempts: {_close(ref)}")
    return "\n".join(rows)


FACTS = """ACCOUNT
{{products_block}}

DATE WORDS
{{week_table}}

CALENDAR. Each line says, per product, what a named day means:
{{all_calendar}}"""


def _end_rules(spec: dict) -> str:
    rb = spec.get("read_back") or {}
    notes = spec.get("notes") or {}
    after = (spec.get("sentences") or {}).get("after_promise", "")
    note_part = (f"""
NOTES (only when the call is NOT transferred)
- After the promises, call the note tool once for every product without a recorded promise, one per message, with its id and its reason: {', '.join(notes.get('reasons') or [])}.
- After a transfer, never write a note.""" if notes.get("used") else "\nNOTES: this bank does not use notes. Never call a note tool.")
    ol = spec.get("outcome_logic") or {}
    return f"""NEVER ask "how much can you pay?". You propose every amount.

READ-BACK (once, for all agreed products together)
- When every product is settled, read back ALL agreed products in ONE message: for each, the product, the amount and the date (weekday, day, month). If a product's date was moved to its own deadline, say so for that product. End with "{rb.get('ask', 'Do you confirm?')}". Ask for one confirmation only.
- If they change a date or an amount, check the new value and read everything back again.
- If no product is agreed, skip the read-back.

RECORD
- After a clear yes, call the promise tool once per agreed product, in product order, one per message.
- Follow what_to_do_next after each result. Never say a promise is recorded until the tool said so. After all are recorded say once: "{after}"
- A recorded promise cannot be changed or cancelled in this call.
{note_part}

CLOSE
- Then thank the customer, say goodbye, and in the same message call the closing tool.
- Outcome: {ol.get('on_promise', '')} if at least one promise was recorded. Otherwise use the codes of what settled the products:
{_closing_codes(spec)}"""


def readback_task(spec: dict) -> str:
    return f"""Every product has been handled. Products ({{{{n_products}}}}): {{{{product_list}}}}.

For each product in order, work out from the conversation its status: agreed (amount and date), refused, or settled by a special case.
Every agreed product has a line where you said "Noted, <amount> on <date>." for it: find each of those lines. A product with such a line is agreed, even if the customer refused other products.
If the customer named one date for everything: each product is agreed at its full past-due amount on that date, except a product whose deadline is earlier: that product is agreed on its own deadline.

YOUR FIRST MESSAGE IN THIS STEP: if at least one product is agreed, the single read-back of all agreed products. Otherwise go straight to closing.
Use the DATE WORDS and the CALENDAR below for every date you say: never work out a weekday or a date yourself.

{FACTS}

{_end_rules(spec)}"""


def offer_task(spec: dict, s: dict) -> str:
    acc, dec = s.get("accept") or {}, s.get("decline") or {}
    return f"""The customer said: {s.get('trigger', s['name'])}. You have ALREADY said the line for this case once. Never say it again and never repeat the offer. {s.get('action', '')}. Make NO persuasion attempt: propose no amount and no date.

Check these in order:
- They said no to the offer, at any point in this step: they declined. If they also asked for something you cannot offer, say you cannot offer it. Then thank them, say goodbye, and in the same message call the closing tool with {_close(dec.get('close'))}. Never ask again.
- They accept: call the transfer tool with queue {acc.get('transfer', '')}.
- Their reply is cut off or about something else: say "Take your time." and nothing more.
- They name a date or an amount THEMSELVES for a product: check it against that product's facts and record it after one read-back. Never suggest an amount or a date yourself.

{FACTS}

{_end_rules(spec)}"""


def retry_ok_task(spec: dict) -> str:
    return f"""A payment promise just failed once and was then saved on the automatic retry. Tell the customer it is now saved and say exactly: "{(spec.get('sentences') or {}).get('after_promise', '')}" If another agreed product is not recorded yet, record it now with the promise tool. Do not read anything back again.

{FACTS}

{_end_rules(spec)}"""


def retry_failed_task(spec: dict) -> str:
    notes = spec.get("notes") or {}
    pf = (spec.get("outcome_logic") or {}).get("promise_failed")
    note = (f" Write a note for this product with reason {notes.get('service_error_reason', '')}." if notes.get("used") else "")
    return f"""A payment promise could NOT be saved: the bank's service failed twice. Never say it is saved. Tell the customer you could not save it because of a technical problem. Keep any promise that was saved. If another agreed product is not recorded yet, record it now with the promise tool.{note} If no promise was saved at all, close with {_close(pf)}.

{FACTS}

{_end_rules(spec)}"""
