"""Tool hooks for the reference workflow. Every name and value comes from spec.json via CFG.

Each source starts with `CFG = json.loads(...)`, never raises, and has no double brace.
"""
from lib.calendar_code import calendar_source, json_literal
from lib.hooks import identity_pre_source

_TV = r'''
def tv(x):
    return x is True or str(x).strip().lower() == 'true'
def failed(res):
    if not isinstance(res, dict):
        return True
    sc = res.get('status_code')
    if sc is not None and str(sc) != '200':
        return True
    return not isinstance(res.get('data'), dict)
def tell(result, msg):
    if isinstance(result.get('data'), dict):
        result['data']['what_to_do_next'] = msg
    else:
        result['what_to_do_next'] = msg
'''


def _with_cfg(cfg: dict, body: str) -> str:
    src = "import json\nCFG = json.loads(" + json_literal(cfg) + ")\n" + _TV + body
    assert "{{" not in src and "}}" not in src
    return src


VERIFY_POST = r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        R = CFG.get('response') or dict()
        if failed(result):
            tell(result, 'The check service failed and nothing was checked. This is not a wrong answer. Call the check again with the same answer.')
        else:
            d = result['data']
            left = d.get(R.get('left') or 'left')
            hint = d.get(R.get('hint') or 'hint')
            hints = CFG.get('hints') or dict()
            if tv(d.get(R.get('all_verified') or 'all_verified')):
                msg = 'All answers are correct. The customer is verified.'
            elif left is not None and str(left) == '0' and not tv(d.get(R.get('verified') or 'verified')):
                msg = ('The identity check has ENDED. Ask nothing more and say nothing about why you called or about any account. '
                       + str(CFG.get('failed_say') or '') + ' Thank them, say goodbye, and call the closing tool with outcome '
                       + str((CFG.get('failed_close') or ['', ''])[0]) + ' and reason ' + str((CFG.get('failed_close') or ['', ''])[1]) + '.')
            elif hint and str(hint) in hints:
                msg = 'This does NOT count as a wrong answer. ' + str(hints[str(hint)])
            elif str(d.get(R.get('ok') or 'ok')).lower() == 'false':
                msg = 'The answer could not be read. This does NOT count as a wrong answer. Ask the customer to say it again more clearly.'
            elif tv(d.get(R.get('verified') or 'verified')):
                msg = 'That answer is correct. Now ask the next security question that has not been answered yet.'
            else:
                msg = ('That answer is WRONG. Wrong answers left: ' + str(left) + '. Tell the customer it does not match our records '
                       'and ask the same question again. Never reveal the correct answer.')
            d['what_to_do_next'] = msg
except Exception:
    pass
'''


def verify_pre(spec: dict) -> str:
    ident = spec.get("identity") or {}
    return identity_pre_source({
        "question_field": ident.get("question_field"), "answer_field": ident.get("answer_field"),
        "numeric_date_order": ident.get("numeric_date_order") or "dmy",
        "kinds": {q.get("value"): q.get("kind") for q in ident.get("questions", [])},
    })


def verify_post(spec: dict) -> str:
    ident = spec.get("identity") or {}
    return _with_cfg({"response": ident.get("response") or {}, "hints": ident.get("hints") or {},
                      "failed_say": (ident.get("on_failed") or {}).get("say", ""),
                      "failed_close": (ident.get("on_failed") or {}).get("close", ["", ""])}, VERIFY_POST)


PROMISE_PRE = r'''
try:
    b = config.get('body')
    F = CFG.get('fields') or dict()
    if isinstance(b, dict):
        tool = str(CFG.get('tool') or '')
        for key in ('product', 'amount', 'date'):
            f = F.get(key) or key
            v = b.get(f)
            if v is None or str(v).strip() == '' or '{' in str(v):
                for cand in (tool + '_args.' + tool + '_' + f, tool + '_args.' + f):
                    if vars.get(cand) not in (None, ''):
                        b[f] = vars.get(cand)
                        break
        ids = [s for s in str(vars.get('product_ids') or '').split(',') if s]
        pf = F.get('product') or 'product_id'
        pid = str(b.get(pf) or '').strip()
        if pid not in ids and ids:
            if len(ids) == 1:
                pid = ids[0]
            else:
                for k, s in enumerate(ids):
                    if pid.lower() in (str(k + 1), 'product ' + str(k + 1), s.lower()):
                        pid = s
        b[pf] = pid
        dls = json.loads(str(vars.get('deadlines_json') or '') or 'null') or dict()
        df = F.get('date') or 'date'
        ds = str(b.get(df) or '')[:10]
        if dls.get(pid) and len(ds) == 10:
            d, dd = D.fromisoformat(ds), D.fromisoformat(dls.get(pid))
            if d > dd:
                d = dd
            elif not isbiz(d):
                nb = nextbiz(d)
                d = nb if nb <= dd else dd
            b[df] = d.isoformat()
        af = F.get('amount') or 'amount'
        try:
            amt = float(str(b.get(af)).replace(',', ''))
            lim = (json.loads(str(vars.get('limits_json') or '') or 'null') or dict()).get(pid)
            if lim and lim[1] is not None and amt > float(lim[1]):
                amt = float(lim[1])
            b[af] = round(amt, 2)
        except Exception:
            pass
        config['body'] = b
except Exception:
    pass
