import json,sys
wf=open('work/workflow.json').read(); wf=json.dumps(json.loads(wf),ensure_ascii=False)
r=json.load(open('work/validate-rules.json'))
miss=[s for s in r['required_sentences_checked_by_own_script'] if s not in wf]
print('missing:',miss) if miss else print('all required sentences present')
