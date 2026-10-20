# -*- coding: utf-8 -*-
"""查近 14 天晨脉"""
import datetime

import requests

INFLUX = "http://127.0.0.1:8086"
ORG = "training-org"
TOKEN = "training-super-secret-token-2026"


def to_bj(ts):
    """InfluxDB 返回 UTC（Z），转北京时间，避免日期看错一天。"""
    t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (t + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


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
        print(to_bj(row["_time"]), "| bpm =", row["_value"], "| sid =", row.get("session_id", ""))
