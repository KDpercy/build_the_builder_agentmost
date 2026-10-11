import json, pathlib
A="2026-10-08-statement-debt-analysis.md"; R="2026-10-09-decisions-recap.txt"; C="2026-10-01-service-contract.md"; F="2026-10-10-follow-up-session-transcript.txt"
rules=[
("R1",A,"The assistant does **not** ask for any code, PIN or date of birth.","identity","Never ask for code, PIN or birth date.","system_prompt"),
("R2",A,"One eligible card: it is the card. No question, go to the debt.","other","Single card is read without asking.","cards_list post hook yapilacak"),
("R3",A,"At most two examples, and only names from this caller's own list.","other","Selection question gives max two own card names.","cards_list post hook"),
("R4",A,"Every reading opens with “Sonu [son 4 hane] ile biten [kart adı]”, every time, also on the second card in the same call.","debt_statement","Reading opens with last four and card name.","cards_balance post hook"),
("R5",A,"Currency names in full, never the code: TL → Türk Lirası, USD → Dolar, EUR → Euro, GBP → İngiliz Sterlini.","forbidden","Full currency names.","cards_balance post hook + system_prompt"),
("R6",A,"A currency whose block is missing or empty in `cards.balance` (the card simply doesn't have it) is **left out** of this sentence.","debt_statement","Missing blocks are omitted.","cards_balance post hook"),
("R7",A,"Only a clear \"evet\" counts.","read_back","Only explicit evet confirms week change.","assistant task step 6"),
("R8",A,"Only after a clear yes, call `statement.pdf.send`, and only ever with the registered address.","special_case","PDF only after yes, registered address only.","assistant task step 5"),
("R9",A,"The caller asks for a person, at any point: put them through at once, no tries, no persuading.","special_case","Immediate transfer on request.","system_prompt"),
("R10",R,"Whatever comes back, the assistant never reads out","forbidden","Never read more than the last four digits of a card.","system_prompt"),
("R11",R,"One correction: on the angry caller it was three calming replies, not two.","special_case","Three calming replies before transfer (recap wins).","system_prompt"),
("R12",F,"If there is another card, first that.","multi_product","Another-card question before offer.","assistant task step 3"),
("R13",F,"Opening whichever, then the total debt.","dates","On cut day read total debt.","cards_balance post hook kesim_gunu_metni"),
("R14",C,"Card number: always send the `cardNumber` **exactly as `cards.list` returned it**.","other","Use cardNumber as returned.","tool parameter descriptions"),
]
txt={p.name:p.read_text() for p in pathlib.Path('input/case').rglob('*') if p.is_file() and p.suffix in ('.md','.txt')}
out=[]
for i,f,q,k,r,m in rules:
    if q not in txt[f]: print("skip",i); continue
    out.append({"id":i,"file":f,"quote":q,"kind":k,"rule":r,"implemented_by":m})
json.dump({"rules":out,"conflicts":[{"topic":"angry caller","earlier":"5. Angry or abusive caller: up to two calming replies, then agent.","later":"One correction: on the angry caller it was three calming replies, not two.","winner":"three"},{"topic":"another card before offer","later":"If there is another card, first that.","winner":"another-card question first"}]},open('work/rules.json','w'),ensure_ascii=False,indent=1)
json.dump({"kind":"inbound statement debt (own generator work/build_workflow.py)","language":"tr","call_variables":{"customerNumber":"8-digit customer number from IVR","now":"call time, Istanbul"},"tool_timeout_ms":25000,"gaps":["slow-service timeout not agreed: 25 s used (12 s delay in test data)","yearly week-change flag not exposed: change always offered","transferAmount line not drafted by bank: not said","silence handled by platform inactivity monitor and prompt"]},open('work/spec.json','w'),ensure_ascii=False,indent=1)
print(len(out),"rules")
