"""Python snippets that run inside the Freya workflow (code nodes and tool hooks) for Brief A.

Every snippet reads and writes through `vars` / `config` / `result`, never raises and contains no
double braces (the platform may template them).
"""

HELPERS = r'''
import datetime
HOL = ['2026-10-26', '2026-11-11', '2026-11-26', '2026-12-25', '2027-01-01']
DN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
D = datetime.date
TD = datetime.timedelta
def isbiz(d):
    return d.weekday() < 5 and d.isoformat() not in HOL
def sp(d):
    return DN[d.weekday()] + ' ' + str(d.day) + ' ' + MN[d.month - 1] + ' ' + str(d.year)
def nextbiz(d):
    x = d + TD(days=1)
    while not isbiz(x):
        x = x + TD(days=1)
    return x
def nth_biz_after(d, n):
    x = d
    k = 0
    while k < n:
        x = x + TD(days=1)
        if isbiz(x):
            k += 1
    return x
'''

SETUP_CODE = HELPERS + r'''
try:
    now = str(vars.get('now') or '')
    today = D.fromisoformat(now[:10])
    hm = now[11:16] if len(now) >= 16 else '09:00'
    vars['today_iso'] = today.isoformat()
    vars['today_spoken'] = sp(today)
    vars['now_time'] = hm
    tm = today + TD(days=1)
    vars['tomorrow_spoken'] = sp(tm) + ' (' + tm.isoformat() + ')'
    nb = nextbiz(today)
    lines = []
    if hm < '19:00':
        start = 'from 10:00' if hm < '10:00' else 'any time later than ' + hm
        lines.append('- Today, ' + sp(today) + ' (' + today.isoformat() + '): ' + start + ' up to 19:00 included.')
    else:
        lines.append('- Today is no longer possible: it is after 19:00.')
    lines.append('- The next business day, ' + sp(nb) + ' (' + nb.isoformat() + '): from 10:00 to 19:00, both included.')
    lines.append('- Every other day, and every time before 10:00 or after 19:00, is OUTSIDE the window.')
    if tm != nb:
        lines.append('- Tomorrow, ' + sp(tm) + ', is not a business day, so it is OUTSIDE the window.')
    vars['callback_facts'] = '\n'.join(lines)
    vars['setup_state'] = 'ok'
except Exception as e:
    vars['today_iso'] = str(vars.get('now') or '')[:10]
    vars['today_spoken'] = str(vars.get('now') or '')
    vars['now_time'] = str(vars.get('now') or '')[11:16]
    vars['tomorrow_spoken'] = 'the day after today'
    vars['callback_facts'] = '- Today later than now up to 19:00, or the next business day from 10:00 to 19:00.'
    vars['setup_state'] = 'error ' + str(e)
'''

GET_ACCOUNT_POST = r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        d = result.get('data')
        if isinstance(d, dict):
            pr = d.get('products')
            if isinstance(pr, list) and pr and isinstance(pr[0], dict):
                p = pr[0]
                for k in ['product_id', 'type', 'card_last4', 'past_due', 'days_late', 'minimum_payment', 'instalment_amount']:
                    if k in p:
                        d['p_' + k] = p[k]
except Exception:
    pass
'''

DEBT_CODE = HELPERS + r'''
import json, re
def num(x):
    try:
        return float(str(x).replace(',', ''))
    except Exception:
        return None
def money(x):
    return '%.2f' % x
def find_product():
    if vars.get('acc_type'):
        return {'type': vars.get('acc_type'), 'product_id': vars.get('acc_product_id'), 'past_due': vars.get('acc_past_due'),
                'days_late': vars.get('acc_days_late'), 'minimum_payment': vars.get('acc_minimum_payment'),
                'instalment_amount': vars.get('acc_instalment_amount'), 'card_last4': vars.get('acc_card_last4')}
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
        return pr[0]
    p = dict()
    for k, v in list(vars.items()):
        m = re.search(r'products(?:\.|\[)0\]?\.(\w+)$', str(k))
        if m:
            p[m.group(1)] = v
        m = re.search(r'\.data\.p_(\w+)$', str(k))
        if m and m.group(1) not in p:
            p[m.group(1)] = v
    return p
