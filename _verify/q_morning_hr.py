# -*- coding: utf-8 -*-
"""查近 14 天晨脉，验证 10-16 录入"""
import requests

INFLUX = "http://127.0.0.1:8086"
ORG = "training-org"
TOKEN = "training-super-secret-token-2026"

q = 'from(bucket:"training")\n  |> range(start: -14d)\n  |> filter(fn: (r) => r._measurement == "ppl_morning_hr")\n  |> keep(columns:["_time", "_value", "session_id", "source"])\n  |> sort(columns:["_time"])'
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
        print(row["_time"][:16], "| bpm =", row["_value"], "| sid =", row.get("session_id", ""))
