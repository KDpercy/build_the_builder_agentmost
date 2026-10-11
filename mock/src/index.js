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

function notFound(message) {
  return Response.json({ data: null, result: { returnCode: "0", messageText: message, code: "0", message, type: "E" } }, { status: 404, headers: CORS });
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
    if (isTemplate(keys.customer)) {
      keys.customer = FIRST;
      const cards = DATA[FIRST]["cards.list"].response.data.cards;
      if (!keys.card || isTemplate(keys.card)) keys.card = cards[0].cardNumber;
      if (!keys.week || isTemplate(keys.week)) keys.week = "2";
    }
    const ans = answerFor(route.service, keys);
    if (ans.missing) return notFound(`No test data (${ans.missing})`);
    if (ans.delaySeconds) await new Promise((r) => setTimeout(r, ans.delaySeconds * 1000));
    return new Response(JSON.stringify(ans.response), { status: ans.http, headers: { ...CORS, "content-type": "application/json; charset=utf-8" } });
  },
};
