"""Generate code-node source that turns the call variable `now` into date facts for prompts.

All values come from spec.json, which the builder fills from the brief at run time:
    {"calendar": {"holidays": [...], "weekend": [5, 6], "count_today": false},
     "bands": [{"name": "<from brief>", "min_days": <int>, "max_days": <int>,
                "deadline": "<date expression>", "attempts": <int>}, ...],
     "attempt_dates": ["<date expression>", ...],          one per persuasion attempt
     "callback": {"days": ["today", "next_business_day"], "from": "HH:MM", "to": "HH:MM",
                  "later_than_now": true}}
Date expressions: "today", "next_business_day", "deadline", "business_days_after_today:N",
"calendar_days_after_today:N" (optionally ":back" or ":forward" to move off a non-working day),
"last_business_day_this_week_or_next_if_today", "last_business_day_this_week".
The generated code writes text variables and never raises. Nothing here is specific to one brief.
"""
import json

from lib.calendar_code import calendar_source, json_literal

FACTS = r'''
def date_expr(expr, today, deadline=None):
    e = str(expr or '')
    if e == 'today':
        return today
    if e == 'next_business_day':
        return nextbiz(today)
    if e == 'deadline':
        return deadline or today
    if e.startswith('business_days_after_today:'):
        return nth_biz_after(today, int(e.split(':')[1]))
    if e.startswith('calendar_days_after_today:'):
        bits = e.split(':')
        d = today + TD(days=int(bits[1]))
        how = bits[2] if len(bits) > 2 else ''
        while how in ('back', 'forward') and not isbiz(d):
            d = d + TD(days=-1 if how == 'back' else 1)
        return d
    if e in ('last_business_day_this_week', 'last_business_day_this_week_or_next_if_today'):
        d = week_end_biz(today)
        if d is None or d < today or (d == today and e.endswith('_if_today')):
            d = week_end_biz(today + TD(days=7))
        if deadline and d and d > deadline:
            d = deadline
        return d or today
    return today
def band_for(late):
    for b in SPEC.get('bands') or []:
        if int(b.get('min_days', 0)) <= late <= int(b.get('max_days', 10 ** 6)):
            return b
    return None
def week_table(today):
    rows = ['- today = ' + sp(today) + ' (' + today.isoformat() + ')',
            '- tomorrow = ' + sp(today + TD(days=1)) + ' (' + (today + TD(days=1)).isoformat() + ')']
    for i in range(7):
        t, n = this_weekday(today, i), next_weekday(today, i)
        rows.append('- "this ' + DN[i] + '" = ' + sp(t) + ('  (in the past)' if t < today else '') + '; "next ' + DN[i] + '" = ' + sp(n))
    return '\n'.join(rows)
def calendar_lines(today, deadline, days_after=21):
    rows, x = [], today
    while x <= deadline + TD(days=days_after):
        tag = sp(x) + ' (' + x.isoformat() + ')' + (' [today]' if x == today else '')
        if x > deadline:
            act = ('AFTER the deadline. Say: "The latest date I can record is ' + sp(deadline) + '. Can you pay on that day?" '
                   'If they say yes, ' + sp(deadline) + ' is the agreed date: do not ask for another day.')
        elif isbiz(x):
            act = 'OK, can be recorded.'
        else:
            why = 'a bank holiday' if x.isoformat() in HOL else 'not a business day'
            nb = nextbiz(x)
            act = ('NOT allowed, ' + why + '. Offer the next business day, ' + sp(nb) + '.') if nb <= deadline else (
                  'NOT allowed, ' + why + ', and the next business day is after the deadline. Offer ' + sp(deadline) + '.')
        rows.append('- ' + tag + ': ' + act)
        x = x + TD(days=1)
    return '\n'.join(rows)
def callback_text(today, hm):
    cb = SPEC.get('callback') or dict()
    lo, hi = cb.get('from', ''), cb.get('to', '')
    rows = []
    for day in cb.get('days') or []:
        d = date_expr(day, today)
        if d == today and cb.get('later_than_now'):
            if hi and hm >= hi:
                rows.append('- Today is no longer possible: it is after ' + hi + '.')
                continue
            start = 'from ' + lo if (lo and hm < lo) else 'any time later than ' + hm
            rows.append('- Today, ' + sp(d) + ' (' + d.isoformat() + '): ' + start + ' up to ' + hi + ' included.')
        else:
            rows.append('- ' + sp(d) + ' (' + d.isoformat() + '): from ' + lo + ' to ' + hi + ', both included.')
    rows.append('- Every other day, and every other time, is OUTSIDE the window.')
    return '\n'.join(rows)
try:
    now = str(vars.get(SPEC.get('now_variable') or 'now') or '')
    today = D.fromisoformat(now[:10])
    hm = now[11:16] if len(now) >= 16 else '00:00'
    vars['today_iso'] = today.isoformat()
    vars['today_spoken'] = sp(today)
    vars['now_time'] = hm
    vars['week_table'] = week_table(today)
    vars['callback_facts'] = callback_text(today, hm)
    vars['date_state'] = 'ok'
except Exception as e:
    vars['today_spoken'] = str(vars.get(SPEC.get('now_variable') or 'now') or '')
    vars['week_table'] = ''
    vars['callback_facts'] = ''
    vars['date_state'] = 'error ' + str(e)
'''


def date_facts_source(spec: dict) -> str:
    """Source for the first code node. Defines date_expr, band_for, calendar_lines for later nodes too."""
    src = calendar_source(spec.get("calendar") or {}) + "\nSPEC = json.loads(" + json_literal(spec) + ")\n" + FACTS
    assert "{{" not in src and "}}" not in src
    return src
