"""Our own acceptance test for the final case: a chat simulation of example scenarios against an agent."""
import json, sys, time
sys.path.insert(0, ".")
import freya
NOW = "2026-10-12T10:30:00+03:00"
RULES = ("Sadece telefonda söyleyeceğin sözleri yaz, parantez ya da açıklama yok. Kısa konuş, bir iki cümle. "
         "Asistan seni ana menüye aktardığında ya da vedalaştığında 'Teşekkürler, iyi günler.' de ve başka bir şey söyleme.")
P = [
 ("EX1 below-minimum", "95004361", "Sen bir Freya Bank müşterisisin, kredi kartı ekstre borcunu öğrenmek için aradın. Borcunu dinle, teşekkür et ve başka bir şey istemediğini söyle.",
  ["the card is not asked about; reading starts with last four 2000, Yıldız Premium and statement date 5 October 2026",
   "TL: statement debt 12.000, minimum 4.800, remaining 9.500, remaining minimum 2.000",
   "Euro 85,20 and minimum 34,10 read; dollar and pound with no debt stated in one sentence",
   "due date 15 October 2026 stated, then an additional transaction offered once; after thanks routed to main menu"]),
 ("EX2 week change", "96158684", "Sen bir Freya Bank müşterisisin. Önce ekstre borcunu dinle. Sonra hesap kesim tarihini değiştirmek istediğini söyle; ayın üçüncü haftasını seç. Yeni tarihler okununca 'Evet' de.",
  ["debt 10.000 TL, remaining 5.000 TL and thanks for the minimum payment; due date 19 October 2026",
   "current week (2nd) and next dates 9 November 2026 / 19 November 2026 stated; only weeks 1, 3, 4 offered",
   "new dates 16 November 2026 / 26 November 2026 read and confirmation asked; changed only after evet, once; then routed to main menu"]),
 ("EX4 last month's statement", "92460108", "Sen bir Freya Bank müşterisisin. Ekstre borcunu dinle. Sonra geçen ayın ekstresini e-postana istemek. Sadece son ekstre gönderilebilir denirse kabul et ve göndermeleri için 'Evet' de.",
  ["TL 18.500 (minimum 7.400), dollar 650 (minimum 260), euro 380 (minimum 152), no pound; due date 15 October 2026",
   "says only the latest statement can be sent; never says a past statement was sent",
   "reads ece.demir@freyabank.example and asks for confirmation; says sent only after success; routed to main menu"]),
 ("EX6 first digits", "96125950", "Sen bir Freya Bank müşterisisin, kartın yanında değil. Borcunu dinle. Sonra kartının ilk on iki hanesini söylemelerini iste; olmazsa ilk altı hanesine razı ol. Olmazsa teşekkür et.",
  ["Yıldız Premium ending 7200, statement date 9 October 2026, debt 7.200 TL, minimum 2.880 TL, no USD/EUR/GBP in one sentence, due date 19 October 2026",
   "e-mail not offered (no registered e-mail); only statement date change offered",
   "first twelve or first six digits never said; card referred to only by last four; routed to main menu"]),
]
agent = sys.argv[1]
personas = [{"name": f"FINAL {n}", "prompt": f"{RULES}\n\n{s}", "successCriteria": "All of these are true:\n- " + "\n- ".join(c), "tags": ["final-check"]} for n, _, s, c in P]
made = freya.create_personas(personas)["personas"]
vars_ = {p["id"]: {"customerNumber": no, "now": NOW} for p, (_, no, _, _) in zip(made, P)}
sim_id, it_id, status = freya.run_simulation(agent, f"final check {time.strftime('%H:%M')}", vars_)
runs = freya.get_iteration(sim_id, it_id)["runs"]
names = {p["id"]: n for p, (n, _, _, _) in zip(made, P)}
for r in runs:
    print(("PASS" if r.get("outcome") == "pass" else "FAIL"), names.get(r.get("personaId")), "|", r.get("callId"), "|", " ".join(str(r.get("reason") or "").split())[:500])
print("simulation", sim_id, status)
