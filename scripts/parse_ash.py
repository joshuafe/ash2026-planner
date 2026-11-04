"""Parse cached onlineprogram.hematology.org pages into JSON.
Usage: python3 -I parse_ash.py <cache_dir> <out_dir>
"""
import re, os, sys, json, html
from bs4 import BeautifulSoup

CACHE, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

def soup(path):
    return BeautifulSoup(open(path, encoding='utf-8', errors='replace').read(), 'lxml')

def clean(s):
    s = html.unescape(s or '')
    return re.sub(r'\s+', ' ', s).strip()

def block_text(el):
    """Text of an element with <br> and block boundaries as newlines, header label removed."""
    if el is None: return ''
    for br in el.find_all('br'): br.replace_with('\n')
    for h in el.find_all('h3'): h.decompose()
    for d in el.find_all(['div', 'p', 'li']): d.insert_before('\n'); d.insert_after('\n')
    t = html.unescape(el.get_text())
    t = re.sub(r'[ \t\r\f\v]+', ' ', t)
    t = re.sub(r' *\n *', '\n', t)
    t = re.sub(r'\n{2,}', '\n', t)
    return t.strip()

DEGREES = {'MD','PhD','MSc','MS','MPH','MBBS','MBChB','DO','PharmD','RN','BSc','BS','BA','MA','MBA','FRCP','FRCPath','FRACP','FRCPC','FACP','Jr','Sr','II','III','IV','MHS','MSCE','MSCI','MHSc','DNP','NP','PA-C','MPhil','DPhil','DSc','MDCM','MRCP','MRCPath','FRCPA','DM','ScD','MEd','MSN','BSN','PA','CNP','APRN','RPh','MBE','MSPH','MMSc','PhD(c)','FAAP','FACS','MHA','Dr. med.','PD Dr. med.','Prof.','MD/PhD','MD-PhD','FRCPE','FRCPI','FRCPCH','DrPH','MMed','ChB','MBBCh','BM','BCh','BAO','MPhil','MRes','DMD','DDS','DVM','FACC','FAHA','FASCO','FRCS','MDiv','MSW','LLM','JD','Med','med.','habil.','Dr.'}

