// Mock of Freya Bank's statement services for the final case.
// Answers: exactly what test-environment/test-customers.json lists per customer (status, body,
// delay). Routes: the integration document, section 6 (ROUTES below).
import DATA from "./data.js";

// POST <PREFIX><service>, as under the bank's base address (cloudflare-mock/README.md, contract).
const PREFIX = "/voice/v1/";
const SERVICES = ["cards.list", "cards.balance", "statement.week.get", "statement.week.decide",
  "statement.week.change", "contact.email.get", "statement.pdf.send"];
const CORS = { "Access-Control-Allow-Origin": "*" };

const CUSTOMER_FIELDS = ["customerNo", "customerNumber", "musteriNo"];
const CARD_FIELDS = ["cardNumber", "maskedCardNumber", "cardNo"];
const WEEK_FIELDS = ["newStatementWeek", "statementWeek", "week"];

function pick(sources, names) {
  for (const s of sources) {
    for (const n of names) {
      if (s && s[n] !== undefined && s[n] !== null && String(s[n]) !== "") return String(s[n]);
    }
  }
  return undefined;
}

// A card-keyed service: the masked number exactly as cards.list gave it. Another mask of the same
// card (first 4 + last 4, as cards.balance shows it) matches only when exactly one card has those
// visible first digits and those last four.
function byCard(table, card) {
  if (!table || !card) return undefined;
  if (table[card]) return table[card];
  const m = String(card).match(/^(\d*)\D+(\d{4})$/);
  if (!m || m[1].length < 4) return undefined;
  const keys = Object.keys(table).filter((k) => k.startsWith(m[1]) && k.endsWith(m[2]));
  return keys.length === 1 ? table[keys[0]] : undefined;
}

// Contract section 4: error answers have only `result`.
function guid() {
  return [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function errorAnswer(http, code, type, message, rootCause) {
  const g = guid();
  return Response.json({ result: { guid: g, returnCode: code, messageText: message, code, message, type,
    details: { guid: g, rootCause: rootCause || null, errorOrigin: "ivr-gateway-test:ivr-channel-v0" } } },
    { status: http, headers: CORS });
}
function notFound(message) {
  return errorAnswer(404, "NOT_FOUND", "ERROR", message);
}
// Required `data` fields per service (contract section 5) and how the 400 names them.
const REQUIRED = {
  "cards.list": ["customerNo"],
  "cards.balance": ["cardNumber"],
  "statement.week.get": ["cardNumber"],
  "statement.week.decide": ["cardNumber", "newStatementWeek", "statementDay"],
  "statement.week.change": ["cardNumber", "newStatementWeek", "statementDay"],
  "contact.email.get": ["customerNo", "intAddressInfoType"],
  "statement.pdf.send": ["customerNo", "cardNumber", "currencyType", "statementDate", "emailAddress"],
};
const FIELD_WORDS = { customerNo: "customer number", cardNumber: "card number" };
// The service's own "not found" (contract section 4); services without one answer 400.
const NOT_FOUND = {
  "cards.list": [404, "FB_IVR_CHANNEL_102", "Müşteriye ait geçerli kart bilgisi bulunamadı."],
  "cards.balance": [404, "FB_IVR_CHANNEL_120", "Kart bilgisi bulunamadı."],
  "statement.week.get": [404, "FB_IVR_CHANNEL_121", "Kart bilgisi bulunamadı."],
  "statement.pdf.send": [404, "FB_IVR_CHANNEL_107", "Pdf dokümanı bulunamadı"],
};
function missingAnswer(service) {
  const nf = NOT_FOUND[service];
  if (nf) return errorAnswer(nf[0], nf[1], "WARNING", nf[2]);
  return errorAnswer(400, "INVALID_ARGUMENTS_ERROR", "ERROR", "no record for the given arguments", "InvalidArguments");
}

// The panel's "Test API Request" button sends variables unfilled, e.g. "{{customerNumber}}".
function isTemplate(v) {
  return typeof v === "string" && (v.includes("{{") || v.includes("%7B%7B"));
}
const FIRST = Object.keys(DATA)[0];


// Card-keyed services may be called with the card number only: find the card's owner.
function ownerOf(service, card) {
  for (const [no, svcs] of Object.entries(DATA)) {
    if (svcs[service] && svcs[service].http === undefined && byCard(svcs[service], card)) return no;
  }
  return undefined;
}

export function answerFor(service, keys) {
  const customer = DATA[keys.customer] || (keys.card ? DATA[ownerOf(service, keys.card)] : undefined);
  if (!customer) return { http: 404, response: null, missing: "customer" };
  let node = customer[service];
  if (!node) return { http: 404, response: null, missing: "service" };
  if (node.http === undefined) node = byCard(node, keys.card);
  if (node && node.http === undefined) node = node[keys.week];
  if (!node || node.http === undefined) return { http: 404, response: null, missing: "card or week" };
  return node;
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: { ...CORS, "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "*" } });
    }
    if (url.pathname === "/health") return Response.json({ ok: true, customers: Object.keys(DATA).length }, { headers: CORS });
    const service = url.pathname.startsWith(PREFIX) ? url.pathname.slice(PREFIX.length) : "";
    if (request.method !== "POST" || !SERVICES.includes(service)) return notFound("Unknown service");
    const route = { service };
    let body = {};
    if (request.method !== "GET") {
      try { body = await request.json(); } catch { body = {}; }
    }
    const query = Object.fromEntries(url.searchParams);
    const headers = Object.fromEntries(request.headers);
    const sources = [body, body && body.data, query, headers];
    const keys = {
      customer: pick(sources, CUSTOMER_FIELDS),
      card: pick(sources, CARD_FIELDS),
      week: pick(sources, WEEK_FIELDS),
    };
    if (isTemplate(keys.customer) || isTemplate(keys.card)) {
      keys.customer = FIRST;
      const cards = DATA[FIRST]["cards.list"].response.data.cards;
      if (!keys.card || isTemplate(keys.card)) keys.card = cards[0].cardNumber;
      if (!keys.week || isTemplate(keys.week)) keys.week = "2";
    }
    const data = (body && typeof body.data === "object" && body.data) || {};
    for (const f of REQUIRED[service]) {
      const v = data[f];
      if (v === undefined || v === null || String(v).trim() === "") {
        return errorAnswer(400, "INVALID_ARGUMENTS_ERROR", "ERROR", `${FIELD_WORDS[f] || f} cannot be empty`, "InvalidArguments");
      }
    }
    const ans = answerFor(route.service, keys);
    if (ans.missing) return missingAnswer(service);
    if (ans.delaySeconds) await new Promise((r) => setTimeout(r, ans.delaySeconds * 1000));
    return new Response(JSON.stringify(ans.response), { status: ans.http, headers: { ...CORS, "content-type": "application/json; charset=utf-8" } });
  },
};
