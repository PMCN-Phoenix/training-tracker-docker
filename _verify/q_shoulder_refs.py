# -*- coding: utf-8 -*-
"""查感悟记录中肩部相关条目"""
import requests

INFLUX = "http://127.0.0.1:8086"
ORG = "training-org"
TOKEN = "training-super-secret-token-2026"

q = '''from(bucket:"training")
  |> range(start: 2026-07-01T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "ppl_reflection" and r._field == "content")
  |> keep(columns: ["_time", "_value", "exercise", "direction"])
  |> sort(columns: ["_time"])'''
r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode(),
                  headers={"Authorization": f"Token {TOKEN}",
                           "Content-Type": "application/vnd.flux",
                           "Accept": "application/csv"}, timeout=30)
r.raise_for_status()
header = None
for ln in r.text.splitlines():
    ln = ln.replace("\r", "")
    if ln.startswith("#") or not ln.strip():
        continue
    parts = ln.split(",")
    if ln.startswith(",result"):
        header = parts
        continue
    if header and len(parts) == len(header):
        row = dict(zip(header, parts))
        v = row.get("_value", "")
        if "肩" in v or "斜方" in v or "背阔" in v:
            print(row["_time"][:10], row.get("exercise", "-"), "|", v)
