"""Build a keyword co-occurrence web from the merged program.
Usage: python3 -I build_graph.py <ash2026_program.json> <dest_dir>
Writes <dest>/data/graph.js = window.ASH_GRAPH = {terms:[{id,label,kind,df}], items:{itemId:[[titleTermIds],[bodyTermIds]]}, edges:[[a,b,w],...]}
"""
import re, sys, os, json, math, collections, itertools, unicodedata
SRC, DEST = sys.argv[1], sys.argv[2]
d = json.load(open(SRC)); items = d['items']; N = len(items)

STOP = set("""a an the and or of to in on for with without by from at as is are was were be been being this that these those it its their there here which who whom whose what when where while than then also both either neither not no nor into onto over under between among within across after before during through via per about above below up down out off again further once all any each few more most other some such only own same so too very s t can will just should now
we our us i you your he she they them his her all one two three four five six seven eight nine ten first second third
patients patient study studies results result methods method background conclusion conclusions aim aims objective objectives purpose analysis analyses analyzed data group groups median mean rate rates significant significantly respectively compared comparison versus vs including included include includes however overall total number numbers year years month months day days week weeks cohort cohorts used using use associated association associations higher lower increase increased increases decrease decreased decreases levels level based also well may might can one new novel approach approaches evaluate evaluated evaluating evaluation assess assessed assessing assessment observed observation found showed show shown shows demonstrate demonstrated demonstrates reported report reports further additional potential important importantly clinical clinically outcomes outcome treatment treated treat therapy therapies therapeutic disease diseases cases case control controls range time times baseline follow-up followup respectively ratio interval confidence hazard odds proportion percent percentage vs. p-value value values model models performed performing perform conducted conduct identify identified identifies identification determine determined determining define defined defining characterize characterized characterization investigate investigated investigation describe described examine examined explore explored provide provided provides previously prior recent recently current currently present presented presenting presentation suggest suggested suggests indicate indicated indicates remain remains remained support supported supports whether although despite among amongst underwent undergoing received receiving receive given give giving need needs needed required require requires available availability regarding related relative relatively particularly especially specifically primarily mainly largely often frequently rarely commonly similar similarly different differences difference distinct unique several various multiple single less least many much larger smaller largest smallest greater lower lowest highest high low long short longer shorter early late later earlier initial final primary secondary main major minor non none another others either per least year-old years-old aged age older younger adult adults pediatric children child male female males females men women sex gender
indicating suggesting suggest revealed reveal reveals whereas together collected collect enhanced enhance enhances following impact impacts large small samples sample notably interestingly importantly consistent consistently markedly robust strongly approximately remained exhibited exhibit displayed display confirmed confirm validated validate measured measure detected detect obtained obtain achieved achieve achieving resulted resulting led contributed contribute highlights highlight underscore underscores warrant warrants warranted ongoing future limited lack absence presence within across along toward towards yet thus therefore hence moreover furthermore additionally finally taken collectively represents represent representing critical key role roles effect effects effective efficacy safety profile profiles setting settings population populations subgroup subgroups arm arms dose doses enrolled enrollment eligible eligibility endpoint endpoints evaluable analyzed analysed assessed estimated estimate estimates calculated calculate tested test tests testing considered consider considering noted note notes seen see showing known unknown possible possibly likely unlikely able unable allow allows allowing enable enables enabling leading lead leads due owing because since until without whereas while thereby wherein hereby per-protocol intention-to-treat months-old weeks-old
occurred status reduced reduction common commonly activity improved improve improvement criteria followed developed develop development characteristics standard death deaths independent independently grade grades burden combined combination plus sensitivity specificity negative positive cycles cycle regimen regimens initiated initiation continued continue discontinued discontinuation completed completion administered administration received receipt duration frequency frequent incidence prevalence percent proportion majority minority subset subsets cohort-wide upon versus whereby wherein thereof overall-survival progression-free event-free rate-of n-of defined-as according accordingly addition additionally apparent apparently appear appears appeared approximately around average below above nearly roughly respective similar similarly significance significant signficantly statistically substantial substantially
excluded exclude excluding poor pts pt iqr center centers human humans elevated system systems stage stages highly classified classify management managed subsequent subsequently type types experienced experience against durable inferior superior validation validated target targets targeting protein proteins mechanism mechanisms alone either/or whom hence onset nature cause causes caused cumulative favorable unfavorable worse better best worst good bad real actual actually true truly false unclear clear clearly
abstract introduction summary table figure fig vs. e.g i.e et al n= p= p< p> hr= or= ci= ci: 95% 95 ci""".split())
DOMAIN_KEEP = set()  # placeholder for exceptions

tok_re = re.compile(r"[a-z0-9][a-z0-9\-\+/]*[a-z0-9\+]|[a-z0-9]")
def sentences(text):
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.encode('ascii', 'ignore').decode('ascii').lower()
    return re.split(r"[\.\;\:\?\!\(\)\[\]\{\}\n,]+|\s[-–—]\s", text)
