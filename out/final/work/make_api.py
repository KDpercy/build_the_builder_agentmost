import json
S=lambda t,**k: dict(type=t,**k)
result={"type":"object","properties":{k:S("string") for k in ["guid","returnCode","messageText","code","message","type"]}|{"details":S("object",properties={"guid":S("string"),"rootCause":S("string"),"errorOrigin":S("string")})}}
call=S("object",properties={"ani":S("string"),"lang":S("string")})
debt=S("object",properties={k:S("number") for k in ["transferAmount","statementDebt","minPayment","remainingDebt","remainingMinPayment","currentPeriodExpense","totalDebt","remainAutomaticPaymentAmount"]}|{"statementPaymentStatus":S("string",enum=["HAS_DEBT","NO_DEBT"]),"totalDebtPaymentStatus":S("string",enum=["HAS_DEBT","NO_DEBT"])})
svc={
"cards.list":("customer number in, the customer's eligible cards out",
  {"customerNo":S("string",description="Customer number, string or number"),"aiFlow":S("string",description='Use case, "CardOps"')},["customerNo"],
  {"cards":S("array",items=S("object",properties={"cardNumber":S("string"),"cardNumberLast4":S("string"),"productName":S("string"),"status":S("string"),"isMainCard":S("boolean")})),"validCardsCount":S("integer"),"exitState":S("string",enum=["1_CARD","MULTI_CARD"])},["404","500"]),
"cards.balance":("statement and due dates, debt per currency",{"cardNumber":S("string",description="cardNumber exactly as cards.list returned it")},["cardNumber"],
  {"cardNumber":S("string"),"cardNumberLast4":S("string"),"productName":S("string"),"statementDate":S("string"),"lastPayDate":S("string"),"nextStatementDate":S("string"),"nextLastPayDate":S("string"),"debtTL":debt,"debtUSD":debt,"debtEUR":debt,"debtGBP":debt,"statementPaymentStatus":S("string"),"totalDebtPaymentStatus":S("string"),"automaticPaymentFlag":S("string",enum=["Y","N"])},["400","404","500"]),
"statement.week.get":("the card's current statement week and day, joint statement info",{"cardNumber":S("string")},["cardNumber"],
  {"cardNumber":S("string"),"cardNumberLast4":S("string"),"productName":S("string"),"statementWeek":S("integer"),"statementDay":S("integer"),"statementDate":S("string"),"lastPayDate":S("string"),"nextStatementDate":S("string"),"nextLastPayDate":S("string"),"relationType":S("string",enum=["","M","C"]),"relatedCardNumber":S("string"),"relatedCardProductName":S("string")},["404","500"]),
"statement.week.decide":("preview of the dates with the requested week; changes nothing",{"cardNumber":S("string"),"newStatementWeek":S("integer",description="1-4, number or string"),"statementDay":S("integer",description="current statementDay from statement.week.get")},["cardNumber","newStatementWeek","statementDay"],
  {"statementDate":S("string"),"statementDueDate":S("string"),"statementDay":S("integer"),"responseCode":S("integer"),"responseMessage":S("string")},["400","500"]),
"statement.week.change":("changes the statement week",{"cardNumber":S("string"),"newStatementWeek":S("integer",description="1-4, number or string"),"statementDay":S("integer",description="current statementDay")},["cardNumber","newStatementWeek","statementDay"],
  {"responseCode":S("integer"),"responseMessage":S("string"),"statementWeek":S("string"),"statementDay":S("string"),"exitState":S("string")},["400","401","500"]),
"contact.email.get":("registered e-mail / phone",{"customerNo":S("string",description="Customer number, string or number"),"intAddressInfoType":S("string",enum=["E","P","B"])},["customerNo","intAddressInfoType"],
  {k:S("string") for k in ["communicationType","ibanCountryCode","ibanAreaCode","ibanPhoneNum","ibanEmail","ttsEmail","commGramType","exitState"]},["400","500"]),
"statement.pdf.send":("sends the statement PDF by e-mail",{"customerNo":S("string"),"cardNumber":S("string"),"currencyType":S("string",enum=["TL","USD","EUR","GBP"]),"statementDate":S("string",description="dd.MM.yyyy, statementDate from cards.balance"),"emailAddress":S("string")},["customerNo","cardNumber","currencyType","statementDate","emailAddress"],
  {"exitState":S("string")},["400","404","500"]),
}
paths={}
for name,(summ,dp,req,rp,errs) in svc.items():
    resp={"200":{"description":"Success","content":{"application/json":{"schema":S("object",properties={"data":S("object",properties=rp),"result":result})}}}}
    for e in errs: resp[e]={"description":"Error, result only","content":{"application/json":{"schema":S("object",properties={"result":result})}}}
    paths["/voice/v1/"+name]={"post":{"operationId":name.replace(".","_"),"summary":summ,
      "requestBody":{"required":True,"content":{"application/json":{"schema":S("object",required=["data"],properties={"data":S("object",required=req,properties=dp),"call":call})}}},"responses":resp}}
json.dump({"openapi":"3.0.3","info":{"title":"Freya Bank voice statement services","version":"1.0"},"servers":[{"url":"https://freya-bank-mock.dakkerem.workers.dev"}],"paths":paths},open("work/tool-api.json","w"),indent=1,ensure_ascii=False)
