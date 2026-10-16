# -*- coding: utf-8 -*-
"""10-14 蹲日：做组记录 vs 当日 PR 最大值 全量对撞"""
import requests

INFLUX = "http://127.0.0.1:8086"
ORG, TOKEN = "training-org", "training-super-secret-token-2026"
DAY = "2026-10-14"


def flux(q):
    r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode("utf-8"),
                      headers={"Authorization": f"Token {TOKEN}",
                               "Content-Type": "application/vnd.flux",
                               "Accept": "application/csv"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse_csv(txt):
    header, rows = None, []
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


# 当日 PR（每动作每重量最大次数）
q_pr = f"""
from(bucket:"training")
  |> range(start: {DAY}T00:00:00Z, stop: {DAY}T23:59:59Z)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> filter(fn: (r) => r._field == "weight_kg" or r._field == "max_reps")
  |> drop(columns: ["weight_kg"])
  |> pivot(rowKey:["_time","exercise","set_index","session_id"], columnKey:["_field"], valueColumn:"_value")
  |> group()
  |> keep(columns:["_time","exercise","weight_kg","max_reps"])
  |> sort(columns:["_time"])
"""
pr_rows = parse_csv(flux(q_pr))
pr_max = {}   # (exercise, weight) -> (max_reps, _time)
for r in pr_rows:
    k = (r["exercise"], float(r["weight_kg"]))
    v = int(r["max_reps"])
    if k not in pr_max or v > pr_max[k][0]:
        pr_max[k] = (v, r["_time"])

print(f"=== 当日 PR 档位数: {len(pr_max)} ===")

# 当日做组
q_wo = f"""
from(bucket:"training")
  |> range(start: {DAY}T00:00:00Z, stop: {DAY}T23:59:59Z)
  |> filter(fn: (r) => r._measurement =~ /^ppl_squat_/)
  |> filter(fn: (r) => r.source == "phone")
  |> filter(fn: (r) => r._field == "weight_kg" or r._field == "reps")
  |> drop(columns: ["weight_kg"])
  |> pivot(rowKey:["_time","_measurement","exercise","set_index","session_id"], columnKey:["_field"], valueColumn:"_value")
  |> group()
  |> keep(columns:["_time","_measurement","exercise","weight_kg","reps","set_index","session_id"])
  |> sort(columns:["_time"])
"""
wo = parse_csv(flux(q_wo))
print(f"=== 当日做组记录数: {len(wo)} ===\n")

cur = None
bad = []
for r in wo:
    key = (r["exercise"], r["_time"][:19])
    if key != cur:
        cur = key
        print(f"[{key[1]}] {key[0]}  (measurement={r['_measurement']}, session={r['session_id']})")
    w, reps = float(r["weight_kg"]), int(r["reps"])
    pm = pr_max.get((r["exercise"], w))
    flag = ""
    if pm and reps > pm[0]:
        flag = f"  <<< 矛盾：PR 最大 {pm[0]} 次"
        bad.append(r)
    print(f"   set{r.get('set_index','?')}: {w:g}kg x {reps}{flag}")

print(f"\n=== 矛盾记录合计: {len(bad)} 条 ===")
for r in bad:
    pm = pr_max[(r["exercise"], float(r["weight_kg"]))]
    print(f"  {r['exercise']} {float(r['weight_kg']):g}kg x {r['reps']} -> 应为 <= {pm[0]}"
          f"  (_time={r['_time']}, session={r['session_id']}, set={r.get('set_index')})")
