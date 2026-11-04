# ASH 2026 program extract + planner

Personal planning tool for the ASH 2026 Annual Meeting (New Orleans, Dec 9–18, 2026; times are Central).
Open `index.html` in a browser, or publish the folder with GitHub Pages and share the URL.

## The planner (`index.html`)
Phone-first, works offline from the folder or from GitHub Pages. Four tabs:
- **Picks** — every session, abstract and talk ranked by fit, with day pills, search and filters (type, program, decision, minimum fit, order). Tap an entry for the full abstract, people, why it fits, the talks inside a session, notes and links. Star to attend, or choose attend / maybe / skip in the sheet.
- **Plan** — your picks day by day with free gaps and overlap flags (a time grid on wide screens). *Add to calendar* downloads an `.ics` file for Outlook, Google or Apple Calendar: Central-time events with a VTIMEZONE block, stable identifiers so re-imports update, room, presenters, abstract excerpt and link.
- **Web** — the keyword web: your terms, the related keywords it picked up (add or mute them), and a draggable map. Tap a keyword to see what it travels with and the best entries that mention it.
- **Me** — name, the interest editor, *Rebuild my interest web* (the setup wizard), share link, back up and restore.

**Each person builds their own web.** On first open the wizard asks for areas of interest (22 bundles with weights) and a free-text description of your work, from which it extracts matching keywords from the corpus. Everything is saved in that browser only, so anyone you send the link to gets their own profile, picks and notes. A **share link** carries your picks and interests to someone else as an overlay they can copy or adopt, without touching their own.

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
