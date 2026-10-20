import requests, json, collections, sys, datetime

TOKEN = "training-super-secret-token-2026"
ORG = "training-org"
URL = "http://127.0.0.1:8086/api/v2/query"

def flux(q):
    r = requests.post(URL, params={"org": ORG}, headers={
        "Authorization": f"Token {TOKEN}",
        "Accept": "application/csv",
        "Content-Type": "application/vnd.flux",
    }, data=q.encode("utf-8"), timeout=60)
    if r.status_code >= 300:
        print("ERR", r.status_code, r.text[:400]); sys.exit(1)
    lines = [l for l in r.text.split("\r\n") if l and not l.startswith("#")]
    if len(lines) < 2:
        return []
    hdr = lines[0].split(",")
    return [dict(zip(hdr, l.split(","))) for l in lines[1:]]

# 原始行样例
q = '''
from(bucket: "training")
  |> range(start: -45d)
  |> filter(fn: (r) => r._measurement =~ /^ppl_(push|pull|squat)_/)
  |> limit(n: 6)
'''
rows = flux(q)
print("=== SAMPLE ROWS ===")
for r in rows:
    print(json.dumps(r, ensure_ascii=False)[:400])
print("\n=== KEYS ===", list(rows[0].keys()) if rows else None)

# 统计每个 measurement 的字段
q2 = '''
from(bucket: "training")
  |> range(start: -45d)
  |> filter(fn: (r) => r._measurement =~ /^ppl_(push|pull|squat)_/)
  |> keep(columns: ["_measurement","_field"])
  |> group(columns: ["_measurement","_field"])
  |> count()
'''
rows2 = flux(q2)
print("\n=== FIELDS ===")
for r in rows2:
    print(r["_measurement"], "|", r["_field"], "|", r["_value"])
