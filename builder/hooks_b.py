"""Python snippets for the Brief B workflow (up to three products).

Reuses the Brief A helpers and adds multi-product account facts, per-product promise clamping,
note tracking and an outcome rule for close_call. No snippet may contain double braces.
"""
import hooks_a as A

MAX_PRODUCTS = 3
FIELDS = ["product_id", "type", "card_last4", "past_due", "days_late", "minimum_payment", "instalment_amount"]

GET_ACCOUNT_POST = r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        d = result.get('data')
        if isinstance(d, dict):
            pr = d.get('products')
            if isinstance(pr, list):
                d['n_products'] = len(pr)
                for i, p in enumerate(pr[:3]):
                    if isinstance(p, dict):
                        for k in ['product_id', 'type', 'card_last4', 'past_due', 'days_late', 'minimum_payment', 'instalment_amount']:
                            if k in p:
                                d['prod' + str(i + 1) + '_' + k] = p[k]
except Exception:
    pass
'''

DEBT_CODE = A.HELPERS + r'''
import json, re
def num(x):
    try:
        return float(str(x).replace(',', ''))
    except Exception:
        return None
def money(x):
    return '%.2f' % x
def load_products():
    out = []
    for i in range(1, 4):
        if vars.get('acc' + str(i) + '_type'):
            p = dict()
            for k in ['product_id', 'type', 'card_last4', 'past_due', 'days_late', 'minimum_payment', 'instalment_amount']:
                v = vars.get('acc' + str(i) + '_' + k)
                if v is not None and v != '':
                    p[k] = v
            out.append(p)
    if out:
        return out
    pr = vars.get('products')
    if isinstance(pr, str):
        try:
            pr = json.loads(pr)
        except Exception:
            try:
                import ast
                pr = ast.literal_eval(pr)
            except Exception:
                pr = None
    if isinstance(pr, list) and pr and isinstance(pr[0], dict):
        return pr[:3]
    by = dict()
    for k, v in list(vars.items()):
        m = re.search(r'products(?:\.|\[)(\d)\]?\.(\w+)$', str(k))
        if m:
            by.setdefault(int(m.group(1)), dict())[m.group(2)] = v
    return [by[i] for i in sorted(by)][:3]
def words_of(p):
    t = str(p.get('type') or '')
    if t == 'credit_card':
        return 'credit card ending ' + str(p.get('card_last4') or '')
    return 'personal loan' if t == 'personal_loan' else 'car loan'
def attempt1(today, deadline):
    monday = today - TD(days=today.weekday())
    a1 = monday + TD(days=4)
    while a1 > monday and not isbiz(a1):
        a1 = a1 - TD(days=1)
    if a1 <= today or not isbiz(a1):
        a1 = monday + TD(days=11)
        while not isbiz(a1):
            a1 = a1 - TD(days=1)
    return a1 if a1 <= deadline else deadline
