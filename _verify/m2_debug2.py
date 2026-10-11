# -*- coding: utf-8 -*-
"""深挖 PR weight_kg 与 tags 读取：直接跑 repo 相同 Flux 看 CSV"""
import requests, json, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
INFLUX = "http://127.0.0.1:8086"
ORG, BUCKET, TOKEN = "training-org", "training", "training-super-secret-token-2026"

def flux(q):
    r = requests.post(f"{INFLUX}/api/v2/query?org={ORG}", data=q.encode("utf-8"),
                      headers={"Authorization": f"Token {TOKEN}", "Content-Type": "application/vnd.flux",
                               "Accept": "application/csv"}, timeout=30)
    r.raise_for_status()
    return r.text

def show(txt, n=12):
    for ln in txt.strip().splitlines()[:n]:
        print("  ", repr(ln[:160]))

print("=== A) get_pr_tests 的查询（keep + sort，无 pivot）===")
q = f'''from(bucket:"{BUCKET}") |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> keep(columns: ["_time", "session_id", "exercise", "direction", "weight_kg", "_field", "_value"])
  |> sort(columns: ["_time"])'''
show(flux(q), 16)

print("=== B) 同查询 + pivot（对照）===")
q = f'''from(bucket:"{BUCKET}") |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_pr_test")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "session_id", "exercise", "direction", "weight_kg", "max_reps"])'''
show(flux(q), 10)

print("=== C) 感悟 GET 查询（pivot + keep tags）===")
q = f'''from(bucket:"{BUCKET}") |> range(start: -365d)
  |> filter(fn: (r) => r._measurement == "ppl_reflection")
  |> filter(fn: (r) => r.id == "ref_20261011_a5333476")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time", "id", "date", "direction", "exercise", "set_index", "session_id", "source", "content", "title", "tags"])
  |> limit(n: 1)'''
show(flux(q), 8)
