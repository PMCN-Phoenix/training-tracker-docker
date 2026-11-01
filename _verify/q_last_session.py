# -*- coding: utf-8 -*-
"""查询最近一次训练的完整录入明细（默认查 10-29 蹲日）"""
import requests

s = requests.Session()
s.trust_env = False

q = '''from(bucket: "training")
  |> range(start: 2026-10-29T00:00:00+08:00, stop: 2026-10-30T00:00:00+08:00)
  |> filter(fn: (r) => r._measurement =~ /ppl_/ and (r._field == "reps" or r._field == "weight_kg" or r._field == "reflection"))
  |> pivot(rowKey: ["_time", "_measurement", "set_index"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "_measurement", "set_index", "reps", "weight_kg", "reflection"])
  |> sort(columns: ["_time"])'''

r = s.post(
    "http://127.0.0.1:8086/api/v2/query?org=training-org",
    headers={
        "Authorization": "Token training-super-secret-token-2026",
        "Accept": "application/csv",
        "Content-Type": "application/vnd.flux",
    },
    data=q.encode("utf-8"),
    timeout=30,
)
r.raise_for_status()

rows = []
cols = None
for line in r.text.splitlines():
    if line.startswith("#") or not line.strip():
        continue
    vals = line.split(",")
    if cols is None:
        cols = vals
        continue
    rec = dict(zip(cols, vals))
    rows.append(rec)

cur = None
for rec in rows:
    m = rec["_measurement"]
    if m != cur:
        cur = m
        print("==", m)
    si = rec.get("set_index", "?")
    w = rec.get("weight_kg", "")
    rp = rec.get("reps", "")
    ref = rec.get("reflection", "")
    line = f"  第{si}组: {w}kg x {rp}"
    if ref:
        line += f"  ｜笔记: {ref}"
    print(line)
print(f"\n共 {len(rows)} 组记录")
