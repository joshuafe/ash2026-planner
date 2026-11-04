"""Fetch paper-details pages for a list of ids. Usage: python3 -I scrape_papers.py <cache_dir> <ids.txt> <workers>"""
import os, sys, time, concurrent.futures, requests
BASE='https://onlineprogram.hematology.org/'; CACHE=sys.argv[1]; IDS=[l.strip() for l in open(sys.argv[2]) if l.strip()]; W=int(sys.argv[3])
sess=requests.Session(); sess.headers.update({'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) personal-schedule-planner'})
LOG=open(os.path.join(CACHE,'scrape_papers.log'),'a')
def log(m): LOG.write(time.strftime('%H:%M:%S ')+m+'\n'); LOG.flush()
def fetch(pid):
    path=os.path.join(CACHE,'papers',f'{pid}.html')
    if os.path.exists(path) and os.path.getsize(path)>1000: return 'cached'
    if os.path.exists(path+'.404'): return '404'
    for a in range(5):
        try:
            r=sess.get(BASE+f'paper-details.aspx?pid={pid}',timeout=40)
            if r.status_code==200 and len(r.content)>1000:
                open(path,'wb').write(r.content); return 'ok'
            if r.status_code==404: open(path+'.404','w').write('404'); return '404'
            log(f'HTTP {r.status_code} {pid} attempt {a}')
        except Exception as e: log(f'ERR {pid}: {e} attempt {a}')
        time.sleep(1.5*(a+1))
    return 'fail'
os.makedirs(os.path.join(CACHE,'papers'),exist_ok=True)
done={'ok':0,'cached':0,'404':0,'fail':0}; n=0; t0=time.time()
with concurrent.futures.ThreadPoolExecutor(W) as ex:
    for res in ex.map(fetch, IDS):
        done[res]+=1; n+=1
        if n%200==0: log(f'papers {n}/{len(IDS)} {done} {time.time()-t0:.0f}s')
log(f'papers DONE {done} {time.time()-t0:.0f}s')
