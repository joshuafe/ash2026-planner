# ASH 2026 program extract + planner

Personal planning tool for the ASH 2026 Annual Meeting (New Orleans, Dec 9–18, 2026; times are Central).
Open `index.html` in a browser, or publish the folder with GitHub Pages and share the URL.

## The planner (`index.html`)
- **Rank & review** — every session, abstract and talk ranked by your interest profile; filters by day, program, type; full-text search; ★ attend / ? maybe / ✕ skip; notes; links to the ASH program page and the app.
- **My calendar** — day grid of your picks with time-conflict flags, posters grouped per poster session, `.ics` export (Apple/Google/Outlook), CSV export, printable list.
- **Keyword web** — a co-occurrence graph of ~4,000 keywords mined from all titles and abstracts plus ASH's own topic tags. Your interest terms seed it; weight spreads to linked keywords, which then add points to items that mention them. Add a suggested keyword to your interests, mute one, click any node to see its neighbours and top items.
- **Interests** — topics (terms + weight), people, institutions, excluded terms, program weights, and the keyword-web strength/spread.

Everything you do is saved in **your own browser** (localStorage). Anyone you send the app or its link to starts with the default profile and keeps their own picks. To show someone your picks, use **Share link**: it encodes your attend/maybe choices and interest profile in the URL; they can view them as an overlay, copy them, or adopt your profile — their own choices are never overwritten. **Backup/Restore** moves your state between browsers or devices.

## Scoring
A term scores when it appears in a title (3), ASH keywords (2), session title (1.5), abstract (1–2 by frequency) or description (1); per topic the sum is capped and multiplied by the topic weight. The keyword web adds `6·ln(1 + s/4)` where `s` sums propagated keyword weights (title hits count double, broad keywords are down-weighted). The total is scaled by the program weight; people (+8) and institutions (+3) add bonuses; excluded terms subtract 8. A session also inherits 60% of the mean of its three best talks.

## Data files
- `ash2026_program.json` — one record per item (sessions, abstracts, talks) with `children` lists.
- `ash2026_program.csv` — flat spreadsheet version.
- `data/core.js`, `data/abstracts.js`, `data/graph.js` — what the app loads.

| field | meaning |
|---|---|
| `id` / `ash_id` | EventPilot id / ASH-site id (same number without the trailing letter) |
| `type` | `session`, `abstract` (has an abstract page), `talk` (sub-item without one) |
| `program` / `ep_category` | ASH program name / EventPilot category |
| `date`, `start`, `end`, `location` | from the EventPilot app (15-minute oral slots) |
| `participants`, `authors`, `presenters` | roles from ASH session pages; authors with presenting flag |
| `abstract`, `affiliations`, `keywords`, `cme` | from the ASH online program |

## Rebuilding (`scripts/`)
1. `fetch_eventpilot.sh <dir>` — EventPilot API (`eppro02.ativ.me`): agenda + speakers.
2. `scrape_ash.py <cache> <agenda_raw.json>` then `scrape_papers.py <cache> <ids.txt> <workers>` — `onlineprogram.hematology.org` session and paper pages (slow site, 2–7 s per page).
3. `parse_ash.py <cache> <parsed>` → `merge.py <eventpilot_dir> <parsed> <this folder>` → `build_graph.py ash2026_program.json <this folder>`.

Abstract text exists only on the ASH online program; the app never exposes it.