try:
    today = D.fromisoformat(str(vars.get('now'))[:10])
    raw = load_products()
    prods = []
    for i, p in enumerate(raw):
        t = str(p.get('type') or '')
        past = num(p.get('past_due'))
        dl = int(float(str(p.get('days_late'))))
        floor = num(p.get('minimum_payment')) if t == 'credit_card' else num(p.get('instalment_amount'))
        early = dl <= 7
        deadline = nth_biz_after(today, 12 if early else 7)
        prods.append(dict(n=i + 1, pid=str(p.get('product_id') or ''), words=words_of(p), past=past, floor=floor, dl=dl,
                          band='early' if early else 'late', attempts=1 if early else 2, deadline=deadline,
                          a1=attempt1(today, deadline)))
    n = len(prods)
    ok = n > 0 and all(x['pid'] and x['past'] and x['floor'] and x['words'] for x in prods)
    blocks = []
    for x in prods:
        b = ['PRODUCT ' + str(x['n']) + ' of ' + str(n) + ': ' + x['words'] + ' (product_id ' + x['pid'] + ')',
             '- Full past-due amount: ' + money(x['past']),
             '- Days late: ' + str(x['dl']) + ' (band: ' + x['band'] + ')',
             '- Floor, the lowest amount you may record: ' + money(x['floor']),
             '- Deadline, the latest date you may record: ' + sp(x['deadline']) + ' (' + x['deadline'].isoformat() + ')',
             '- Persuasion attempts allowed for this product: ' + str(x['attempts']),
             '- Attempt 1: propose ' + money(x['past']) + ' on ' + sp(x['a1']) + '. If the customer already said the full amount of this product is too much, propose ' + money(x['floor']) + ' on ' + sp(x['a1']) + ' instead.']
        if x['attempts'] == 2:
            b.append('- Attempt 2: propose ' + money(x['floor']) + ' on ' + sp(x['deadline']) + '.')
        b.append('- After that, no attempts are left for this product: it is refused. Do not repeat any offer for it.')
        blocks.append('\n'.join(b))
    monday = today - TD(days=today.weekday())
    wk = []
    tm = today + TD(days=1)
    wk.append('- today = ' + sp(today) + ' (' + today.isoformat() + ')')
    wk.append('- tomorrow = ' + sp(tm) + ' (' + tm.isoformat() + ')')
    for i in range(7):
        t = monday + TD(days=i)
        nx = monday + TD(days=7 + i)
        wk.append('- "this ' + DN[i] + '" = ' + sp(t) + ('  (in the past)' if t < today else '') + '; "next ' + DN[i] + '" = ' + sp(nx))
    last = max([x['deadline'] for x in prods] or [today])
    cal = []
    xd = today
    while xd <= last + TD(days=21):
        tag = sp(xd) + ' (' + xd.isoformat() + ')' + (' [today]' if xd == today else '')
        parts = []
        for x in prods:
            nm = 'product ' + str(x['n']) + ' (' + x['words'] + ')' if n > 1 else 'the product'
            if xd > x['deadline']:
                act = 'AFTER its deadline. The latest date for it is ' + sp(x['deadline']) + '.'
            elif isbiz(xd):
                act = 'OK.'
            else:
                why = 'a Freya Bank holiday' if xd.isoformat() in HOL else 'a weekend day'
                nb = nextbiz(xd)
                act = ('NOT allowed, ' + why + '. Offer the next business day, ' + sp(nb) + '.') if nb <= x['deadline'] else (
                      'NOT allowed, ' + why + '. Offer ' + sp(x['deadline']) + '.')
            parts.append(nm + ': ' + act if n > 1 else act)
        cal.append('- ' + tag + ': ' + ' '.join(parts))
        xd = xd + TD(days=1)
    if n == 1:
        x = prods[0]
        line = ('Thank you, you are verified. I am calling from the collections team about a late payment on your ' + x['words'] +
                '. The past-due amount is ' + money(x['past']) + ', and it is ' + str(x['dl']) + ' days late. Can you make this payment today?')
    else:
        sents = []
        for x in prods:
            sents.append('Your ' + x['words'] + ' has a past-due amount of ' + money(x['past']) + ' and is ' + str(x['dl']) + ' days late.')
        line = ('Thank you, you are verified. I am calling from the collections team about late payments on ' + str(n) + ' of your products. ' +
                ' '.join(sents) + ' Can you pay all of them today?')
    for x in prods:
        k = str(x['n'])
        intro = ('Let us start with your ' if x['n'] == 1 else 'Now your ') + x['words'] + '. '
        vars['p' + k + '_block'] = blocks[x['n'] - 1]
        vars['p' + k + '_words'] = x['words']
        vars['p' + k + '_a1_line'] = intro + 'Can you pay the full ' + money(x['past']) + ' on ' + sp(x['a1']) + '?'
        vars['p' + k + '_a1_floor_line'] = intro + 'Can you pay ' + money(x['floor']) + ' on ' + sp(x['a1']) + '?'
        vars['p' + k + '_a2_line'] = ('Could you pay ' + money(x['floor']) + ' on ' + sp(x['deadline']) + ' instead?') if x['attempts'] == 2 else 'none, this product has only one attempt'
        if x['attempts'] == 2:
            rule = ('This product is in the late band: it has TWO persuasion attempts. A flat refusal or a non-answer uses one attempt, in order. '
                    'Attempt 1: the attempt 1 line. Attempt 2: say "' + vars['p' + k + '_a2_line'] + '" '
                    'If an offer was already said and refused, that attempt is used up. When both attempts are refused, make NO other offer.')
        else:
            rule = ('This product is in the early band: it has ONE persuasion attempt only, the attempt 1 line. '
                    'When the customer refuses it or does not answer it, make NO other offer for this product: no floor, no lower amount, no other date.')
        vars['p' + k + '_attempt_rule'] = rule
        vars['p' + k + '_floor_line'] = 'The lowest amount I can accept for your ' + x['words'] + ' is ' + money(x['floor']) + ', and the rest stays overdue.'
        pc = []
        xd = today
        while xd <= x['deadline'] + TD(days=21):
            tag = sp(xd) + ' (' + xd.isoformat() + ')' + (' [today]' if xd == today else '')
            if xd > x['deadline']:
                act = 'AFTER the deadline. Say the latest date you can record for it is ' + sp(x['deadline']) + ' and offer it.'
            elif isbiz(xd):
                act = 'OK, can be recorded.'
            else:
                why = 'a Freya Bank holiday' if xd.isoformat() in HOL else 'a weekend day'
                nb = nextbiz(xd)
                act = ('NOT allowed, ' + why + '. Offer the next business day, ' + sp(nb) + '.') if nb <= x['deadline'] else (
                      'NOT allowed, ' + why + '. Offer ' + sp(x['deadline']) + '.')
            pc.append('- ' + tag + ': ' + act)
            xd = xd + TD(days=1)
        vars['p' + k + '_calendar'] = '\n'.join(pc)
    dt = []
    xd = today
    while xd <= last + TD(days=21):
        tag = sp(xd) + ' (' + xd.isoformat() + ')' + (' [today]' if xd == today else '')
        if isbiz(xd):
            act = 'business day.'
        else:
            why = 'a Freya Bank holiday' if xd.isoformat() in HOL else 'a weekend day'
            act = 'NOT a business day (' + why + '). Offer the next business day, ' + sp(nextbiz(xd)) + '.'
        dt.append('- ' + tag + ': ' + act)
        xd = xd + TD(days=1)
    vars['day_table'] = '\n'.join(dt)
    vars['debt_line'] = line
    vars['n_products'] = str(n)
    vars['product_ids'] = ','.join(x['pid'] for x in prods)
    vars['product_list'] = '; '.join('product ' + str(x['n']) + ' = ' + x['words'] + ' (' + x['pid'] + ')' for x in prods)
    vars['products_block'] = '\n\n'.join(blocks)
    vars['deadlines_json'] = json.dumps(dict((x['pid'], x['deadline'].isoformat()) for x in prods))
    vars['limits_json'] = json.dumps(dict((x['pid'], [x['floor'], x['past']]) for x in prods))
    vars['week_table'] = '\n'.join(wk)
    vars['calendar'] = '\n'.join(cal)
    vars['debt_state'] = 'ok' if ok else 'error'