try:
    today = D.fromisoformat(str(vars.get('now'))[:10])
    p = find_product()
    ptype = str(p.get('type') or '')
    pid = str(p.get('product_id') or '')
    past = num(p.get('past_due'))
    dl = int(float(str(p.get('days_late'))))
    if ptype == 'credit_card':
        floor = num(p.get('minimum_payment'))
        words = 'credit card ending ' + str(p.get('card_last4') or '')
    else:
        floor = num(p.get('instalment_amount'))
        words = 'personal loan' if ptype == 'personal_loan' else 'car loan'
    early = dl <= 7
    band = 'early' if early else 'late'
    deadline = nth_biz_after(today, 12 if early else 7)
    attempts = 1 if early else 2
    monday = today - TD(days=today.weekday())
    a1 = monday + TD(days=4)
    while a1 > monday and not isbiz(a1):
        a1 = a1 - TD(days=1)
    if a1 <= today or not isbiz(a1):
        a1 = monday + TD(days=11)
        while not isbiz(a1):
            a1 = a1 - TD(days=1)
    if a1 > deadline:
        a1 = deadline
    wk = []
    tm = today + TD(days=1)
    wk.append('- today = ' + sp(today) + ' (' + today.isoformat() + ')')
    wk.append('- tomorrow = ' + sp(tm) + ' (' + tm.isoformat() + ')')
    for i in range(7):
        t = monday + TD(days=i)
        n = monday + TD(days=7 + i)
        wk.append('- "this ' + DN[i] + '" = ' + sp(t) + ('  (in the past)' if t < today else '') + '; "next ' + DN[i] + '" = ' + sp(n))
    cal = []
    x = today
    end = deadline + TD(days=21)
    while x <= end:
        tag = sp(x) + ' (' + x.isoformat() + ')' + (' [today]' if x == today else '')
        if x > deadline:
            act = 'AFTER the deadline. Say the latest date you can record is ' + sp(deadline) + ' and offer it.'
        elif isbiz(x):
            act = 'OK, can be recorded.'
        else:
            why = 'a Freya Bank holiday' if x.isoformat() in HOL else 'a weekend day'
            nbx = nextbiz(x)
            if nbx <= deadline:
                act = 'NOT allowed, ' + why + '. Offer the next business day, ' + sp(nbx) + '.'
            else:
                act = 'NOT allowed, ' + why + ', and the next business day is after the deadline. Offer ' + sp(deadline) + '.'
        cal.append('- ' + tag + ': ' + act)
        x = x + TD(days=1)
    vars['product_id'] = pid
    vars['product_words'] = words
    vars['past_due_text'] = money(past)
    vars['floor_text'] = money(floor)
    vars['days_late_text'] = str(dl)
    vars['band'] = band
    vars['attempts'] = str(attempts)
    vars['deadline_iso'] = deadline.isoformat()
    vars['deadline_spoken'] = sp(deadline)
    vars['attempt1_iso'] = a1.isoformat()
    vars['attempt1_spoken'] = sp(a1)
    fp = ['- Attempt 1: propose ' + money(floor) + ' on ' + sp(a1) + '.']
    if attempts == 2 and deadline != a1:
        fp.append('- Attempt 2: propose ' + money(floor) + ' on ' + sp(deadline) + '.')
    fp.append('- After that no attempts are left: stop, thank them, say goodbye and call close_call with outcome no_promise and reason refused.')
    vars['floor_plan'] = '\n'.join(fp)
    vars['week_table'] = '\n'.join(wk)
    vars['calendar'] = '\n'.join(cal)
    vars['debt_state'] = 'ok' if (pid and past and floor and ptype) else 'error'
except Exception as e:
    vars['debt_state'] = 'error'
    vars['debt_error'] = str(e)
