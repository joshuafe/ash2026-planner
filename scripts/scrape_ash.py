"""Scrape onlineprogram.hematology.org: day/CME list pages, session-details, paper-details.
Usage: python3 -I scrape_ash.py <cache_dir> <eventpilot_agenda_raw.json>
"""
import re, os, sys, time, json, concurrent.futures, requests

BASE = 'https://onlineprogram.hematology.org/'
CACHE = sys.argv[1]
EP_JSON = sys.argv[2]
WORKERS = 6
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) personal-schedule-planner'}
sess = requests.Session(); sess.headers.update(HEADERS)
LOG = open(os.path.join(CACHE, 'scrape.log'), 'a')

def log(msg):
    LOG.write(time.strftime('%H:%M:%S ') + msg + '\n'); LOG.flush()

def fetch(url, path, retries=5):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return 'cached'
    for attempt in range(retries):
        try:
            r = sess.get(url, timeout=40)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(path, 'wb') as f: f.write(r.content)
                time.sleep(0.05)
                return 'ok'
            if r.status_code == 404:
                with open(path + '.404', 'w') as f: f.write(str(r.status_code))
                return '404'
            log(f'HTTP {r.status_code} {url} (attempt {attempt})')
        except Exception as e:
            log(f'ERR {url}: {e} (attempt {attempt})')
        time.sleep(1.5 * (attempt + 1))
    return 'fail'

def run(jobs, label):
    done = {'ok': 0, 'cached': 0, '404': 0, 'fail': 0}
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(fetch, u, p): u for u, p in jobs}
        n = 0
        for f in concurrent.futures.as_completed(futs):
            done[f.result()] += 1; n += 1
            if n % 100 == 0: log(f'{label}: {n}/{len(jobs)} {done}')
    log(f'{label} DONE {done}')
    return done

for d in ['lists', 'sessions', 'papers']:
    os.makedirs(os.path.join(CACHE, d), exist_ok=True)

# Phase 0: list pages
dates = ['2026-12-%02d' % i for i in range(9, 19)]
cme_dates = ['2026-12-%02d' % i for i in range(11, 16)]
jobs = [(BASE + f'results-day.aspx?date={d}', os.path.join(CACHE, 'lists', f'day_{d}.html')) for d in dates]
jobs += [(BASE + f'results-cme.aspx?date={d}', os.path.join(CACHE, 'lists', f'cme_{d}.html')) for d in cme_dates]
run(jobs, 'lists')

# Phase 1: sessions
sids = set()
for fn in os.listdir(os.path.join(CACHE, 'lists')):
    if fn.endswith('.html'):
        t = open(os.path.join(CACHE, 'lists', fn), encoding='utf-8', errors='replace').read()
        sids |= set(re.findall(r'session-details\.aspx\?sid=(\d+)', t))
ep = json.load(open(EP_JSON))
norm = lambda s: re.sub(r'[A-Z]+$', '', s)
ep_parents = {norm(r['sessionid']) for r in ep if not r['parent']}
ep_children = {norm(r['sessionid']) for r in ep if r['parent']}
log(f'sids from lists: {len(sids)}; EP parents: {len(ep_parents)}; union: {len(sids | ep_parents)}')
sids |= ep_parents
jobs = [(BASE + f'session-details.aspx?sid={s}', os.path.join(CACHE, 'sessions', f'{s}.html')) for s in sorted(sids)]
run(jobs, 'sessions')

# Phase 2: papers
pids = set()
for fn in os.listdir(os.path.join(CACHE, 'sessions')):
    if fn.endswith('.html'):
        t = open(os.path.join(CACHE, 'sessions', fn), encoding='utf-8', errors='replace').read()
        pids |= set(re.findall(r'paper-details\.aspx\?pid=(\d+)', t))
log(f'pids from sessions: {len(pids)}; EP children: {len(ep_children)}; union: {len(pids | ep_children)}')
pids |= ep_children
jobs = [(BASE + f'paper-details.aspx?pid={p}', os.path.join(CACHE, 'papers', f'{p}.html')) for p in sorted(pids)]
run(jobs, 'papers')
log('ALL DONE')
