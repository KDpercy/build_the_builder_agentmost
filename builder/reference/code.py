"""Code-node and hook sources for the reference workflow, driven by spec.json.

No brief values here: products, fields, bands, floors, attempts and sentences come from the spec.
"""
import json

from lib.calendar_code import calendar_source
from lib.date_facts import date_facts_source

MAX_PRODUCTS = 3

DEBT = r'''
import json, re
def num(x):
    try:
        return float(str(x).replace(',', ''))
    except Exception:
        return None
def money(x):
    return '%.2f' % x if x is not None else ''
PF = (SPEC.get('products') or dict()).get('fields') or dict()
TYPES = (SPEC.get('products') or dict()).get('types') or dict()
TYPE_FIELD = (SPEC.get('products') or dict()).get('type_field') or 'type'
ATTEMPTS = (SPEC.get('persuasion') or dict()).get('attempts') or []
def products_from_vars():
    pr = vars.get('account_products')
    if isinstance(pr, str):
        try:
            pr = json.loads(pr)
        except Exception:
            try:
                import ast
                pr = ast.literal_eval(pr)
            except Exception:
                pr = None
    if isinstance(pr, list) and pr:
        return [p for p in pr if isinstance(p, dict)][:MAXP]
    path = str((SPEC.get('products') or dict()).get('response_path') or 'data.products')
    if path.startswith('data.'):
        path = path[5:]
    pat = re.compile(r'_response\.(?:data\.)?' + re.escape(path) + r'\.(\d+)\.(\w+)$')     # with or without the envelope
    by = dict()
    for key, val in list(vars.items()):
        m = pat.search(str(key))
        if m:
            by.setdefault(int(m.group(1)), dict())[m.group(2)] = val
    return [by[i] for i in sorted(by)][:MAXP]
def spoken(p):
    t = TYPES.get(str(p.get(TYPE_FIELD) or '')) or dict()
    s = str(t.get('spoken') or str(p.get(TYPE_FIELD) or 'product').replace('_', ' '))
    for k, v in p.items():
        s = s.replace('{' + str(k) + '}', str(v))
    return s
def offer(kind, x, too_much):
    if kind == 'floor' or (kind == 'full_or_floor_if_too_much' and too_much):
        return x['floor']
    return x['past']
try:
    today = D.fromisoformat(str(vars.get(SPEC.get('now_variable') or 'now'))[:10])
    raw = products_from_vars()
    prods = []
    for i, p in enumerate(raw):
        dl = int(float(str(p.get(PF.get('late_days') or ''))))
        band = band_for(dl) or dict()
        deadline = date_expr(band.get('deadline'), today)
        t = TYPES.get(str(p.get(TYPE_FIELD) or '')) or dict()
        x = dict(n=i + 1, pid=str(p.get(PF.get('id') or '') or ''), words=spoken(p),
                 past=num(p.get(PF.get('due_amount') or '')), floor=num(p.get(t.get('floor_field') or '')),
                 dl=dl, band=str(band.get('name') or ''), attempts=int(band.get('attempts') or 0), deadline=deadline)
        x['dates'] = [date_expr(a.get('date'), today, deadline) for a in ATTEMPTS]
        prods.append(x)
    n = len(prods)
    ok = n > 0 and all(x['pid'] and x['past'] and x['words'] for x in prods)
    for x in prods:
        k = str(x['n'])
        lines = []
        for j in range(x['attempts']):
            if j < len(ATTEMPTS):
                a = ATTEMPTS[j]
                lines.append('- Attempt ' + str(j + 1) + ': propose ' + money(offer(a.get('amount'), x, False)) + ' on ' + sp(x['dates'][j]) + '.')
        lines.insert(0, 'This product allows exactly ' + str(len(lines)) + ' persuasion attempt(s). Count them.')
        lines.append('- After attempt ' + str(len(lines) - 1) + ' no attempts are left: make NO other offer for this product, no floor, no lower amount, '
                     'no other date. It is refused; do not repeat any offer.')
        vars['p' + k + '_attempts'] = '\n'.join(lines)
        vars['p' + k + '_block'] = '\n'.join([
            'PRODUCT ' + k + ' of ' + str(n) + ': ' + x['words'] + ' (id ' + x['pid'] + ')',
            '- Full past-due amount: ' + money(x['past']),
            '- Days late: ' + str(x['dl']) + ' (band: ' + x['band'] + ')',
            '- Floor, the lowest amount you may record: ' + money(x['floor']),
            '- Deadline, the latest date you may record: ' + sp(x['deadline']) + ' (' + x['deadline'].isoformat() + ')',
            '- Persuasion attempts allowed: ' + str(x['attempts'])])
        vars['p' + k + '_calendar'] = calendar_lines(today, x['deadline'])
        vars['p' + k + '_words'] = x['words']
        vars['p' + k + '_floor'] = money(x['floor'])
        vars['p' + k + '_past'] = money(x['past'])
        vars['p' + k + '_deadline'] = sp(x['deadline'])
    vars['products_block'] = '\n\n'.join(vars['p' + str(x['n']) + '_block'] for x in prods)
    last = max([x['deadline'] for x in prods] or [today])
    cal, d = [], today
    while d <= last + TD(days=21):
        parts = []
        for x in prods:
            if d > x['deadline']:
                act = 'after its deadline; the latest date for it is ' + sp(x['deadline'])
            elif isbiz(d):
                act = 'OK'
            else:
                nb = nextbiz(d)
                act = 'not a business day; offer ' + sp(nb if nb <= x['deadline'] else x['deadline'])
            parts.append(('product ' + str(x['n']) + ': ' if n > 1 else '') + act + '.')
        cal.append('- ' + sp(d) + ' (' + d.isoformat() + ')' + (' [today]' if d == today else '') + ': ' + ' '.join(parts))
        d = d + TD(days=1)
    vars['all_calendar'] = '\n'.join(cal)
    vars['agreements_json'] = '[]'
    vars['agreements_text'] = 'none yet'
    for x in prods:
        vars['p' + str(x['n']) + '_agreed'] = 'no'
        vars['p' + str(x['n']) + '_words_id'] = x['words'] + ' (id ' + x['pid'] + ')' 
    vars['n_products'] = str(n)
    vars['prod_ids'] = ','.join(x['pid'] for x in prods)
    vars['product_list'] = '; '.join('product ' + str(x['n']) + ' = ' + x['words'] + ' (' + x['pid'] + ')' for x in prods)
    vars['deadlines_json'] = json.dumps(dict((x['pid'], x['deadline'].isoformat()) for x in prods))
    vars['limits_json'] = json.dumps(dict((x['pid'], [x['floor'], x['past']]) for x in prods))
    st = str(SPEC.get('debt_statement') or '')
    if n == 1:
        x = prods[0]
        vars['debt_line'] = ('Thank you, you are verified. ' + st + ' on your ' + x['words'] + '. The past-due amount is ' + money(x['past'])
                             + ', and it is ' + str(x['dl']) + ' days late. ' + str(SPEC.get('first_ask') or ''))
    else:
        sents = ['Your ' + x['words'] + ' has a past-due amount of ' + money(x['past']) + ' and is ' + str(x['dl']) + ' days late.' for x in prods]
        vars['debt_line'] = ('Thank you, you are verified. ' + st + ' on ' + str(n) + ' of your products. ' + ' '.join(sents) + ' '
                             + str(SPEC.get('first_ask_all') or SPEC.get('first_ask') or ''))
    vars['debt_state'] = 'ok' if ok else 'error'
except Exception as e:
    vars['debt_state'] = 'error'
    vars['debt_error'] = str(e)
'''