def ngrams_of(text):
    out = {1: set(), 2: set(), 3: set()}
    for s in sentences(text):
        toks = tok_re.findall(s)
        toks = [t.strip('-/+') for t in toks]
        toks = [t for t in toks if t]
        L = len(toks)
        for i in range(L):
            for n in (1, 2, 3):
                if i + n > L: break
                g = toks[i:i+n]
                if g[0] in STOP or g[-1] in STOP: continue
                if any(not re.search(r'[a-z]', t) for t in g): continue       # numeric-only token
                if any(len(t) < 2 for t in g): continue
                if n == 1 and (len(g[0]) < 3 and not re.search(r'\d', g[0])): continue
                out[n].add(' '.join(g))
    return out

doc_title, doc_body = {}, {}
df = collections.Counter()
for it in items:
    tt = ngrams_of(it['title'] or '')
    bt = ngrams_of(' . '.join([it.get('abstract') or '', it.get('description') or '']))
    doc_title[it['id']] = tt[1] | tt[2] | tt[3]
    doc_body[it['id']] = (bt[1] | bt[2] | bt[3]) | doc_title[it['id']]
    for g in doc_body[it['id']]: df[g] += 1

MIN = {1: 25, 2: 12, 3: 8}; MAXDF = {1: 0.10 * N, 2: 0.22 * N, 3: 0.22 * N}
cand = {g: c for g, c in df.items() if c >= MIN[g.count(' ') + 1] and c <= MAXDF[g.count(' ') + 1]}
# prune shorter grams absorbed by a longer gram with nearly the same DF
by_len = sorted(cand, key=lambda g: -g.count(' '))
longer_index = collections.defaultdict(list)
for g in by_len:
    if g.count(' ') >= 1:
        toks = g.split()
        for n in range(1, len(toks)):
            for i in range(len(toks) - n + 1):
                longer_index[' '.join(toks[i:i+n])].append(g)
drop = set()
for g, c in cand.items():
    for u in longer_index.get(g, []):
        if u in cand and cand[u] >= 0.8 * c: drop.add(g); break
vocab = sorted((g for g in cand if g not in drop), key=lambda g: -cand[g])[:4000]
tid = {g: i for i, g in enumerate(vocab)}
terms = [{'id': i, 'label': g, 'kind': 'term', 'df': cand[g]} for g, i in tid.items()]

# ASH taxonomy keywords as nodes (session-level, inherited by children)
kw_df = collections.Counter()
for it in items:
    for k in set(it.get('keywords') or []): kw_df[k] += 1
for k, c in kw_df.most_common():
    if c >= 3:
        i = len(terms); terms.append({'id': i, 'label': k, 'kind': 'taxonomy', 'df': c}); tid['\x00' + k] = i

item_terms = {}
for it in items:
    t_ids = sorted({tid[g] for g in doc_title[it['id']] if g in tid})
    b_ids = {tid[g] for g in doc_body[it['id']] if g in tid} | {tid['\x00' + k] for k in set(it.get('keywords') or []) if '\x00' + k in tid}
    b_ids = sorted(b_ids - set(t_ids))
    item_terms[it['id']] = [t_ids, b_ids]

# co-occurrence edges (over items), normalized PMI
tf = collections.Counter(); co = collections.Counter()
for it in items:
    ts = item_terms[it['id']][0] + item_terms[it['id']][1]
    if len(ts) > 80: ts = sorted(ts, key=lambda i: terms[i]['df'])[:80]   # cap very long docs to their rarer terms
    for i in ts: tf[i] += 1
    for a, b in itertools.combinations(sorted(ts), 2): co[(a, b)] += 1
edges_by = collections.defaultdict(list)
for (a, b), c in co.items():
    if c < 4: continue
    pab = c / N; pa = tf[a] / N; pb = tf[b] / N
    pmi = math.log(pab / (pa * pb)); npmi = pmi / (-math.log(pab))
    if npmi < 0.12: continue
    w = round(npmi * min(1.0, math.log(1 + c) / math.log(40)), 3)
    edges_by[a].append((w, b, c)); edges_by[b].append((w, a, c))
keep = set()
for a, lst in edges_by.items():
    lst.sort(reverse=True)
    for w, b, c in lst[:15]: keep.add((min(a, b), max(a, b)))
edges = [[a, b, round(max(x[0] for x in edges_by[a] if x[1] == b), 3)] for a, b in sorted(keep)]

os.makedirs(os.path.join(DEST, 'data'), exist_ok=True)
graph = {'terms': terms, 'items': item_terms, 'edges': edges, 'n_items': N}
with open(os.path.join(DEST, 'data', 'graph.js'), 'w', encoding='utf-8') as f:
    f.write('window.ASH_GRAPH=' + json.dumps(graph, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(f'items {N}, vocab terms {len(vocab)} (+{len(terms)-len(vocab)} taxonomy), edges {len(edges)}, avg terms/item {sum(len(a)+len(b) for a,b in item_terms.values())/N:.1f}')
print('top terms:', [t['label'] for t in terms[:40]])
nb = collections.defaultdict(list)
for a, b, w in edges: nb[a].append((w, b)); nb[b].append((w, a))
for q in ['gvhd', 'car-t', 'flow cytometry', 'immune reconstitution', 'allogeneic', 'machine learning', 'treg', 'sickle cell disease', 'mrd']:
    if q in tid:
        i = tid[q]; print(f'\n{q} (df {terms[i]["df"]}):', [(terms[b]['label'], w) for w, b in sorted(nb[i], reverse=True)[:12]])
    else: print(f'\n{q}: not in vocab')