except Exception as e:
    vars['debt_state'] = 'error'
    vars['debt_error'] = str(e)
'''

PROMISE_PRE = A.HELPERS + r'''
import json
try:
    b = config.get('body')
    if isinstance(b, dict):
        ids = [s for s in str(vars.get('product_ids') or '').split(',') if s]
        pid = str(b.get('product_id') or '').strip()
        if pid not in ids and ids:
            low = pid.lower()
            for k, s in enumerate(ids):
                if low in (str(k + 1), 'product ' + str(k + 1), s.lower()):
                    pid = s
        b['product_id'] = pid
        dls = json.loads(str(vars.get('deadlines_json') or '') or 'null') or dict()
        dlv = dls.get(pid)
        ds = str(b.get('date') or '')[:10]
        if dlv and len(ds) == 10:
            d = D.fromisoformat(ds)
            dd = D.fromisoformat(dlv)
            if d > dd:
                d = dd
            elif not isbiz(d):
                nb = nextbiz(d)
                d = nb if nb <= dd else dd
            b['date'] = d.isoformat()
        lim = (json.loads(str(vars.get('limits_json') or '') or 'null') or dict()).get(pid)
        try:
            amt = float(str(b.get('amount')).replace(',', ''))
            if lim and amt > float(lim[1]):
                amt = float(lim[1])
            b['amount'] = round(amt, 2)
        except Exception:
            pass
        vars['cp_last_pid'] = pid
        config['body'] = b
except Exception:
    pass
'''

PROMISE_POST = A._TV + r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        ok = (not failed(result)) and tv(result['data'].get('ok'))
        if ok:
            vars['promise_ok_count'] = str(int(float(str(vars.get('promise_ok_count') or '0'))) + 1)
        msg = ('This promise is RECORDED. If another agreed product is not recorded yet, call create_promise for it now. '
               'When every agreed product is recorded, tell the customer the promises are recorded and say exactly: "You will receive a text message confirming this promise." '
               'Then call add_note for each product that has no promise, one per message. Then thank them, say goodbye and call close_call.') if ok else (
               'The service failed and this promise is NOT saved. Do not say it is recorded. '
               'If this is the first failed create_promise for this product, say only: "There was a technical problem, one moment while I try again." and in the same message call create_promise again for the same product with exactly the same amount and date, without asking the customer. '
               'If create_promise already failed once before for this product, tell the customer you could not record the promise for this product. '
               'Keep the promises that are recorded. Continue with the next agreed product. Later call add_note for this product with reason service_error.')
        if isinstance(result.get('data'), dict):
            result['data']['what_to_do_next'] = msg
        else:
            result['what_to_do_next'] = msg
except Exception:
    pass
'''

