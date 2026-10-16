# -*- coding: utf-8 -*-
"""验证 10-16 推日容量做组落库"""
import requests

INFLUX = "http://127.0.0.1:8086"
ORG = "training-org"
TOKEN = "training-super-secret-token-2026"

q = '''from(bucket:"training")
  |> range(start: 2026-10-15T00:00:00Z, stop: 2026-10-17T00:00:00Z)
  |> filter(fn: (r) => r._measurement =~ /ppl_push_/ and (r._field == "reps" or r._field == "weight_kg"))
  |> pivot(rowKey: ["_time", "_measurement", "exercise", "set_index", "session_id"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "_measurement", "exercise", "weight_kg", "reps", "set_index", "session_id"])
  |> sort(columns: ["_time", "_measurement", "set_index"])'''
r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode(),
                  headers={"Authorization": f"Token {TOKEN}",
                           "Content-Type": "application/vnd.flux",
                           "Accept": "application/csv"}, timeout=20)
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
        print(row["_time"][:16], row["exercise"], row["weight_kg"] + "kg x" + row["reps"], "set" + row["set_index"], row["session_id"])
