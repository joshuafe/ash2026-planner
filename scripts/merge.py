"""Merge EventPilot agenda/speakers with parsed ASH online-program data.
Usage: python3 -I merge.py <api_dir> <ash_parsed_dir> <dest_dir>
Outputs: ash2026_program.json, ash2026_program.csv, data/core.js, data/abstracts.js
"""
import re, os, sys, json, html, csv, datetime
API, ASH, DEST = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.join(DEST, 'data'), exist_ok=True)

def xml_json(path):
    t = open(path, encoding='utf-8').read()
    m = re.search(r'<Item([^>]*)>(.*)</Item>', t, re.S)
    return json.loads(html.unescape(m.group(2)))['data']

ep = json.load(open(os.path.join(API, 'agenda_raw.json')))
speakers = {}
for fn in sorted(os.listdir(API)):
    if fn.startswith('speakers_') and fn.endswith('.xml'):
        for s in xml_json(os.path.join(API, fn)):
            speakers[str(s['personid'])] = {'name': (s['firstname'] + ' ' + s['lastname']).strip(), 'org': s.get('description') or s.get('org') or ''}
sessions = json.load(open(os.path.join(ASH, 'ash_sessions.json')))
papers = json.load(open(os.path.join(ASH, 'ash_papers.json')))
cme = set(json.load(open(os.path.join(ASH, 'cme_sids.json'))))
# full titles / authors of papers as listed on their session pages (fallback for truncated app titles)
listed = {}
for s in sessions.values():
    for pp in s.get('papers', []):
        if pp.get('pid'): listed[pp['pid']] = pp

norm = lambda s: re.sub(r'[A-Z]+$', '', s)
def clean_ep_desc(d):
    d = html.unescape(d or '')
    d = re.sub(r'<br\s*/?>', '\n', d, flags=re.I); d = re.sub(r'<[^>]+>', '', d)
    d = re.sub(r'td \{border:[^}]*\}br \{[^}]*\}', '', d)
    d = re.sub(r'[ \t]+', ' ', d); d = re.sub(r'\n\s*\n+', '\n', d)
    return d.strip()
def hm(t): return t[:5] if t else None
SURL = 'https://onlineprogram.hematology.org/session-details.aspx?sid='
PURL = 'https://onlineprogram.hematology.org/paper-details.aspx?pid='

ep_by_id = {r['sessionid']: r for r in ep}
ep_parent_by_norm = {norm(r['sessionid']): r['sessionid'] for r in ep if not r['parent']}
ep_child_by_norm = {norm(r['sessionid']): r['sessionid'] for r in ep if r['parent']}
items = {}

for r in ep:
    sid_n = norm(r['sessionid'])
    is_parent = not r['parent']
    a = sessions.get(sid_n)                       # ASH session page (parents, and some sub-items ASH treats as sessions)
    p = papers.get(sid_n) if not is_parent else None
    if p and not (p.get('abstract') or p.get('authors')): p = None   # empty paper page
    lp = listed.get(sid_n) if not is_parent else None
    parent = ep_by_id.get(r['parent']) if r['parent'] else None
    parent_ash = sessions.get(norm(r['parent'])) if r['parent'] else None
    src = a or p or lp or {}
    typ = 'session' if is_parent else ('abstract' if (p and p.get('abstract')) else 'talk')
    title = (a or {}).get('title') or (p or {}).get('title') or (lp or {}).get('title') or r['title']
    number = (p or lp or {}).get('number')
    if not number:
        m = re.search(r'Paper No:\s*(\d+)', r['description'] or ''); number = m.group(1) if m else None
    keywords = (a or p or parent_ash or {}).get('keywords') or []
    program = (a or p or parent_ash or {}).get('program') or r['catname']
    participants = [{'name': x['name'], 'role': x['role']} for x in (a or {}).get('participants', [])]
    authors = (p or lp or {}).get('authors') or []
    ep_speakers = [speakers[s]['name'] for s in (r['speakers'] or '').split(',') if s and s in speakers]
    presenters = [x['name'] for x in participants] or [x['name'] for x in authors if x['presenting']] or ep_speakers
    cme_flag = (sid_n in cme) or (not is_parent and norm(r['parent']) in cme)
    if a and p and p.get('abstract'): ash_url = PURL + p['pid']
    elif a: ash_url = SURL + a['sid']
    elif p: ash_url = PURL + p['pid']
    else: ash_url = None
    items[r['sessionid']] = {
        'id': r['sessionid'], 'ash_id': (a or p or {}).get('sid') if a else (p or {}).get('pid'),
        'type': typ, 'parent_id': r['parent'] or None, 'number': number, 'title': title,
        'program': program, 'ep_category': r['catname'],
        'date': r['date'] or src.get('date'), 'start': hm(r['start']), 'end': hm(r['stop']),
        'location': r['location'] or src.get('location') or '',
        'session_title': (parent['title'] if parent else None) if not is_parent else None,
        'keywords': keywords, 'cme': bool(cme_flag),
        'participants': participants, 'authors': authors, 'ep_speakers': ep_speakers, 'presenters': presenters,
        'description': (a or {}).get('description') or '',
        'ep_description': clean_ep_desc(r['description']),
        'abstract': (p or {}).get('abstract') or '', 'affiliations': (p or lp or {}).get('affiliations') or {},
        'disclosures': (p or {}).get('disclosures') or '',
        'ash_url': ash_url,
        'ep_url': 'https://eppro02.ativ.me/web/page.php?page=Session&project=ASH26&id=' + r['sessionid'],
    }
    if not is_parent and parent is None and p and p.get('sid'):
        items[r['sessionid']]['parent_id'] = ep_parent_by_norm.get(p['sid'], 'ash-' + p['sid'])

