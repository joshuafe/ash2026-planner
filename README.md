# ASH 2026 program extract + planner

Personal planning tool for the ASH 2026 Annual Meeting (New Orleans, Dec 9–18, 2026; times are Central).

## Files
- `index.html` — the planner. Open it directly in a browser (double-click) or serve the folder. It loads `data/core.js` and `data/abstracts.js`.
  - **Rank & review**: every session, abstract and talk ranked by your interest profile, with filters, search, and ★ attend / ? maybe / ✕ skip decisions.
  - **My calendar**: day grid of your picks with conflict flags, poster lists, `.ics` export (Apple/Google/Outlook), CSV export, print list.
  - **Interests**: edit topics/terms/weights, people, institutions, excluded terms, program weights. Decisions, notes and profile are saved in the browser (use Backup/Restore to move them).
- `ash2026_program.json` — full merged dataset (one record per item, with children lists).
- `ash2026_program.csv` — flat spreadsheet version.
- `scripts/` — how the data was built:
  1. `fetch_eventpilot.sh <dir>` — EventPilot app API (`eppro02.ativ.me`): all agenda items with exact times (15-min oral slots), locations, categories, speaker ids.
  2. `scrape_ash.py <cache> <agenda_raw.json>` and `scrape_papers.py <cache> <ids.txt> <workers>` — `onlineprogram.hematology.org` session and paper pages (abstracts, authors, affiliations, keywords, participants, CME lists). Slow site: 2–7 s per page.
  3. `parse_ash.py <cache> <parsed>` → JSON; `merge.py <eventpilot_dir> <parsed> <this folder>` → the outputs above.

## Data notes
- Item ids are EventPilot ids; `ash_id` is the ASH site id (same number without the trailing letter).
- `type`: `session` (parent), `abstract` (has an abstract page), `talk` (sub-item of a session without an abstract page, e.g. Education/Scientific Program talks).
- `program` is the ASH site program name (finer than the app's category, kept in `ep_category`). `cme` comes from the ASH CME-eligible lists.
- Abstract text comes only from the ASH online program; the app itself never exposes it.