NOTE_PRE = r'''
try:
    b = config.get('body')
    if isinstance(b, dict):
        ids = [s for s in str(vars.get('product_ids') or '').split(',') if s]
        pid = str(b.get('product_id') or '').strip()
        if pid not in ids and ids:
            low = pid.lower()
            for k, s in enumerate(ids):
                if low in (str(k + 1), 'product ' + str(k + 1), s.lower()):
                    pid = s
        b['product_id'] = pid
        r = str(b.get('reason') or '')
        seen = str(vars.get('notes_seen') or '')
        if pid and r:
            vars['notes_seen'] = (seen + ';' if seen else '') + pid + ':' + r
        vars['note_last'] = pid + ':' + r
        config['body'] = b
except Exception:
    pass
'''

NOTE_POST = A._TV + r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        ok = (not failed(result)) and tv(result['data'].get('ok'))
        pid = str(vars.get('add_note_args.product_id') or '')
        r = str(vars.get('add_note_args.reason') or '')
        last = str(vars.get('note_last') or '')
        item = (pid + ':' + r) if (pid and r) else last
        seen = str(vars.get('notes_post') or '')
        if ok and item and item not in seen.split(';'):
            vars['notes_post'] = (seen + ';' if seen else '') + item
        msg = ('The note is saved. Call add_note for the next product without a promise, if any. When every product without a promise has its note, thank the customer, say goodbye and call close_call.') if ok else (
               'The note was NOT saved: the service failed. Call add_note again once with the same product_id and reason. If it fails again, continue.')
        if isinstance(result.get('data'), dict):
            result['data']['what_to_do_next'] = msg
        else:
            result['what_to_do_next'] = msg
except Exception:
    pass
'''

CLOSE_PRE = A._TV + r'''
def notes():
    out = dict()
    for key in ['notes_post', 'notes_seen']:
        for it in str(vars.get(key) or '').split(';'):
            if ':' in it:
                p, r = it.split(':', 1)
                if p and r and p not in out:
                    out[p] = r
    return out
try:
    b = config.get('body')
    if isinstance(b, dict):
        tok = tv(vars.get('transfer_to_agent_response.data.ok'))
        q = str(vars.get('transfer_to_agent_args.queue') or '')
        pcount = int(float(str(vars.get('promise_ok_count') or '0')))
        last_ok = tv(vars.get('create_promise_response.data.ok'))
        has_p = 'create_promise_response.data.ok' in vars
        succ = int(float(str(vars.get('create_promise_success_count') or '0')))
        left = str(vars.get('verify_identity_response.data.wrong_answers_left'))
        av = tv(vars.get('verify_identity_response.data.all_verified'))
        nt = notes()
        ids = [s for s in str(vars.get('product_ids') or '').split(',') if s]
        if tok and q in ('general', 'support', 'restructuring'):
            b['outcome'] = 'transferred'
            b['reason'] = 'human' if q == 'general' else q
        elif pcount > 0 or last_ok or (b.get('outcome') == 'promise' and succ > 0 and has_p):
            b['outcome'] = 'promise'
        elif nt:
            order = [p for p in ids if p in nt] + [p for p in nt if p not in ids]
            if all(nt[p] == 'paid' for p in order):
                b['outcome'] = 'paid'
            else:
                b['outcome'] = 'no_promise'
                b['reason'] = [nt[p] for p in order if nt[p] != 'paid'][0]
        elif has_p and b.get('outcome') == 'promise':
            b['outcome'] = 'no_promise'
            b['reason'] = 'service_error'
        elif left == '0' and not av:
            b['outcome'] = 'not_verified'
            b['reason'] = 'failed'
        if b.get('outcome') in ('promise', 'paid') or not b.get('reason'):
            b.pop('reason', None)
        config['body'] = b
except Exception:
    pass
'''

for _name, _src in list(globals().items()):
    if _name.isupper() and isinstance(_src, str):
        assert '{{' not in _src and '}}' not in _src, _name
