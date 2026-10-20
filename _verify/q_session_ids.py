import requests, collections, datetime, sys

TOKEN = "training-super-secret-token-2026"
ORG = "training-org"
URL = "http://127.0.0.1:8086/api/v2/query"

def flux(q):
    r = requests.post(URL, params={"org": ORG}, headers={
        "Authorization": f"Token {TOKEN}",
        "Accept": "application/csv",
        "Content-Type": "application/vnd.flux",
    }, data=q.encode("utf-8"), timeout=90)
    if r.status_code >= 300:
        print("ERR", r.status_code, r.text[:400]); sys.exit(1)
    lines = [l for l in r.text.split("\r\n") if l and not l.startswith("#")]
    if len(lines) < 2:
        return []
    hdr = lines[0].split(",")
    return [dict(zip(hdr, l.split(","))) for l in lines[1:]]

def bj(ts):
    t = datetime.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
    return (t + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")

print("=== session_id × 日期（做组记录，reps 行）===")
rows = flux('''
from(bucket: "training")
  |> range(start: -70d)
  |> filter(fn: (r) => r._measurement =~ /^ppl_(push|pull|squat)_/ and r._field == "reps")
  |> keep(columns: ["_time","session_id","_measurement","set_index"])
''')
agg = collections.defaultdict(lambda: {"t": "", "sets": 0, "meas": set()})
for r in rows:
    sid = r["session_id"]
    agg[sid]["t"] = r["_time"]
    agg[sid]["sets"] += 1
    agg[sid]["meas"].add(r["_measurement"])
for sid, v in sorted(agg.items(), key=lambda kv: kv[1]["t"]):
    print(f"{bj(v['t'])}  {sid:<18} sets={v['sets']:<3} acts={len(v['meas'])}")

print("\n=== PR 测试 ppl_pr_test ===")
for r in flux('''
from(bucket: "training")
  |> range(start: -70d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> sort(columns:["_time"])
'''):
    print(f"{bj(r['_time'])}  {r['_field']:<12} {r['_value']:<8} ex={r.get('exercise','')} sid={r.get('session_id','')}")

print("\n=== 时长 ppl_duration_min ===")
for r in flux('''
from(bucket: "training")
  |> range(start: -70d)
  |> filter(fn: (r) => r._measurement == "ppl_duration_min")
  |> sort(columns:["_time"])
'''):
    print(f"{bj(r['_time'])}  {r['_value']} min  sid={r.get('session_id','')}")
