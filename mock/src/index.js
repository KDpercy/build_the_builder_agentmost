// Mock of the bank's services for the final case. Routes and answers come from the bank's
// integration document and its test customers (filled in when the documents arrive).
export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/health") return Response.json({ ok: true });
    return Response.json({ error: "not found" }, { status: 404 });
  },
};