# ASH-only sessions and papers (not present in the app at all)
for sid, a in sessions.items():
    if sid in ep_parent_by_norm or sid in ep_child_by_norm: continue
    items['ash-' + sid] = {
        'id': 'ash-' + sid, 'ash_id': sid, 'type': 'session', 'parent_id': None, 'number': None, 'title': a['title'],
        'program': a['program'], 'ep_category': None, 'date': a['date'], 'start': a['start'], 'end': a['end'],
        'location': a['location'], 'session_title': None, 'keywords': a['keywords'], 'cme': sid in cme,
        'participants': [{'name': x['name'], 'role': x['role']} for x in a['participants']], 'authors': [], 'ep_speakers': [],
        'presenters': [x['name'] for x in a['participants']], 'description': a['description'], 'ep_description': '',
        'abstract': '', 'affiliations': {}, 'disclosures': '', 'ash_url': SURL + sid, 'ep_url': None}
for pid, p in papers.items():
    if pid in ep_child_by_norm or pid in ep_parent_by_norm or not (p.get('abstract') or p.get('authors')): continue
    par = ep_parent_by_norm.get(p['sid']) if p.get('sid') else None
    par = par or (('ash-' + p['sid']) if p.get('sid') in sessions else None)
    items['ash-' + pid] = {
        'id': 'ash-' + pid, 'ash_id': pid, 'type': 'abstract' if p.get('abstract') else 'talk', 'parent_id': par, 'number': p['number'], 'title': p['title'],
        'program': p['program'], 'ep_category': None, 'date': p['date'], 'start': p['start'], 'end': p['end'],
        'location': p['location'], 'session_title': p['session_title'], 'keywords': p['keywords'], 'cme': p.get('sid') in cme,
        'participants': [], 'authors': p['authors'], 'ep_speakers': [], 'presenters': [x['name'] for x in p['authors'] if x['presenting']],
        'description': '', 'ep_description': '', 'abstract': p['abstract'], 'affiliations': p['affiliations'], 'disclosures': p['disclosures'],
        'ash_url': PURL + pid, 'ep_url': None}

for it in items.values(): it['children'] = []
for it in items.values():
    if it['parent_id'] and it['parent_id'] in items:
        items[it['parent_id']]['children'].append(it['id'])
        if not it['session_title']: it['session_title'] = items[it['parent_id']]['title']
        if not it['keywords']: it['keywords'] = items[it['parent_id']]['keywords']
        if not it['location']: it['location'] = items[it['parent_id']]['location']
for it in items.values():
    it['children'].sort(key=lambda c: ((items[c]['start'] or ''), (items[c]['number'] or '').zfill(6), items[c]['title']))

order = sorted(items.values(), key=lambda x: (x['date'] or '', x['start'] or '', x['type'] != 'session', (x['number'] or '').zfill(6), x['title']))
meta = {'generated': datetime.datetime.now().isoformat(timespec='seconds'), 'items': len(order),
        'by_type': {t: sum(1 for x in order if x['type'] == t) for t in ('session', 'abstract', 'talk')},
        'with_abstract': sum(1 for x in order if x['abstract']), 'cme_sessions': sum(1 for x in order if x['cme'] and x['type'] == 'session'),
        'sources': ['https://eppro02.ativ.me/web/index.php?project=ASH26', 'https://onlineprogram.hematology.org/']}
json.dump({'meta': meta, 'items': order}, open(os.path.join(DEST, 'ash2026_program.json'), 'w'), ensure_ascii=False, indent=0)

cols = ['id', 'type', 'program', 'ep_category', 'date', 'start', 'end', 'location', 'number', 'title', 'session_title', 'cme',
        'presenters', 'participants', 'authors', 'keywords', 'description', 'abstract', 'ep_description', 'ash_url', 'ep_url']
with open(os.path.join(DEST, 'ash2026_program.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(cols)
    for it in order:
        row = dict(it)
        row['presenters'] = '; '.join(it['presenters'])
        row['participants'] = '; '.join(f"{x['name']} ({x['role']})" for x in it['participants'])
        row['authors'] = '; '.join((x['name'] + ('*' if x['presenting'] else '')) for x in it['authors'])
        row['keywords'] = '; '.join(it['keywords'])
        w.writerow([row.get(c, '') if row.get(c) is not None else '' for c in cols])

heavy = ('abstract', 'affiliations', 'disclosures', 'ep_description', 'description')
def slim(it):
    c = {k: v for k, v in it.items() if k not in heavy}
    par = items.get(it['parent_id']) if it['parent_id'] else None
    if par and it['keywords'] == par['keywords']: c['keywords'] = []      # the app inherits a parent's keywords
    c['authors'] = [{'name': a['name'], 'presenting': a['presenting']} for a in it['authors']]
    if it['participants'] or it['authors']: c.pop('ep_speakers', None)
    return c
core = [slim(it) for it in order]
with open(os.path.join(DEST, 'data', 'core.js'), 'w', encoding='utf-8') as f:
    f.write('window.ASH_DATA=' + json.dumps({'meta': meta, 'items': core}, ensure_ascii=False, separators=(',', ':')) + ';\n')
with open(os.path.join(DEST, 'data', 'abstracts.js'), 'w', encoding='utf-8') as f:
    def heavy_of(it):
        d = {k: it[k] for k in heavy if it[k] and k != 'disclosures'}
        if it['abstract'] or it['description']: d.pop('ep_description', None)   # app text is redundant once ASH text exists
        if any(a['affil'] for a in it['authors']): d['author_affil'] = [a['affil'] for a in it['authors']]
        return d
    f.write('window.ASH_ABSTRACTS=' + json.dumps({it['id']: heavy_of(it) for it in order}, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(json.dumps(meta, indent=1))
