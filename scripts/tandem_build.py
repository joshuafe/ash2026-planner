"""Build the Tandem 2027 dataset (same schema as the ASH one) from the virtual-meeting API dumps.
Usage: python3 -I tandem_build.py <api_dir> <out_dir>   (out_dir e.g. .../ash2026/data/tandem2027)
"""
import re, os, sys, json, html, csv, datetime, collections
API, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
cs_all = json.load(open(os.path.join(API, 'contentsessions_all.json')))
pres_all = [p['body'] for p in json.load(open(os.path.join(API, 'presentations_all.json')))]
fac_all = [f['body'] for f in json.load(open(os.path.join(API, 'faculty_all.json')))]
event = json.load(open(os.path.join(API, 'sample_event.json')))
SITE = 'https://tandemmeetings.org/program'

def clean_html(h):
    h = html.unescape(h or ''); h = re.sub(r'<br\s*/?>|</p>|</div>|</li>', '\n', h, flags=re.I); h = re.sub(r'<[^>]+>', '', h)
    h = re.sub(r'[ \t]+', ' ', h); h = re.sub(r'\n\s*\n+', '\n', h); return h.strip()
def person_name(u):
    if not u: return ''
    pu = u.get('partner_user') or {}
    name = ' '.join(x for x in [(u.get('firstname') or '').strip(), (u.get('surname') or '').strip()] if x)
    cred = (pu.get('credentials') or u.get('academic_title') or '').strip()
    return name + (', ' + cred if cred and cred.lower() not in name.lower() else '')
def person_inst(u):
    if not u: return ''
    pu = u.get('partner_user') or {}
    inst = (pu.get('institute') or u.get('institute') or '').strip()
    if not inst:
        city = (pu.get('city_name') or u.get('city') or '').strip(); country = (pu.get('country_name') or u.get('country') or '').strip()
        inst = ', '.join(x for x in [city, country] if x)
    return inst
fac_inst = {}
for f in fac_all:
    u = f.get('user') or {}; inst = person_inst(u)
    if inst and u.get('id'): fac_inst[u['id']] = inst
def inst_of(u): return person_inst(u) or fac_inst.get(u.get('id'), '')
def local_parts(ts):   # "2027-02-16T08:00:00-05:00" -> date, HH:MM
    return (ts[:10], ts[11:16]) if ts else (None, None)
def split_code(title):
    m = re.match(r'^\(([A-Za-z0-9/&\- ]{1,12})\)\s*(.+)$', title or '')
    return (m.group(1), m.group(2).strip()) if m else (None, (title or '').strip())

items = {}
for c in cs_all:
    code, title = split_code(c.get('title'))
    date, start = local_parts(c.get('starts_at_local')); _, end = local_parts(c.get('ends_at_local'))
    room = (c.get('room') or {}).get('title') or ''
    groups = [g['name'].strip() for g in c.get('contentsessiongroups') or []]
    tags = [t['name'] for t in c.get('contentsessiontags') or []]
    track = ((c.get('contentsessiontype') or {}).get('name') or '').strip() or 'Session'
    roles = {x['user_id']: x.get('chairtype') or 'Chair' for x in c.get('chairs_contentsessions') or []}
    participants = [{'name': person_name(u), 'role': roles.get(u.get('id'), 'Chair'), 'inst': inst_of(u)} for u in c.get('chairs') or []]
    topic = (c.get('contentsessiontopic') or {}).get('name')
    items['tm-s%d' % c['id']] = {
        'id': 'tm-s%d' % c['id'], 'ash_id': str(c['id']), 'type': 'session', 'parent_id': None, 'number': code, 'title': title,
        'program': track, 'ep_category': ', '.join(groups) or None,
        'date': date, 'start': start, 'end': end, 'location': room if room and room != 'TBD' else 'Room to be announced',
        'session_title': None, 'keywords': groups + ([topic] if topic else []), 'credits': tags, 'cme': 'CME' in tags,
        'participants': [{'name': p['name'], 'role': p['role']} for p in participants], 'authors': [], 'ep_speakers': [],
        'presenters': [p['name'] for p in participants],
        'description': clean_html(c.get('description')), 'ep_description': clean_html(c.get('short_description') or c.get('additional_information') or ''),
        'abstract': '', 'affiliations': {str(i+1): p['inst'] for i, p in enumerate(participants) if p['inst']}, 'disclosures': '',
        'ash_url': 'https://tandemmeetings.org/program/session/%d' % c['id'], 'ep_url': None,
    }
