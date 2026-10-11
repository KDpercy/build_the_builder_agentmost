import json
S=lambda **p:{"type":"object","properties":p}
st={"type":"string"}; num={"type":"number"}; it={"type":"integer"}; bo={"type":"boolean"}
call=S(ani=st,lang=st)
result=S(guid=st,returnCode=st,messageText=st,code=st,message=st,type=st,details=S(guid=st,rootCause=st,errorOrigin=st))
debt=S(statementPaymentStatus=st,transferAmount=num,statementDebt=num,minPayment=num,remainingDebt=num,remainingMinPayment=num,currentPeriodExpense=num,totalDebt=num,totalDebtPaymentStatus=st,remainAutomaticPaymentAmount=num)
svc={
 "cards.list":(S(customerNo=st,aiFlow=st),["customerNo","aiFlow"],S(cards={"type":"array","items":S(cardNumber=st,cardNumberLast4=st,productName=st,status=st,isMainCard=bo)},validCardsCount=it,exitState=st),"Card list for the customer"),
 "cards.balance":(S(cardNumber=st),["cardNumber"],S(cardNumber=st,cardNumberLast4=st,productName=st,statementDate=st,lastPayDate=st,nextStatementDate=st,nextLastPayDate=st,debtTL=debt,debtUSD=debt,debtEUR=debt,debtGBP=debt,statementPaymentStatus=st,totalDebtPaymentStatus=st,automaticPaymentFlag=st),"Statement and debt per currency for a card"),
 "statement.week.get":(S(cardNumber=st),["cardNumber"],S(cardNumber=st,cardNumberLast4=st,productName=st,statementWeek=it,statementDay=it,statementDate=st,lastPayDate=st,nextStatementDate=st,nextLastPayDate=st,relationType=st,relatedCardNumber=st,relatedCardProductName=st),"Current statement week of a card"),
 "statement.week.decide":(S(cardNumber=st,newStatementWeek=it,statementDay=it),["cardNumber","newStatementWeek","statementDay"],S(statementDate=st,statementDueDate=st,statementDay=it,responseCode=it,responseMessage=st),"Preview dates for a new statement week (changes nothing)"),
 "statement.week.change":(S(cardNumber=st,newStatementWeek=it,statementDay=it),["cardNumber","newStatementWeek","statementDay"],S(responseCode=it,responseMessage=st,statementWeek=st,statementDay=st,exitState=st),"Change the statement week"),
 "contact.email.get":(S(customerNo=st,intAddressInfoType={"type":"string","enum":["E","P","B"]}),["customerNo","intAddressInfoType"],S(communicationType=st,ibanCountryCode=st,ibanAreaCode=st,ibanPhoneNum=st,ibanEmail=st,ttsEmail=st,commGramType=st,exitState=st),"Registered e-mail / phone"),
 "statement.pdf.send":(S(customerNo=st,cardNumber=st,currencyType={"type":"string","enum":["TL","USD","EUR","GBP"]},statementDate=st,emailAddress=st),["customerNo","cardNumber","currencyType","statementDate","emailAddress"],S(exitState=st),"Send statement PDF by e-mail"),
}
paths={}
for n,(req,reqd,resp,summ) in svc.items():
    rq=dict(req); rq["required"]=reqd
    paths["/voice/v1/"+n]={"post":{"operationId":n.replace(".","_"),"summary":summ,
      "requestBody":{"required":True,"content":{"application/json":{"schema":{"type":"object","required":["data"],"properties":{"data":rq,"call":call}}}}},
      "responses":{"200":{"description":"Success","content":{"application/json":{"schema":S(data=resp,result=result)}}},
                   "default":{"description":"Error (400/404/500): result only","content":{"application/json":{"schema":S(result=result)}}}}}}
api={"openapi":"3.0.3","info":{"title":"Freya Bank voice statement services","version":"2026-10-01"},
 "servers":[{"url":"https://freya-bank-mock.dakkerem.workers.dev"}],"paths":paths}
json.dump(api,open("work/tool-api.json","w"),ensure_ascii=False,indent=1)
