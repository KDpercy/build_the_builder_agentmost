import json
S={"type":"string"}; N={"type":"number"}; I={"type":"integer"}; B={"type":"boolean"}
def obj(p,req=None):
    o={"type":"object","properties":p}
    if req: o["required"]=req
    return o
call=obj({"ani":S,"lang":S})
details=obj({"guid":S,"rootCause":S,"errorOrigin":S})
result=obj({"guid":S,"returnCode":S,"messageText":S,"code":S,"message":S,"type":S,"details":details})
debt=obj({k:S if 'Status' in k else N for k in ["statementPaymentStatus","transferAmount","statementDebt","minPayment","remainingDebt","remainingMinPayment","currentPeriodExpense","totalDebt","totalDebtPaymentStatus","remainAutomaticPaymentAmount"]})
card=obj({"cardNumber":S,"cardNumberLast4":S,"productName":S,"status":S,"isMainCard":B})
svc={
 "cards.list":("Customer's cards",obj({"customerNo":S,"aiFlow":S},["customerNo"]),
   obj({"cards":{"type":"array","items":card},"validCardsCount":I,"exitState":{"type":"string","enum":["1_CARD","MULTI_CARD"]}}),["404","500"]),
 "cards.balance":("Statement and due dates, debt per currency",obj({"cardNumber":S},["cardNumber"]),
   obj({"cardNumber":S,"cardNumberLast4":S,"productName":S,"statementDate":S,"lastPayDate":S,"nextStatementDate":S,"nextLastPayDate":S,
        "debtTL":debt,"debtUSD":debt,"debtEUR":debt,"debtGBP":debt,"statementPaymentStatus":S,"totalDebtPaymentStatus":S,"automaticPaymentFlag":{"type":"string","enum":["Y","N"]}}),["400","404","500"]),
 "statement.week.get":("Current statement week and day, joint statement info",obj({"cardNumber":S},["cardNumber"]),
   obj({"cardNumber":S,"cardNumberLast4":S,"productName":S,"statementWeek":I,"statementDay":I,"statementDate":S,"lastPayDate":S,"nextStatementDate":S,"nextLastPayDate":S,
        "relationType":{"type":"string","enum":["","M","C"]},"relatedCardNumber":S,"relatedCardProductName":S}),["404","500"]),
 "statement.week.decide":("Preview of the dates with the requested week (changes nothing)",obj({"cardNumber":S,"newStatementWeek":I,"statementDay":I},["cardNumber","newStatementWeek","statementDay"]),
   obj({"statementDate":S,"statementDueDate":S,"statementDay":I,"responseCode":I,"responseMessage":S}),["400","500"]),
 "statement.week.change":("Changes the statement week",obj({"cardNumber":S,"newStatementWeek":I,"statementDay":I},["cardNumber","newStatementWeek","statementDay"]),
   obj({"responseCode":I,"responseMessage":S,"statementWeek":S,"statementDay":S,"exitState":S}),["400","401","500"]),
 "contact.email.get":("Registered e-mail / phone",obj({"customerNo":S,"intAddressInfoType":{"type":"string","enum":["E","P","B"]}},["customerNo","intAddressInfoType"]),
   obj({"communicationType":S,"ibanCountryCode":S,"ibanAreaCode":S,"ibanPhoneNum":S,"ibanEmail":S,"ttsEmail":S,"commGramType":S,"exitState":S}),["400","500"]),
 "statement.pdf.send":("Sends the statement PDF by e-mail",obj({"customerNo":S,"cardNumber":S,"currencyType":{"type":"string","enum":["TL","USD","EUR","GBP"]},"statementDate":S,"emailAddress":S},["customerNo","cardNumber","currencyType","statementDate","emailAddress"]),
   obj({"exitState":S}),["400","404","500"]),
}
desc={"400":"INVALID_ARGUMENTS_ERROR","401":"Token missing or expired","404":"Not found (WARNING)","500":"FBE00099 technical error"}
paths={}
for name,(summ,data,resp,errs) in svc.items():
    r={"200":{"description":"Success (result.returnCode \"1\")","content":{"application/json":{"schema":obj({"data":resp,"result":result})}}}}
    for e in errs: r[e]={"description":desc[e],"content":{"application/json":{"schema":obj({"result":result})}}}
    paths["/voice/v1/"+name]={"post":{"summary":summ,"requestBody":{"required":True,"content":{"application/json":{"schema":obj({"data":data,"call":call},["data"])}}},"responses":r}}
api={"openapi":"3.0.3","info":{"title":"Freya Bank voice assistant statement services","version":"2026-10-01"},
 "servers":[{"url":"https://freya-bank-mock.dakkerem.workers.dev"}],"paths":paths,
 "components":{"securitySchemes":{"bearer":{"type":"http","scheme":"bearer"}}},"security":[{"bearer":[]}]}
json.dump(api,open("work/tool-api.json","w"),ensure_ascii=False,indent=1)