'''

PROMISE_POST = r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        ok = (not failed(result)) and tv(result['data'].get('ok'))
        if ok:
            vars['promise_ok_count'] = str(int(float(str(vars.get('promise_ok_count') or '0'))) + 1)
            msg = ('This promise is RECORDED. If another agreed product is not recorded yet, record it now. When every agreed product is recorded, '
                   'tell the customer, and say exactly: "' + str(CFG.get('after_promise') or '') + '" '
                   + ('Then write a note for each product without a promise, one per message. ' if CFG.get('notes') else '')
                   + 'Then thank them, say goodbye and call the closing tool.')
        else:
            msg = ('The service failed and this promise is NOT saved. Never say it is saved. '
                   'If this is the first failure for this product, say only that there was a technical problem and you are trying again, and in the same message '
                   'call the promise tool again for the same product with exactly the same amount and date, without asking the customer. '
                   'If it already failed once for this product, tell the customer you could not record it. Keep the promises that are recorded. '
                   + ('Later write a note for this product with reason ' + str(CFG.get('service_error_note') or '') + '. ' if CFG.get('notes') else '')
                   + 'Continue with the next agreed product, or close.')
        tell(result, msg)
except Exception:
    pass
'''


def promise_pre(spec: dict) -> str:
    src = calendar_source(spec.get("calendar") or {}) + "\nCFG = json.loads(" + json_literal(
        {"fields": spec.get("tool_fields") or {}, "tool": (spec.get("tool_names") or {}).get("promise", "")}) + ")\n" + PROMISE_PRE
    assert "{{" not in src and "}}" not in src
    return src


def promise_post(spec: dict) -> str:
    notes = (spec.get("notes") or {})
    return _with_cfg({"after_promise": (spec.get("sentences") or {}).get("after_promise", ""),
                      "notes": bool(notes.get("used")), "service_error_note": notes.get("service_error_reason", "")},
                     PROMISE_POST)


NOTE_PRE = r'''
try:
    b = config.get('body')
    F = CFG.get('fields') or dict()
    if isinstance(b, dict):
        pf, rf = F.get('product') or 'product_id', F.get('note_reason') or 'reason'
        pid, r = str(b.get(pf) or '').strip(), str(b.get(rf) or '')
        seen = str(vars.get('notes_seen') or '')
        if pid and r:
            vars['notes_seen'] = (seen + ';' if seen else '') + pid + ':' + r
        config['body'] = b
except Exception:
    pass
'''


def note_pre(spec: dict) -> str:
    return _with_cfg({"fields": spec.get("tool_fields") or {}}, NOTE_PRE)


SIMPLE_POST = r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        ok = (not failed(result)) and tv(result['data'].get('ok'))
        tell(result, str(CFG.get('ok_msg') or '') if ok else str(CFG.get('fail_msg') or ''))
except Exception:
    pass
'''


def simple_post(ok_msg: str, fail_msg: str) -> str:
    return _with_cfg({"ok_msg": ok_msg, "fail_msg": fail_msg}, SIMPLE_POST)


CLOSE_PRE = r'''
def notes():
    out = dict()
    for it in str(vars.get('notes_seen') or '').split(';'):
        if ':' in it:
            p, r = it.split(':', 1)
            if p and r and p not in out:
                out[p] = r
    return out
try:
    b = config.get('body')
    L = CFG.get('logic') or dict()
    T = CFG.get('tools') or dict()
    F = CFG.get('fields') or dict()
    of, rf = F.get('outcome') or 'outcome', F.get('reason') or 'reason'
    if isinstance(b, dict) and L:
        tr = T.get('transfer') or ''
        tok = tv(vars.get(tr + '_response.data.ok'))
        q = str(vars.get(tr + '_args.' + (F.get('queue') or 'queue')) or '')
        pr = T.get('promise') or ''
        pcount = int(float(str(vars.get('promise_ok_count') or '0')))
        last_ok = tv(vars.get(pr + '_response.data.ok'))
        tried = (pr + '_response.data.ok') in vars or (pr + '_failure_count') in vars
        R = CFG.get('response') or dict()
        vf = T.get('verify') or ''
        left = str(vars.get(vf + '_response.data.' + (R.get('left') or 'left')))
        av = tv(vars.get(vf + '_response.data.' + (R.get('all_verified') or 'all_verified')))
        nt = notes()
        ids = [s for s in str(vars.get('product_ids') or '').split(',') if s]
        rq = L.get('reason_by_queue') or dict()
        if tok and q in rq:
            b[of], b[rf] = L.get('on_transfer'), rq[q]
        elif pcount > 0 or last_ok:
            b[of] = L.get('on_promise')
        elif nt and L.get('all_notes_paid'):
            order = [p for p in ids if p in nt] + [p for p in nt if p not in ids]
            if all(nt[p] == L.get('paid_note', 'paid') for p in order):
                b[of] = L.get('all_notes_paid')
            else:
                b[of] = L.get('no_promise')
                b[rf] = [nt[p] for p in order if nt[p] != L.get('paid_note', 'paid')][0]
        elif tried and b.get(of) == L.get('on_promise') and L.get('promise_failed'):
            b[of], b[rf] = L['promise_failed'][0], L['promise_failed'][1]
        elif left == '0' and not av and L.get('verify_failed'):
            b[of], b[rf] = L['verify_failed'][0], L['verify_failed'][1]
        if not b.get(rf) or b.get(of) in (L.get('on_promise'), L.get('all_notes_paid')):
            b.pop(rf, None)
        config['body'] = b
except Exception:
    pass
'''


def close_pre(spec: dict) -> str:
    return _with_cfg({"logic": spec.get("outcome_logic") or {}, "tools": spec.get("tool_names") or {},
                      "fields": spec.get("tool_fields") or {},
                      "response": (spec.get("identity") or {}).get("response") or {}}, CLOSE_PRE)
