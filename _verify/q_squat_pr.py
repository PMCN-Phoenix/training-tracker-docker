# -*- coding: utf-8 -*-
"""蹲日 PR 宽窗口查询（-120d，覆盖 08-12 旧轮）"""
import requests

INFLUX = "http://127.0.0.1:8086"
ORG, TOKEN = "training-org", "training-super-secret-token-2026"


def flux(q):
    r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode("utf-8"),
                      headers={"Authorization": f"Token {TOKEN}",
                               "Content-Type": "application/vnd.flux",
                               "Accept": "application/csv"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse_csv(txt):
    header = None
    rows = []
    for ln in txt.strip().splitlines():
        ln = ln.replace("\r", "")
        if ln.startswith("#") or not ln.strip():
            continue
        if ln.startswith(",result"):
            header = ln.split(",")
            continue
        if header:
            row = ln.split(",")
            if len(row) == len(header):
                rows.append(dict(zip(header, row)))
    return rows


q = """
from(bucket:"training")
  |> range(start: -120d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> filter(fn: (r) => r.direction == "squat")
  |> filter(fn: (r) => r._field == "weight_kg" or r._field == "max_reps")
  |> drop(columns: ["weight_kg"])
  |> pivot(rowKey:["_time","exercise","set_index","session_id"], columnKey:["_field"], valueColumn:"_value")
  |> group()
  |> keep(columns:["_time","exercise","weight_kg","max_reps"])
  |> sort(columns:["_time"])
"""
rows = parse_csv(flux(q))
print("=== 蹲日 PR（-120d）===")
cur = None
for r in rows:
    k = (r["exercise"], r["_time"][:10])
    if k != cur:
        cur = k
        print(f"\n[{k[1]}] {k[0]}")
    print(f"   {r['weight_kg']}kg x {r['max_reps']}")
if not rows:
    print("  (无记录)")