'''

VERIFY_PRE = r'''
import re
MONTHS = [('jan', 1), ('feb', 2), ('mar', 3), ('apr', 4), ('may', 5), ('jun', 6), ('jul', 7), ('aug', 8), ('sep', 9), ('oct', 10), ('nov', 11), ('dec', 12)]
try:
    b = config.get('body')
    if isinstance(b, dict):
        f = str(b.get('field') or '')
        a = str(b.get('answer') or '').strip()
        if f == 'phone_last4':
            dg = re.sub(r'\D', '', a)
            if len(dg) >= 4:
                b['answer'] = dg[-4:]
        elif f == 'date_of_birth' and not re.match(r'^\d{4}-\d{2}-\d{2}$', a):
            s = a.lower()
            out = None
            m = re.match(r'^(\d{4})[./\- ](\d{1,2})[./\- ](\d{1,2})$', s)
            if m:
                out = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            m = re.match(r'^(\d{1,2})[./\- ](\d{1,2})[./\- ](\d{4})$', s)
            if m:
                out = (int(m.group(3)), int(m.group(2)), int(m.group(1)))
            if out is None:
                yr = re.search(r'(\d{4})', s)
                mo = None
                for k, v in MONTHS:
                    if re.search(r'\b' + k, s):
                        mo = v
                        break
                rest = s.replace(yr.group(1), ' ') if yr else s
                dm = re.search(r'(\d{1,2})', rest)
                if yr and mo and dm:
                    out = (int(yr.group(1)), mo, int(dm.group(1)))
            if out is not None:
                b['answer'] = '%04d-%02d-%02d' % out
        config['body'] = b
except Exception:
    pass
'''

_TV = r'''
def tv(x):
    return x is True or str(x).strip().lower() == 'true'
def failed(res):
    if not isinstance(res, dict):
        return True
    sc = res.get('status_code')
    d = res.get('data')
    if sc is not None and str(sc) != '200':
        return True
    return not isinstance(d, dict)
'''

VERIFY_POST = _TV + r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        if failed(result):
            result['what_to_do_next'] = 'The check service failed and nothing was checked. This is not a wrong answer. Call verify_identity again with the same answer.'
        else:
            d = result['data']
            left = d.get('wrong_answers_left')
            if tv(d.get('all_verified')):
                msg = 'Both answers are correct. The customer is verified.'
            elif left is not None and str(left) == '0' and not tv(d.get('verified')):
                msg = ('The identity check has ENDED after three wrong answers. Do not ask any more questions and do not say anything about why you called or about any account. '
                       'Tell the customer to use the Freya Bank mobile app or visit a branch. Thank them, say goodbye, and call close_call with outcome not_verified and reason failed.')
            elif d.get('hint') == 'day_month_swapped':
                msg = ('The day and the month look swapped. This does NOT count as a wrong answer. '
                       'Ask the customer to say the date of birth again with the month as a word, for example the 5th of June 1980.')
            elif d.get('ok') is False or str(d.get('ok')).lower() == 'false':
                msg = ('The answer could not be read. This does NOT count as a wrong answer. If it was a date of birth, send it again as YYYY-MM-DD, '
                       'or ask the customer to say it again with the month as a word.')
            elif tv(d.get('verified')):
                msg = 'That answer is correct. Now ask the next open security question: the last four digits of the phone number on file.'
            else:
                msg = ('That answer is WRONG. Wrong answers left: ' + str(left) + '. Tell the customer it does not match our records and ask the same question again. '
                       'Do not reveal the correct answer.')
            d['what_to_do_next'] = msg
except Exception:
    pass
'''

