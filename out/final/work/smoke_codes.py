import json,sys
wf=json.load(open('work/workflow.json')); tc=json.load(open('input/case/test-environment/test-customers.json'))
code=lambda n: wf['nodes'][n]['pre_actions'][0]['function']['parameters']['properties']['code']['default']
def run(n,v): exec(code(n),{'vars':v})
def entry(e):
    # find http/response in nested entry
    if isinstance(e,dict) and 'http' in e: return e
    if isinstance(e,dict):
        for x in e.values():
            r=entry(x)
            if r: return r
def svc(cust,s,key=None):
    e=cust['services'].get(s)
    if e is None: return None
    if key is not None and isinstance(e,dict):
        for k,x in e.items():
            if isinstance(x,dict) and key in json.dumps(x)[:200] or k==key: return entry(x)
    return entry(e)
def raw(e): return json.dumps({'status_code':e['http'],'data':e['response']},ensure_ascii=False) if e else ''
custs={c['customerNo']:c for c in tc['customers']}
def call(cno, picks=(), now='2026-10-12T10:30:00+03:00'):
    c=custs[cno]; v={'now':now,'customerNumber':cno}
    v['raw_cards_list']=raw(entry(c['services']['cards.list'])); run('prep_cards',v)
    print('##',cno,v['cards_state'],'|',v.get('select_line'))
    for p in picks:
        v.update(p); run('match_card',v); print('  ->',v['match_result'],'|',v['select_line'])
    if v.get('sel_card_number'):
        bal=c['services'].get('cards.balance',{})
        e=None
        for k,x in (bal.items() if isinstance(bal,dict) else []):
            if v['sel_card_number'] in k or v['sel_card_number'] in json.dumps(x)[:300]: e=entry(x); break
        v['raw_cards_balance']=raw(e); run('prep_reading',v)
        v['raw_contact_email_get']=raw(entry(c['services'].get('contact.email.get'))); run('prep_email',v); run('prep_followup',v)
        print('  READ:',v.get('reading_state'),v.get('reading_text'),'||',v.get('reading_followup'),'| email',v.get('email_state'),v.get('email_question',''))
    return v
for a in sys.argv[1:]: call(a)
