"""Generate the date code that runs inside a Freya code node.

Every value comes from the brief at run time through a config dict, for example:
    {"holidays": ["YYYY-MM-DD", ...],          bank holidays
     "weekend": [5, 6],                         weekday numbers that are not business days (Mon=0)
     "count_today": false}                      whether "the Nth business day after today" counts today
The generated source defines: D, TD, DN, MN, HOL, WEEKEND, isbiz(d), nextbiz(d),
nth_biz_after(d, n), sp(d), week_end_biz(d), this_weekday(today, i), next_weekday(today, i).
Nothing here is specific to one brief. The source never contains a double brace.
"""
import json

TEMPLATE = r'''
import datetime, json
CAL = json.loads(__CONFIG__)
HOL = set(CAL.get('holidays') or [])
WEEKEND = set(CAL.get('weekend') if CAL.get('weekend') is not None else [5, 6])
DN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
D = datetime.date
TD = datetime.timedelta
def isbiz(d):
    return d.weekday() not in WEEKEND and d.isoformat() not in HOL
def sp(d):
    return DN[d.weekday()] + ' ' + str(d.day) + ' ' + MN[d.month - 1] + ' ' + str(d.year)
def nextbiz(d):
    x = d + TD(days=1)
    for _ in range(400):
        if isbiz(x):
            return x
        x = x + TD(days=1)
    return x
def nth_biz_after(d, n):
    x = d
    k = 1 if (CAL.get('count_today') and isbiz(d)) else 0
    for _ in range(400):
        if k >= n:
            return x
        x = x + TD(days=1)
        if isbiz(x):
            k += 1
    return x
def week_end_biz(d):
    """Last business day of d's calendar week (Monday to Sunday), or None if there is none."""
    monday = d - TD(days=d.weekday())
    x = monday + TD(days=6)
    while x >= monday:
        if isbiz(x):
            return x
        x = x - TD(days=1)
    return None
def this_weekday(today, i):
    return today - TD(days=today.weekday()) + TD(days=i)
def next_weekday(today, i):
    return this_weekday(today, i) + TD(days=7)
'''


def calendar_source(config: dict) -> str:
    """Python source for a code node. `config` holds only values read from the brief."""
    text = json.dumps(config, separators=(",", ":")).replace("}}", "} }").replace("{{", "{ {")
    src = TEMPLATE.replace("__CONFIG__", repr(text))
    assert "{{" not in src and "}}" not in src
    return src