def setup_source(spec: dict) -> str:
    return date_facts_source(spec)


def debt_source(spec: dict) -> str:
    src = date_facts_source(spec) + "\nMAXP = " + str(MAX_PRODUCTS) + "\n" + DEBT
    assert "{{" not in src and "}}" not in src
    return src


GET_ACCOUNT_POST = r'''
try:
    if isinstance(result, dict):
        result.pop('header', None)
except Exception:
    pass
'''


def products_mapping(spec: dict) -> list:
    """get_account response -> the variable the debt code reads (a JSON list of products)."""
    path = (spec.get("products") or {}).get("response_path") or "data.products"
    return [{"path": path, "variable": "account_products"}]


AGREE = r'''
import json
try:
    p = params if isinstance(params, dict) else dict()
except Exception:
    p = dict()
try:
    k = str(p.get('product_number') or '').strip()
    amt = float(str(p.get('amount')).replace(',', ''))
    d = str(p.get('date') or '')[:10]
    day = D.fromisoformat(d)
    items = [a for a in json.loads(str(vars.get('agreements_json') or '[]')) if str(a.get('n')) != k]
    items.append(dict(n=k, words=str(vars.get('p' + k + '_words_id') or ('product ' + k)), amount='%.2f' % amt, date=d, spoken=sp(day)))
    items.sort(key=lambda a: int(a['n']))
    vars['agreements_json'] = json.dumps(items)
    vars['agreements_text'] = '\n'.join('- product ' + a['n'] + ', ' + a['words'] + ': ' + a['amount'] + ' on ' + a['spoken'] + ' (' + a['date'] + ')' for a in items)
    vars['p' + k + '_agreed'] = 'yes'
except Exception as e:
    vars['agree_error'] = str(e)[:200]
'''


def agree_source(spec: dict) -> str:
    """Code of the note_agreement tool: stores one agreed product (from params) in variables."""
    src = calendar_source(spec.get("calendar") or {}) + AGREE
    assert "{{" not in src and "}}" not in src
    return src
