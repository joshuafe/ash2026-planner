# Conference planner: ASH 2026 and Tandem 2027

Personal planning tool for hematology meetings. Two conferences are loaded so far, switchable from the title in the top bar (or `?c=ash2026` / `?c=tandem2027` in the URL):

| conference | dates and place | what is in | data folder |
|---|---|---|---|
| ASH 2026 Annual Meeting | December 12–15, 2026, Morial Convention Center, New Orleans (Central time) | 7,996 entries: 765 sessions, 6,374 abstracts with full text, 857 talks | `data/ash2026/` |
| 2027 Tandem Meetings (ASTCT and CIBMTR) | February 16–20, 2027, Orlando World Center Marriott (Eastern time) | 555 entries: 220 sessions with tracks, rooms and chairs, 335 talks with speakers; abstracts not yet released | `data/tandem2027/` |

Interests, name and sync code are shared across conferences; picks and notes are kept per conference. Live at https://joshuafe.github.io/ash2026-planner/ (first load of ASH is about 50 MB; Tandem is under 1 MB).

## The planner (`index.html`)
Phone-first, works offline from the folder or from GitHub Pages. Four tabs:
- **Picks** — every session, abstract and talk ranked by fit, with day pills, search and filters (type, program, decision, minimum fit, order). Tap an entry for the full abstract, people, why it fits, the talks inside a session, notes and links. Star to attend, or choose attend / maybe / skip in the sheet.
- **Plan** — your picks day by day with free gaps and overlap flags (a time grid on wide screens). *Add to calendar* downloads an `.ics` file for Outlook, Google or Apple Calendar: Central-time events with a VTIMEZONE block, stable identifiers so re-imports update, room, presenters, abstract excerpt and link.
- **Web** — the keyword web: your terms, the related keywords it picked up (add or mute them), and a draggable map. Tap a keyword to see what it travels with and the best entries that mention it.
- **Me** — name, the interest editor, *Rebuild my interest web* (the setup wizard), share link, back up and restore.

**Each person builds their own web.** On first open the wizard asks for areas of interest (22 bundles with weights) and a free-text description of your work, from which it extracts matching keywords from the corpus. Everything is saved in that browser only, so anyone you send the link to gets their own profile, picks and notes. A **share link** carries your picks and interests to someone else as an overlay they can copy or adopt, without touching their own.

## Sync across devices and the live calendar feed
Optional, under **Me**. *Create a sync code* makes an account on a small Supabase backend (project `ash2026-planner`, `supabase/`): a secret code like `ABCD-EFGH-JKLM` is the only credential, so there is no sign-up or email. Enter the same code on another device and both merge, newest change per entry wins; picks, notes, name and interests all sync, and the app re-syncs whenever it comes to the foreground. Unlink keeps local data and leaves the account for other devices.

Each account also gets a **live feed link** (`…/functions/v1/ics?t=<token>`, optionally `&m=1` for maybe picks). Subscribe to it in Outlook (Add calendar → Subscribe from web), Google Calendar (From URL) or Apple Calendar and it follows your picks; calendar apps refresh subscriptions every few hours. The feed token is separate from the sync code, so sharing the feed never exposes the account.

Backend pieces: `supabase/migrations/20261104_create_accounts.sql` (one `accounts` row per code, row-level security on, no anon access) and two edge functions deployed with JWT verification off because they authenticate with the code or token themselves: `supabase/functions/sync` (create / merge / read) and `supabase/functions/ics` (feed).

## Scoring
A term scores when it appears in a title (3), ASH keywords (2), session title (1.5), abstract (1–2 by frequency) or description (1); per topic the sum is capped and multiplied by the topic weight. The keyword web adds `6·ln(1 + s/4)` where `s` sums propagated keyword weights (title hits count double, broad keywords are down-weighted). The total is scaled by the program weight; people (+8) and institutions (+3) add bonuses; excluded terms subtract 8. A session also inherits 60% of the mean of its three best talks.

## Data files
- `data/<conference>/program.json` — one record per item (sessions, abstracts, talks) with `children` lists.
- `data/<conference>/program.csv` — flat spreadsheet version.
- `data/<conference>/core.js`, `abstracts.js`, `graph.js` — what the app loads; `data/conferences.js` lists the conferences (name, dates, venue, time zone, folder).

| field | meaning |
|---|---|
| `id` / `ash_id` | EventPilot id / ASH-site id (same number without the trailing letter) |
| `type` | `session`, `abstract` (has an abstract page), `talk` (sub-item without one) |
| `program` / `ep_category` | ASH program name / EventPilot category |
| `date`, `start`, `end`, `location` | from the EventPilot app (15-minute oral slots) |
| `participants`, `authors`, `presenters` | roles from ASH session pages; authors with presenting flag |
| `abstract`, `affiliations`, `keywords`, `cme` | from the ASH online program |

## Rebuilding (`scripts/`)
### ASH 2026
1. `fetch_eventpilot.sh <dir>` — EventPilot API (`eppro02.ativ.me`): agenda + speakers.
2. `scrape_ash.py <cache> <agenda_raw.json>` then `scrape_papers.py <cache> <ids.txt> <workers>` — `onlineprogram.hematology.org` session and paper pages (slow site, 2–7 s per page).
3. `parse_ash.py <cache> <parsed>` → `merge.py <eventpilot_dir> <parsed> <this folder>` (writes `data/ash2026/`) → `build_graph.py data/ash2026/program.json data/ash2026/graph.js`.

Abstract text exists only on the ASH online program; the app never exposes it.

### Tandem 2027
The program is served by the public tandemmeetings.org site from its m-events program API (event 605): session records, presentations and faculty. Raw JSON was captured from the site in a browser session and saved under an API dump folder; `tandem_build.py <api_dir> data/tandem2027` turns it into the planner schema and `build_graph.py data/tandem2027/program.json data/tandem2027/graph.js` builds the keyword web. Abstracts are not published yet; when they are, the same steps add their text to the talks.
