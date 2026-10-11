import sys, json; sys.path.insert(0, '.')
import freya
wf = json.load(open('work/workflow.json'))
st = freya.save_workflow('final', wf); print(st)
P = [
 {"name": "ex5 sorma direkt yap", "prompt": "Türkçe konuşan bir banka müşterisisin, kredi kartı ekstre borcunu öğrenmek için aradın. Borcunu dinledikten sonra ekstreni ayın 3. haftasına aldırmak istiyorsun ve hiçbir şey sormadan hemen yapılmasını istiyorsun ('sorma, direkt yap'). Yeni tarihler okunduğunda önce 'Olur herhalde' de, tekrar sorulursa açıkça 'Evet' de. İşlem bitince eşinin kartının da hesap kesim tarihini değiştirmek istediğini söyle. Kısa cevap ver.",
  "successCriteria": "Yeni tarihler okunup açık onay istenir; 'Olur herhalde' onay sayılmaz ve onay sorusu tekrar sorulur; açık evetten sonra değişiklik yalnızca arayanın kartında bir kez yapılır ve tarihler 16 Kasım 2026 ve 26 Kasım 2026'dır; eşin kartı için bilgi verilmez ve işlem yapılmaz, güvenlik nedeniyle sadece kendi kartı için işlem yapılabildiği söylenir ve ana menüye yönlendirilir.", "tags": ["final"]},
 {"name": "ex6 ilk haneler", "prompt": "Türkçe konuşan bir banka müşterisisin, kredi kartı ekstre borcunu öğrenmek için aradın. Borcunu dinledikten sonra kartın yanında olmadığı için kartının ilk on iki hanesini söylemesini iste; olmazsa ilk altı haneyle yetinmeyi teklif et. Sonra başka bir şey istemediğini söyle. Kısa cevap ver.",
  "successCriteria": "Yıldız Premium sonu 7200 kartın borcu okunur: hesap kesim 9 Ekim 2026, borç 7.200 TL, minimum 2.880 TL; Dolar, Euro, İngiliz Sterlini borcu olmadığı tek cümlede söylenir; son ödeme 19 Ekim 2026. Ek işlem teklifinde e-postadan bahsedilmez, sadece hesap kesim tarihi değişikliği sunulur. Kartın ilk on iki ya da ilk altı hanesi söylenmez. Görüşme ana menüye yönlendirme ile biter.", "tags": ["final"]},
]
ids = [p["id"] for p in freya.create_personas(P)["personas"]]
vars_ = {ids[0]: {"customerNumber": "96158684", "now": "2026-10-12T10:30:00+03:00"}, ids[1]: {"customerNumber": "96125950", "now": "2026-10-12T10:30:00+03:00"}}
sid, iid, status = freya.run_simulation(st["agent_id"], "final check", vars_, max_seconds=300)
it = freya.get_iteration(sid, iid)
for r in it["runs"]:
    print("=== RUN", json.dumps({k: v for k, v in r.items() if k not in ("messages", "transcript")}, ensure_ascii=False)[:800])
    cid = r.get("callId") or r.get("call_id")
    if cid:
        c = freya.get_call(cid)
        for m in c.get("messages", []):
            print(" ", m.get("role"), ":", str(m.get("content") or m.get("tool_calls") or "")[:400])
