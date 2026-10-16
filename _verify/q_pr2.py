# -*- coding: utf-8 -*-
"""补充查询：推日 PR 宽窗口 + 全部做组 60 天"""
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


print("=== ① 推日 PR（-120 天宽窗口）===")
q = """
from(bucket:"training")
  |> range(start: -120d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> filter(fn: (r) => r.direction == "push")
  |> filter(fn: (r) => r._field == "weight_kg" or r._field == "max_reps")
  |> drop(columns: ["weight_kg"])
  |> pivot(rowKey:["_time","exercise","set_index","session_id"], columnKey:["_field"], valueColumn:"_value")
  |> group()
  |> keep(columns:["_time","exercise","weight_kg","max_reps"])
  |> sort(columns:["_time"])
"""
rows = parse_csv(flux(q))
cur = None
for r in rows:
    key = (r["exercise"], r["_time"][:10])
    if key != cur:
        cur = key
        print(f"\n[{key[1]}] {key[0]}")
    print(f"   {r['weight_kg']}kg x {r['max_reps']}")
if not rows:
    print("  (无记录)")

print("\n\n=== ② 全部做组（-60 天, phone）===")
q2 = """
from(bucket:"training")
  |> range(start: -60d)
  |> filter(fn: (r) => r._measurement =~ /^ppl_(push|pull|squat)_/)
  |> filter(fn: (r) => r.source == "phone")
  |> filter(fn: (r) => r._field == "weight_kg" or r._field == "reps")
  |> drop(columns: ["weight_kg"])
  |> pivot(rowKey:["_time","_measurement","exercise","set_index","session_id"], columnKey:["_field"], valueColumn:"_value")
  |> group()
  |> keep(columns:["_time","direction","exercise","weight_kg","reps"])
  |> sort(columns:["_time"])
"""
rows2 = parse_csv(flux(q2))
cur = None
for r in rows2:
    key = (r["direction"], r["exercise"], r["_time"][:10])
    if key != cur:
        cur = key
        print(f"\n[{key[2]}] {key[0]} / {key[1]}")
    print(f"   {r['weight_kg']}kg x {r['reps']}")
if not rows2:
    print("  (无记录)")
