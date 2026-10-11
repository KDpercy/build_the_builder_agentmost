import json, copy, sys
wf = json.load(open('work/workflow.json')); tc = json.load(open('input/case/test-environment/test-customers.json'))
hooks = {t['function']['name']: t.get('post_process_code') for t in wf['nodes']['assistant']['tools'] if t.get('post_process_code')}
code = wf['nodes']['date_facts']['pre_actions'][0]['function']['parameters']['properties']['code']['default']
v = {'now': '2026-10-12T10:30:00+03:00'}; exec(code, {'vars': v}); print(v)
want = sys.argv[1:]
for c in tc['customers']:
    if want and c['customerNo'] not in want: continue
    print('==', c['customerNo'])
    for svc, ans in c['services'].items():
        name = svc.replace('.', '_')
        items = [ans] if 'http' in ans else list(ans.values())
        flat = []
        for it in items:
            if 'http' in it: flat.append(it)
            else: flat += [x for x in it.values() if isinstance(x, dict) and 'http' in x]
        for it in flat:
            r = {'status': 'ok', 'data': copy.deepcopy(it['response']), 'status_code': it['http'], 'header': {}}
            g = {'result': r}; exec(hooks[name], g)
            print(' ', name, it['http'], json.dumps(g['result']['data'], ensure_ascii=False)[:700])
