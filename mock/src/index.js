// Mock of Freya Bank's statement services for the final case.
// Answers: exactly what test-environment/test-customers.json lists per customer (status, body,
// delay). Routes: the integration document, section 6 (ROUTES below).
import DATA from "./data.js";

// method + path -> service name in test-customers.json, and where each key is in the request.
// FILLED FROM SECTION 6 of the integration document.
const ROUTES = [
  // { method: "POST", path: "/...", service: "cards.list" },
];

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

// A card-keyed service: exact masked number first, then the same last four digits.
function byCard(table, card) {
  if (!table || !card) return undefined;
  if (table[card]) return table[card];
  const last4 = card.replace(/\D/g, "").slice(-4);
  const keys = Object.keys(table).filter((k) => k.replace(/\D/g, "").slice(-4) === last4);
  return keys.length === 1 ? table[keys[0]] : undefined;
}

function notFound(message) {
  return Response.json({ data: null, result: { returnCode: "0", messageText: message, code: "0", message, type: "E" } }, { status: 404 });
}

export function answerFor(service, keys) {
  const customer = DATA[keys.customer];
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
    if (url.pathname === "/health") return Response.json({ ok: true, customers: Object.keys(DATA).length });
    const route = ROUTES.find((r) => r.method === request.method && r.path === url.pathname);
    if (!route) return notFound("Unknown service");
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
    const ans = answerFor(route.service, keys);
    if (ans.missing) return notFound(`No test data (${ans.missing})`);
    if (ans.delaySeconds) await new Promise((r) => setTimeout(r, ans.delaySeconds * 1000));
    return new Response(JSON.stringify(ans.response), { status: ans.http, headers: { "content-type": "application/json; charset=utf-8" } });
  },
};
