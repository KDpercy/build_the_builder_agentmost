import json,sys
src=open('hooks_src.py').read()
data=json.load(open('../input/case/test-environment/test-customers.json'))
want=sys.argv[1:]
for c in data['customers']:
    if want and c['customerNo'] not in want: continue
    for svc,e in c['services'].items():
        tool=svc.replace('.','_')
        entries=[e] if 'http' in e else [(k,v) for k,v in e.items()]
        flat=[]
        def walk(x,key=''):
            if isinstance(x,dict) and 'http' in x: flat.append((key,x))
            elif isinstance(x,dict):
                for k,v in x.items(): walk(v,key+'/'+k)
        walk(e)
        for key,x in flat:
            g={'vars':{'now':'2026-10-12T10:30:00+03:00'}}
            exec(src,g)
            res={'status':'success','data':json.loads(json.dumps(x['response'])),'status_code':x['http'],'header':{}}
            g['post'](tool,res)
            print(c['customerNo'],svc,key,x['http'],json.dumps(res['data'],ensure_ascii=False))
