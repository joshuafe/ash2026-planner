// Sync endpoint for the ASH 2026 planner. One row per account, keyed by a secret sync code.
// POST { create:true, name, profile, profile_ts, picks }            -> creates an account, returns state
// POST { key, name, profile, profile_ts, picks }                     -> merges (newest wins per item), returns state
// GET  ?key=...                                                      -> returns state
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
const URL_ = Deno.env.get("SUPABASE_URL")!;
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const H = { apikey: SERVICE, Authorization: `Bearer ${SERVICE}`, "Content-Type": "application/json" };
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
const code = () => { const a = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"; const r = crypto.getRandomValues(new Uint8Array(12)); const s = [...r].map(b => a[b % a.length]).join(""); return `${s.slice(0,4)}-${s.slice(4,8)}-${s.slice(8,12)}`; };
type Pick = { d: string | null; n: string; ts: number; ev?: unknown };
async function load(key: string) {
  const r = await fetch(`${URL_}/rest/v1/accounts?key=eq.${encodeURIComponent(key)}&select=*`, { headers: H });
  const rows = await r.json(); return Array.isArray(rows) && rows[0] ? rows[0] : null;
}
function merge(remote: Record<string, Pick>, local: Record<string, Pick>) {
  const out: Record<string, Pick> = { ...remote };
  for (const [id, p] of Object.entries(local || {})) { if (!p || typeof p !== "object") continue; const r = out[id]; if (!r || (p.ts || 0) > (r.ts || 0)) out[id] = { d: p.d ?? null, n: String(p.n || "").slice(0, 4000), ts: +p.ts || 0, ev: p.ev }; }
  return out;
}
const shape = (row: any) => ({ key: row.key, feed_token: row.feed_token, name: row.name, profile: row.profile, profile_ts: row.profile_ts, picks: row.picks, server_time: Date.now() });
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  try {
    if (req.method === "GET") {
      const key = new URL(req.url).searchParams.get("key") || ""; if (key.length < 8) return json({ error: "missing key" }, 400);
      const row = await load(key); return row ? json(shape(row)) : json({ error: "unknown code" }, 404);
    }
    if (req.method !== "POST") return json({ error: "method" }, 405);
    const body = await req.json().catch(() => ({}));
    if (JSON.stringify(body).length > 2_000_000) return json({ error: "too large" }, 413);
    if (body.create) {
      const row = { key: code(), feed_token: crypto.randomUUID().replace(/-/g, ""), name: String(body.name || "").slice(0, 80), profile: body.profile || null, profile_ts: +body.profile_ts || 0, picks: merge({}, body.picks || {}) };
      const r = await fetch(`${URL_}/rest/v1/accounts`, { method: "POST", headers: { ...H, Prefer: "return=representation" }, body: JSON.stringify(row) });
      const rows = await r.json(); if (!r.ok) return json({ error: "create failed", detail: rows }, 500);
      return json(shape(rows[0]));
    }
    const key = String(body.key || ""); if (key.length < 8) return json({ error: "missing key" }, 400);
    const row = await load(key); if (!row) return json({ error: "unknown code" }, 404);
    const picks = merge(row.picks || {}, body.picks || {});
    const newer = (+body.profile_ts || 0) > (+row.profile_ts || 0);
    const upd = { picks, profile: newer ? body.profile : row.profile, profile_ts: newer ? +body.profile_ts : row.profile_ts, name: newer || !row.name ? String(body.name ?? row.name ?? "").slice(0, 80) : row.name, updated_at: new Date().toISOString() };
    const r = await fetch(`${URL_}/rest/v1/accounts?key=eq.${encodeURIComponent(key)}`, { method: "PATCH", headers: { ...H, Prefer: "return=representation" }, body: JSON.stringify(upd) });
    const rows = await r.json(); if (!r.ok) return json({ error: "update failed", detail: rows }, 500);
    return json(shape(rows[0]));
  } catch (e) { return json({ error: String(e) }, 500); }
});