for p in pres_all:
    sess = p.get('contentsession') or {}; pid = 'tm-s%d' % sess['id'] if sess.get('id') else None
    parent = items.get(pid)
    date, start = local_parts(p.get('starts_at_local')); _, end = local_parts(p.get('ends_at_local'))
    main = (p.get('main_author') or {}).get('id')
    authors = []; affs = {}; aff_idx = {}
    for a in p.get('authors') or []:
        inst = inst_of(a); idx = None
        if inst:
            if inst not in aff_idx: aff_idx[inst] = str(len(aff_idx) + 1); affs[aff_idx[inst]] = inst
            idx = aff_idx[inst]
        authors.append({'name': person_name(a), 'presenting': a.get('id') == main or (main is None and not authors), 'affil': [idx] if idx else []})
    code, title = split_code(p.get('title'))
    items['tm-p%d' % p['id']] = {
        'id': 'tm-p%d' % p['id'], 'ash_id': str(p['id']), 'type': 'talk', 'parent_id': pid, 'number': p.get('import_id') or None, 'title': title,
        'program': parent['program'] if parent else ((p.get('contenttype') or {}).get('name') or 'Presentation'), 'ep_category': parent['ep_category'] if parent else None,
        'date': date or (parent or {}).get('date'), 'start': start or (parent or {}).get('start'), 'end': end or (parent or {}).get('end'),
        'location': parent['location'] if parent else '', 'session_title': parent['title'] if parent else (sess.get('title') or None),
        'keywords': (parent['keywords'] if parent else []) + [k.get('name', k) if isinstance(k, dict) else k for k in p.get('keywords') or []], 'credits': parent['credits'] if parent else [], 'cme': bool(parent and parent['cme']),
        'participants': [], 'authors': authors, 'ep_speakers': [], 'presenters': [a['name'] for a in authors if a['presenting']] or [a['name'] for a in authors[:1]],
        'description': '', 'ep_description': '', 'abstract': '', 'affiliations': affs, 'disclosures': '',
        'ash_url': (p.get('external_abstract_url') or ('https://tandemmeetings.org/program/session/%d' % sess['id'] if sess.get('id') else SITE)), 'ep_url': None,
    }
for it in items.values(): it['children'] = []
for it in items.values():
    if it['parent_id'] and it['parent_id'] in items: items[it['parent_id']]['children'].append(it['id'])
for it in items.values(): it['children'].sort(key=lambda c: ((items[c]['start'] or ''), (items[c]['number'] or ''), items[c]['title']))
# a session with no presenters inherits its talks' speakers for display
for it in items.values():
    if it['type'] == 'session' and not it['presenters']:
        seen = []; [seen.append(n) for c in it['children'] for n in items[c]['presenters'] if n and n not in seen]
        it['ep_speakers'] = seen[:8]; it['presenters'] = seen[:4]
order = sorted(items.values(), key=lambda x: (x['date'] or '', x['start'] or '', x['type'] != 'session', x['title']))
meta = {'conference': 'tandem2027', 'title': event.get('title'), 'tz': 'America/New_York', 'generated': datetime.datetime.now().isoformat(timespec='seconds'), 'items': len(order),
        'by_type': {t: sum(1 for x in order if x['type'] == t) for t in ('session', 'abstract', 'talk')}, 'with_abstract': 0,
        'cme_sessions': sum(1 for x in order if x['cme'] and x['type'] == 'session'), 'sources': ['https://tandemmeetings.org/program', 'https://api-lb.virtual-meeting.net/v1 (event 605)']}
json.dump({'meta': meta, 'items': order}, open(os.path.join(OUT, 'program.json'), 'w'), ensure_ascii=False, indent=0)
cols = ['id', 'type', 'program', 'ep_category', 'date', 'start', 'end', 'location', 'number', 'title', 'session_title', 'cme', 'credits', 'presenters', 'participants', 'authors', 'keywords', 'description', 'abstract', 'ash_url']
with open(os.path.join(OUT, 'program.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(cols)
    for it in order:
        row = dict(it); row['presenters'] = '; '.join(it['presenters']); row['participants'] = '; '.join(f"{x['name']} ({x['role']})" for x in it['participants']); row['authors'] = '; '.join(x['name'] + ('*' if x['presenting'] else '') for x in it['authors']); row['keywords'] = '; '.join(it['keywords']); row['credits'] = '; '.join(it.get('credits') or [])
        w.writerow([row.get(c, '') if row.get(c) is not None else '' for c in cols])
heavy = ('abstract', 'affiliations', 'disclosures', 'ep_description', 'description')
def slim(it):
    c = {k: v for k, v in it.items() if k not in heavy}
    par = items.get(it['parent_id']) if it['parent_id'] else None
    if par and it['keywords'] == par['keywords']: c['keywords'] = []
    c['authors'] = [{'name': a['name'], 'presenting': a['presenting']} for a in it['authors']]
    return c
with open(os.path.join(OUT, 'core.js'), 'w', encoding='utf-8') as f: f.write('window.ASH_DATA=' + json.dumps({'meta': meta, 'items': [slim(i) for i in order]}, ensure_ascii=False, separators=(',', ':')) + ';\n')
def heavy_of(it):
    d = {k: it[k] for k in heavy if it[k] and k != 'disclosures'}
    if any(a['affil'] for a in it['authors']): d['author_affil'] = [a['affil'] for a in it['authors']]
    return d
with open(os.path.join(OUT, 'abstracts.js'), 'w', encoding='utf-8') as f: f.write('window.ASH_ABSTRACTS=' + json.dumps({it['id']: heavy_of(it) for it in order}, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(json.dumps(meta, indent=1)); print('programs:', collections.Counter(x['program'] for x in order if x['type']=='session').most_common()); print('talks without parent:', sum(1 for x in order if x['type']=='talk' and not x['parent_id'])); print('sessions with chairs:', sum(1 for x in order if x['participants'])); print('talks with authors:', sum(1 for x in order if x['authors']))