def split_authors(em):
    """Parse an <em> block of authors: <strong> marks presenting author, <sup> gives affiliation indices."""
    if em is None: return []
    s = str(em)
    s = re.sub(r'^<em>|</em>$', '', s.strip())
    s = re.sub(r'<strong>(.*?)</strong>', lambda m: '\x03' + m.group(1) + '\x04', s, flags=re.S)
    s = re.sub(r'<sup>(.*?)</sup>', lambda m: '\x01' + m.group(1) + '\x02', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    tokens = re.split(r'(?<=[\x02\x04]),\s*', s)
    authors = []
    for tok in tokens:
        tok = tok.strip()
        if not tok: continue
        presenting = '\x03' in tok
        m = re.search(r'\x01(.*?)\x02', tok)
        aff = [a.strip() for a in m.group(1).split(',') if a.strip()] if m else []
        name = clean(re.sub(r'[\x01-\x04]', ' ', re.sub(r'\x01.*?\x02', '', tok)))
        name = name.strip(' ,')
        # If a token with no markers glued two authors together, split on ', X' where X is not a degree
        if not m and not presenting and ', ' in name:
            parts = [p.strip() for p in name.split(', ')]
            cur = [parts[0]]
            for p in parts[1:]:
                if p in DEGREES or re.match(r'^[A-Z][A-Za-z.]{0,6}$', p): cur.append(p)
                else:
                    authors.append({'name': ', '.join(cur), 'affil': [], 'presenting': False}); cur = [p]
            name = ', '.join(cur)
        authors.append({'name': name, 'affil': aff, 'presenting': presenting})
    return authors

def parse_affiliations(el):
    out = {}
    if el is None: return out
    for d in el.find_all('div'):
        sup = d.find('sup')
        if sup:
            idx = clean(sup.get_text()); sup.extract()
            out[idx] = clean(d.get_text())
    return out

def meta_from_icons(sp):
    """date/time/location from the session-meta block (session or paper page)."""
    meta = {'date_text': '', 'time_text': '', 'location': '', 'property': ''}
    for i in sp.select('.session-meta-item'):
        ic = i.find('i')
        cls = ' '.join(ic.get('class', [])) if ic else ''
        if ic: ic.extract()
        prop = ''
        # the location block has a nested div with optional "Session Property" comment content
        txt = clean(i.get_text())
        if 'calendar' in cls: meta['date_text'] = txt
        elif 'clock' in cls: meta['time_text'] = txt
        elif 'location' in cls: meta['location'] = txt
    return meta

def parse_date(d):
    m = re.search(r'([A-Z][a-z]+), ([A-Z][a-z]+) (\d+), (\d{4})', d)
    if not m: return None
    months = {m_: i for i, m_ in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'], 1)}
    return f"{m.group(4)}-{months[m.group(2)]:02d}-{int(m.group(3)):02d}"

def parse_time_range(t):
    def conv(x):
        m = re.match(r'(\d{1,2}):(\d{2})\s*([ap])\.?m\.?', x.strip(), re.I)
        if not m: return None
        h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3).lower()
        if ap == 'p' and h != 12: h += 12
        if ap == 'a' and h == 12: h = 0
        return f'{h:02d}:{mi:02d}'
    parts = re.split(r'\s*[-–]\s*', t)
    if len(parts) == 2: return conv(parts[0]), conv(parts[1])
    return None, None

def parse_session(path):
    sp = soup(path)
    h2 = sp.select_one('.session-details-header h2.session-title')
    if h2 is None: return None
    prog = sp.select_one('.session-program')
    program = clean(prog.get_text().replace('Program:', '')) if prog else ''
    meta = meta_from_icons(sp)
    start, end = parse_time_range(meta['time_text'])
    desc = block_text(sp.select_one('#ashcontent_pnlSessionDescription'))
    kw = clean(block_text(sp.select_one('#ashcontent_pnlSessionKeywords')))
    keywords = [k.strip() for k in kw.split(',') if k.strip()] if kw else []
    participants = []
    for tr in sp.select('#ashcontent_pnlSessionParticipants tbody tr'):
        tds = tr.find_all('td')
        if len(tds) >= 2:
            participants.append({'role': clean(tds[0].get_text()), 'name': clean(tds[1].get_text()),
                                 'disclosures': clean(tds[2].get_text()) if len(tds) > 2 else ''})
    papers = []
    for item in sp.select('.associated-paper-item'):
        a = item.select_one('a.paper-title-link')
        if not a: continue
        pid = re.search(r'pid=(\d+)', a.get('href', ''))
        title = clean(a.get_text())
        num = re.match(r'^(\d+)\s+(.*)$', title, re.S)
        au = item.select_one('.paper-authors em')
        papers.append({'pid': pid.group(1) if pid else None, 'number': num.group(1) if num else None,
                       'title': num.group(2) if num else title, 'authors': split_authors(au),
                       'affiliations': parse_affiliations(item.select_one('.paper-affiliations'))})
    cnt = sp.select_one('#ashcontent_lblPapersCountTop')
    cnt_m = re.search(r'of (\d+)', clean(cnt.get_text())) if cnt else None
    sid = re.search(r'(\d+)\.html$', path).group(1)
    return {'sid': sid, 'title': clean(h2.get_text()), 'program': program, 'date': parse_date(meta['date_text']),
            'date_text': meta['date_text'], 'start': start, 'end': end, 'time_text': meta['time_text'],
            'location': meta['location'], 'description': desc, 'keywords': keywords,
            'participants': participants, 'papers': papers,
            'papers_total': int(cnt_m.group(1)) if cnt_m else len(papers)}

def parse_paper(path):
    sp = soup(path)
    hdr = sp.find(string=lambda s: isinstance(s, str) and 'Begin Paper Header' in s)
    h2s = sp.select('h2.session-title')
    title_el = None
    for h in h2s:
        # the paper title h2 is inside .session-details-header that is NOT the session block (session title is a link)
        if h.find('a') is None and h.find_parent(id='ashcontent_lnkSessionTitle') is None:
            title_el = h
    if title_el is None: return None
    title = clean(title_el.get_text())
    num = re.match(r'^(\d+)\s+(.*)$', title, re.S)
    lnk = sp.select_one('#ashcontent_lnkSessionTitle')
    sid = re.search(r'sid=(\d+)', lnk.get('href', '')) if lnk else None
    prog = sp.select_one('.session-program')
    meta = meta_from_icons(sp)
    start, end = parse_time_range(meta['time_text'])
    kw = clean(block_text(sp.select_one('#ashcontent_pnlSessionKeywords')))
    abstract = block_text(sp.select_one('#pnlPaperAbstract'))
    disc = block_text(sp.select_one('#ashcontent_pnlPaperDisclosures'))
    pid = re.search(r'(\d+)\.html$', path).group(1)
    return {'pid': pid, 'number': num.group(1) if num else None, 'title': num.group(2) if num else title,
            'sid': sid.group(1) if sid else None, 'session_title': clean(lnk.get_text()) if lnk else '',
            'program': clean(prog.get_text().replace('Program:', '')) if prog else '',
            'date': parse_date(meta['date_text']), 'start': start, 'end': end, 'location': meta['location'],
            'keywords': [k.strip() for k in kw.split(',') if k.strip()] if kw else [],
            'authors': split_authors(sp.select_one('#ashcontent_pnlPaperAuthors em')),
            'affiliations': parse_affiliations(sp.select_one('#ashcontent_pnlPaperAffiliations')),
            'abstract': abstract, 'disclosures': disc}

def parse_list(path):
    """results-day / results-cme pages: every <details class=results-item> block."""
    sp = soup(path)
    items = []
    for det in sp.select('details.results-item'):
        tm = det.select_one('.results-time'); ttl = det.select_one('.results-title'); pr = det.select_one('.results-program')
        a = ttl.find('a') if ttl else None
        sid = re.search(r'sid=(\d+)', a.get('href', '')) if a else None
        loc = ''; desc = ''
        for d in det.select('.results-detail'):
            lab = d.find('strong'); 
            if lab and 'Location' in lab.get_text():
                p = d.find('p'); loc = clean(p.get_text()) if p else ''
        dsc = det.select_one('.results-description, .results-item-description')
        if dsc: desc = block_text(dsc)
        # find the day header this item belongs to: nearest preceding element with a date text
        items.append({'sid': sid.group(1) if sid else None, 'title': clean(ttl.get_text()) if ttl else '',
                      'time_text': clean(tm.get_text()) if tm else '', 'program': clean(pr.get_text().replace('Program:', '')) if pr else '',
                      'location': loc, 'description': desc})
    return items

def _safe(kind, path):
    try:
        r = parse_session(path) if kind == 'session' else parse_paper(path)
        return (kind, os.path.basename(path), r, None)
    except Exception as e:
        return (kind, os.path.basename(path), None, str(e))

if __name__ == '__main__':
    import concurrent.futures
    sessions, papers, errors = {}, {}, []
    jobs = []
    for kind, sub in (('session', 'sessions'), ('paper', 'papers')):
        d = os.path.join(CACHE, sub)
        if os.path.isdir(d):
            jobs += [(kind, os.path.join(d, fn)) for fn in sorted(os.listdir(d)) if fn.endswith('.html')]
    with concurrent.futures.ProcessPoolExecutor() as ex:
        for kind, fn, r, err in ex.map(_safe, [j[0] for j in jobs], [j[1] for j in jobs], chunksize=50):
            if err: errors.append((kind, fn, err))
            elif r is None: errors.append((kind + '-empty', fn))
            elif kind == 'session': sessions[r['sid']] = r
            else: papers[r['pid']] = r
    cme = set(); day_items = {}
    ldir = os.path.join(CACHE, 'lists')
    for fn in sorted(os.listdir(ldir)) if os.path.isdir(ldir) else []:
        if fn.startswith('cme_') and fn.endswith('.html'):
            t = open(os.path.join(ldir, fn), encoding='utf-8', errors='replace').read()
            cme |= set(re.findall(r'session-details\.aspx\?sid=(\d+)', t))
        if fn.startswith('day_') and fn.endswith('.html') and not day_items:  # every day page lists all days
            for it in parse_list(os.path.join(ldir, fn)):
                key = it['sid'] or ('T:' + it['title'] + '|' + it['time_text'])
                day_items.setdefault(key, it)
    json.dump(sessions, open(os.path.join(OUT, 'ash_sessions.json'), 'w'), ensure_ascii=False)
    json.dump(papers, open(os.path.join(OUT, 'ash_papers.json'), 'w'), ensure_ascii=False)
    json.dump(sorted(cme), open(os.path.join(OUT, 'cme_sids.json'), 'w'))
    json.dump(day_items, open(os.path.join(OUT, 'ash_day_items.json'), 'w'), ensure_ascii=False)
    json.dump(errors, open(os.path.join(OUT, 'parse_errors.json'), 'w'))
    print(f'sessions {len(sessions)}, papers {len(papers)}, cme {len(cme)}, day items {len(day_items)}, errors {len(errors)}')
    print(errors[:10])
