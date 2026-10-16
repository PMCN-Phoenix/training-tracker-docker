# -*- coding: utf-8 -*-
"""核实 10-09 推日 PR 是否真的入库：按日期+session 两个维度查"""
import requests

INFLUX = "http://127.0.0.1:8086"
ORG, TOKEN = "training-org", "training-super-secret-token-2026"


def flux(q):
    r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode("utf-8"),
                      headers={"Authorization": f"Token {TOKEN}",
                               "Content-Type": "application/vnd.flux",
                               "Accept": "application/csv"}, timeout=30)
    if r.status_code != 200:
        return f"HTTP {r.status_code}: {r.text[:200]}"
    return r.text


def parse_csv(txt):
    header = None
    rows = []
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


print("=== ① 10-08~10-10 全部 measurement 的数据点 ===")
q1 = """
from(bucket:"training")
  |> range(start: 2026-10-08T00:00:00Z, stop: 2026-10-11T00:00:00Z)
  |> filter(fn: (r) => r._field == "weight_kg" or r._field == "max_reps" or r._field == "reps")
  |> group(columns: ["_measurement", "_field"])
  |> count()
"""
print(flux(q1))

print("\n=== ② 按 session_id s1791539043000 查 ===")
q2 = """
from(bucket:"training")
  |> range(start: -60d)
  |> filter(fn: (r) => r.session_id == "s1791539043000")
  |> group(columns: ["_measurement", "_field"])
  |> count()
"""
print(flux(q2))

print("\n=== ③ 全部 measurement 清单（-60d）===")
q3 = """
from(bucket:"training")
  |> range(start: -60d)
  |> keys(columns: ["_measurement"])
"""
print(flux(q3)[:800])
