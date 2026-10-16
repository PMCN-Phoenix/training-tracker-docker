# -*- coding: utf-8 -*-
"""查看 10-14 做组 4 个矛盾点的完整原始数据（所有字段/标签/所有 source）"""
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


q = f"""
from(bucket:"training")
  |> range(start: {DAY}T00:00:00Z, stop: {DAY}T23:59:59Z)
  |> filter(fn: (r) => r._measurement =~ /^ppl_squat_/)
  |> group()
  |> sort(columns:["_time"])
"""
rows = parse_csv(flux(q))
print(f"当日 squat 系 measurement 全部数据点: {len(rows)} 个（含 PR 与做组、所有 source）\n")
cur = None
for r in rows:
    key = (r["_measurement"], r["_time"], r.get("session_id", ""))
    if key != cur:
        cur = key
        print(f"\n[{r['_time']}] {r['_measurement']} session={r.get('session_id')}")
    print(f"   {r.get('exercise','?'):10s} field={r['_field']:12s} value={r['_value']}"
          f"  tags: set_index={r.get('set_index')} source={r.get('source')} direction={r.get('direction')}")
