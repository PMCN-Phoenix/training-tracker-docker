# -*- coding: utf-8 -*-
"""核查 10 月 PR 数据完整性：10-09（s1791539043000）/ 10-11 / 10-14 各 session 档位数"""
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


# ① 按 session_id 精查 10-09
q = """
from(bucket:"training")
  |> range(start: 2026-10-01T00:00:00Z, stop: 2026-10-16T23:59:59Z)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> group()
  |> keep(columns:["_time","exercise","weight_kg","max_reps","session_id","set_index","source"])
  |> sort(columns:["_time"])
"""
rows = parse_csv(flux(q))
print(f"10 月 ppl_pr_test 总点数（每档 2 个 field 点）: {len(rows)}")

by_session = {}
for r in rows:
    k = (r["_time"][:10], r.get("session_id", "?"), r["exercise"])
    if k not in by_session:
        by_session[k] = set()
    if r["_field"] == "weight_kg" if "_field" in r else False:
        pass
    by_session[k].add((r.get("weight_kg"), r.get("max_reps")))

print("\n=== 10 月 PR 各 session 明细 ===")
for (day, sid, ex) in sorted(by_session):
    pairs = by_session[(day, sid, ex)]
    print(f"[{day}] session={sid} {ex}: {len(pairs)} 档")
    if day == "2026-10-09" or sid == "s1791539043000":
        print("   ", sorted(pairs))
