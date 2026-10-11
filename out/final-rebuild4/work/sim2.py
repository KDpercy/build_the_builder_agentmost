import sys, json; sys.path.insert(0, '.')
import freya
wf = json.load(open('work/workflow.json'))
st = freya.save_workflow('final', wf); print(st)
N="2026-10-12T10:30:00+03:00"
P = [
 ({"name": "ex1 tek kart", "prompt": "Türkçe konuşan banka müşterisisin, kredi kartı ekstre borcunu öğrenmek için aradın. Borcunu dinle, sonra 'Teşekkürler, bu kadar' deyip görüşmeyi bitir. Kısa cevap ver.", "successCriteria": "Kart sorulmaz; okuma son dört hane 2000, Yıldız Premium ve 5 Ekim 2026 hesap kesim tarihiyle başlar. Türk Lirası borcu dört tutarla okunur: ekstre borcu 12.000 TL, minimum 4.800 TL, kalan toplam borç 9.500 TL, kalan minimum 2.000 TL. Euro borcu (85,20 Euro, minimum 34,10 Euro) okunur; Dolar ve İngiliz Sterlini borcu olmadığı tek cümlede söylenir. Son ödeme tarihi 15 Ekim 2026 söylenir, sonra ek işlem teklif edilir. Müşteri teşekkür edince teklif tekrarlanmaz ve ana menüye yönlendirilir.", "tags": ["final"]}, "95004361"),
 ({"name": "ex3 tum kartlar", "prompt": "Türkçe konuşan banka müşterisisin, üç kartın var. Aceleyle 'Bütün kartlarımın borcunu söyle' de. Tek kart seçmen istenince isteğini bir kez daha tekrarla, sonra Yıldız Premium kartını seç. Okumadan sonra başka bir şey istemediğini söyle. Kısa cevap ver.", "successCriteria": "Üç kartın borcu birlikte okunmaz; asistan müşterinin kendi kartlarından örnek vererek hangi kartı istediğini sorar. Müşteri isteğini tekrarlayınca görüşme bitmez, tekrar tek kart seçmesi istenir. Yıldız Premium seçilince yalnızca o kartın borcu okunur: 22.500 TL, minimum 9.000 TL, son ödeme 15 Ekim 2026. Görüşme ana menüye yönlendirme ile biter.", "tags": ["final"]}, "97526380"),
 ({"name": "ex4 gecen ay ekstre", "prompt": "Türkçe konuşan banka müşterisisin, ekstre borcunu öğrenmek için aradın. Borcunu dinledikten sonra geçen ayın ekstresini e-postayla istemek istiyorsun. Sadece son ekstrenin gönderilebileceğini duyunca son ekstreyi kabul et ve adres okunup onay sorulunca 'Evet' de. Kısa cevap ver.", "successCriteria": "Borç servisteki gibi okunur: Türk Lirası 18.500 TL (minimum 7.400 TL), Dolar 650 (minimum 260), Euro 380 (minimum 152), İngiliz Sterlini borcu yok; son ödeme 15 Ekim 2026. Geçen ay ekstresi istenince sadece son ekstrenin gönderilebileceği söylenir; geçmiş dönem ekstresi gönderildi denmez. Müşteri kabul edince kayıtlı adres (ece.demir@freyabank.example) okunur ve onay istenir. Gönderim açık onaydan sonra yapılır; 'gönderildi' yalnızca servis başarı döndürünce söylenir. Sonra ana menüye yönlendirilir.", "tags": ["final"]}, "92460108"),
]
ids = [p["id"] for p in freya.create_personas([x[0] for x in P])["personas"]]
vars_ = {i: {"customerNumber": x[1], "now": N} for i, x in zip(ids, P)}
sid, iid, status = freya.run_simulation(st["agent_id"], "final check", vars_, max_seconds=300)
it = freya.get_iteration(sid, iid)
for r in it["runs"]:
    print("=== RUN", json.dumps({k: v for k, v in r.items() if k not in ("messages", "transcript")}, ensure_ascii=False)[:800])
    cid = r.get("callId") or r.get("call_id")
    if cid:
        c = freya.get_call(cid)
        for m in c.get("messages", []):
            print(" ", m.get("role"), ":", str(m.get("content") or m.get("tool_calls") or "")[:400])
