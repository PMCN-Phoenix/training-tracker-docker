# -*- coding: utf-8 -*-
"""推日历史做组全量画像：各 session 日期/动作/组序列 + 训练时长 + 当日晨脉"""
import requests
from collections import defaultdict

INFLUX = "http://127.0.0.1:8086"
ORG = "training-org"
TOKEN = "training-super-secret-token-2026"

def flux(q):
    r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode(),
                      headers={"Authorization": f"Token {TOKEN}",
                               "Content-Type": "application/vnd.flux",
                               "Accept": "application/csv"}, timeout=30)
    r.raise_for_status()
    header = None
    rows = []
    for ln in r.text.splitlines():
        ln = ln.replace("\r", "")
        if ln.startswith("#") or not ln.strip():
            continue
        parts = ln.split(",")
        if ln.startswith(",result"):
            header = parts
            continue
        if header and len(parts) == len(header):
            rows.append(dict(zip(header, parts)))
    return rows

# 1) 推日全部做组（含今天）
q1 = '''from(bucket:"training")
  |> range(start: 2026-08-01T00:00:00Z)
  |> filter(fn: (r) => r._measurement =~ /ppl_push_/ and (r._field == "reps" or r._field == "weight_kg"))
  |> pivot(rowKey: ["_time", "_measurement", "exercise", "set_index", "session_id"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "exercise", "weight_kg", "reps", "set_index", "session_id"])
  |> sort(columns: ["_time", "exercise", "set_index"])'''
sets = flux(q1)

sessions = defaultdict(list)
for r in sets:
    sessions[(r["session_id"], r["_time"][:16])].append(
        (r["exercise"], float(r["weight_kg"]), int(r["reps"]), int(r["set_index"])))

print("=== 推日做组 session 明细 ===")
for (sid, t), lst in sorted(sessions.items(), key=lambda kv: kv[0][1]):
    lst.sort(key=lambda x: (x[0], x[3]))
    print(f"\n[{t} UTC] {sid}")
    cur = None
    line = ""
    for ex, w, reps, si in lst:
        if ex != cur:
            if line: print("   " + line)
            cur = ex; line = f"{ex}: "
        line += f"{w:g}x{reps} "
    if line: print("   " + line)

# 2) 训练时长（推日）
q2 = '''from(bucket:"training")
  |> range(start: 2026-08-01T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "ppl_duration_min" and r.direction == "push")
  |> keep(columns: ["_time", "_value", "session_id"])
  |> sort(columns: ["_time"])'''
print("\n=== 推日训练时长 ===")
for r in flux(q2):
    print(r["_time"][:16], r["_value"] + " min", r.get("session_id", ""))

# 3) 晨脉（近 30 天，判断训练日状态）
q3 = '''from(bucket:"training")
  |> range(start: 2026-09-20T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "ppl_morning_hr")
  |> keep(columns: ["_time", "_value"])
  |> sort(columns: ["_time"])'''
print("\n=== 晨脉（09-20 起）===")
for r in flux(q3):
    print(r["_time"][:16], r["_value"])
