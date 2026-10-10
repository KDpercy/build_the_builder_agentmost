"""Hook source generators. Field names and answer kinds come from a config the builder fills
from the brief and the tool API file at run time. Nothing here is specific to one brief.

identity_pre_source(config) cleans an identity answer before the bank sees it:
    {"question_field": "field",              body field that names the question
     "answer_field": "answer",               body field that holds the answer
     "kinds": {"<question value>": "date" | "digits:4" | "year" | "text"},
     "numeric_date_order": "dmy" | "mdy" | "ymd"}   how to read a date said only in numbers
"""
import json  # noqa: F401

from lib.calendar_code import json_literal

_PARSER = r'''
import json, re
CFG = json.loads(__CONFIG__)
WORDS = dict(zero=0, oh=0, o=0, one=1, two=2, three=3, four=4, five=5, six=6, seven=7, eight=8, nine=9)
MONTHS = [('jan', 1), ('feb', 2), ('mar', 3), ('apr', 4), ('may', 5), ('jun', 6), ('jul', 7), ('aug', 8), ('sep', 9), ('oct', 10), ('nov', 11), ('dec', 12)]
ORD = dict(first=1, second=2, third=3, fourth=4, fifth=5, sixth=6, seventh=7, eighth=8, ninth=9, tenth=10, eleventh=11, twelfth=12,
           thirteenth=13, fourteenth=14, fifteenth=15, sixteenth=16, seventeenth=17, eighteenth=18, nineteenth=19, twentieth=20, thirtieth=30)
def spoken_digits(s):
    out = []
    for tok in re.findall(r'[a-z]+|\d', s.lower()):
        if tok.isdigit():
            out.append(tok)
        elif tok in WORDS:
            out.append(str(WORDS[tok]))
        elif tok in ('double', 'triple') :
            out.append(tok)
    res = []
    i = 0
    while i < len(out):
        if out[i] in ('double', 'triple') and i + 1 < len(out):
            res.append(out[i + 1] * (2 if out[i] == 'double' else 3))
            i += 2
        else:
            res.append(out[i])
            i += 1
    return ''.join(x for x in res if x.isdigit())
def day_word(s):
    m = re.search(r'\b(twenty|thirty)[\s-]?(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)\b', s)
    if m:
        return (20 if m.group(1) == 'twenty' else 30) + ORD[m.group(2)]
    for w, v in sorted(ORD.items(), key=lambda kv: -len(kv[0])):
        if re.search(r'\b' + w + r'\b', s):
            return v
    return None
def norm_date(a, order):
    s = a.lower().strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return s
    m = re.match(r'^(\d{1,4})[./\- ](\d{1,2})[./\- ](\d{1,4})$', s)
    if m:
        x, y, z = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if x > 999:
            yr, mo, dy = x, y, z
        elif order == 'mdy':
            yr, mo, dy = z, x, y
        else:
            yr, mo, dy = z, y, x
        return '%04d-%02d-%02d' % (yr, mo, dy)
    yr = re.search(r'(\d{4})', s)
    mo = None
    for k, v in MONTHS:
        if re.search(r'\b' + k, s):
            mo = v
            break
    rest = s.replace(yr.group(1), ' ') if yr else s
    dm = re.search(r'\b(\d{1,2})(st|nd|rd|th)?\b', rest)
    dy = int(dm.group(1)) if dm else day_word(rest)
    if yr and mo and dy:
        return '%04d-%02d-%02d' % (int(yr.group(1)), mo, dy)
    return a
def norm(kind, a):
    a = str(a or '').strip()
    if kind == 'date':
        return norm_date(a, CFG.get('numeric_date_order') or 'dmy')
    if kind.startswith('digits'):
        n = int(kind.split(':')[1]) if ':' in kind else 0
        d = spoken_digits(a)
        return d[-n:] if n and len(d) >= n else (d or a)
    if kind == 'year':
        y = re.search(r'(\d{4})', a)
        return y.group(1) if y else a
    return a.strip()
'''

_PRE = r'''
try:
    b = config.get('body')
    if isinstance(b, dict):
        q = str(b.get(CFG.get('question_field') or 'field') or '')
        af = CFG.get('answer_field') or 'answer'
        kind = (CFG.get('kinds') or dict()).get(q)
        if kind and af in b:
            b[af] = norm(kind, b.get(af))
        config['body'] = b
except Exception:
    pass
'''


def _config_literal(config: dict) -> str:
    return json_literal(config)


def identity_parser_source(config: dict) -> str:
    """Defines norm(kind, answer) and its helpers; used by the pre-hook and by tests."""
    src = _PARSER.replace("__CONFIG__", _config_literal(config))
    assert "{{" not in src and "}}" not in src
    return src


def identity_pre_source(config: dict) -> str:
    src = identity_parser_source(config) + _PRE
    assert "{{" not in src and "}}" not in src
    return src
