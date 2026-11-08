// Live calendar feed: GET /ics?t=<feed_token>[&m=1]  -> text/calendar with the account's attend (and maybe) picks.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
const URL_ = Deno.env.get("SUPABASE_URL")!;
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const H = { apikey: SERVICE, Authorization: `Bearer ${SERVICE}` };
const esc = (s: unknown) => String(s ?? "").replace(/\\/g, "\\\\").replace(/\r?\n/g, "\\n").replace(/[,;]/g, (m) => "\\" + m);
const fold = (line: string) => { const out: string[] = []; let s = line; while (s.length > 72) { out.push(s.slice(0, 72)); s = " " + s.slice(72); } out.push(s); return out.join("\r\n"); };
const local = (date: string, hm: string) => date.replace(/-/g, "") + "T" + hm.replace(":", "") + "00";
type Ev = { t?: string; date?: string; s?: string; e?: string; loc?: string; prog?: string; num?: string; sess?: string; pres?: string[]; url?: string; pid?: string; pt?: string; ps?: string; pe?: string; poster?: boolean; abs?: string; tz?: string; conf?: string };
Deno.serve(async (req) => {
  const u = new URL(req.url); const t = u.searchParams.get("t") || ""; const withMaybe = u.searchParams.get("m") === "1"; const confFilter = u.searchParams.get("c") || "";
  if (t.length < 16) return new Response("missing token", { status: 400 });
  const r = await fetch(`${URL_}/rest/v1/accounts?feed_token=eq.${encodeURIComponent(t)}&select=name,picks`, { headers: H });
  const rows = await r.json(); const row = Array.isArray(rows) && rows[0]; if (!row) return new Response("unknown feed", { status: 404 });
  const picks: Record<string, { d: string | null; n: string; ev?: Ev }> = row.picks || {};
  const chosen = Object.entries(picks).filter(([, p]) => p && p.ev && (p.d === "attend" || (withMaybe && p.d === "maybe")) && (!confFilter || (p.ev as Ev).conf === confFilter));
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  const TZ: Record<string, string[]> = {
    "America/Chicago": ["BEGIN:VTIMEZONE", "TZID:America/Chicago", "BEGIN:STANDARD", "DTSTART:19701101T020000", "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU", "TZOFFSETFROM:-0500", "TZOFFSETTO:-0600", "TZNAME:CST", "END:STANDARD", "BEGIN:DAYLIGHT", "DTSTART:19700308T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU", "TZOFFSETFROM:-0600", "TZOFFSETTO:-0500", "TZNAME:CDT", "END:DAYLIGHT", "END:VTIMEZONE"],
    "America/New_York": ["BEGIN:VTIMEZONE", "TZID:America/New_York", "BEGIN:STANDARD", "DTSTART:19701101T020000", "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU", "TZOFFSETFROM:-0400", "TZOFFSETTO:-0500", "TZNAME:EST", "END:STANDARD", "BEGIN:DAYLIGHT", "DTSTART:19700308T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU", "TZOFFSETFROM:-0500", "TZOFFSETTO:-0400", "TZNAME:EDT", "END:DAYLIGHT", "END:VTIMEZONE"],
    "America/Denver": ["BEGIN:VTIMEZONE", "TZID:America/Denver", "BEGIN:STANDARD", "DTSTART:19701101T020000", "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU", "TZOFFSETFROM:-0600", "TZOFFSETTO:-0700", "TZNAME:MST", "END:STANDARD", "BEGIN:DAYLIGHT", "DTSTART:19700308T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU", "TZOFFSETFROM:-0700", "TZOFFSETTO:-0600", "TZNAME:MDT", "END:DAYLIGHT", "END:VTIMEZONE"],
    "America/Los_Angeles": ["BEGIN:VTIMEZONE", "TZID:America/Los_Angeles", "BEGIN:STANDARD", "DTSTART:19701101T020000", "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU", "TZOFFSETFROM:-0700", "TZOFFSETTO:-0800", "TZNAME:PST", "END:STANDARD", "BEGIN:DAYLIGHT", "DTSTART:19700308T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU", "TZOFFSETFROM:-0800", "TZOFFSETTO:-0700", "TZNAME:PDT", "END:DAYLIGHT", "END:VTIMEZONE"],
    "Pacific/Honolulu": ["BEGIN:VTIMEZONE", "TZID:Pacific/Honolulu", "BEGIN:STANDARD", "DTSTART:19700101T000000", "TZOFFSETFROM:-1000", "TZOFFSETTO:-1000", "TZNAME:HST", "END:STANDARD", "END:VTIMEZONE"],
  };
  const tzOf = (ev: Ev) => (ev.tz && TZ[ev.tz]) ? ev.tz : "America/Chicago";
  const L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Conference Planner//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH", `X-WR-CALNAME:Conference picks ${row.name ? "(" + row.name + ")" : ""}`.trim(), "X-PUBLISHED-TTL:PT1H", "REFRESH-INTERVAL;VALUE=DURATION:PT1H"];
  const usedTz = new Set<string>(); for (const p of Object.values(picks)) if (p && p.ev) usedTz.add(tzOf(p.ev as Ev)); if (!usedTz.size) usedTz.add("America/Chicago"); for (const z of usedTz) L.push(...TZ[z]);
  // group posters by their poster session unless the session itself is picked
  const groups = new Map<string, { parent: Ev; posters: [string, Ev, string | null][] }>(); const singles: [string, Ev, string | null, string][] = [];
  const pickedIds = new Set(chosen.map(([id]) => id));
  for (const [id, p] of chosen) { const ev = p.ev as Ev; if (ev.poster && ev.pid && !pickedIds.has(ev.pid)) { const g = groups.get(ev.pid) || { parent: ev, posters: [] }; g.posters.push([id, ev, p.d]); groups.set(ev.pid, g); } else singles.push([id, ev, p.d, p.n]); }
  const push = (uid: string, ev: Ev, title: string, desc: string, start: string, end: string) => { if (!ev.date || !start || !end) return; L.push("BEGIN:VEVENT", `UID:${ev.conf || "ash2026"}-${uid}@planner`, `DTSTAMP:${stamp}`, `DTSTART;TZID=${tzOf(ev)}:${local(ev.date, start)}`, `DTEND;TZID=${tzOf(ev)}:${local(ev.date, end)}`, `SUMMARY:${esc(title)}`, `LOCATION:${esc(ev.loc || "")}`, `DESCRIPTION:${esc(desc)}`, ev.url ? `URL:${ev.url}` : "", "TRANSP:OPAQUE", "END:VEVENT"); };
  for (const [id, ev, d, n] of singles) {
    let desc = [ev.prog, ev.sess ? "Session: " + ev.sess : "", ev.pres?.length ? "Presenters: " + ev.pres.join(", ") : ""].filter(Boolean).join("\n");
    const mine = picks[id]; const posters = Object.entries(picks).filter(([, q]) => q && q.ev && (q.ev as Ev).pid === id && (q.d === "attend" || (withMaybe && q.d === "maybe")));
    if (posters.length) desc += "\nPosters:\n" + posters.map(([, q]) => `${(q.ev as Ev).num || ""} ${(q.ev as Ev).t}`).join("\n");
    if (ev.abs) desc += "\n\n" + ev.abs; if (n) desc += "\n\nNotes: " + n; if (ev.url) desc += "\n" + ev.url;
    push(id, ev, (d === "maybe" ? "Maybe: " : "") + (ev.num ? ev.num + " " : "") + (ev.t || ""), desc, ev.s || "", ev.e || "");
  }
  for (const [pid, g] of groups) { const ev = g.parent; const t = (g.posters.every(([, , d]) => d === "maybe") ? "Maybe: " : "") + (ev.pt || "Poster session"); const desc = "Posters:\n" + g.posters.map(([, e]) => `${e.num || ""} ${e.t} — ${(e.pres || [])[0] || ""}`).join("\n"); push("grp-" + pid, { ...ev, url: undefined }, t, desc, ev.ps || ev.s || "", ev.pe || ev.e || ""); }
  L.push("END:VCALENDAR");
  return new Response(L.filter(Boolean).map(fold).join("\r\n"), { headers: { "Content-Type": "text/calendar; charset=utf-8", "Cache-Control": "no-cache", "Access-Control-Allow-Origin": "*" } });
});