PROMISE_POST = _TV + r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        ok = (not failed(result)) and tv(result['data'].get('ok'))
        msg = ('The promise is RECORDED. Tell the customer it is recorded and say exactly: "You will receive a text message confirming this promise." '
               'Then thank them, say goodbye and call close_call with outcome promise.') if ok else (
               'The service failed and the promise is NOT saved. Do not use the word recorded. '
               'If this is the first failed create_promise in this call, say only: "There was a technical problem, one moment while I try again." and in the same message call create_promise again with exactly the same amount and date, without asking the customer. '
               'If create_promise already failed once before in this call, tell the customer you could not record the promise, thank them, say goodbye and call close_call with outcome no_promise and reason service_error.')
        if isinstance(result.get('data'), dict):
            result['data']['what_to_do_next'] = msg
        else:
            result['what_to_do_next'] = msg
except Exception:
    pass
'''

CALLBACK_POST = _TV + r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        ok = (not failed(result)) and tv(result['data'].get('ok'))
        msg = ('The callback is BOOKED. Tell the person the customer will be called back then. Thank them, say goodbye and call close_call with outcome not_reached and reason callback.') if ok else (
               'The callback was NOT booked: the service failed. Never say it is booked. If this is the first failure, call schedule_callback again with the same date and time. '
               'If it already failed once, tell the person you could not book the callback, thank them, say goodbye and call close_call with outcome not_reached and reason no_callback.')
        if isinstance(result.get('data'), dict):
            result['data']['what_to_do_next'] = msg
        else:
            result['what_to_do_next'] = msg
except Exception:
    pass
'''

TRANSFER_POST = _TV + r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        ok = (not failed(result)) and tv(result['data'].get('ok'))
        msg = ('The transfer is done. Tell the customer you are connecting them now, thank them, say goodbye and call close_call with outcome transferred '
               'and the reason for this queue: restructuring -> restructuring, general -> human, support -> support.') if ok else (
               'The transfer did NOT work: the service failed. Never say they are being transferred. If this is the first failure, call transfer_to_agent again with the same queue. '
               'If it already failed once, tell the customer you could not connect them and continue helping them.')
        if isinstance(result.get('data'), dict):
            result['data']['what_to_do_next'] = msg
        else:
            result['what_to_do_next'] = msg
except Exception:
    pass
'''

CLOSE_PRE = _TV + r'''
try:
    b = config.get('body')
    if isinstance(b, dict):
        tok = tv(vars.get('transfer_to_agent_response.data.ok'))
        q = str(vars.get('transfer_to_agent_args.queue') or '')
        has_p = 'create_promise_response.data.ok' in vars
        pok = tv(vars.get('create_promise_response.data.ok'))
        left = str(vars.get('verify_identity_response.data.wrong_answers_left'))
        av = tv(vars.get('verify_identity_response.data.all_verified'))
        if tok and q in ('general', 'support', 'restructuring'):
            b['outcome'] = 'transferred'
            b['reason'] = 'human' if q == 'general' else q
        elif has_p and pok:
            b['outcome'] = 'promise'
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

CLOSE_POST = _TV + r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
        ok = (not failed(result)) and tv(result['data'].get('ok'))
        if not ok:
            msg = 'close_call failed. Call close_call again with the same outcome and reason. Say nothing else.'
            if isinstance(result.get('data'), dict):
                result['data']['what_to_do_next'] = msg
            else:
                result['what_to_do_next'] = msg
except Exception:
    pass
'''

ALL = {k: v for k, v in dict(globals()).items() if k.isupper() and isinstance(v, str) and k not in ('HELPERS', '_TV')}
for _name, _src in ALL.items():
    assert '{{' not in _src and '}}' not in _src, _name

RETRY_PRE = r'''
try:
    b = config.get('body')
    if not isinstance(b, dict):
        b = dict()
    b['customer_id'] = str(vars.get('customer_id') or b.get('customer_id') or '')
    b['product_id'] = str(vars.get('create_promise_args.product_id') or vars.get('product_id') or b.get('product_id') or '')
    b['amount'] = float(str(vars.get('create_promise_args.amount') or b.get('amount')).replace(',', ''))
    b['date'] = str(vars.get('create_promise_args.date') or b.get('date') or '')[:10]
    config['body'] = b
except Exception:
    pass
'''
assert '{{' not in RETRY_PRE and '}}' not in RETRY_PRE
