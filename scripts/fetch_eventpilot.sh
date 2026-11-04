#!/bin/zsh
# Download the ASH 2026 EventPilot agenda + speakers tables (public, no login) into <out_dir>.
set -e
OUT="${1:-eventpilot}"; mkdir -p "$OUT"; cd "$OUT"
API="https://eppro02.ativ.me/web/api.php"
rm -f cj.txt
curl -s -c cj.txt -b cj.txt "https://eppro02.ativ.me/web/page.php?page=Sessions&project=ASH26" -o /dev/null   # sets the project in the PHP session
for tbl in agenda speakers; do
  off=0
  while :; do
    curl -s -b cj.txt -c cj.txt -X POST "$API" --data-urlencode "interface=webfilter" --data-urlencode "action=getlist" \
      --data-urlencode "confid=ASH26" --data-urlencode "table=$tbl" --data-urlencode 'filters=[]' --data-urlencode "order=" \
      --data-urlencode "offset=$off" --data-urlencode "limit=5000" --data-urlencode "adapter=" -o "${tbl}_${off}.xml"
    n=$(python3 -I -c "import re,html,json,sys; t=open('${tbl}_${off}.xml',encoding='utf-8').read(); m=re.search(r'<Item([^>]*)>(.*)</Item>',t,re.S); print(len(json.loads(html.unescape(m.group(2)))['data']))")
    echo "$tbl offset $off: $n rows"
    [ "$n" -lt 5000 ] && break
    off=$((off+5000))
  done
done
python3 -I - <<'PY'
import re,html,json,glob
rows=[]
for f in sorted(glob.glob('agenda_*.xml'), key=lambda x:int(re.search(r'_(\d+)',x).group(1))):
    t=open(f,encoding='utf-8').read(); m=re.search(r'<Item([^>]*)>(.*)</Item>',t,re.S); rows+=json.loads(html.unescape(m.group(2)))['data']
json.dump(rows,open('agenda_raw.json','w'),ensure_ascii=False); print('agenda_raw.json:',len(rows),'rows')
PY
