# -*- coding: utf-8 -*-
"""查询最近 PR 测试全档位 + 最近做组记录（供处方重算）"""
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


# ① PR 全档位（最近 60 天）
q_pr = """
from(bucket:"training")
  |> range(start: -60d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> filter(fn: (r) => r._field == "weight_kg" or r._field == "max_reps")
  |> drop(columns: ["weight_kg"])
  |> pivot(rowKey:["_time","exercise","set_index","session_id"], columnKey:["_field"], valueColumn:"_value")
  |> group()
  |> keep(columns:["_time","direction","exercise","weight_kg","max_reps","source"])
  |> sort(columns:["_time"])
"""
pr_rows = parse_csv(flux(q_pr))
print("=== PR 测试记录（最近 60 天）===")
cur = None
for r in pr_rows:
    key = (r["direction"], r["exercise"], r["_time"][:10])
    if key != cur:
        cur = key
        print(f"\n[{key[2]}] {key[0]} / {key[1]} (session {r.get('session_id','')})")
    print(f"   {r['weight_kg']}kg x {r['max_reps']}")

if not pr_rows:
    print("  (无记录)")

# ② 最近做组记录（手机来源，最近 21 天）
q_work = """
from(bucket:"training")
  |> range(start: -21d)
  |> filter(fn: (r) => r._measurement =~ /^ppl_(push|pull|squat)_/)
  |> filter(fn: (r) => r.source == "phone")
  |> filter(fn: (r) => r._field == "weight_kg" or r._field == "reps")
  |> drop(columns: ["weight_kg"])
  |> pivot(rowKey:["_time","_measurement","exercise","set_index","session_id"], columnKey:["_field"], valueColumn:"_value")
  |> group()
  |> keep(columns:["_time","direction","exercise","weight_kg","reps"])
  |> sort(columns:["_time"])
"""
work_rows = parse_csv(flux(q_work))
print("\n\n=== 做组记录（最近 21 天, source=phone）===")
cur = None
for r in work_rows:
    key = (r["direction"], r["exercise"], r["_time"][:10])
    if key != cur:
        cur = key
        print(f"\n[{key[2]}] {key[0]} / {key[1]} (session {r.get('session_id','')})")
    print(f"   {r['weight_kg']}kg x {r['reps']}")

if not work_rows:
    print("  (无记录)")
