# -*- coding: utf-8 -*-
"""查询用户所有弯举类动作的历史重量记录（EZ杆 / 哑铃 / 杠铃），并计算口径换算"""
import requests, collections, sys, re

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
        print("ERR", r.status_code, r.text[:500]); sys.exit(1)
    lines = [l for l in r.text.split("\r\n") if l and not l.startswith("#")]
    if len(lines) < 2:
        return []
    hdr = lines[0].split(",")
    return [dict(zip(hdr, l.split(","))) for l in lines[1:]]

# 1) 所有 measurement
Q1 = '''
import "influxdata/influxdb/schema"
schema.measurements(bucket: "training")
'''
rows = flux(Q1)
ms = sorted({r.get("_value", "") for r in rows if r.get("_value")})
print("=== measurements (%d) ===" % len(ms))
for m in ms:
    print("  ", m)

# 2) 所有做组记录里含 exercise 标签的，找弯举
Q2 = '''
from(bucket: "training")
  |> range(start: -400d)
  |> filter(fn: (r) => r._measurement =~ /^ppl_(push|pull|squat)_/)
  |> keep(columns: ["_time","_field","_value","_measurement","session_id","set_index","exercise","direction"])
  |> sort(columns:["_time"])
'''
rows = flux(Q2)
print("\n=== 做组记录行数: %d ===" % len(rows))

cells = collections.defaultdict(dict)
meta = {}
for r in rows:
    key = (r["session_id"], r["_measurement"], r["set_index"])
    cells[key][r["_field"]] = r["_value"]
    meta[r["session_id"]] = (r["_time"], r.get("direction", ""))

# 按 measurement 汇总
agg = collections.defaultdict(list)   # measurement -> [(ts, weight, reps)]
for (sid, meas, si), f in cells.items():
    ts = meta[sid][0]
    w = float(f.get("weight_kg", 0) or 0)
    rp = float(f.get("reps", 0) or 0)
    agg[meas].append((ts, w, rp))

print("\n=== 每个动作的重量/次数分布 ===")
for meas, lst in sorted(agg.items()):
    ws = sorted({w for _, w, _ in lst})
    print(f"\n## {meas}  ({len(lst)} 组)")
    print("   重量档位:", ", ".join(f"{w:g}" for w in ws))
    # 最佳组（重量×次数）
    best = sorted(lst, key=lambda x: -(x[1] * x[2]))[:6]
    print("   最高容量组:")
    for ts, w, rp in best:
        print(f"     {ts[:10]}  {w:g}kg x {rp:g}  = {w*rp:g}")
